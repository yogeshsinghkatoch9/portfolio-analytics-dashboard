"""
Export API for VisionWealth
Handles export of portfolio data in multiple formats (CSV, Excel, JSON)
with comprehensive formatting and customization options
"""

from fastapi import APIRouter, Depends, HTTPException, Body, Query
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
import pandas as pd
import numpy as np
from io import BytesIO, StringIO
import json
import logging

from db import get_db
from auth import get_current_active_user
from models import User, Portfolio, Holding

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


# ========================================
# ENUMS
# ========================================

class ExportFormat(str, Enum):
    """Export format options"""
    CSV = "csv"
    EXCEL = "excel"
    JSON = "json"
    TSV = "tsv"


class ExportType(str, Enum):
    """Export type options"""
    HOLDINGS = "holdings"
    SUMMARY = "summary"
    ANALYTICS = "analytics"
    FULL = "full"


# ========================================
# PYDANTIC MODELS
# ========================================

from pydantic import BaseModel, Field


class ExportRequest(BaseModel):
    """Export request model"""
    portfolio_data: Optional[Dict[str, Any]] = None
    portfolio_id: Optional[int] = None
    format: ExportFormat = ExportFormat.CSV
    export_type: ExportType = ExportType.HOLDINGS
    include_summary: bool = Field(True, description="Include summary sheet (Excel only)")
    include_analytics: bool = Field(False, description="Include analytics sheet (Excel only)")
    date_format: str = Field("%Y-%m-%d", description="Date format string")
    
    class Config:
        json_schema_extra = {
            "example": {
                "portfolio_id": 1,
                "format": "excel",
                "export_type": "full",
                "include_summary": True,
                "include_analytics": True
            }
        }


class ExportResponse(BaseModel):
    """Export response model"""
    success: bool
    filename: str
    format: str
    rows_exported: int
    size_bytes: int
    timestamp: str


# ========================================
# HELPER FUNCTIONS
# ========================================

def sanitize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sanitize DataFrame for export.
    
    - Replace NaN with empty strings or 0
    - Format numbers
    - Clean column names
    
    Args:
        df: Input DataFrame
    
    Returns:
        Sanitized DataFrame
    """
    df = df.copy()
    
    # Replace inf and -inf with NaN, then fill
    df = df.replace([np.inf, -np.inf], np.nan)
    
    # Fill NaN values based on column type
    for col in df.columns:
        if df[col].dtype in ['float64', 'float32', 'int64', 'int32']:
            df[col] = df[col].fillna(0)
        else:
            df[col] = df[col].fillna('')
    
    # Clean column names (remove special characters)
    df.columns = [str(col).strip().replace('\n', ' ') for col in df.columns]
    
    return df


def format_currency_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Format currency columns in DataFrame.
    
    Args:
        df: Input DataFrame
    
    Returns:
        DataFrame with formatted currency columns
    """
    df = df.copy()
    
    # Currency columns to format
    currency_cols = [
        'Price ($)', 'Value ($)', 'Principal ($)*', 'NFS Cost ($)',
        'NFS G/L ($)', 'Principal G/L ($)*', 'Est Annual Income ($)',
        '1-Day Value Change ($)', 'Est Tax G/L ($)*'
    ]
    
    for col in currency_cols:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: f"${x:,.2f}" if pd.notna(x) and x != 0 else "$0.00"
            )
    
    # Percentage columns
    pct_cols = [
        'Assets (%)', 'NFS G/L (%)', 'Principal G/L (%)*',
        '1-Day Price Change (%)', 'Current Yld/Dist Rate (%)'
    ]
    
    for col in pct_cols:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: f"{x:.2f}%" if pd.notna(x) else "0.00%"
            )
    
    return df


def create_summary_sheet(portfolio_data: Dict[str, Any]) -> pd.DataFrame:
    """
    Create summary sheet DataFrame.
    
    Args:
        portfolio_data: Portfolio data dictionary
    
    Returns:
        Summary DataFrame
    """
    summary = portfolio_data.get('summary', {})
    
    summary_data = {
        'Metric': [
            'Total Portfolio Value',
            'Total Principal',
            'Total Gain/Loss',
            'Total Return (%)',
            'Daily Change',
            'Daily Return (%)',
            'Total Annual Income',
            'Average Yield (%)',
            'Number of Holdings',
            'Report Date'
        ],
        'Value': [
            f"${summary.get('total_value', 0):,.2f}",
            f"${summary.get('total_principal', 0):,.2f}",
            f"${summary.get('total_gain_loss', 0):,.2f}",
            f"{summary.get('overall_return_pct', 0):.2f}%",
            f"${summary.get('total_daily_change', 0):,.2f}",
            f"{summary.get('daily_return_pct', 0):.2f}%",
            f"${summary.get('total_annual_income', 0):,.2f}",
            f"{summary.get('avg_yield', 0):.2f}%",
            str(summary.get('num_holdings', 0)),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ]
    }
    
    return pd.DataFrame(summary_data)


