"""
Data Import Module - Enhanced
Flexible CSV/Excel file parsing with support for various portfolio formats.
Handles standard portfolios, brokerage exports, custom formats, and smart data cleaning.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple, Optional, Union
from datetime import datetime
import io
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ========================================
# CONSTANTS
# ========================================

# Invalid ticker values to filter out
INVALID_TICKER_VALUES = [
    'nan', 'none', 'null', '', 'nat', 'n/a', '#n/a', '#ref!', '#value!',
    '#div/0!', '#name?', '#num!', 'total', 'grand total', 'symbol', 'ticker',
    'description', 'quantity', 'price', 'value', 'assets', 'account',
    'cash', 'pending', 'subtotal', 'balance', 'summary'
]

# File size limits (10MB default)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes


# ========================================
# DATA IMPORTER
# ========================================

class DataImporter:
    """
    Handles flexible import of portfolio data from various sources.
    
    Features:
    - Auto-detection of file formats and brokerages
    - Flexible column mapping
    - Data normalization and cleaning
    - Validation and error reporting
    - Missing data computation
    """
    
    # Common column name mappings for different brokerages/formats
    COLUMN_MAPPINGS = {
        'ticker': [
            'symbol', 'ticker', 'stock', 'symbol name', 'security id',
            'cusip', 'isin', 'security', 'instrument'
        ],
        'quantity': [
            'quantity', 'qty', 'shares', 'units', 'share count',
            'num shares', 'number of shares', 'position'
        ],
        'price': [
            'price ($)', 'price', 'current price', 'market price',
            'last price', 'close price', 'price per unit', 'last',
            'market value per share', 'unit price'
        ],
        'value': [
            'value ($)', 'market value', 'total value', 'value',
            'current value', 'position value', 'market val',
            'total market value', 'mv'
        ],
        'cost_basis': [
            'principal ($)*', 'nfs cost ($)', 'cost basis', 'cost base',
            'initial cost', 'purchase cost', 'basis', 'avg cost',
            'average cost', 'book value', 'original cost'
        ],
        'gain_loss': [
            'principal g/l ($)*', 'nfs g/l ($)', 'gain/loss', 'gl',
            'profit/loss', 'unrealized g/l', 'gain loss', 'pnl',
            'unrealized gain/loss', 'gain/(loss)'
        ],
        'gain_loss_pct': [
            'principal g/l (%)*', 'nfs g/l (%)', 'gain/loss %', 'gl %',
            'return %', 'pnl %', 'unrealized %', 'gl%', '% gain/loss',
            'return', '% return'
        ],
        'dividend': [
            'est annual income ($)', 'dividend', 'annual dividend',
            'dividend income', 'annual income', 'est income',
            'estimated annual income', 'total dividend'
        ],
        'yield': [
            'current yld/dist rate (%)', 'yield', 'yield %',
            'dividend yield', 'yld', 'annual yield', 'yld %',
            'yield %', 'distribution rate'
        ],
        'description': [
            'description', 'name', 'company', 'security name',
            'asset', 'asset name', 'security description',
            'company name', 'full name'
        ],
        'date_purchased': [
            'initial purchase date', 'date purchased', 'purchase date',
            'acquisition date', 'buy date', 'start date', 'open date',
            'date acquired', 'date opened'
        ],
        'account_type': [
            'account type', 'account', 'account class', 'type',
            'category', 'account name'
        ],
        'asset_type': [
            'asset type', 'asset class', 'class', 'type',
            'security type', 'instrument type'
        ],
        'asset_category': [
            'asset category', 'category', 'sector', 'industry',
            'sub-category', 'classification'
        ],
        'daily_change_value': [
            '1-day value change ($)', 'daily change', 'day change $',
            'change $', 'today\'s gain/loss', 'day change',
            'todays change'
        ],
        'daily_change_pct': [
            '1-day price change (%)', 'daily change %', 'day change %',
            'change %', 'today\'s gain/loss %', '% change',
            'todays % change'
        ],
        'allocation_pct': [
            'assets (%)', 'allocation', 'portfolio %', 'weight',
            '% of portfolio', 'portfolio weight', '% allocation'
        ],
        'dividend_instructions': [
            'dividend instructions', 'div instructions',
            'dividend reinvestment', 'drip'
        ],
        'cap_gain_instructions': [
            'cap gain instructions', 'cg instructions',
            'capital gains instructions'
        ],
        'est_tax_gl': [
            'est tax g/l ($)*', 'tax g/l', 'est tax gain/loss',
            'estimated tax gain/loss', 'tax basis'
        ]
    }
    
    def __init__(self):
        """Initialize data importer"""
        self.detected_format = None
        self.auto_mapped_columns = {}
        logger.info("DataImporter initialized")
    
    def detect_format(self, df: pd.DataFrame) -> str:
        """
        Detect the format/source of portfolio data.
        
        Args:
            df: DataFrame to analyze
        
        Returns:
            Format identifier string
        """
        columns = [col.lower().strip() for col in df.columns]
        
        # Check for common broker signatures
        if any('schwab' in col or 'charles' in col for col in columns):
            logger.info("Detected format: Charles Schwab")
            return 'charles_schwab'
        
        if any('fidelity' in col for col in columns):
            logger.info("Detected format: Fidelity")
            return 'fidelity'
        
        if any('vanguard' in col for col in columns):
            logger.info("Detected format: Vanguard")
            return 'vanguard'
        
        if any('etrade' in col or 'e-trade' in col for col in columns):
            logger.info("Detected format: E*TRADE")
            return 'etrade'
        
        if any('ibkr' in col or 'interactive broker' in col for col in columns):
            logger.info("Detected format: Interactive Brokers")
            return 'interactive_brokers'
        
        if any('td ameritrade' in col or 'tda' in col for col in columns):
            logger.info("Detected format: TD Ameritrade")
            return 'td_ameritrade'
        
        if any('robinhood' in col for col in columns):
            logger.info("Detected format: Robinhood")
            return 'robinhood'
        
        # Check for standard format
        if self._has_standard_columns(columns):
            logger.info("Detected format: Standard")
            return 'standard'
        
        logger.info("Detected format: Generic")
        return 'generic'
    
    def _has_standard_columns(self, columns: List[str]) -> bool:
        """
        Check if dataframe has standard portfolio columns.
        
        Args:
            columns: List of column names (lowercase)
        
        Returns:
            True if has required columns
        """
        required_mappings = ['ticker', 'quantity', 'price', 'value']
        
        for req in required_mappings:
            if not any(col in columns for col in self.COLUMN_MAPPINGS[req]):
                return False
        
        return True
    
    def auto_map_columns(self, df: pd.DataFrame) -> Dict[str, str]:
        """
        Automatically map detected columns to standard names.
        
        Args:
            df: DataFrame to analyze
        
        Returns:
            Dictionary mapping {detected_col: standard_name}
        """
        mapping = {}
        df_columns_lower = {col.lower().strip(): col for col in df.columns}
        
        for standard_name, aliases in self.COLUMN_MAPPINGS.items():
            for alias in aliases:
                if alias in df_columns_lower:
                    detected_col = df_columns_lower[alias]
                    mapping[detected_col] = standard_name
                    logger.debug(f"Mapped column '{detected_col}' -> '{standard_name}'")
                    break
        
        self.auto_mapped_columns = mapping
        logger.info(f"Auto-mapped {len(mapping)} columns")
        
        return mapping
    
    def normalize_dataframe(
        self,
        df: pd.DataFrame,
        column_map: Optional[Dict[str, str]] = None
    ) -> pd.DataFrame:
        """
        Normalize dataframe columns to standard names and clean data.
        
        Args:
            df: DataFrame to normalize
            column_map: Optional custom column mapping
        
        Returns:
            Normalized DataFrame
        """
        # Use provided mapping or auto-detect
        if column_map is None:
            column_map = self.auto_map_columns(df)
        
        # Rename columns
        df = df.rename(columns=column_map)
        
        # Clean ticker column if it exists
        if 'ticker' in df.columns:
            # Convert to string and strip whitespace
            df['ticker'] = df['ticker'].astype(str).str.strip().str.upper()
            
            # Filter out invalid values (case-insensitive)
            df = df[~df['ticker'].str.lower().isin(INVALID_TICKER_VALUES)]
            
            # Remove rows where ticker is just whitespace
            df = df[df['ticker'].str.len() > 0]
            
            logger.info(f"Cleaned ticker column, {len(df)} valid rows remaining")
        
        # Convert numeric columns
        numeric_cols = [
            'quantity', 'price', 'value', 'cost_basis', 'gain_loss',
            'gain_loss_pct', 'dividend', 'yield', 'daily_change_value',
            'daily_change_pct', 'allocation_pct', 'est_tax_gl'
        ]
        
        for col in numeric_cols:
            if col in df.columns:
                # Remove currency symbols and commas
                if df[col].dtype == 'object':
                    df[col] = df[col].astype(str).str.replace('$', '', regex=False)
                    df[col] = df[col].str.replace(',', '', regex=False)
                    df[col] = df[col].str.replace('%', '', regex=False)
                
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Convert date columns
        date_cols = ['date_purchased']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        logger.info("DataFrame normalized successfully")
        
        return df
    
    def validate_data(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Validate imported data for completeness and integrity.
        
        Args:
            df: DataFrame to validate
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check required columns
        required = ['ticker', 'quantity', 'price']
        for col in required:
            if col not in df.columns:
                errors.append(f"Missing required column: '{col}'")
        
        # Check for empty dataframe
        if len(df) == 0:
            errors.append("No data rows found in file")
            return False, errors
        
        # Check for duplicates (if ticker exists)
        if 'ticker' in df.columns:
            valid_tickers = df[
                ~df['ticker'].astype(str).str.lower().isin(INVALID_TICKER_VALUES)
            ]
            
            duplicates = valid_tickers[
                valid_tickers['ticker'].duplicated()
            ]['ticker'].unique()
            
            if len(duplicates) > 0:
                dup_list = [str(d) for d in list(duplicates)]
                errors.append(f"Duplicate tickers found: {', '.join(dup_list)}")
        
        # Validate numeric columns have reasonable values
        if 'price' in df.columns:
            negative_prices = (df['price'] < 0).sum()
            if negative_prices > 0:
                errors.append(f"{negative_prices} holdings have negative prices")
        
        if 'quantity' in df.columns:
            negative_qty = (df['quantity'] < 0).sum()
            if negative_qty > 0:
                errors.append(f"{negative_qty} holdings have negative quantities")
        
        # Check for all zero values
        if 'value' in df.columns:
            if (df['value'] == 0).all():
                errors.append("All position values are zero")
        
        is_valid = len(errors) == 0
        
        if is_valid:
            logger.info("Data validation passed")
        else:
            logger.warning(f"Data validation failed: {len(errors)} errors")
        
        return is_valid, errors
    
    def compute_missing_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute missing metrics from available data.
        
        Args:
            df: DataFrame with raw data
        
        Returns:
            DataFrame with computed metrics
        """
        computed_count = 0
        
        # Compute value if missing
        if 'value' not in df.columns or df['value'].isna().any():
            if 'quantity' in df.columns and 'price' in df.columns:
                df['value'] = df['quantity'] * df['price']
                computed_count += 1
                logger.debug("Computed 'value' from quantity × price")
        
        # Compute cost basis if missing
        if 'cost_basis' not in df.columns or df['cost_basis'].isna().any():
            if 'value' in df.columns and 'gain_loss' in df.columns:
                df['cost_basis'] = df['value'] - df['gain_loss']
                computed_count += 1
                logger.debug("Computed 'cost_basis' from value - gain_loss")
        
        # Compute gain/loss if missing
        if 'gain_loss' not in df.columns or df['gain_loss'].isna().any():
            if 'value' in df.columns and 'cost_basis' in df.columns:
                df['gain_loss'] = df['value'] - df['cost_basis']
                computed_count += 1
                logger.debug("Computed 'gain_loss' from value - cost_basis")
        
        # Compute gain/loss % if missing
        if 'gain_loss_pct' not in df.columns or df['gain_loss_pct'].isna().any():
            if 'gain_loss' in df.columns and 'cost_basis' in df.columns:
                df['gain_loss_pct'] = np.where(
                    df['cost_basis'] != 0,
                    (df['gain_loss'] / df['cost_basis'] * 100),
                    0
                )
                computed_count += 1
                logger.debug("Computed 'gain_loss_pct'")
        
        # Compute yield if missing
        if 'yield' not in df.columns or df['yield'].isna().any():
            if 'dividend' in df.columns and 'value' in df.columns:
                df['yield'] = np.where(
                    df['value'] != 0,
                    (df['dividend'] / df['value'] * 100),
                    0
                )
                computed_count += 1
                logger.debug("Computed 'yield' from dividend / value")
        
        # Compute allocation percentage
        if 'allocation_pct' not in df.columns or df['allocation_pct'].isna().any():
            if 'value' in df.columns:
                total_value = df['value'].sum()
                if total_value > 0:
                    df['allocation_pct'] = (df['value'] / total_value * 100)
                    computed_count += 1
                    logger.debug("Computed 'allocation_pct'")
        
        if computed_count > 0:
            logger.info(f"Computed {computed_count} missing metrics")
        
        return df


