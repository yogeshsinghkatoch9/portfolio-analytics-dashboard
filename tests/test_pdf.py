
import sys
import os
sys.path.append('backend')
import pdf_generator

def test_pdf_generation():
    try:
        with open('sample_portfolio.xlsx', 'rb') as f:
            content = f.read()
        
        output_path = 'test_output.pdf'
        print(f"Testing PDF generation with sample_portfolio.xlsx...")
        pdf_generator.generate_pdf_from_upload(content, 'sample_portfolio.xlsx', output_path)
        print(f"Success! PDF generated at {output_path}")
    except Exception as e:
        print(f"Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pdf_generation()
