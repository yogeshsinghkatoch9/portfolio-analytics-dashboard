"""
Professional PDF Report Generator for Portfolio Analytics
Creates client-ready PDF reports with charts, metrics, and analysis
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, 
    PageBreak, Image, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT, TA_JUSTIFY
from reportlab.pdfgen import canvas
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
from datetime import datetime
import io
from typing import Dict, List, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ColorScheme:
    """Professional color palette for reports"""
    PRIMARY = colors.HexColor('#2563eb')
    SECONDARY = colors.HexColor('#64748b')
    SUCCESS = colors.HexColor('#10b981')
    DANGER = colors.HexColor('#ef4444')
    WARNING = colors.HexColor('#f59e0b')
    DARK = colors.HexColor('#1e293b')
    LIGHT = colors.HexColor('#f8fafc')
    WHITE = colors.white
    
    CHART_COLORS = [
        '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
        '#ec4899', '#14b8a6', '#f97316', '#06b6d4', '#84cc16'
    ]


class ChartGenerator:
    """Handles chart generation for PDF reports"""
    
    @staticmethod
    def create_pie_chart(data: List[Dict], title: str = "Portfolio Allocation", max_items: int = 10) -> io.BytesIO:
        """Create a professional pie chart"""
        try:
            fig, ax = plt.subplots(figsize=(8, 6))
            
            labels = []
            values = []
            
            for i, item in enumerate(data[:max_items]):
                label = item.get('Symbol') or item.get('Asset Type') or f"Item {i+1}"
                value = item.get('Value ($)') or item.get('Assets (%)') or 0
                
                if value > 0:
                    labels.append(label)
                    values.append(value)
            
            if not values:
                raise ValueError("No data to chart")
            
            wedges, texts, autotexts = ax.pie(
                values, labels=labels, autopct='%1.1f%%',
                colors=ColorScheme.CHART_COLORS[:len(values)],
                startangle=90, pctdistance=0.85
            )
            
            for text in texts:
                text.set_fontsize(9)
                text.set_weight('bold')
            
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontsize(8)
                autotext.set_weight('bold')
            
            ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
            ax.axis('equal')
            
            plt.tight_layout()
            
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight', facecolor='white')
            plt.close(fig)
            img_buffer.seek(0)
            
            return img_buffer
            
        except Exception as e:
            logger.error(f"Error creating pie chart: {e}")
            plt.close('all')
            return None


class NumberedCanvas(canvas.Canvas):
    """Custom canvas for adding page numbers and footers"""
    
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
            self.draw_page_elements(page_num, page_count)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)
    
    def draw_page_elements(self, page_num: int, page_count: int):
        """Draw page number and footer"""
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.grey)
        
        self.drawRightString(7.5 * inch, 0.5 * inch, f"Page {page_num} of {page_count}")
        self.drawString(0.75 * inch, 0.5 * inch, f"Generated: {datetime.now().strftime('%B %d, %Y')}")
        
        self.setStrokeColor(colors.lightgrey)
        self.setLineWidth(0.5)
        self.line(0.75 * inch, 0.65 * inch, 7.5 * inch, 0.65 * inch)


class PDFReportGenerator:
    """Main class for generating professional PDF reports"""
    
    def __init__(self):
        """Initialize the report generator"""
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        self.chart_gen = ChartGenerator()
    
    def _setup_custom_styles(self):
        """Set up custom paragraph styles"""
        self.title_style = ParagraphStyle(
            'CustomTitle', parent=self.styles['Heading1'], fontSize=28,
            textColor=ColorScheme.PRIMARY, spaceAfter=30, alignment=TA_CENTER,
            fontName='Helvetica-Bold', leading=34
        )
        
        self.heading_style = ParagraphStyle(
            'CustomHeading', parent=self.styles['Heading2'], fontSize=18,
            textColor=ColorScheme.DARK, spaceAfter=15, spaceBefore=20,
            fontName='Helvetica-Bold', borderWidth=2, borderColor=ColorScheme.PRIMARY,
            borderPadding=8, leading=22
        )
        
        self.subheading_style = ParagraphStyle(
            'CustomSubHeading', parent=self.styles['Heading3'], fontSize=14,
            textColor=ColorScheme.SECONDARY, spaceAfter=10, spaceBefore=12,
            fontName='Helvetica-Bold', leading=17
        )
        
        self.body_style = ParagraphStyle(
            'CustomBody', parent=self.styles['Normal'], fontSize=10,
            textColor=colors.black, spaceAfter=12, alignment=TA_JUSTIFY, leading=14
        )
        
        self.client_style = ParagraphStyle(
            'ClientName', parent=self.styles['Normal'], fontSize=20,
            textColor=ColorScheme.SECONDARY, alignment=TA_CENTER,
            fontName='Helvetica-Bold', spaceAfter=20, leading=24
        )
    
    def generate_report(
        self, portfolio_data: Dict[str, Any], analytics_data: Dict[str, Any],
        output_path: str, client_name: str = "Portfolio Report", include_charts: bool = True
    ) -> str:
        """Generate comprehensive portfolio PDF report"""
        logger.info(f"Generating PDF report for {client_name}")
        
        try:
            doc = SimpleDocTemplate(
                output_path, pagesize=letter, rightMargin=0.75 * inch, leftMargin=0.75 * inch,
                topMargin=1 * inch, bottomMargin=1.25 * inch,
                title=f"Portfolio Report - {client_name}", author="VisionWealth Platform"
            )
            
            story = []
            story.extend(self._create_cover_page(portfolio_data, client_name))
            story.append(PageBreak())
            story.extend(self._create_executive_summary(portfolio_data))
            story.append(PageBreak())
            story.extend(self._create_allocation_section(portfolio_data, include_charts))
            story.append(PageBreak())
            story.extend(self._create_holdings_section(portfolio_data))
            
            if analytics_data:
                story.append(PageBreak())
                story.extend(self._create_risk_analysis(analytics_data))
            
            story.extend(self._create_disclaimer())
            
            doc.build(story, canvasmaker=NumberedCanvas)
            
            logger.info(f"PDF report generated successfully: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error generating PDF report: {e}", exc_info=True)
            raise
    
    def _create_cover_page(self, portfolio_data: Dict[str, Any], client_name: str) -> List:
        """Create professional cover page"""
        elements = []
        elements.append(Spacer(1, 2 * inch))
        elements.append(Paragraph("PORTFOLIO ANALYSIS REPORT", self.title_style))
        elements.append(Spacer(1, 0.5 * inch))
        elements.append(Paragraph(client_name, self.client_style))
        elements.append(Spacer(1, 0.8 * inch))
        
        summary = portfolio_data.get('summary', {})
        
        cover_data = [
            ['Total Portfolio Value', self._format_currency(summary.get('total_value', 0))],
            ['Total Gain/Loss', self._format_currency_colored(summary.get('total_gain_loss', 0))],
            ['Overall Return', self._format_percentage(summary.get('overall_return_pct', 0))],
            ['Number of Holdings', str(summary.get('num_holdings', 0))],
            ['Report Date', datetime.now().strftime('%B %d, %Y')]
        ]
        
        cover_table = Table(cover_data, colWidths=[3.2 * inch, 2.3 * inch])
        cover_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 13),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, 0), (0, -1), ColorScheme.SECONDARY),
            ('TEXTCOLOR', (1, 0), (1, -1), ColorScheme.DARK),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('LINEBELOW', (0, 0), (-1, -2), 0.5, ColorScheme.LIGHT),
        ]))
        
        elements.append(cover_table)
        return elements
    
    def _create_executive_summary(self, portfolio_data: Dict[str, Any]) -> List:
        """Create executive summary section"""
        elements = []
        elements.append(Paragraph("Executive Summary", self.heading_style))
        elements.append(Spacer(1, 0.2 * inch))
        
        summary = portfolio_data.get('summary', {})
        
        exec_text = f"""This report provides a comprehensive analysis of your investment portfolio as of 
        {datetime.now().strftime('%B %d, %Y')}. Your portfolio consists of <b>{summary.get('num_holdings', 0)}</b> 
        holdings with a total value of <b>${summary.get('total_value', 0):,.2f}</b>."""
        
        elements.append(Paragraph(exec_text, self.body_style))
        elements.append(Spacer(1, 0.3 * inch))
        
        perf_data = [
            ['Metric', 'Value'],
            ['Total Portfolio Value', self._format_currency(summary.get('total_value', 0))],
            ['Total Cost Basis', self._format_currency(summary.get('total_principal', 0))],
            ['Total Gain/Loss', self._format_currency_colored(summary.get('total_gain_loss', 0))],
            ['Overall Return', self._format_percentage(summary.get('overall_return_pct', 0))],
        ]
        
        perf_table = Table(perf_data, colWidths=[3.5 * inch, 2.5 * inch])
        perf_table.setStyle(self._get_standard_table_style())
        
        elements.append(perf_table)
        return elements
    
    def _create_allocation_section(self, portfolio_data: Dict[str, Any], include_charts: bool) -> List:
        """Create portfolio allocation section with charts"""
        elements = []
        elements.append(Paragraph("Portfolio Allocation", self.heading_style))
        elements.append(Spacer(1, 0.2 * inch))
        
        if include_charts:
            allocation_data = portfolio_data.get('charts', {}).get('allocation_by_symbol', [])
            
            if allocation_data:
                try:
                    chart_buffer = self.chart_gen.create_pie_chart(allocation_data, "Holdings Distribution")
                    
                    if chart_buffer:
                        img = Image(chart_buffer, width=5.5 * inch, height=4 * inch)
                        elements.append(img)
                        elements.append(Spacer(1, 0.3 * inch))
                except Exception as e:
                    logger.warning(f"Failed to add allocation chart: {e}")
        
        elements.append(Paragraph("Top 10 Holdings", self.subheading_style))
        elements.append(Spacer(1, 0.1 * inch))
        
        holdings = portfolio_data.get('holdings', [])[:10]
        
        if holdings:
            holdings_data = [['Symbol', 'Description', 'Value', '% Portfolio']]
            
            for holding in holdings:
                desc = holding.get('Description', '')
                if len(desc) > 30:
                    desc = desc[:27] + '...'
                
                holdings_data.append([
                    holding.get('Symbol', 'N/A'),
                    desc,
                    self._format_currency(holding.get('Value ($)', 0)),
                    f"{holding.get('Assets (%)', 0):.2f}%"
                ])
            
            holdings_table = Table(holdings_data, colWidths=[1 * inch, 2.5 * inch, 1.3 * inch, 1.2 * inch])
            holdings_table.setStyle(self._get_standard_table_style(font_size=9))
            
            elements.append(holdings_table)
        
        return elements
    
    def _create_holdings_section(self, portfolio_data: Dict[str, Any]) -> List:
        """Create detailed holdings section"""
        elements = []
        elements.append(Paragraph("Detailed Holdings", self.heading_style))
        elements.append(Spacer(1, 0.2 * inch))
        
        holdings = portfolio_data.get('holdings', [])
        
        if not holdings:
            elements.append(Paragraph("No holdings data available.", self.body_style))
            return elements
        
        holdings_data = [['Symbol', 'Quantity', 'Price', 'Value', 'Cost Basis', 'Gain/Loss']]
        
        total_value = 0
        total_cost = 0
        
        for holding in holdings:
            value = holding.get('Value ($)', 0)
            cost = holding.get('Principal ($)*', 0)
            gain_loss = holding.get('NFS G/L ($)', 0)
            
            total_value += value
            total_cost += cost
            
            holdings_data.append([
                holding.get('Symbol', 'N/A'),
                f"{holding.get('Quantity', 0):,.2f}",
                self._format_currency(holding.get('Price ($)', 0)),
                self._format_currency(value),
                self._format_currency(cost),
                self._format_currency_colored(gain_loss)
            ])
        
        total_gain_loss = total_value - total_cost
        holdings_data.append([
            'TOTAL', '', '',
            self._format_currency(total_value),
            self._format_currency(total_cost),
            self._format_currency_colored(total_gain_loss)
        ])
        
        holdings_table = Table(
            holdings_data,
            colWidths=[0.9 * inch, 0.9 * inch, 0.9 * inch, 1.1 * inch, 1.1 * inch, 1.1 * inch]
        )
        
        style = self._get_standard_table_style(font_size=8)
        style.add('BACKGROUND', (0, -1), (-1, -1), ColorScheme.LIGHT)
        style.add('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold')
        style.add('LINEABOVE', (0, -1), (-1, -1), 2, ColorScheme.PRIMARY)
        
        holdings_table.setStyle(style)
        
        elements.append(holdings_table)
        return elements
    
    def _create_risk_analysis(self, analytics_data: Dict[str, Any]) -> List:
        """Create risk analysis section"""
        elements = []
        elements.append(Paragraph("Risk Analysis", self.heading_style))
        elements.append(Spacer(1, 0.2 * inch))
        
        risk_metrics = analytics_data.get('risk_metrics', {})
        diversification = analytics_data.get('diversification', {})
        
        risk_data = [
            ['Risk Metric', 'Value'],
            ['Value at Risk (95%)', self._format_currency(risk_metrics.get('value_at_risk_95', 0))],
            ['Portfolio Volatility', f"{risk_metrics.get('portfolio_volatility', 0):.2f}%"],
            ['Diversification Score', f"{diversification.get('score', 0):.0f}/100"],
            ['Number of Holdings', str(diversification.get('num_holdings', 0))],
        ]
        
        risk_table = Table(risk_data, colWidths=[3.5 * inch, 2.5 * inch])
        risk_table.setStyle(self._get_standard_table_style())
        
        elements.append(risk_table)
        return elements
    
    def _create_disclaimer(self) -> List:
        """Create disclaimer section"""
        elements = []
        elements.append(Spacer(1, 0.5 * inch))
        
        disclaimer_text = f"""<b>Important Disclaimer:</b><br/>
        This report is for informational purposes only and does not constitute investment advice. 
        Past performance is not indicative of future results. All investments involve risk.<br/><br/>
        Generated by VisionWealth Platform - {datetime.now().strftime('%B %d, %Y %I:%M %p')}"""
        
        disclaimer_style = ParagraphStyle(
            'Disclaimer', parent=self.styles['Normal'], fontSize=8,
            textColor=ColorScheme.SECONDARY, spaceAfter=10, leading=10
        )
        
        elements.append(Paragraph(disclaimer_text, disclaimer_style))
        return elements
    
    def _get_standard_table_style(self, header_color: colors.Color = None, font_size: int = 10) -> TableStyle:
        """Get standard table style"""
        if header_color is None:
            header_color = ColorScheme.PRIMARY
        
        return TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), header_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), font_size),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, ColorScheme.LIGHT]),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ])
    
    @staticmethod
    def _format_currency(value: float) -> str:
        return f"${value:,.2f}"
    
    @staticmethod
    def _format_currency_colored(value: float) -> str:
        sign = '+' if value >= 0 else ''
        return f"{sign}${value:,.2f}"
    
    @staticmethod
    def _format_percentage(value: float) -> str:
        sign = '+' if value >= 0 else ''
        return f"{sign}{value:.2f}%"


# Backward compatibility
def generate_portfolio_pdf(
    portfolio_data: Dict[str, Any],
    analytics_data: Dict[str, Any],
    output_path: str,
    client_name: str = "Portfolio Report"
) -> str:
    """Generate comprehensive portfolio PDF report"""
    generator = PDFReportGenerator()
    return generator.generate_report(portfolio_data, analytics_data, output_path, client_name)