# ========================================
# PORTFOLIO IMPORTER
# ========================================

class PortfolioImporter:
    """
    High-level interface for importing portfolio files.
    
    Features:
    - File parsing (CSV, Excel)
    - Header detection
    - Format detection
    - Data validation
    - Error reporting
    """
    
    def __init__(self):
        """Initialize portfolio importer"""
        self.importer = DataImporter()
        logger.info("PortfolioImporter initialized")
    
    def _find_header_row(self, df: pd.DataFrame) -> Optional[int]:
        """
        Find the index of the row that likely contains headers.
        
        Args:
            df: DataFrame to search
        
        Returns:
            Index of header row, or None if not found
        """
        key_cols = ['symbol', 'ticker', 'quantity', 'qty', 'price', 'value', 'shares']
        
        # Check first 20 rows
        for idx in range(min(20, len(df))):
            row = df.iloc[idx]
            row_str = [str(val).lower().strip() for val in row.values]
            
            # Count matches
            matches = sum(
                1 for col in key_cols
                if any(col == val or col in val for val in row_str)
            )
            
            # If we find at least 2 key columns, this is likely the header
            if matches >= 2:
                logger.debug(f"Found header row at index {idx}")
                return idx
        
        logger.debug("No header row found, using first row")
        return None
    
    def _validate_file_size(self, file_content: bytes, filename: str) -> Tuple[bool, Optional[str]]:
        """
        Validate file size.
        
        Args:
            file_content: File bytes
            filename: File name
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        file_size = len(file_content)
        
        if file_size == 0:
            return False, "File is empty"
        
        if file_size > MAX_FILE_SIZE:
            return False, f"File size ({file_size / 1024 / 1024:.1f} MB) exceeds maximum ({MAX_FILE_SIZE / 1024 / 1024:.1f} MB)"
        
        return True, None
    
    def import_file(
        self,
        file_content: bytes,
        filename: str,
        column_map: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Import portfolio file and return normalized dataframe with metadata.
        
        Args:
            file_content: File bytes
            filename: File name
            column_map: Optional custom column mapping
        
        Returns:
            Dictionary with:
            {
                'success': bool,
                'dataframe': pd.DataFrame,
                'metadata': {...},
                'errors': List[str],
                'warnings': List[str]
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
            logger.info(f"Importing file: {filename}")
            
            # Validate file size
            size_valid, size_error = self._validate_file_size(file_content, filename)
            if not size_valid:
                result['errors'].append(size_error)
                return result
            
            # Parse file - read without header first to detect structure
            if filename.endswith('.csv'):
                df_raw = pd.read_csv(io.BytesIO(file_content), header=None, encoding='utf-8', on_bad_lines='skip')
            elif filename.endswith(('.xlsx', '.xls')):
                df_raw = pd.read_excel(io.BytesIO(file_content), header=None)
            else:
                result['errors'].append(f"Unsupported file format: {filename}")
                return result
            
            logger.debug(f"Raw file parsed: {len(df_raw)} rows, {len(df_raw.columns)} columns")
            
            # Find header row
            header_idx = self._find_header_row(df_raw)
            
            if header_idx is not None:
                # Set columns from the found header row
                df_raw.columns = df_raw.iloc[header_idx].astype(str).tolist()
                # Slice dataframe to keep only rows after header
                df = df_raw.iloc[header_idx + 1:].copy()
                df = df.reset_index(drop=True)
            else:
                # Assume first row is header (standard behavior)
                df_raw.columns = df_raw.iloc[0].astype(str).tolist()
                df = df_raw.iloc[1:].copy()
                df = df.reset_index(drop=True)
            
            logger.debug(f"Header row processed: {len(df)} data rows")
            
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
                result['warnings'].extend(validation_errors)
            
            # Compute missing metrics
            df = self.importer.compute_missing_metrics(df)
            
            # Ensure allocation percentage is computed
            if 'value' in df.columns:
                total_value = df['value'].sum()
                if total_value > 0:
                    df['allocation_pct'] = (df['value'] / total_value * 100)
                else:
                    df['allocation_pct'] = 0
            
            # Set metadata
            result['metadata']['filename'] = filename
            result['metadata']['rows'] = len(df)
            result['metadata']['columns'] = df.columns.tolist()
            result['metadata']['total_value'] = round(float(df['value'].sum()), 2) if 'value' in df.columns else 0
            result['metadata']['num_holdings'] = len(df)
            result['metadata']['import_date'] = datetime.now().isoformat()
            
            result['dataframe'] = df
            result['success'] = len(result['errors']) == 0
            
            if result['success']:
                logger.info(f"Import successful: {len(df)} holdings, ${result['metadata']['total_value']:,.2f} total value")
            else:
                logger.error(f"Import failed: {len(result['errors'])} errors")
        
        except Exception as e:
            logger.error(f"File parsing error: {e}", exc_info=True)
            result['errors'].append(f"File parsing error: {str(e)}")
        
        return result


# ========================================
# CONVENIENCE FUNCTIONS
# ========================================

def import_csv_file(file_content: bytes, filename: str) -> pd.DataFrame:
    """
    Simple CSV import function.
    
    Args:
        file_content: CSV file bytes
        filename: File name
    
    Returns:
        Normalized DataFrame
    
    Raises:
        ValueError: If import fails
    """
    importer = PortfolioImporter()
    result = importer.import_file(file_content, filename)
    
    if not result['success']:
        raise ValueError(f"Import failed: {', '.join(result['errors'])}")
    
    return result['dataframe']


def import_excel_file(file_content: bytes, filename: str) -> pd.DataFrame:
    """
    Simple Excel import function.
    
    Args:
        file_content: Excel file bytes
        filename: File name
    
    Returns:
        Normalized DataFrame
    
    Raises:
        ValueError: If import fails
    """
    importer = PortfolioImporter()
    result = importer.import_file(file_content, filename)
    
    if not result['success']:
        raise ValueError(f"Import failed: {', '.join(result['errors'])}")
    
    return result['dataframe']


def get_supported_formats() -> Dict[str, Any]:
    """
    Get information about supported file formats.
    
    Returns:
        Dictionary with format information
    """
    return {
        'formats': ['csv', 'xlsx', 'xls'],
        'brokerages': [
            'Charles Schwab',
            'Fidelity',
            'Vanguard',
            'E*TRADE',
            'TD Ameritrade',
            'Interactive Brokers',
            'Robinhood',
            'Generic/Standard'
        ],
        'max_file_size_mb': MAX_FILE_SIZE / 1024 / 1024,
        'required_columns': ['ticker', 'quantity', 'price'],
        'optional_columns': [
            'value', 'cost_basis', 'gain_loss', 'gain_loss_pct',
            'dividend', 'yield', 'description', 'asset_type'
        ]
    }


# Export all public items
__all__ = [
    'DataImporter',
    'PortfolioImporter',
    'import_csv_file',
    'import_excel_file',
    'get_supported_formats',
    'INVALID_TICKER_VALUES',
    'MAX_FILE_SIZE'
]
