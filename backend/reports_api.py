"""
Reports API for VisionWealth
Handles report generation requests
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Dict, Any

from database import get_db
from models import User
from auth import get_current_active_user
from report_service import ReportService

router = APIRouter()


@router.post("/reports/generate")
async def generate_report(
    portfolio_data: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_active_user)
):
    """
    Generate a PDF report (Latex with Fallback)
    """
    try:
        import pdf_generator
        import tempfile
        import zipfile
        import shutil
        import os
        from latex_generator import LatexReportGenerator
        from fastapi.responses import FileResponse
        from datetime import datetime
        
        client_name = current_user.full_name or "Client"
        # client_name = "Client" # Temp fallback while auth disabled for test
        
        analytics_data = portfolio_data.get('analytics', {})
        
        # 1. Generate Fallback PDF
        temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        fallback_pdf_path = temp_pdf.name
        temp_pdf.close()
        
        # Ensure 'summary', 'charts', 'holdings' exist
        p_data = {
            'summary': portfolio_data.get('summary', {}),
            'charts': portfolio_data.get('charts', {}),
            'holdings': portfolio_data.get('holdings', [])
        }
        
        pdf_generator.generate_portfolio_pdf(p_data, analytics_data, fallback_pdf_path, client_name=client_name)

        # 2. Try Latex Generation
        latex_gen = LatexReportGenerator()
        success, latex_result, build_dir = latex_gen.generate_report(p_data, analytics_data, "unused.pdf", client_name=client_name)

        # Decision Logic
        if success:
            os.unlink(fallback_pdf_path)
            shutil.rmtree(build_dir, ignore_errors=True)
            return FileResponse(
                latex_result, 
                media_type='application/pdf', 
                filename=f"Portfolio_Report_Pro_{datetime.now().strftime('%Y%m%d')}.pdf"
            )
        else:
            zip_filename = f"Portfolio_Report_Bundle_{datetime.now().strftime('%Y%m%d')}.zip"
            temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
            zip_path = temp_zip.name
            temp_zip.close()

            with zipfile.ZipFile(zip_path, 'w') as zf:
                zf.write(fallback_pdf_path, "Portfolio_Report_QuickView.pdf")
                tex_source_name = "latex_source"
                for root, dirs, files in os.walk(build_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.join(tex_source_name, file)
                        zf.write(file_path, arcname)
                
                readme_content = """
VisionWealth Portfolio Report Bundle
====================================

This bundle contains two versions of your report:

1. Portfolio_Report_QuickView.pdf
   - This was generated immediately for your convenience.

2. latex_source/
   - This folder contains the professional Latex source code.
   - We attempted to compile this into a high-quality PDF but 'pdflatex' was not found.
   - You can upload this folder to Overleaf or compile locally.

Thank you for using VisionWealth.
                """
                zf.writestr("README.txt", readme_content)

            os.unlink(fallback_pdf_path)
            if build_dir and os.path.exists(build_dir):
                shutil.rmtree(build_dir, ignore_errors=True)
            
            return FileResponse(
                zip_path,
                media_type='application/zip',
                filename=zip_filename
            )

    except Exception as e:
        print(f"Report generation error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reports/generate-enhanced")
async def generate_enhanced_report(
    portfolio_data: Dict[str, Any] = Body(...),
    include_ai_insights: bool = True
):
    """
    Generate enhanced PDF report with professional templates and AI insights
    
    Returns a beautifully formatted PDF with:
    - Professional cover page
    - Executive summary (AI-powered if enabled)
    - Risk analysis
    - Holdings tables
    - Sector allocation
    - AI recommendations
    """
    try:
        from enhanced_pdf import get_pdf_generator
        from ai_service import get_ai_service
        from fastapi.responses import Response
        from datetime import datetime
        
        # Extract data
        holdings = portfolio_data.get('holdings', [])
        analytics = portfolio_data.get('analytics', {})
        
        # Get AI insights if requested
        ai_insights = None
        if include_ai_insights:
            try:
                ai_service = get_ai_service()
                if ai_service.is_available():
                    portfolio_context = {
                        'holdings': holdings,
                        'total_value': sum(h.get('value', 0) for h in holdings),
                        'risk_metrics': analytics.get('risk_metrics', {}),
                        'sectors': analytics.get('allocation', {}).get('sectors', {})
                    }
                    ai_insights = ai_service.generate_portfolio_analysis(portfolio_context)
            except Exception as e:
                logger.warning(f"AI insights generation failed: {e}")
                # Continue without AI insights
        
        #Generate PDF
        pdf_generator = get_pdf_generator()
        pdf_bytes = pdf_generator.generate_report(
            portfolio_data=portfolio_data,
            analytics=analytics,
            ai_insights=ai_insights
        )
        
        # Return PDF
        filename = f"Portfolio_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except Exception as e:
        logger.error(f"Enhanced report generation error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")
