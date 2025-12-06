"""
Reports API for VisionWealth
Handles report generation requests with multiple format options
"""

from fastapi import APIRouter, Depends, HTTPException, Body, Query, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse, Response
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field
import logging
import tempfile
import zipfile
import shutil
import os
import traceback

from db import get_db
from models import User
from auth import get_current_active_user

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Models

class ReportGenerationRequest(BaseModel):
    """Request model for report generation"""
    portfolio_data: Dict[str, Any] = Field(..., description="Portfolio data including holdings, summary, and charts")
    client_name: Optional[str] = Field(None, description="Client name for report personalization")
    include_ai_insights: bool = Field(True, description="Whether to include AI-powered insights")
    report_format: Literal["pdf", "latex", "both"] = Field("pdf", description="Output format")


@router.post("/reports/generate", response_class=FileResponse, tags=["Reports"])
async def generate_report(
    portfolio_data: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_active_user),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Generate a PDF report with LaTeX fallback (Legacy endpoint)"""
    start_time = datetime.now()
    fallback_pdf_path = None
    build_dir = None
    zip_path = None
    
    try:
        logger.info(f"Generating report for user {current_user.id}")
        
        # Import dependencies
        try:
            import pdf_generator
            from latex_generator import LatexReportGenerator
        except ImportError as e:
            logger.error(f"Missing dependencies: {e}")
            raise HTTPException(status_code=500, detail="Report generation dependencies not available")
        
        client_name = current_user.full_name or "Client"
        analytics_data = portfolio_data.get('analytics', {})
        
        p_data = {
            'summary': portfolio_data.get('summary', {}),
            'charts': portfolio_data.get('charts', {}),
            'holdings': portfolio_data.get('holdings', [])
        }
        
        # 1. Generate Fallback PDF
        logger.info("Generating fallback PDF")
        temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        fallback_pdf_path = temp_pdf.name
        temp_pdf.close()
        
        try:
            pdf_generator.generate_portfolio_pdf(p_data, analytics_data, fallback_pdf_path, client_name=client_name)
            logger.info(f"Fallback PDF generated: {fallback_pdf_path}")
        except Exception as e:
            logger.error(f"Fallback PDF generation failed: {e}")
            raise HTTPException(status_code=500, detail=f"Fallback PDF generation failed: {str(e)}")
        
        # 2. Try LaTeX Generation
        logger.info("Attempting LaTeX generation")
        latex_gen = LatexReportGenerator()
        success, latex_result, build_dir = latex_gen.generate_report(p_data, analytics_data, "portfolio_report.pdf", client_name=client_name)
        
        # 3. Decision Logic
        if success:
            logger.info("LaTeX compilation successful")
            
            def cleanup():
                try:
                    if os.path.exists(fallback_pdf_path):
                        os.unlink(fallback_pdf_path)
                    if build_dir and os.path.exists(build_dir):
                        shutil.rmtree(build_dir, ignore_errors=True)
                except Exception as e:
                    logger.warning(f"Cleanup error: {e}")
            
            background_tasks.add_task(cleanup)
            
            generation_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Report generated in {generation_time:.2f}s")
            
            filename = f"Portfolio_Report_Pro_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            return FileResponse(
                latex_result,
                media_type='application/pdf',
                filename=filename,
                headers={"X-Generation-Time": str(generation_time), "X-Report-Format": "latex"}
            )
        else:
            # Create bundle
            logger.warning("LaTeX compilation failed, creating bundle")
            
            zip_filename = f"Portfolio_Report_Bundle_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
            zip_path = temp_zip.name
            temp_zip.close()
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.write(fallback_pdf_path, "Portfolio_Report_QuickView.pdf")
                
                if build_dir and os.path.exists(build_dir):
                    tex_source_name = "latex_source"
                    for root, dirs, files in os.walk(build_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            rel_path = os.path.relpath(file_path, build_dir)
                            arcname = os.path.join(tex_source_name, rel_path)
                            zf.write(file_path, arcname)
                
                readme_content = f"""
VisionWealth Portfolio Report Bundle
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Client: {client_name}

Contents:
1. Portfolio_Report_QuickView.pdf - Immediate viewing
2. latex_source/ - Professional LaTeX source

