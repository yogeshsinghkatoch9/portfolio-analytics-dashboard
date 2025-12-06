"""
LaTeX Report Generator for Portfolio Reports
Generates professional, publication-quality PDF reports using LaTeX
with fallback to source distribution if compilation fails
"""

import os
import jinja2
import pandas as pd
import numpy as np
from datetime import datetime
import subprocess
import tempfile
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
import io
import shutil
import logging
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set style for matplotlib
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")


class LatexReportGenerator:
    """
    Professional LaTeX report generator for portfolio analysis.
    
    Features:
    - Custom Jinja2 delimiters to avoid LaTeX conflicts
    - Automatic chart generation with matplotlib
    - LaTeX special character escaping
    - Graceful fallback if pdflatex not available
    - Professional formatting and styling
    """
    
    def __init__(self, template_dir: str = "templates"):
        """
        Initialize LaTeX report generator.
        
        Args:
            template_dir: Directory containing LaTeX templates
        """
        self.template_dir = template_dir
        
        # Set up Jinja2 environment with custom delimiters
        # Custom delimiters prevent conflicts with LaTeX syntax
        template_path = os.path.join(os.path.dirname(__file__), template_dir)
        
        if not os.path.exists(template_path):
            logger.warning(f"Template directory not found: {template_path}")
            # Create directory if it doesn't exist
            os.makedirs(template_path, exist_ok=True)
        
        self.template_loader = jinja2.FileSystemLoader(searchpath=template_path)
        self.template_env = jinja2.Environment(
            loader=self.template_loader,
            block_start_string=r'\BLOCK{',
            block_end_string='}',
            variable_start_string=r'\VAR{',
            variable_end_string='}',
            comment_start_string=r'\#{',
            comment_end_string='}',
            line_statement_prefix='%%',
            line_comment_prefix='%#',
            trim_blocks=True,
            autoescape=False,
        )
        
        # Add custom filters
        self.template_env.filters['escape_latex'] = self.escape_latex
        self.template_env.filters['format_currency'] = self.format_currency
        self.template_env.filters['format_percent'] = self.format_percent
        
        logger.info("LaTeX report generator initialized")
    
    def escape_latex(self, text: Any) -> str:
        """
        Escape special LaTeX characters.
        
        Args:
            text: Text to escape
        
        Returns:
            LaTeX-safe string
        """
        if not isinstance(text, str):
            return str(text)
        
        # LaTeX special characters
        chars = {
            '&': r'\&',
            '%': r'\%',
            '$': r'\$',
            '#': r'\#',
            '_': r'\_',
            '{': r'\{',
            '}': r'\}',
            '~': r'\textasciitilde{}',
            '^': r'\^{}',
            '\\': r'\textbackslash{}',
        }
        
        return "".join([chars.get(c, c) for c in text])
    
    def format_currency(self, value: float, symbol: str = r'\$') -> str:
        """
        Format value as currency for LaTeX.
        
        Args:
            value: Numeric value
            symbol: Currency symbol (default: $)
        
        Returns:
            Formatted currency string
        """
        try:
            return f"{symbol}{abs(value):,.2f}"
        except (ValueError, TypeError):
            return f"{symbol}0.00"
    
    def format_percent(self, value: float, decimals: int = 2) -> str:
        """
        Format value as percentage for LaTeX.
        
        Args:
            value: Numeric value
            decimals: Decimal places
        
        Returns:
            Formatted percentage string
        """
        try:
            return f"{value:.{decimals}f}\\%"
        except (ValueError, TypeError):
            return "0.00\\%"
    
    def generate_charts(
        self,
        df: pd.DataFrame,
        output_dir: str,
        charts_data: Optional[Dict] = None
    ) -> Dict[str, str]:
        """
        Generate portfolio charts and save as PNG files.
        
        Args:
            df: Portfolio DataFrame
            output_dir: Directory to save chart images
            charts_data: Optional pre-computed chart data
        
        Returns:
            Dictionary mapping chart names to filenames
        """
        charts = {}
        
        try:
            # 1. Asset Allocation Pie Chart
            logger.info("Generating asset allocation chart")
            
            fig, ax = plt.subplots(figsize=(8, 6))
            
            # Get top 10 holdings
            top_10 = df.nlargest(10, 'Value ($)')
            other_val = df['Value ($)'].sum() - top_10['Value ($)'].sum()
            
            labels = top_10['Symbol'].tolist()
            values = top_10['Value ($)'].tolist()
            
            if other_val > 0:
                labels.append('Other')
                values.append(other_val)
            
            # Create pie chart with better styling
            colors = plt.cm.Set3(range(len(labels)))
            wedges, texts, autotexts = ax.pie(
                values,
                labels=labels,
                autopct='%1.1f%%',
                startangle=90,
                colors=colors,
                textprops={'fontsize': 10}
            )
            
            # Enhance text readability
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
            
            ax.set_title('Portfolio Allocation by Holding', fontsize=14, fontweight='bold', pad=20)
            plt.tight_layout()
            
            alloc_path = os.path.join(output_dir, 'allocation.png')
            plt.savefig(alloc_path, dpi=300, bbox_inches='tight', facecolor='white')
            plt.close(fig)
            
            charts['allocation'] = 'allocation.png'
            logger.info("Asset allocation chart generated")
            
        except Exception as e:
            logger.error(f"Failed to generate allocation chart: {e}")
        
        try:
            # 2. Asset Type Distribution
            if 'Asset Type' in df.columns:
                logger.info("Generating asset type chart")
                
                fig, ax = plt.subplots(figsize=(8, 6))
                
                asset_type_data = df.groupby('Asset Type')['Value ($)'].sum()
                
                if not asset_type_data.empty:
                    colors = plt.cm.Pastel1(range(len(asset_type_data)))
                    wedges, texts, autotexts = ax.pie(
                        asset_type_data.values,
                        labels=asset_type_data.index,
                        autopct='%1.1f%%',
                        startangle=90,
                        colors=colors,
                        textprops={'fontsize': 10}
                    )
                    
                    for autotext in autotexts:
                        autotext.set_color('white')
                        autotext.set_fontweight('bold')
                    
                    ax.set_title('Asset Allocation by Type', fontsize=14, fontweight='bold', pad=20)
                    plt.tight_layout()
                    
                    sector_path = os.path.join(output_dir, 'asset_type.png')
                    plt.savefig(sector_path, dpi=300, bbox_inches='tight', facecolor='white')
                    plt.close(fig)
                    
                    charts['asset_type'] = 'asset_type.png'
                    logger.info("Asset type chart generated")
        
        except Exception as e:
            logger.error(f"Failed to generate asset type chart: {e}")
        
        try:
            # 3. Top Gainers/Losers Bar Chart
            if 'NFS G/L ($)' in df.columns:
                logger.info("Generating gainers/losers chart")
                
                fig, ax = plt.subplots(figsize=(10, 6))
                
                # Get top 5 gainers and losers
                top_gainers = df.nlargest(5, 'NFS G/L ($)')
                top_losers = df.nsmallest(5, 'NFS G/L ($)')
                
                combined = pd.concat([top_losers, top_gainers])
                
                colors = ['red' if x < 0 else 'green' for x in combined['NFS G/L ($)']]
                
                ax.barh(combined['Symbol'], combined['NFS G/L ($)'], color=colors, alpha=0.7)
                ax.set_xlabel('Gain/Loss ($)', fontsize=12, fontweight='bold')
                ax.set_ylabel('Symbol', fontsize=12, fontweight='bold')
                ax.set_title('Top Gainers and Losers', fontsize=14, fontweight='bold', pad=20)
                ax.axvline(x=0, color='black', linestyle='--', linewidth=0.8)
                ax.grid(axis='x', alpha=0.3)
                
                plt.tight_layout()
                
                gainloss_path = os.path.join(output_dir, 'gainers_losers.png')
                plt.savefig(gainloss_path, dpi=300, bbox_inches='tight', facecolor='white')
                plt.close(fig)
                
                charts['gainers_losers'] = 'gainers_losers.png'
                logger.info("Gainers/losers chart generated")
        
        except Exception as e:
            logger.error(f"Failed to generate gainers/losers chart: {e}")
        
        try:
            # 4. Dividend Yield Distribution
            if 'Current Yld/Dist Rate (%)' in df.columns:
                logger.info("Generating dividend yield chart")
                
                # Filter holdings with dividends
                dividend_holders = df[df['Current Yld/Dist Rate (%)'] > 0].copy()
                
                if not dividend_holders.empty and len(dividend_holders) > 0:
                    fig, ax = plt.subplots(figsize=(10, 6))
                    
                    # Get top 10 dividend payers
                    top_div = dividend_holders.nlargest(10, 'Current Yld/Dist Rate (%)')
                    
                    ax.bar(
                        top_div['Symbol'],
                        top_div['Current Yld/Dist Rate (%)'],
                        color='steelblue',
                        alpha=0.7
                    )
                    ax.set_xlabel('Symbol', fontsize=12, fontweight='bold')
                    ax.set_ylabel('Dividend Yield (%)', fontsize=12, fontweight='bold')
                    ax.set_title('Top Dividend Yields', fontsize=14, fontweight='bold', pad=20)
                    ax.grid(axis='y', alpha=0.3)
                    
                    plt.xticks(rotation=45, ha='right')
                    plt.tight_layout()
                    
                    div_path = os.path.join(output_dir, 'dividend_yields.png')
                    plt.savefig(div_path, dpi=300, bbox_inches='tight', facecolor='white')
                    plt.close(fig)
                    
                    charts['dividend_yields'] = 'dividend_yields.png'
                    logger.info("Dividend yield chart generated")
        
        except Exception as e:
            logger.error(f"Failed to generate dividend yield chart: {e}")
        
        logger.info(f"Generated {len(charts)} charts successfully")
        
        return charts
    
    def format_holdings_table(self, holdings_raw: List[Dict]) -> List[Dict]:
        """
        Format holdings data for LaTeX table.
        
        Args:
            holdings_raw: Raw holdings data
        
        Returns:
            Formatted holdings for LaTeX
        """
        holdings = []
        
        for h in holdings_raw:
            holdings.append({
                'Symbol': self.escape_latex(str(h.get('Symbol', ''))),
                'Description': self.escape_latex(str(h.get('Description', ''))),
                'Quantity': f"{h.get('Quantity', 0):,.2f}",
                'Price': self.format_currency(h.get('Price ($)', 0)),
                'Value': self.format_currency(h.get('Value ($)', 0)),
                'Assets': self.format_percent(h.get('Assets (%)', 0)),
                'GainLoss': self.format_currency(h.get('NFS G/L ($)', 0)),
                'GainLossPct': self.format_percent(h.get('NFS G/L (%)', 0))
            })
        
        return holdings
    
    def format_summary(self, summary: Dict) -> Dict:
        """
        Format summary data for LaTeX.
        
        Args:
            summary: Raw summary data
        
        Returns:
            Formatted summary
        """
        total_gain_loss = summary.get('total_gain_loss', 0)
        
        formatted = {
            'total_value': self.format_currency(summary.get('total_value', 0)),
            'total_principal': self.format_currency(summary.get('total_principal', 0)),
            'total_gain_loss': self.format_currency(total_gain_loss),
            'gain_loss_color': 'green' if total_gain_loss >= 0 else 'red',
            'total_return_pct': self.format_percent(summary.get('overall_return_pct', 0)),
            'num_holdings': str(summary.get('num_holdings', 0)),
            'total_annual_income': self.format_currency(summary.get('total_annual_income', 0)),
            'avg_yield': self.format_percent(summary.get('avg_yield', 0)),
            'daily_change': self.format_currency(summary.get('total_daily_change', 0)),
            'daily_change_pct': self.format_percent(summary.get('daily_return_pct', 0))
        }
        
        return formatted
    
    def format_analytics(self, analytics_data: Dict) -> Dict:
        """
        Format analytics data for LaTeX.
        
        Args:
            analytics_data: Raw analytics data
        
        Returns:
            Formatted analytics
        """
        formatted = {}
        
        # Risk Metrics
        if 'risk_metrics' in analytics_data:
            risk = analytics_data['risk_metrics']
            formatted['risk_metrics'] = {
                'volatility': self.format_percent(risk.get('portfolio_volatility', 0)),
                'sharpe_ratio': f"{risk.get('sharpe_ratio', 0):.2f}",
                'var_95': self.format_percent(risk.get('var_95', 0)),
                'beta': f"{risk.get('beta', 0):.2f}"
            }
        
        # Diversification
        if 'diversification' in analytics_data:
            div = analytics_data['diversification']
            formatted['diversification'] = {
                'score': f"{div.get('diversification_score', 0):.2f}",
                'hhi': f"{div.get('hhi_index', 0):.4f}"
            }
        
        # Dividend Metrics
        if 'dividend_metrics' in analytics_data:
            div_metrics = analytics_data['dividend_metrics']
            
            # Format top dividend payers
            top_payers = []
            for p in div_metrics.get('top_dividend_payers', [])[:5]:
                top_payers.append({
                    'Symbol': self.escape_latex(str(p.get('Symbol', ''))),
                    'Income': self.format_currency(p.get('Est Annual Income ($)', 0)),
                    'Yield': self.format_percent(p.get('Current Yld/Dist Rate (%)', 0))
                })
            
            formatted['dividend_metrics'] = {
                'total_annual_income': self.format_currency(
                    div_metrics.get('total_annual_income', 0)
                ),
                'avg_yield': self.format_percent(div_metrics.get('portfolio_yield', 0)),
                'top_payers': top_payers
            }
        
        return formatted
    
    def check_pdflatex_available(self) -> bool:
        """
        Check if pdflatex is available on the system.
        
        Returns:
            True if pdflatex is available, False otherwise
        """
        try:
            result = subprocess.run(
                ['pdflatex', '--version'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def compile_latex(
        self,
        tex_path: str,
        build_dir: str,
        runs: int = 2
    ) -> Tuple[bool, Optional[str]]:
        """
        Compile LaTeX document to PDF.
        
        Args:
            tex_path: Path to .tex file
            build_dir: Build directory
            runs: Number of pdflatex runs (for references)
        
        Returns:
            Tuple of (success, pdf_path or error_message)
        """
        tex_filename = os.path.basename(tex_path)
        pdf_filename = tex_filename.replace('.tex', '.pdf')
        pdf_path = os.path.join(build_dir, pdf_filename)
        
        try:
            # Run pdflatex multiple times for references
            for run in range(runs):
                logger.info(f"Running pdflatex (pass {run + 1}/{runs})")
                
                result = subprocess.run(
                    ['pdflatex', '-interaction=nonstopmode', tex_filename],
                    cwd=build_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=30
                )
                
                if result.returncode != 0:
                    error_msg = result.stderr.decode('utf-8', errors='ignore')
                    logger.error(f"pdflatex failed: {error_msg}")
                    return False, f"Compilation error: {error_msg[:500]}"
            
            # Check if PDF was generated
            if os.path.exists(pdf_path):
                logger.info("PDF successfully generated")
                return True, pdf_path
            else:
                return False, "PDF file not generated"
        
        except subprocess.TimeoutExpired:
            return False, "Compilation timeout"
        except Exception as e:
            return False, f"Compilation exception: {str(e)}"
    
    def generate_report(
        self,
        portfolio_data: Dict,
        analytics_data: Dict,
        output_path: str,
        client_name: str = "Client"
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Generate LaTeX portfolio report.
        
        Args:
            portfolio_data: Portfolio data (summary, holdings, charts)
            analytics_data: Analytics data (risk, diversification, etc.)
            output_path: Output path for PDF (if successful)
            client_name: Client name for report
        
        Returns:
            Tuple of (success, result_path_or_error, build_dir)
            - success: True if PDF generated successfully
            - result_path_or_error: PDF path if success, error message otherwise
            - build_dir: Build directory with source files
        """
        logger.info(f"Starting LaTeX report generation for client: {client_name}")
        
        # Create temporary build directory
        build_dir = tempfile.mkdtemp(prefix='latex_report_')
        logger.info(f"Build directory: {build_dir}")
        
        try:
            # Extract data
            summary = portfolio_data.get('summary', {})
            holdings_raw = portfolio_data.get('holdings', [])
            
            # Format data for LaTeX
            holdings = self.format_holdings_table(holdings_raw)
            formatted_summary = self.format_summary(summary)
            formatted_analytics = self.format_analytics(analytics_data)
            
            # Generate charts
            df_chart = pd.DataFrame(holdings_raw)
            charts = self.generate_charts(df_chart, build_dir)
            
            # Prepare context for template
            context = {
                'client_name': self.escape_latex(client_name),
                'date': datetime.now().strftime('%B %d, %Y'),
                'summary': formatted_summary,
                'holdings': holdings[:50],  # Limit to 50 for PDF
                'total_holdings': len(holdings),
                'analytics': formatted_analytics,
                'charts': charts,
                'report_title': f"Portfolio Analysis Report for {self.escape_latex(client_name)}"
            }
            
            # Render LaTeX template
            try:
                template = self.template_env.get_template('report_template.tex')
                latex_source = template.render(context)
            except jinja2.TemplateNotFound:
                logger.warning("Template not found, using fallback template")
                latex_source = self._generate_fallback_template(context)
            
            # Write LaTeX source
            tex_filename = 'portfolio_report.tex'
            tex_path = os.path.join(build_dir, tex_filename)
            
            with open(tex_path, 'w', encoding='utf-8') as f:
                f.write(latex_source)
            
            logger.info("LaTeX source written successfully")
            
            # Check if pdflatex is available
            if not self.check_pdflatex_available():
                logger.warning("pdflatex not available, returning source files")
                return False, "pdflatex not found on system", build_dir
            
            # Compile LaTeX to PDF
            success, result = self.compile_latex(tex_path, build_dir)
            
            if success:
                # Copy PDF to output path
                shutil.copy(result, output_path)
                logger.info(f"PDF successfully generated: {output_path}")
                return True, output_path, build_dir
            else:
                logger.error(f"LaTeX compilation failed: {result}")
                return False, result, build_dir
        
        except Exception as e:
            logger.error(f"Report generation failed: {e}", exc_info=True)
            return False, str(e), build_dir
    
    def _generate_fallback_template(self, context: Dict) -> str:
        """
        Generate a basic LaTeX template if template file not found.
        
        Args:
            context: Template context
        
        Returns:
            LaTeX source code
        """
        latex = r"""
\documentclass[11pt,letterpaper]{article}
\usepackage[utf8]{inputenc}
\usepackage[margin=1in]{geometry}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{fancyhdr}
\usepackage{xcolor}

\pagestyle{fancy}
\fancyhf{}
\rhead{Portfolio Report}
\lhead{""" + context['client_name'] + r"""}
\cfoot{\thepage}

\title{Portfolio Analysis Report}
\author{""" + context['client_name'] + r"""}
\date{""" + context['date'] + r"""}

\begin{document}

\maketitle
\thispagestyle{empty}

\section{Executive Summary}

\begin{itemize}
\item Total Value: """ + context['summary']['total_value'] + r"""
\item Total Return: """ + context['summary']['total_return_pct'] + r"""
\item Number of Holdings: """ + context['summary']['num_holdings'] + r"""
\end{itemize}

\section{Portfolio Holdings}

Holdings table would appear here.

\section{Analytics}

Analytics would appear here.

\end{document}
        """
        return latex


# Convenience function
def generate_latex_report(
    portfolio_data: Dict,
    analytics_data: Dict,
    output_path: str,
    client_name: str = "Client"
) -> Tuple[bool, str, Optional[str]]:
    """
    Convenience function to generate LaTeX report.
    
    Args:
        portfolio_data: Portfolio data
        analytics_data: Analytics data
        output_path: Output PDF path
        client_name: Client name
    
    Returns:
        Tuple of (success, result, build_dir)
    """
    generator = LatexReportGenerator()
    return generator.generate_report(
        portfolio_data,
        analytics_data,
        output_path,
        client_name
    )