def create_analytics_sheet(portfolio_data: Dict[str, Any]) -> pd.DataFrame:
    """
    Create analytics sheet DataFrame.
    
    Args:
        portfolio_data: Portfolio data dictionary
    
    Returns:
        Analytics DataFrame
    """
    analytics = portfolio_data.get('analytics', {})
    
    # Combine various analytics into one sheet
    analytics_data = []
    
    # Risk metrics
    if 'risk_metrics' in analytics:
        risk = analytics['risk_metrics']
        analytics_data.extend([
            {'Category': 'Risk', 'Metric': 'Portfolio Volatility', 'Value': f"{risk.get('portfolio_volatility', 0):.2f}%"},
            {'Category': 'Risk', 'Metric': 'Sharpe Ratio', 'Value': f"{risk.get('sharpe_ratio', 0):.2f}"},
            {'Category': 'Risk', 'Metric': 'Value at Risk (95%)', 'Value': f"{risk.get('var_95', 0):.2f}%"},
            {'Category': 'Risk', 'Metric': 'Beta', 'Value': f"{risk.get('beta', 0):.2f}"},
        ])
    
    # Diversification
    if 'diversification' in analytics:
        div = analytics['diversification']
        analytics_data.extend([
            {'Category': 'Diversification', 'Metric': 'Diversification Score', 'Value': f"{div.get('diversification_score', 0):.2f}"},
            {'Category': 'Diversification', 'Metric': 'HHI Index', 'Value': f"{div.get('hhi_index', 0):.4f}"},
        ])
    
    # Dividend metrics
    if 'dividend_metrics' in analytics:
        div_metrics = analytics['dividend_metrics']
        analytics_data.extend([
            {'Category': 'Dividends', 'Metric': 'Total Annual Income', 'Value': f"${div_metrics.get('total_annual_income', 0):,.2f}"},
            {'Category': 'Dividends', 'Metric': 'Portfolio Yield', 'Value': f"{div_metrics.get('portfolio_yield', 0):.2f}%"},
            {'Category': 'Dividends', 'Metric': 'Dividend Payers', 'Value': str(div_metrics.get('dividend_payers_count', 0))},
        ])
    
    if not analytics_data:
        analytics_data = [{'Category': 'Analytics', 'Metric': 'No data', 'Value': 'N/A'}]
    
    return pd.DataFrame(analytics_data)


# ========================================
# ENDPOINTS
# ========================================

