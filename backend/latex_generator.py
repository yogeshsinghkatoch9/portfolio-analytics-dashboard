
import os
import jinja2
import pandas as pd
from datetime import datetime
import subprocess
import tempfile
import matplotlib.pyplot as plt
import io
import shutil

class LatexReportGenerator:
    def __init__(self, template_dir="templates"):
        # Set up Jinja2 environment with custom delimiters to avoid conflict with Latex
        self.template_loader = jinja2.FileSystemLoader(searchpath=os.path.join(os.path.dirname(__file__), template_dir))
        self.template_env = jinja2.Environment(
            loader=self.template_loader,
            block_start_string='\BLOCK{',
            block_end_string='}',
            variable_start_string='\VAR{',
            variable_end_string='}',
            comment_start_string='\#{',
            comment_end_string='}',
            line_statement_prefix='%%',
            line_comment_prefix='%#',
            trim_blocks=True,
            autoescape=False,
        )

    def escape_latex(self, text):
        """Escape special Latex characters"""
        if not isinstance(text, str):
            return text
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

    def generate_charts(self, df, output_dir):
        """Generate charts and save as PNGs in output_dir"""
        charts = {}
        
        # Allocation by Symbol
        plt.figure(figsize=(6, 4))
        # Top 10 + Other
        top_10 = df.nlargest(10, 'Value ($)')
        other_val = df['Value ($)'].sum() - top_10['Value ($)'].sum()
        
        labels = top_10['Symbol'].tolist()
        values = top_10['Value ($)'].tolist()
        
        if other_val > 0:
            labels.append('Other')
            values.append(other_val)
            
        plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=90)
        plt.title('Asset Allocation')
        plt.tight_layout()
        
        alloc_path = os.path.join(output_dir, 'allocation.png')
        plt.savefig(alloc_path, dpi=150)
        plt.close()
        charts['allocation'] = 'allocation.png'

        # Sector Allocation if possible
        if 'Asset Type' in df.columns:
            plt.figure(figsize=(6, 4))
            sector_counts = df.groupby('Asset Type')['Value ($)'].sum()
            sector_counts.plot(kind='pie', autopct='%1.1f%%', startangle=90)
            plt.title('Asset Allocation by Type')
            plt.ylabel('')
            plt.tight_layout()
            
            sector_path = os.path.join(output_dir, 'sector.png')
            plt.savefig(sector_path, dpi=150)
            plt.close()
            charts['sector'] = 'sector.png'
            
        return charts

    def generate_report(self, portfolio_data, analytics_data, output_path, client_name="Client"):
        """
        Generate Latex report.
        Returns tuple: (success, pdf_path_or_err, latex_source_path)
        """
        
        # Prepare context data
        summary = portfolio_data.get('summary', {})
        holdings_raw = portfolio_data.get('holdings', [])
        
        # Format holdings for Latex
        holdings = []
        for h in holdings_raw:
            holdings.append({
                'Symbol': self.escape_latex(h.get('Symbol', '')),
                'Description': self.escape_latex(h.get('Description', '')),
                'Quantity': f"{h.get('Quantity', 0):,.2f}",
                'Value': f"\\${h.get('Value ($)', 0):,.2f}",
                'Assets': f"{h.get('Assets (%)', 0):.2f}\\%"
            })

        # Format Summary
        formatted_summary = {
            'total_value': f"\\${summary.get('total_value', 0):,.2f}",
            'total_gain_loss': f"\\${summary.get('total_gain_loss', 0):,.2f}",
            'gain_loss_color': 'success' if summary.get('total_gain_loss', 0) >= 0 else 'danger',
            'total_return_pct': f"{summary.get('overall_return_pct', 0):.2f}",
            'num_holdings': str(summary.get('num_holdings', 0)),
            'total_annual_income': f"\\${summary.get('total_annual_income', 0):,.2f}",
            'avg_yield': f"{summary.get('avg_yield', 0):.2f}"
        }

        # Format Dividend Payer
        div_metrics = analytics_data.get('dividend_metrics', {})
        top_payers = []
        if div_metrics:
            for p in div_metrics.get('top_dividend_payers', [])[:5]:
                top_payers.append({
                    'Symbol': self.escape_latex(p.get('Symbol', '')),
                    'Income': f"\\${p.get('Est Annual Income ($)', 0):,.2f}",
                    'Yield': f"{p.get('Current Yld/Dist Rate (%)', 0):.2f}"
                })
            div_metrics['top_dividend_payers'] = top_payers
            analytics_data['dividend_metrics'] = div_metrics

        # Create temporary directory for building
        build_dir = tempfile.mkdtemp()
        
        try:
            # Generate charts
            df = pd.DataFrame(holdings_raw) # Re-create DF for chart utils if needed, or pass DF
            # Actually easier to use the raw list if possible, but our chart func expects DF-like or we can just reconstruct
            # For simplicity, let's assume valid DF columns exists in holdings_raw list of dicts
            df_chart = pd.DataFrame(holdings_raw)
            charts = self.generate_charts(df_chart, build_dir)

            context = {
                'client_name': self.escape_latex(client_name),
                'date': datetime.now().strftime('%B %d, %Y'),
                'summary': formatted_summary,
                'holdings': holdings,
                'analytics': analytics_data,
                'charts': charts
            }

            # Render template
            template = self.template_env.get_template('report_template.tex')
            latex_source = template.render(context)
            
            tex_filename = 'portfolio_report.tex'
            tex_path = os.path.join(build_dir, tex_filename)
            
            with open(tex_path, 'w') as f:
                f.write(latex_source)
            
            # Attempt compilation
            try:
                # Check for pdflatex first
                subprocess.run(['pdflatex', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                
                # specific compilation command
                subprocess.run(['pdflatex', '-interaction=nonstopmode', tex_filename], cwd=build_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                
                # Check if PDF exists
                pdf_filename = 'portfolio_report.pdf'
                pdf_generated_path = os.path.join(build_dir, pdf_filename)
                
                if os.path.exists(pdf_generated_path):
                    # Move PDF to output path
                    shutil.copy(pdf_generated_path, output_path)
                    return True, output_path, tex_path
                else:
                    return False, "PDF not generated despite success exit code", tex_path
                    
            except (subprocess.CalledProcessError, FileNotFoundError):
                # Compilation failed or pdflatex missing
                # Return the path to the Tex file and images (we will zip them up in the caller)
                return False, "pdflatex not found or compilation failed", build_dir

        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, str(e), build_dir