For Overleaf: Upload latex_source folder and recompile
                """
                zf.writestr("README.txt", readme_content)
            
            def cleanup_bundle():
                try:
                    if os.path.exists(fallback_pdf_path):
                        os.unlink(fallback_pdf_path)
                    if build_dir and os.path.exists(build_dir):
                        shutil.rmtree(build_dir, ignore_errors=True)
                except Exception as e:
                    logger.warning(f"Cleanup error: {e}")
            
            background_tasks.add_task(cleanup_bundle)
            
            generation_time = (datetime.now() - start_time).total_seconds()
            
            return FileResponse(
                zip_path,
                media_type='application/zip',
                filename=zip_filename,
                headers={"X-Generation-Time": str(generation_time), "X-Report-Format": "bundle"}
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Report generation error: {e}")
        logger.error(traceback.format_exc())
        
        try:
            if fallback_pdf_path and os.path.exists(fallback_pdf_path):
                os.unlink(fallback_pdf_path)
            if build_dir and os.path.exists(build_dir):
                shutil.rmtree(build_dir, ignore_errors=True)
            if zip_path and os.path.exists(zip_path):
                os.unlink(zip_path)
        except:
            pass
        
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


@router.post("/reports/generate-enhanced", response_class=Response, tags=["Reports"])
async def generate_enhanced_report(
    portfolio_data: Dict[str, Any] = Body(...),
    include_ai_insights: bool = Query(True, description="Include AI-powered insights"),
    current_user: User = Depends(get_current_active_user)
):
    """Generate enhanced PDF report with professional templates and AI insights"""
    start_time = datetime.now()
    
    try:
        logger.info(f"Generating enhanced report for user {current_user.id}, AI insights: {include_ai_insights}")
        
        try:
            from enhanced_pdf import get_pdf_generator
            from ai_service import get_ai_service
        except ImportError as e:
            logger.error(f"Missing dependencies: {e}")
            raise HTTPException(status_code=500, detail="Enhanced report generator not available")
        
        holdings = portfolio_data.get('holdings', [])
        analytics = portfolio_data.get('analytics', {})
        
        # Get AI insights if requested
        ai_insights = None
        ai_generation_time = 0
        
        if include_ai_insights:
            try:
                ai_start = datetime.now()
                ai_service = get_ai_service()
                
                if ai_service.is_available():
                    logger.info("Generating AI insights")
                    
                    portfolio_context = {
                        'holdings': holdings,
                        'total_value': sum(h.get('value', 0) for h in holdings),
                        'risk_metrics': analytics.get('risk_metrics', {}),
                        'sectors': analytics.get('allocation', {}).get('sectors', {}),
                        ' performance': analytics.get('performance', {})
                    }
                    
                    ai_insights = ai_service.generate_portfolio_analysis(portfolio_context)
                    ai_generation_time = (datetime.now() - ai_start).total_seconds()
                    logger.info(f"AI insights generated in {ai_generation_time:.2f}s")
                    
            except Exception as e:
                logger.warning(f"AI insights generation failed: {e}")
        
        # Generate PDF
        logger.info("Generating PDF report")
        pdf_start = datetime.now()
        
        pdf_generator = get_pdf_generator()
        pdf_bytes = pdf_generator.generate_report(
            portfolio_data=portfolio_data,
            analytics=analytics,
            ai_insights=ai_insights,
            client_name=current_user.full_name or "Client"
        )
        
        pdf_generation_time = (datetime.now() - pdf_start).total_seconds()
        total_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"PDF generated in {pdf_generation_time:.2f}s, total time: {total_time:.2f}s")
        
        filename = f"Portfolio_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        file_size_kb = len(pdf_bytes) / 1024
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "X-Generation-Time": str(total_time),
                "X-AI-Time": str(ai_generation_time),
                "X-PDF-Time": str(pdf_generation_time),
                "X-File-Size-KB": str(file_size_kb),
                "X-AI-Included": str(include_ai_insights and ai_insights is not None)
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Enhanced report generation error: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


@router.post("/reports/preview", tags=["Reports"])
async def generate_report_preview(
    portfolio_data: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_active_user)
):
    """Generate a quick preview of what the report will contain"""
    try:
        holdings = portfolio_data.get('holdings', [])
        analytics = portfolio_data.get('analytics', {})
        
        total_value = sum(h.get('value', 0) for h in holdings)
        num_holdings = len(holdings)
        
        has_risk_metrics = bool(analytics.get('risk_metrics'))
        has_allocation = bool(analytics.get('allocation'))
        has_performance = bool(analytics.get('performance'))
        
        preview = {
            "metadata": {
                "client_name": current_user.full_name or "Client",
                "generation_date": datetime.now().isoformat(),
                "report_type": "Enhanced Portfolio Analysis"
            },
            "summary": {
                "total_holdings": num_holdings,
                "total_value": total_value,
                "has_risk_analysis": has_risk_metrics,
                "has_allocation_data": has_allocation,
                "has_performance_data": has_performance
            },
            "sections": {
                "cover_page": True,
                "executive_summary": True,
                "holdings_table": num_holdings > 0,
                "risk_analysis": has_risk_metrics,
                "sector_allocation": has_allocation,
                "performance_metrics": has_performance,
                "recommendations": True
            },
            "data_quality": {
                "completeness_score": sum([num_holdings > 0, has_risk_metrics, has_allocation, has_performance]) / 4 * 100,
                "warnings": []
            }
        }
        
        if num_holdings == 0:
            preview["data_quality"]["warnings"].append("No holdings data provided")
        if not has_risk_metrics:
            preview["data_quality"]["warnings"].append("Risk metrics missing")
        if not has_allocation:
            preview["data_quality"]["warnings"].append("Allocation data missing")
        
        return preview
    
    except Exception as e:
        logger.error(f"Preview generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Preview generation failed: {str(e)}")


@router.get("/reports/formats", tags=["Reports"])
async def get_report_formats():
    """Get information about available report formats"""
    return {
        "formats": [
            {
                "id": "enhanced_pdf",
                "name": "Enhanced PDF Report",
                "description": "Professional PDF with AI insights and advanced formatting",
                "features": ["Professional cover page", "AI-powered insights", "Risk analysis", "Sector allocation charts", "Performance metrics", "Recommendations"],
                "endpoint": "/reports/generate-enhanced",
                "typical_generation_time": "2-5 seconds",
                "recommended_for": "Most users - best balance of quality and speed"
            },
            {
                "id": "latex_pdf",
                "name": "LaTeX Professional Report",
                "description": "Publication-quality PDF with LaTeX typesetting",
                "features": ["Professional typesetting", "High-quality formatting", "Source code included if compilation fails", "Customizable templates"],
                "endpoint": "/reports/generate",
                "typical_generation_time": "5-10 seconds",
                "recommended_for": "Users who need publication-quality output",
                "note": "May return ZIP bundle if LaTeX compiler unavailable"
            }
        ],
        "default_format": "enhanced_pdf",
        "ai_insights_available": True
    }


@router.get("/reports/status", tags=["Reports"])
async def get_report_status():
    """Check the status and availability of report generation services"""
    try:
        status = {"service": "operational", "generators": {}, "features": {}}
        
        try:
            import pdf_generator
            status["generators"]["basic_pdf"] = "available"
        except ImportError:
            status["generators"]["basic_pdf"] = "unavailable"
        
        try:
            from latex_generator import LatexReportGenerator
            status["generators"]["latex"] = "available"
            
            import shutil
            if shutil.which('pdflatex'):
                status["features"]["latex_compilation"] = "available"
            else:
                status["features"]["latex_compilation"] = "unavailable"
        except ImportError:
            status["generators"]["latex"] = "unavailable"
        
        try:
            from enhanced_pdf import get_pdf_generator
            status["generators"]["enhanced_pdf"] = "available"
        except ImportError:
            status["generators"]["enhanced_pdf"] = "unavailable"
        
        try:
            from ai_service import get_ai_service
            ai_service = get_ai_service()
            status["features"]["ai_insights"] = "available" if ai_service.is_available() else "unavailable"
        except ImportError:
            status["features"]["ai_insights"] = "unavailable"
        
        return status
    
    except Exception as e:
        logger.error(f"Status check error: {e}")
        return {"service": "degraded", "error": str(e)}
