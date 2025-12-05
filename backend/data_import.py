"""
Data Import Module - Phase 2
Flexible CSV/Excel file parsing with support for various portfolio formats
Handles standard portfolios, brokerage exports, and custom formats
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
import io
import re


class DataImporter:
    """
    Handles flexible import of portfolio data from various sources
    Supports custom columns, auto-detection of formats, and data normalization
    """
    
    # Common column name mappings for different brokerages/formats
    COLUMN_MAPPINGS = {
        'ticker': ['symbol', 'ticker', 'stock', 'symbol name', 'security id', 'cusip'],
        'quantity': ['quantity', 'qty', 'shares', 'units', 'share count', 'num shares'],
        'price': ['price ($)', 'price', 'current price', 'market price', 'last price', 'close price', 'price per unit'],
        'value': ['value ($)', 'market value', 'total value', 'value', 'current value', 'position value', 'market val'],
        'cost_basis': ['principal ($)*', 'nfs cost ($)', 'cost basis', 'cost base', 'initial cost', 'purchase cost', 'basis', 'avg cost'],
        'gain_loss': ['principal g/l ($)*', 'nfs g/l ($)', 'gain/loss', 'gl', 'profit/loss', 'unrealized g/l', 'gain loss', 'pnl'],
        'gain_loss_pct': ['principal g/l (%)*', 'nfs g/l (%)', 'gain/loss %', 'gl %', 'return %', 'pnl %', 'unrealized %', 'gl%'],
        'dividend': ['est annual income ($)', 'dividend', 'annual dividend', 'dividend income', 'annual income', 'est income'],
        'yield': ['current yld/dist rate (%)', 'yield', 'yield %', 'dividend yield', 'yld', 'annual yield', 'yld %'],
        'description': ['description', 'name', 'company', 'security name', 'asset', 'asset name'],
        'date_purchased': ['initial purchase date', 'date purchased', 'purchase date', 'acquisition date', 'buy date', 'start date'],
        'account_type': ['account type', 'account', 'account class', 'type', 'category'],
        'asset_type': ['asset type', 'asset class', 'class', 'type'],
        'asset_category': ['asset category', 'category', 'sector', 'industry'],
        'daily_change_value': ['1-day value change ($)', 'daily change', 'day change $', 'change $'],
        'daily_change_pct': ['1-day price change (%)', 'daily change %', 'day change %', 'change %'],
        'allocation_pct': ['assets (%)', 'allocation', 'portfolio %', 'weight'],
        'dividend_instructions': ['dividend instructions', 'div instructions'],
        'cap_gain_instructions': ['cap gain instructions', 'cg instructions'],
        'est_tax_gl': ['est tax g/l ($)*', 'tax g/l', 'est tax gain/loss']
    }
    
    def __init__(self):
        self.detected_format = None
        self.auto_mapped_columns = {}
    
    def detect_format(self, df: pd.DataFrame) -> str:
        """Detect the format/source of portfolio data"""
        columns = [col.lower().strip() for col in df.columns]
        
        # Check for common broker signatures
        if any('schwab' in col or 'charles' in col for col in columns):
            return 'charles_schwab'
        if any('fidelity' in col for col in columns):
            return 'fidelity'
        if any('vanguard' in col for col in columns):
            return 'vanguard'
        if any('etrade' in col for col in columns):
            return 'etrade'
        if any('ibkr' in col or 'interactive broker' in col for col in columns):
            return 'interactive_brokers'
        
        # Check for standard format (most common)
        if self._has_standard_columns(columns):
            return 'standard'
        
        return 'generic'
    
    def _has_standard_columns(self, columns: List[str]) -> bool:
        """Check if dataframe has standard portfolio columns"""
        required_mappings = ['ticker', 'quantity', 'price', 'value']
        for req in required_mappings:
            if not any(col in columns for col in self.COLUMN_MAPPINGS[req]):
                return False
        return True
    
    def auto_map_columns(self, df: pd.DataFrame) -> Dict[str, str]:
        """
        Automatically map detected columns to standard names
        Returns mapping: {detected_col: standard_name}
        """
        mapping = {}
        df_columns_lower = {col.lower().strip(): col for col in df.columns}
        
        for standard_name, aliases in self.COLUMN_MAPPINGS.items():
            for alias in aliases:
                if alias in df_columns_lower:
                    detected_col = df_columns_lower[alias]
                    mapping[detected_col] = standard_name
                    break
        
        self.auto_mapped_columns = mapping
        return mapping
    
    def normalize_dataframe(self, df: pd.DataFrame, column_map: Optional[Dict[str, str]] = None) -> pd.DataFrame:
        """
        Normalize dataframe columns to standard names
        Apply data type conversions and cleaning
        """
        # Use provided mapping or auto-detect
        if column_map is None:
            column_map = self.auto_map_columns(df)
        
        # Rename columns
        df = df.rename(columns=column_map)
        
        # Clean ticker column if it exists
        if 'ticker' in df.columns:

            # Convert to string and strip whitespace
            df['ticker'] = df['ticker'].astype(str).str.strip()
            
            # Robustly filter out invalid values (case-insensitive)
            invalid_values = ['nan', 'none', 'null', '', 'nat', 'n/a', '#n/a', '#ref!', '#value!', '#div/0!', '#name?',
                              'total', 'grand total', 'symbol', 'ticker', 'description', 'quantity', 'price', 'value', 'assets', 'account']
            df = df[~df['ticker'].str.lower().isin(invalid_values)]

        
        # Convert numeric columns
        numeric_cols = ['quantity', 'price', 'value', 'cost_basis', 'gain_loss', 
                       'gain_loss_pct', 'dividend', 'yield', 'daily_change_value', 
                       'daily_change_pct', 'allocation_pct', 'est_tax_gl']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Convert date columns
        date_cols = ['date_purchased']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        return df
    
    def validate_data(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Validate imported data for completeness and integrity
        Returns: (is_valid, list_of_errors)
        """
        errors = []
        
        # Check required columns
        required = ['ticker', 'quantity', 'price']
        for col in required:
            if col not in df.columns:
                errors.append(f"Missing required column: {col}")
        
        # Check for duplicates
        if 'ticker' in df.columns:
            # Filter out 'nan' string just in case

            valid_tickers = df[~df['ticker'].astype(str).str.lower().isin(['nan', 'none', ''])]
            duplicates = valid_tickers[valid_tickers['ticker'].duplicated()]['ticker'].unique()
            
            if len(duplicates) > 0:

                # Ensure we stringify elements before joining (tickers may be numeric)
                dup_list = [str(d) for d in list(duplicates)]
                errors.append(f"Duplicate tickers found: {', '.join(dup_list)}")
        

        
        # Check for empty rows
        if len(df) == 0:
            errors.append("No data rows found in file")
        
        # Validate numeric columns have reasonable values
        if 'price' in df.columns and (df['price'] < 0).any():
            errors.append("Some prices are negative")
        
        return len(errors) == 0, errors
    
    def compute_missing_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute missing metrics from available data"""
        
        # Compute value if missing
        if 'value' not in df.columns or df['value'].isna().any():
            if 'quantity' in df.columns and 'price' in df.columns:
                df['value'] = df['quantity'] * df['price']
        
        # Compute cost basis if missing
        if 'cost_basis' not in df.columns or df['cost_basis'].isna().any():
            if 'value' in df.columns and 'gain_loss' in df.columns:
                df['cost_basis'] = df['value'] - df['gain_loss']
        
        # Compute gain/loss if missing
        if 'gain_loss' not in df.columns or df['gain_loss'].isna().any():
            if 'value' in df.columns and 'cost_basis' in df.columns:
                df['gain_loss'] = df['value'] - df['cost_basis']
        
        # Compute gain/loss % if missing
        if 'gain_loss_pct' not in df.columns or df['gain_loss_pct'].isna().any():
            if 'gain_loss' in df.columns and 'cost_basis' in df.columns:
                df['gain_loss_pct'] = np.where(
                    df['cost_basis'] != 0,
                    (df['gain_loss'] / df['cost_basis'] * 100),
                    0
                )
        
        # Compute yield if missing
        if 'yield' not in df.columns or df['yield'].isna().any():
            if 'dividend' in df.columns and 'value' in df.columns:
                df['yield'] = np.where(
                    df['value'] != 0,
                    (df['dividend'] / df['value'] * 100),
                    0
                )
        
        return df


class PortfolioImporter:
    """
    High-level interface for importing portfolio files
    Handles file parsing, validation, and conversion
    """
    
    def __init__(self):
        self.importer = DataImporter()
    
    def _find_header_row(self, df: pd.DataFrame) -> Optional[int]:
        """Find the index of the row that likely contains headers"""
        # Look for key columns
        key_cols = ['symbol', 'ticker', 'quantity', 'qty', 'price']
        
        # Check first 20 rows
        for idx in range(min(20, len(df))):
            row = df.iloc[idx]
            # Convert row to string and lower case
            row_str = [str(val).lower() for val in row.values]
            
            # Count matches
            matches = sum(1 for col in key_cols if any(col == str(val) or col in str(val) for val in row_str))
            
            # If we find at least 2 key columns, this is likely the header
            if matches >= 2:
                return idx
        return None

    def import_file(self, file_content: bytes, filename: str, 
                   column_map: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Import portfolio file and return normalized dataframe with metadata
        
        Returns:
        {
            'success': bool,
            'dataframe': pd.DataFrame,
            'metadata': {
                'filename': str,
                'format': str,
                'rows': int,
                'columns': list,
                'auto_mapped': dict,
                'detected_issues': list
            },
            'errors': list,
            'warnings': list
        }
        """
        result = {
            'success': False,
            'dataframe': None,
            'metadata': {},
            'errors': [],
            'warnings': []
        }
        
        try:
            # Parse file - read without header first to detect structure
            if filename.endswith('.csv'):
                df_raw = pd.read_csv(io.BytesIO(file_content), header=None)
            elif filename.endswith(('.xlsx', '.xls')):
                df_raw = pd.read_excel(io.BytesIO(file_content), header=None)
            else:
                result['errors'].append(f"Unsupported file format: {filename}")
                return result
            
            # Find header row
            header_idx = self._find_header_row(df_raw)
            
            if header_idx is not None:

                # Set columns from the found header row
                df_raw.columns = df_raw.iloc[header_idx].astype(str).tolist()
                # Slice dataframe to keep only rows after header
                df = df_raw.iloc[header_idx + 1:].copy()
                # Reset index
                df = df.reset_index(drop=True)
            else:

                # Assume first row is header (standard behavior)
                df_raw.columns = df_raw.iloc[0].astype(str).tolist()
                df = df_raw.iloc[1:].copy()
                df = df.reset_index(drop=True)
            
            # Detect format
            detected_format = self.importer.detect_format(df)
            result['metadata']['format'] = detected_format
            
            # Auto-map columns
            auto_mapping = self.importer.auto_map_columns(df)
            result['metadata']['auto_mapped'] = auto_mapping
            
            # Use provided mapping or auto-detected
            final_map = column_map if column_map else auto_mapping
            
            # Normalize dataframe
            df = self.importer.normalize_dataframe(df, final_map)
            
            # Validate data
            is_valid, validation_errors = self.importer.validate_data(df)
            if not is_valid:
                result['errors'].extend(validation_errors)
                # Don't return yet - try to continue with warnings
                result['warnings'].extend(validation_errors)
            
            # Compute missing metrics
            df = self.importer.compute_missing_metrics(df)
            
            # Enrich with computed percentages
            total_value = df['value'].sum()
            if total_value > 0:
                df['allocation_pct'] = (df['value'] / total_value * 100)
            else:
                df['allocation_pct'] = 0
            
            # Set metadata
            result['metadata']['filename'] = filename
            result['metadata']['rows'] = len(df)
            result['metadata']['columns'] = df.columns.tolist()
            result['metadata']['total_value'] = round(float(df['value'].sum()), 2)
            result['metadata']['num_holdings'] = len(df)
            result['metadata']['import_date'] = datetime.now().isoformat()
            
            result['dataframe'] = df
            result['success'] = len(result['errors']) == 0
            
        except Exception as e:
            result['errors'].append(f"File parsing error: {str(e)}")
        
        return result


def import_csv_file(file_content: bytes, filename: str) -> pd.DataFrame:
    """Simple CSV import function"""
    importer = PortfolioImporter()
    result = importer.import_file(file_content, filename)
    
    if not result['success']:
        raise ValueError(f"Import failed: {', '.join(result['errors'])}")
    
    return result['dataframe']


def import_excel_file(file_content: bytes, filename: str) -> pd.DataFrame:
    """Simple Excel import function"""
    importer = PortfolioImporter()
    result = importer.import_file(file_content, filename)
    
    if not result['success']:
        raise ValueError(f"Import failed: {', '.join(result['errors'])}")
    
    return result['dataframe']
