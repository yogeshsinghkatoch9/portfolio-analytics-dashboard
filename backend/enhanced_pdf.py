"""
Enhanced PDF Report Generator
Professional-grade portfolio reports with AI insights, charts, and branding
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
from typing import Dict, List, Optional
import io
import os
import logging

logger = logging.getLogger(__name__)


class EnhancedPDFReportGenerator:
    """Generate professional portfolio reports with AI insights"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Define custom paragraph styles"""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1e40af'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#374151'),
            spaceAfter=12,
            spaceBefore=20,
            borderPadding=5
        ))
        
        self.styles.add(ParagraphStyle(
            name='AIInsight',
            parent=self.styles['BodyText'],
            fontSize=11,
            textColor=colors.HexColor('#6b21a8'),
            leftIndent=20,
            rightIndent=20,
            spaceAfter=15,
            borderColor=colors.HexColor('#c084fc'),
            borderWidth=1,
            borderPadding=10,
            backColor=colors.HexColor('#faf5ff')
        ))
    
    def generate_report(
        self,
        portfolio_data: Dict,
        analytics: Dict,
        ai_insights: Optional[Dict] = None,
        output_path: str = None
    ) -> bytes:
        """
        Generate comprehensive PDF report
        
        Args:
            portfolio_data: Portfolio holdings and metadata
            analytics: Risk metrics, allocation, performance
            ai_insights: AI-generated analysis
            output_path: Optional file path to save PDF
            
        Returns:
            PDF as bytes
        """
        logger.info(f"Generating enhanced PDF report for portfolio: {portfolio_data.get('name', 'Unnamed')}")
        
        # Create buffer
        buffer = io.BytesIO()
        
        # Create PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=inch,
            leftMargin=inch,
            topMargin=inch,
            bottomMargin=inch
        )
        
        # Build content
        story = []
        
        # Cover page
        story.extend(self._create_cover_page(portfolio_data))
        story.append(PageBreak())
        
        # Executive Summary (with AI if available)
        story.extend(self._create_executive_summary(portfolio_data, analytics, ai_insights))
        story.append(Spacer(1, 0.3*inch))
        
        # Portfolio Overview
        story.extend(self._create_portfolio_overview(portfolio_data))
        story.append(Spacer(1, 0.3*inch))
        
        # Risk Analysis
        story.extend(self._create_risk_analysis(analytics))
        story.append(PageBreak())
        
        # Holdings Table
        story.extend(self._create_holdings_table(portfolio_data))
        story.append(Spacer(1, 0.3*inch))
        
        # Allocation Analysis
        story.extend(self._create_allocation_section(analytics))
        
        # AI Insights (if available)
        if ai_insights:
            story.append(PageBreak())
            story.extend(self._create_ai_insights_section(ai_insights))
        
        # Recommendations
        if ai_insights and ai_insights.get('recommendations'):
            story.append(PageBreak())
            story.extend(self._create_recommendations_section(ai_insights))
        
        # Footer with disclaimer
        story.append(PageBreak())
        story.extend(self._create_disclaimer())
        
        # Build PDF
        doc.build(story)
        
        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        # Optionally save to file
        if output_path:
            with open(output_path, 'wb') as f:
                f.write(pdf_bytes)
            logger.info(f"PDF saved to: {output_path}")
        
        logger.info(f"PDF report generated successfully ({len(pdf_bytes)} bytes)")
        return pdf_bytes
    
    def _create_cover_page(self, portfolio_data: Dict) -> List:
        """Create professional cover page"""
        elements = []
        
        # Title
        title = Paragraph(
            f"<b>Portfolio Analysis Report</b>",
            self.styles['CustomTitle']
        )
        elements.append(Spacer(1, 2*inch))
        elements.append(title)
        elements.append(Spacer(1, 0.5*inch))
        
        # Portfolio name
        name = portfolio_data.get('name', 'Investment Portfolio')
        elements.append(Paragraph(
            f"<b>{name}</b>",
            self.styles['Heading2']
        ))
        elements.append(Spacer(1, 0.3*inch))
        
        # Date
        date_str = datetime.now().strftime("%B %d, %Y")
        elements.append(Paragraph(
            f"Generated on {date_str}",
            self.styles['Normal']
        ))
        elements.append(Spacer(1, inch))
        
        # Key metrics box
        total_value = portfolio_data.get('total_value', 0)
        num_holdings = len(portfolio_data.get('holdings', []))
        
        metrics_data = [
            ['Total Portfolio Value', f"${total_value:,.2f}"],
            ['Number of Holdings', str(num_holdings)],
            ['Report Type', 'Comprehensive Analysis']
        ]
        
        metrics_table = Table(metrics_data, colWidths=[3*inch, 2*inch])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1f2937')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#d1d5db')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(metrics_table)
        
        return elements
    
    def _create_executive_summary(
        self,
        portfolio_data: Dict,
        analytics: Dict,
        ai_insights: Optional[Dict]
    ) -> List:
        """Create executive summary with AI insights"""
        elements = []
        
        elements.append(Paragraph(
            "<b>Executive Summary</b>",
            self.styles['SectionHeader']
        ))
        
        if ai_insights and ai_insights.get('summary'):
            # AI-generated summary
            summary_text = ai_insights['summary']
            elements.append(Paragraph(
                f"<i>{summary_text}</i>",
                self.styles['AIInsight']
            ))
        else:
            # Fallback summary
            total_value = portfolio_data.get('total_value', 0)
            num_holdings = len(portfolio_data.get('holdings', []))
            
            summary = f"""
            This portfolio consists of {num_holdings} holdings with a total value of ${total_value:,.2f}.
            The analysis includes comprehensive risk metrics, sector allocation breakdown, and performance analytics.
            """
            elements.append(Paragraph(summary, self.styles['BodyText']))
        
        # Portfolio score (if available from AI)
        if ai_insights and ai_insights.get('score'):
            score = ai_insights['score']
            score_color = self._get_score_color(score)
            
            score_text = f"""
            <b>Portfolio Health Score:</b> <font color="{score_color}"><b>{score}/100</b></font>
            """
            elements.append(Spacer(1, 0.2*inch))
            elements.append(Paragraph(score_text, self.styles['BodyText']))
        
        return elements
    
    def _create_portfolio_overview(self, portfolio_data: Dict) -> List:
        """Create portfolio overview section"""
        elements = []
        
        elements.append(Paragraph(
            "<b>Portfolio Overview</b>",
            self.styles['SectionHeader']
        ))
        
        total_value = portfolio_data.get('total_value', 0)
        holdings = portfolio_data.get('holdings', [])
        
        # Summary statistics
        stats_data = [
            ['Metric', 'Value'],
            ['Total Value', f"${total_value:,.2f}"],
            ['Number of Holdings', str(len(holdings))],
            ['Largest Holding', self._get_largest_holding(holdings)],
            ['Smallest Holding', self._get_smallest_holding(holdings)]
        ]
        
        stats_table = Table(stats_data, colWidths=[2.5*inch, 2.5*inch])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(stats_table)
        
        return elements
    
    def _create_risk_analysis(self, analytics: Dict) -> List:
        """Create risk analysis section"""
        elements = []
        
        elements.append(Paragraph(
            "<b>Risk Analysis</b>",
            self.styles['SectionHeader']
        ))
        
        risk_metrics = analytics.get('risk_metrics', {})
        
        risk_data = [['Metric', 'Value', 'Interpretation']]
        
        if 'beta' in risk_metrics:
            beta = risk_metrics['beta']
            interpretation = "Higher than market" if beta > 1 else "Lower than market"
            risk_data.append(['Beta', f"{beta:.2f}", interpretation])
        
        if 'sharpe_ratio' in risk_metrics:
            sharpe = risk_metrics['sharpe_ratio']
            interpretation = "Excellent" if sharpe > 2 else ("Good" if sharpe > 1 else "Moderate")
            risk_data.append(['Sharpe Ratio', f"{sharpe:.2f}", interpretation])
        
        if 'volatility' in risk_metrics:
            vol = risk_metrics['volatility']
            risk_data.append(['Volatility', f"{vol:.1%}", "Annual standard deviation"])
        
        if 'var_95' in risk_metrics:
            var = risk_metrics['var_95']
            risk_data.append(['Value at Risk (95%)', f"{var:.1%}", "Potential worst-case loss"])
        
        risk_table = Table(risk_data, colWidths=[2*inch, 1.5*inch, 2*inch])
        risk_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dc2626')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#fee2e2')),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(risk_table)
        
        return elements
    
    def _create_holdings_table(self, portfolio_data: Dict) -> List:
        """Create detailed holdings table"""
        elements = []
        
        elements.append(Paragraph(
            "<b>Portfolio Holdings</b>",
            self.styles['SectionHeader']
        ))
        
        holdings = portfolio_data.get('holdings', [])
        
        # Sort by value
        sorted_holdings = sorted(holdings, key=lambda x: x.get('value', 0), reverse=True)
        
        # Table data
        table_data = [['Ticker', 'Shares', 'Price', 'Value', 'Weight', 'Sector']]
        
        total_value = portfolio_data.get('total_value', 1)
        
        for holding in sorted_holdings[:20]:  # Top 20 holdings
            ticker = holding.get('ticker', 'N/A')
            shares = holding.get('quantity', 0)
            price = holding.get('current_price', 0)
            value = holding.get('value', 0)
            weight = (value / total_value * 100) if total_value > 0 else 0
            sector = holding.get('sector', 'N/A')[:15]  # Truncate long names
            
            table_data.append([
                ticker,
                f"{shares:.2f}",
                f"${price:.2f}",
                f"${value:,.0f}",
                f"{weight:.1f}%",
                sector
            ])
        
        holdings_table = Table(table_data, colWidths=[0.8*inch, 0.8*inch, 0.8*inch, 1.2*inch, 0.8*inch, 1.5*inch])
        holdings_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#059669')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0fdf4')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))
        
        elements.append(holdings_table)
        
        if len(holdings) > 20:
            elements.append(Spacer(1, 0.1*inch))
            elements.append(Paragraph(
                f"<i>Showing top 20 of {len(holdings)} total holdings</i>",
                self.styles['Normal']
            ))
        
        return elements
    
    def _create_allocation_section(self, analytics: Dict) -> List:
        """Create allocation analysis"""
        elements = []
        
        elements.append(Paragraph(
            "<b>Asset Allocation</b>",
            self.styles['SectionHeader']
        ))
        
        sectors = analytics.get('allocation', {}).get('sectors', {})
        
        if sectors:
            sector_data = [['Sector', 'Allocation']]
            for sector, weight in sorted(sectors.items(), key=lambda x: x[1], reverse=True):
                sector_data.append([sector, f"{weight:.1f}%"])
            
            sector_table = Table(sector_data, colWidths=[3*inch, 1.5*inch])
            sector_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#7c3aed')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#faf5ff')]),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey)
            ]))
            
            elements.append(sector_table)
        
        return elements
    
    def _create_ai_insights_section(self, ai_insights: Dict) -> List:
        """Create AI insights section"""
        elements = []
        
        elements.append(Paragraph(
            "<b>AI-Powered Insights</b>",
            self.styles['SectionHeader']
        ))
        
        # Risks
        if ai_insights.get('risks'):
            elements.append(Paragraph("<b>Identified Risks:</b>", self.styles['Heading3']))
            for risk in ai_insights['risks']:
                elements.append(Paragraph(f"• {risk}", self.styles['BodyText']))
            elements.append(Spacer(1, 0.2*inch))
        
        # Opportunities
        if ai_insights.get('opportunities'):
            elements.append(Paragraph("<b>Opportunities:</b>", self.styles['Heading3']))
            for opp in ai_insights['opportunities']:
                elements.append(Paragraph(f"• {opp}", self.styles['BodyText']))
        
        return elements
    
    def _create_recommendations_section(self, ai_insights: Dict) -> List:
        """Create recommendations section"""
        elements = []
        
        elements.append(Paragraph(
            "<b>Recommended Actions</b>",
            self.styles['SectionHeader']
        ))
        
        for i, rec in enumerate(ai_insights['recommendations'], 1):
            elements.append(Paragraph(
                f"<b>{i}.</b> {rec}",
                self.styles['BodyText']
            ))
            elements.append(Spacer(1, 0.1*inch))
        
        return elements
    
    def _create_disclaimer(self) -> List:
        """Create disclaimer section"""
        elements = []
        
        disclaimer_text = """
        <b>Disclaimer:</b> This report is for informational purposes only and does not constitute 
        investment advice. Past performance is not indicative of future results. Please consult 
        with a qualified financial advisor before making investment decisions.
        """
        
        elements.append(Paragraph(disclaimer_text, self.styles['Normal']))
        
        return elements
    
    def _get_largest_holding(self, holdings: List[Dict]) -> str:
        """Get largest holding by value"""
        if not holdings:
            return "N/A"
        largest = max(holdings, key=lambda x: x.get('value', 0))
        return f"{largest.get('ticker', 'N/A')} (${largest.get('value', 0):,.0f})"
    
    def _get_smallest_holding(self, holdings: List[Dict]) -> str:
        """Get smallest holding by value"""
        if not holdings:
            return "N/A"
        smallest = min(holdings, key=lambda x: x.get('value', 0))
        return f"{smallest.get('ticker', 'N/A')} (${smallest.get('value', 0):,.0f})"
    
    def _get_score_color(self, score: int) -> str:
        """Get color for portfolio score"""
        if score >= 80:
            return "#059669"  # Green
        elif score >= 60:
            return "#d97706"  # Yellow
        else:
            return "#dc2626"  # Red


# Global instance
_pdf_generator = None

def get_pdf_generator() -> EnhancedPDFReportGenerator:
    """Get or create PDF generator instance"""
    global _pdf_generator
    if _pdf_generator is None:
        _pdf_generator = EnhancedPDFReportGenerator()
    return _pdf_generator
