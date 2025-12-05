"""
Professional PDF Report Generator for Portfolio Analytics
Creates client-ready PDF reports with charts, metrics, and analysis
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, 
    PageBreak, Image, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.pdfgen import canvas
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
from datetime import datetime
import io
from typing import Dict, List, Any
import tempfile
import os
import pandas as pd


# Color scheme for professional reports
COLORS = {
    'primary': colors.HexColor('#2563eb'),  # Blue
    'secondary': colors.HexColor('#64748b'),  # Gray
    'success': colors.HexColor('#10b981'),  # Green
    'danger': colors.HexColor('#ef4444'),  # Red
    'dark': colors.HexColor('#1e293b'),
    'light': colors.HexColor('#f8fafc')
}


def create_chart_image(chart_data: List[Dict], chart_type: str = 'pie') -> io.BytesIO:
    """Create chart image and return BytesIO object"""
    fig, ax = plt.subplots(figsize=(6, 4))
    
    if chart_type == 'pie':
        labels = [item.get('Symbol', item.get('Asset Type', '')) for item in chart_data[:10]]
        values = [item.get('Value ($)', item.get('Assets (%)', 0)) for item in chart_data[:10]]
        
        colors_list = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
                       '#ec4899', '#14b8a6', '#f97316', '#06b6d4', '#84cc16']
        
        ax.pie(values, labels=labels, autopct='%1.1f%%', colors=colors_list, startangle=90)
        ax.axis('equal')
    
    elif chart_type == 'horizontal_bar':
        labels = [item['Symbol'] for item in chart_data[:10]]
        values = [item.get('NFS G/L ($)', 0) for item in chart_data[:10]]
        
        colors_list = ['#10b981' if v >= 0 else '#ef4444' for v in values]
        
        ax.barh(labels, values, color=colors_list)
        ax.set_xlabel('Amount ($)')
        ax.grid(axis='x', alpha=0.3)
    
    plt.tight_layout()
    
    # Save to BytesIO
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
    plt.close()
    img_buffer.seek(0)
    
    return img_buffer


class NumberedCanvas(canvas.Canvas):
    """Custom canvas to add page numbers"""
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self.pages = []

    def showPage(self):
        self.pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        page_count = len(self.pages)
        for page_num, page in enumerate(self.pages, 1):
            self.__dict__.update(page)
            self.draw_page_number(page_num, page_count)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_num, page_count):
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.grey)
        self.drawRightString(
            7.5 * inch, 0.5 * inch,
            f"Page {page_num} of {page_count}"
        )
        self.drawString(
            0.75 * inch, 0.5 * inch,
            f"Generated: {datetime.now().strftime('%B %d, %Y')}"
        )


def generate_portfolio_pdf(
    portfolio_data: Dict[str, Any],
    analytics_data: Dict[str, Any],
    output_path: str,
    client_name: str = "Portfolio Report"
) -> str:
    """
    Generate comprehensive portfolio PDF report
    
    Args:
        portfolio_data: Basic portfolio data (summary, holdings, charts)
        analytics_data: Advanced analytics data (risk, diversification, etc.)
        output_path: Path where PDF should be saved
        client_name: Name to display on cover page
    
    Returns:
        Path to generated PDF file
    """
    
    # Create PDF document
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=1*inch
    )
    
    # Container for PDF elements
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=COLORS['primary'],
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=COLORS['dark'],
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    
    subheading_style = ParagraphStyle(
        'CustomSubHeading',
        parent=styles['Heading3'],
        fontSize=12,
        textColor=COLORS['secondary'],
        spaceAfter=6,
        fontName='Helvetica-Bold'
    )
    
    # ==== COVER PAGE ====
    story.append(Spacer(1, 2*inch))
    story.append(Paragraph("PORTFOLIO ANALYSIS REPORT", title_style))
    story.append(Spacer(1, 0.5*inch))
    
    # Client name
    client_style = ParagraphStyle(
        'Client',
        parent=styles['Normal'],
        fontSize=18,
        textColor=COLORS['secondary'],
        alignment=TA_CENTER,
        fontName='Helvetica'
    )
    story.append(Paragraph(client_name, client_style))
    story.append(Spacer(1, inch))
    
    # Key metrics on cover
    summary = portfolio_data.get('summary', {})
    cover_data = [
        ['Total Portfolio Value', f"${summary.get('total_value', 0):,.2f}"],
        ['Total Gain/Loss', f"${summary.get('total_gain_loss', 0):,.2f}"],
        ['Overall Return', f"{summary.get('overall_return_pct', 0):.2f}%"],
        ['Annual Income', f"${summary.get('total_annual_income', 0):,.2f}"],
        ['Holdings', str(summary.get('num_holdings', 0))],
        ['Report Date', datetime.now().strftime('%B %d, %Y')]
    ]
    
    cover_table = Table(cover_data, colWidths=[3*inch, 2*inch])
    cover_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 0), (0, -1), COLORS['secondary']),
        ('TEXTCOLOR', (1, 0), (1, -1), COLORS['dark']),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    story.append(cover_table)
    story.append(PageBreak())
    
    # ==== EXECUTIVE SUMMARY ====
    story.append(Paragraph("Executive Summary", heading_style))
    story.append(Spacer(1, 0.2*inch))
    
    exec_summary_text = f"""
    This report provides a comprehensive analysis of your investment portfolio as of {datetime.now().strftime('%B %d, %Y')}.
    Your portfolio consists of {summary.get('num_holdings', 0)} holdings with a total value of ${summary.get('total_value', 0):,.2f}.
    The portfolio has generated a total return of {summary.get('overall_return_pct', 0):.2f}% with an overall gain/loss of ${summary.get('total_gain_loss', 0):,.2f}.
    """
    story.append(Paragraph(exec_summary_text, styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    # Performance metrics table
    perf_data = [
        ['Metric', 'Value'],
        ['Total Value', f"${summary.get('total_value', 0):,.2f}"],
        ['Total Principal', f"${summary.get('total_principal', 0):,.2f}"],
        ['Total Gain/Loss', f"${summary.get('total_gain_loss', 0):,.2f}"],
        ['Overall Return', f"{summary.get('overall_return_pct', 0):.2f}%"],
        ['Daily Change', f"${summary.get('total_daily_change', 0):,.2f}"],
        ['Annual Income', f"${summary.get('total_annual_income', 0):,.2f}"],
        ['Average Yield', f"{summary.get('avg_yield', 0):.2f}%"],
    ]
    
    perf_table = Table(perf_data, colWidths=[3*inch, 2.5*inch])
    perf_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLORS['primary']),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLORS['light']]),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    story.append(perf_table)
    story.append(PageBreak())
    
    # ==== PORTFOLIO ALLOCATION ====
    story.append(Paragraph("Portfolio Allocation", heading_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Create allocation pie chart
    allocation_data = portfolio_data.get('charts', {}).get('allocation_by_symbol', [])
    if allocation_data:
        chart_buffer = create_chart_image(allocation_data, 'pie')
        try:
            img = Image(chart_buffer, width=5*inch, height=3.3*inch)
            story.append(img)
        except Exception as e:
            print(f"Error adding chart to PDF: {e}")
    
    story.append(Spacer(1, 0.3*inch))
    
    # Top holdings table
    story.append(Paragraph("Top 10 Holdings", subheading_style))
    holdings = portfolio_data.get('holdings', [])[:10]
    
    holdings_data = [['Symbol', 'Description', 'Value', '% of Portfolio']]
    for holding in holdings:
        holdings_data.append([
            holding.get('Symbol', ''),
            holding.get('Description', '')[:30] + '...' if len(holding.get('Description', '')) > 30 else holding.get('Description', ''),
            f"${holding.get('Value ($)', 0):,.2f}",
            f"{holding.get('Assets (%)', 0):.2f}%"
        ])
    
    holdings_table = Table(holdings_data, colWidths=[1*inch, 2.5*inch, 1.2*inch, 1.2*inch])
    holdings_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLORS['primary']),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLORS['light']]),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    
    story.append(holdings_table)
    story.append(PageBreak())
    
    # ==== RISK ANALYSIS ====
    if analytics_data:
        story.append(Paragraph("Risk Analysis", heading_style))
        story.append(Spacer(1, 0.2*inch))
        
        risk_metrics = analytics_data.get('risk_metrics', {})
        diversification = analytics_data.get('diversification', {})
        
        risk_data = [
            ['Risk Metric', 'Value'],
            ['Value at Risk (95%)', f"${risk_metrics.get('value_at_risk_95', 0):,.2f}"],
            ['Value at Risk (99%)', f"${risk_metrics.get('value_at_risk_99', 0):,.2f}"],
            ['Portfolio Volatility', f"{risk_metrics.get('portfolio_volatility', 0):.2f}%"],
            ['Diversification Score', f"{diversification.get('score', 0):.0f}/100"],
            ['Concentration Risk', diversification.get('concentration_risk', 'N/A')],
            ['Number of Holdings', str(diversification.get('num_holdings', 0))],
        ]
        
        risk_table = Table(risk_data, colWidths=[3*inch, 2.5*inch])
        risk_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), COLORS['primary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLORS['light']]),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        story.append(risk_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Tax Loss Harvesting
        tax_opps = analytics_data.get('tax_loss_harvesting', [])
        if tax_opps:
            story.append(Paragraph("Tax Loss Harvesting Opportunities", subheading_style))
            story.append(Spacer(1, 0.1*inch))
            
            tax_data = [['Symbol', 'Current Loss', 'Est. Tax Benefit']]
            for opp in tax_opps[:5]:
                tax_data.append([
                    opp.get('symbol', ''),
                    f"${opp.get('current_loss', 0):,.2f}",
                    f"${opp.get('estimated_tax_benefit', 0):,.2f}"
                ])
            
            tax_table = Table(tax_data, colWidths=[2*inch, 2*inch, 2*inch])
            tax_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), COLORS['danger']),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLORS['light']]),
            ]))
            
            story.append(tax_table)
        
        story.append(PageBreak())
    
    # ==== DIVIDEND ANALYSIS ====
    if analytics_data and analytics_data.get('dividend_metrics'):
        story.append(Paragraph("Dividend Analysis", heading_style))
        story.append(Spacer(1, 0.2*inch))
        
        div_metrics = analytics_data.get('dividend_metrics', {})
        
        div_summary = f"""
        Your portfolio generates ${div_metrics.get('total_annual_income', 0):,.2f} in annual dividend income
        from {div_metrics.get('dividend_stocks_count', 0)} dividend-paying stocks, representing an average yield
        of {div_metrics.get('average_yield', 0):.2f}%. This translates to approximately ${div_metrics.get('monthly_income', 0):,.2f} per month
        or ${div_metrics.get('quarterly_income', 0):,.2f} per quarter.
        """
        story.append(Paragraph(div_summary, styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        # Top dividend payers
        top_payers = div_metrics.get('top_dividend_payers', [])[:5]
        if top_payers:
            story.append(Paragraph("Top Dividend Payers", subheading_style))
            
            div_data = [['Symbol', 'Description', 'Annual Income', 'Yield %']]
            for payer in top_payers:
                div_data.append([
                    payer.get('Symbol', ''),
                    payer.get('Description', '')[:25] + '...' if len(payer.get('Description', '')) > 25 else payer.get('Description', ''),
                    f"${payer.get('Est Annual Income ($)', 0):,.2f}",
                    f"{payer.get('Current Yld/Dist Rate (%)', 0):.2f}%"
                ])
            
            div_table = Table(div_data, colWidths=[1*inch, 2.2*inch, 1.2*inch, 1*inch])
            div_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), COLORS['success']),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLORS['light']]),
            ]))
            
            story.append(div_table)
    
    # Build PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    
    return output_path


def generate_pdf_from_upload(file_content: bytes, filename: str, output_path: str, client_name: str = "Portfolio Report") -> str:
    """
    Generate PDF report from uploaded portfolio file
    
    Args:
        file_content: Raw file content
        filename: Original filename
        output_path: Where to save PDF
    
    Returns:
        Path to generated PDF
    """
    # Import portfolio processing functions
    # Import helper functions from backend.main using full package path
    from backend.main import parse_portfolio_file, clean_portfolio_data, compute_summary_metrics, generate_chart_data, prepare_holdings_table
    # Use package import to resolve backend analytics module
    from backend import analytics
    
    # Try to parse the uploaded file using the flexible importer (supports many formats)
    from backend import data_import

    importer = data_import.PortfolioImporter()
    import_result = importer.import_file(file_content, filename)
    if not import_result.get('success') and import_result.get('dataframe') is None:
        # If importer failed to parse, fall back to strict parser in main
        df = parse_portfolio_file(file_content, filename)
        df = clean_portfolio_data(df)
    else:
        df = import_result.get('dataframe')

    # Normalize columns to expected main.py names so downstream functions work
    # Map common importer columns to main expected columns
    rename_map = {}
    if 'ticker' in df.columns:
        rename_map['ticker'] = 'Symbol'
    if 'quantity' in df.columns:
        rename_map['quantity'] = 'Quantity'
    if 'price' in df.columns:
        rename_map['price'] = 'Price ($)'
    if 'value' in df.columns:
        rename_map['value'] = 'Value ($)'
    if 'allocation_pct' in df.columns:
        rename_map['allocation_pct'] = 'Assets (%)'
    if 'description' in df.columns:
        rename_map['description'] = 'Description'
    if 'dividend' in df.columns:
        rename_map['dividend'] = 'Est Annual Income ($)'
    if 'yield' in df.columns:
        rename_map['yield'] = 'Current Yld/Dist Rate (%)'
    if 'cost_basis' in df.columns:
        rename_map['cost_basis'] = 'Principal ($)*'
    if 'gain_loss' in df.columns:
        rename_map['gain_loss'] = 'NFS G/L ($)'

    if rename_map:
        df = df.rename(columns=rename_map)

    # Ensure required numeric columns exist (align with main.clean_portfolio_data expectations)
    required_numeric = [
        'Quantity', 'Price ($)', 'Value ($)', 'Assets (%)',
        '1-Day Value Change ($)', '1-Day Price Change (%)',
        'Principal ($)*', 'Principal G/L ($)*', 'Principal G/L (%)*',
        'NFS Cost ($)', 'NFS G/L ($)', 'NFS G/L (%)',
        'Est Annual Income ($)', 'Current Yld/Dist Rate (%)', 'Est Tax G/L ($)*'
    ]
    for col in required_numeric:
        if col not in df.columns:
            df[col] = 0

    # Ensure text columns used in grouping exist
    for txt_col in ['Asset Type', 'Asset Category', 'Description', 'Symbol']:
        if txt_col not in df.columns:
            df[txt_col] = ''

    # Convert to numeric safely
    for col in required_numeric:
        try:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        except Exception:
            df[col] = 0

    # Use existing helpers to compute summary and charts
    summary = compute_summary_metrics(df)
    charts = generate_chart_data(df)
    holdings = prepare_holdings_table(df)
    
    portfolio_data = {
        'summary': summary,
        'charts': charts,
        'holdings': holdings
    }
    
    # Get analytics
    try:
        print("Calculating risk metrics...")
        risk_metrics = analytics.calculate_risk_metrics(df)
        print("Calculating diversification...")
        diversification = analytics.calculate_diversification_score(df)
        print("Identifying tax loss harvesting...")
        tax_loss_harvesting = analytics.identify_tax_loss_harvesting(df)
        print("Calculating dividend metrics...")
        dividend_metrics = analytics.calculate_dividend_metrics(df)
        
        analytics_data = {
            'risk_metrics': risk_metrics,
            'diversification': diversification,
            'tax_loss_harvesting': tax_loss_harvesting,
            'dividend_metrics': dividend_metrics
        }
    except Exception as e:
        print(f"Error calculating analytics: {e}")
        analytics_data = {}
    
    # Generate PDF
    print(f"Generating PDF at {output_path}...")
    try:
        return generate_portfolio_pdf(portfolio_data, analytics_data, output_path, client_name=client_name)
    except Exception as e:
        print(f"Error generating PDF: {e}")
        import traceback
        traceback.print_exc()
        raise e
