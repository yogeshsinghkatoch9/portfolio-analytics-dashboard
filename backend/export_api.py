"""
Export API for VisionWealth
Handles CSV export of portfolio data
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import StreamingResponse
from typing import Dict, Any
import pandas as pd
from io import BytesIO, StringIO

from auth import get_current_active_user
from models import User

router = APIRouter()

@router.post("/export/csv")
async def export_portfolio_csv(
    portfolio_data: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_active_user)
):
    """
    Generate a CSV export of the portfolio holdings
    """
    try:
        holdings = portfolio_data.get('holdings', [])
        
        if not holdings:
            raise HTTPException(status_code=400, detail="No holdings to export")
            
        # Convert to DataFrame
        df = pd.DataFrame(holdings)
        
        # Create CSV buffer
        stream = StringIO()
        df.to_csv(stream, index=False)
        
        response = StreamingResponse(
            iter([stream.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=portfolio_export.csv"}
        )
        return response
        
    except Exception as e:
        print(f"Export error: {e}")
        raise HTTPException(status_code=500, detail="Failed to export CSV")