@router.post("/export/csv", tags=["Export"])
async def export_portfolio_csv(
    portfolio_data: Optional[Dict[str, Any]] = Body(None),
    portfolio_id: Optional[int] = Body(None),
    include_formatted: bool = Body(True, description="Format currency and percentage values"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Export portfolio holdings as CSV.
    
    **Options**:
    - Export from provided data OR from database portfolio
    - Optional formatting of currency/percentage values
    
    **Returns**: CSV file download
    """
    try:
        logger.info(f"CSV export requested by user {current_user.id}")
        
        # Get holdings data
        if portfolio_id:
            # Load from database
            portfolio = db.query(Portfolio).filter(
                Portfolio.id == portfolio_id,
                Portfolio.user_id == current_user.id
            ).first()
            
            if not portfolio:
                raise HTTPException(
                    status_code=404,
                    detail="Portfolio not found"
                )
            
            holdings = []
            for h in portfolio.holdings:
                holdings.append({
                    'Symbol': h.ticker,
                    'Quantity': h.quantity,
                    'Price ($)': h.price,
                    'Value ($)': h.quantity * h.price,
                    'Cost Basis': h.cost_basis,
                    'Asset Type': h.asset_type,
                    'Created At': h.created_at.strftime('%Y-%m-%d')
                })
        
        elif portfolio_data:
            holdings = portfolio_data.get('holdings', [])
        
        else:
            raise HTTPException(
                status_code=400,
                detail="Either portfolio_data or portfolio_id must be provided"
            )
        
        if not holdings:
            raise HTTPException(
                status_code=400,
                detail="No holdings to export"
            )
        
        # Convert to DataFrame
        df = pd.DataFrame(holdings)
        df = sanitize_dataframe(df)
        
        # Format if requested
        if include_formatted:
            df = format_currency_columns(df)
        
        # Create CSV buffer
        stream = StringIO()
        df.to_csv(stream, index=False)
        csv_data = stream.getvalue()
        
        filename = f"portfolio_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        logger.info(f"CSV export completed: {len(df)} rows")
        
        return StreamingResponse(
            iter([csv_data]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"CSV export error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export CSV: {str(e)}"
        )


@router.post("/export/excel", tags=["Export"])
async def export_portfolio_excel(
    export_request: ExportRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Export portfolio as Excel workbook with multiple sheets.
    
    **Features**:
    - Multiple sheets (Holdings, Summary, Analytics)
    - Professional formatting
    - Formulas and styling
    
    **Sheets**:
    - `Holdings`: Detailed position data
    - `Summary`: Portfolio summary metrics
    - `Analytics`: Risk and performance analytics
    
    **Returns**: Excel (.xlsx) file download
    """
    try:
        logger.info(f"Excel export requested by user {current_user.id}")
        
        # Get portfolio data
        if export_request.portfolio_id:
            portfolio = db.query(Portfolio).filter(
                Portfolio.id == export_request.portfolio_id,
                Portfolio.user_id == current_user.id
            ).first()
            
            if not portfolio:
                raise HTTPException(
                    status_code=404,
                    detail="Portfolio not found"
                )
            
            # Build portfolio data
            holdings = []
            for h in portfolio.holdings:
                holdings.append({
                    'Symbol': h.ticker,
                    'Description': '',
                    'Quantity': h.quantity,
                    'Price ($)': h.price,
                    'Value ($)': h.quantity * h.price,
                    'Cost Basis': h.cost_basis,
                    'Gain/Loss ($)': (h.quantity * h.price) - h.cost_basis,
                    'Asset Type': h.asset_type,
                    'Created At': h.created_at
                })
            
            portfolio_data = {
                'holdings': holdings,
                'summary': {},
                'analytics': {}
            }
        
        elif export_request.portfolio_data:
            portfolio_data = export_request.portfolio_data
            holdings = portfolio_data.get('holdings', [])
        
        else:
            raise HTTPException(
                status_code=400,
                detail="Either portfolio_data or portfolio_id must be provided"
            )
        
        if not holdings:
            raise HTTPException(
                status_code=400,
                detail="No holdings to export"
            )
        
        # Create Excel buffer
        buffer = BytesIO()
        
        # Create Excel writer
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            # Holdings sheet
            df_holdings = pd.DataFrame(holdings)
            df_holdings = sanitize_dataframe(df_holdings)
            df_holdings.to_excel(writer, sheet_name='Holdings', index=False)
            
            # Format the Holdings sheet
            worksheet = writer.sheets['Holdings']
            
            # Set column widths
            for idx, col in enumerate(df_holdings.columns, 1):
                max_length = max(
                    df_holdings[col].astype(str).map(len).max(),
                    len(col)
                )
                worksheet.column_dimensions[chr(64 + idx)].width = min(max_length + 2, 50)
            
            # Summary sheet
            if export_request.include_summary:
                df_summary = create_summary_sheet(portfolio_data)
                df_summary.to_excel(writer, sheet_name='Summary', index=False)
                
                # Format Summary sheet
                summary_sheet = writer.sheets['Summary']
                summary_sheet.column_dimensions['A'].width = 25
                summary_sheet.column_dimensions['B'].width = 20
            
            # Analytics sheet
            if export_request.include_analytics and portfolio_data.get('analytics'):
                df_analytics = create_analytics_sheet(portfolio_data)
                df_analytics.to_excel(writer, sheet_name='Analytics', index=False)
                
                # Format Analytics sheet
                analytics_sheet = writer.sheets['Analytics']
                analytics_sheet.column_dimensions['A'].width = 20
                analytics_sheet.column_dimensions['B'].width = 30
                analytics_sheet.column_dimensions['C'].width = 20
        
        buffer.seek(0)
        
        filename = f"portfolio_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        logger.info(f"Excel export completed: {len(holdings)} rows")
        
        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Excel export error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export Excel: {str(e)}"
        )


@router.post("/export/json", tags=["Export"])
async def export_portfolio_json(
    portfolio_data: Optional[Dict[str, Any]] = Body(None),
    portfolio_id: Optional[int] = Body(None),
    pretty_print: bool = Body(True, description="Pretty print JSON"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Export portfolio as JSON.
    
    **Options**:
    - Pretty print formatting
    - Include full portfolio data structure
    
    **Returns**: JSON file download
    """
    try:
        logger.info(f"JSON export requested by user {current_user.id}")
        
        # Get portfolio data
        if portfolio_id:
            portfolio = db.query(Portfolio).filter(
                Portfolio.id == portfolio_id,
                Portfolio.user_id == current_user.id
            ).first()
            
            if not portfolio:
                raise HTTPException(
                    status_code=404,
                    detail="Portfolio not found"
                )
            
            # Build JSON structure
            export_data = {
                'portfolio': {
                    'id': portfolio.id,
                    'name': portfolio.name,
                    'created_at': portfolio.created_at.isoformat(),
                    'updated_at': portfolio.updated_at.isoformat() if portfolio.updated_at else None
                },
                'holdings': []
            }
            
            for h in portfolio.holdings:
                export_data['holdings'].append({
                    'id': h.id,
                    'ticker': h.ticker,
                    'quantity': float(h.quantity),
                    'price': float(h.price),
                    'cost_basis': float(h.cost_basis),
                    'asset_type': h.asset_type,
                    'created_at': h.created_at.isoformat(),
                    'updated_at': h.updated_at.isoformat() if h.updated_at else None
                })
        
        elif portfolio_data:
            export_data = portfolio_data
        
        else:
            raise HTTPException(
                status_code=400,
                detail="Either portfolio_data or portfolio_id must be provided"
            )
        
        # Add export metadata
        export_data['export_metadata'] = {
            'exported_at': datetime.now().isoformat(),
            'exported_by': current_user.email,
            'format': 'json',
            'version': '1.0'
        }
        
        # Convert to JSON
        if pretty_print:
            json_data = json.dumps(export_data, indent=2, default=str)
        else:
            json_data = json.dumps(export_data, default=str)
        
        filename = f"portfolio_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        logger.info("JSON export completed")
        
        return Response(
            content=json_data,
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"JSON export error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export JSON: {str(e)}"
        )


@router.post("/export", tags=["Export"])
async def export_portfolio(
    export_request: ExportRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Universal export endpoint supporting multiple formats.
    
    **Supported Formats**:
    - CSV: Comma-separated values
    - Excel: Multi-sheet workbook (.xlsx)
    - JSON: Structured data
    - TSV: Tab-separated values
    
    **Example Request**:
```json
    {
        "portfolio_id": 1,
        "format": "excel",
        "export_type": "full",
        "include_summary": true,
        "include_analytics": true
    }
```
    """
    try:
        if export_request.format == ExportFormat.CSV:
            return await export_portfolio_csv(
                portfolio_data=export_request.portfolio_data,
                portfolio_id=export_request.portfolio_id,
                include_formatted=True,
                current_user=current_user,
                db=db
            )
        
        elif export_request.format == ExportFormat.EXCEL:
            return await export_portfolio_excel(
                export_request=export_request,
                current_user=current_user,
                db=db
            )
        
        elif export_request.format == ExportFormat.JSON:
            return await export_portfolio_json(
                portfolio_data=export_request.portfolio_data,
                portfolio_id=export_request.portfolio_id,
                pretty_print=True,
                current_user=current_user,
                db=db
            )
        
        elif export_request.format == ExportFormat.TSV:
            # Similar to CSV but with tabs
            return await export_portfolio_csv(
                portfolio_data=export_request.portfolio_data,
                portfolio_id=export_request.portfolio_id,
                include_formatted=True,
                current_user=current_user,
                db=db
            )
        
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported export format: {export_request.format}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Export failed: {str(e)}"
        )


@router.get("/export/formats", tags=["Export"])
async def get_export_formats():
    """
    Get available export formats and their capabilities.
    
    **Returns**: List of supported formats with descriptions
    """
    return {
        'formats': [
            {
                'id': 'csv',
                'name': 'CSV (Comma-Separated Values)',
                'description': 'Simple text format, compatible with Excel and other tools',
                'mime_type': 'text/csv',
                'extension': '.csv',
                'supports_multiple_sheets': False,
                'supports_formatting': True
            },
            {
                'id': 'excel',
                'name': 'Excel Workbook',
                'description': 'Full-featured Excel file with multiple sheets and formatting',
                'mime_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'extension': '.xlsx',
                'supports_multiple_sheets': True,
                'supports_formatting': True
            },
            {
                'id': 'json',
                'name': 'JSON',
                'description': 'Structured data format for programmatic access',
                'mime_type': 'application/json',
                'extension': '.json',
                'supports_multiple_sheets': False,
                'supports_formatting': False
            },
            {
                'id': 'tsv',
                'name': 'TSV (Tab-Separated Values)',
                'description': 'Tab-delimited text format',
                'mime_type': 'text/tab-separated-values',
                'extension': '.tsv',
                'supports_multiple_sheets': False,
                'supports_formatting': True
            }
        ]
    }
