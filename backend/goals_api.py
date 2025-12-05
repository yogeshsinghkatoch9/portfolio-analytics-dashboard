"""
Goals API for VisionWealth
Handles creation and retrieval of financial goals
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from database import get_db
from models import Goal, User
from auth import get_current_active_user

router = APIRouter()

# Pydantic Models
class GoalCreate(BaseModel):
    name: str
    target_value: float
    target_date: Optional[datetime] = None
    description: Optional[str] = None

class GoalResponse(BaseModel):
    id: int
    name: str
    target_value: float
    current_value: float = 0.0  # Calculated field
    target_date: Optional[datetime]
    description: Optional[str]
    progress_pct: float = 0.0   # Calculated field
    
    class Config:
        from_attributes = True

@router.post("/goals", response_model=GoalResponse)
async def create_goal(
    goal: GoalCreate, 
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new financial goal"""
    new_goal = Goal(
        user_id=current_user.id,
        name=goal.name,
        target_value=goal.target_value,
        target_date=goal.target_date,
        description=goal.description
    )
    
    db.add(new_goal)
    db.commit()
    db.refresh(new_goal)
    
    return new_goal

@router.get("/goals", response_model=List[GoalResponse])
async def get_goals(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all goals for the current user"""
    goals = db.query(Goal).filter(Goal.user_id == current_user.id).all()
    
    # Calculate progress based on portfolio value (simplified logic)
    # In a real app, we might link goals to specific accounts or assets
    # For now, we'll assume the goal tracks against the user's total portfolio value
    # We need to fetch the latest portfolio value for this user
    
    # This is a simplification. Ideally, we'd get the total value from the Portfolio service
    # For this MVP, we'll return the goals and let the frontend calculate progress 
    # against the currently loaded portfolio total value
    
    return goals

@router.delete("/goals/{goal_id}")
async def delete_goal(
    goal_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a goal"""
    goal = db.query(Goal).filter(Goal.id == goal_id, Goal.user_id == current_user.id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
        
    db.delete(goal)
    db.commit()
    return {"message": "Goal deleted successfully"}
