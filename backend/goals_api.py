"""
Goals API for VisionWealth
Handles creation, retrieval, updating, and tracking of financial goals
with comprehensive progress calculation and milestone tracking
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime, timedelta
from enum import Enum
import logging

from db import get_db
from models import Goal, User, Portfolio, GoalStatus
from auth import get_current_active_user

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


# ========================================
# ENUMS
# ========================================

class GoalCategory(str, Enum):
    """Goal category types"""
    RETIREMENT = "retirement"
    EDUCATION = "education"
    HOME = "home"
    VACATION = "vacation"
    EMERGENCY_FUND = "emergency_fund"
    INVESTMENT = "investment"
    DEBT_PAYOFF = "debt_payoff"
    OTHER = "other"


class GoalPriority(str, Enum):
    """Goal priority levels"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ========================================
# PYDANTIC MODELS
# ========================================

class MilestoneInput(BaseModel):
    """Milestone input model"""
    date: datetime
    amount: float = Field(..., gt=0)
    description: Optional[str] = None


class GoalCreate(BaseModel):
    """Goal creation model"""
    name: str = Field(..., min_length=1, max_length=255)
    target_value: float = Field(..., gt=0, description="Target amount to save")
    target_date: Optional[datetime] = None
    description: Optional[str] = Field(None, max_length=1000)
    category: Optional[GoalCategory] = GoalCategory.OTHER
    priority: Optional[int] = Field(1, ge=1, le=5, description="Priority (1=highest, 5=lowest)")
    monthly_contribution: Optional[float] = Field(0, ge=0)
    expected_return: Optional[float] = Field(0.07, ge=0, le=1, description="Expected annual return")
    portfolio_id: Optional[int] = None
    milestones: Optional[List[MilestoneInput]] = None
    
    @validator('target_date')
    def validate_target_date(cls, v):
        if v and v < datetime.now():
            raise ValueError("Target date must be in the future")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Retirement Fund",
                "target_value": 1000000,
                "target_date": "2050-12-31T00:00:00",
                "description": "Build retirement savings",
                "category": "retirement",
                "priority": 1,
                "monthly_contribution": 1000,
                "expected_return": 0.08
            }
        }


class GoalUpdate(BaseModel):
    """Goal update model"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    target_value: Optional[float] = Field(None, gt=0)
    current_value: Optional[float] = Field(None, ge=0)
    target_date: Optional[datetime] = None
    description: Optional[str] = Field(None, max_length=1000)
    category: Optional[GoalCategory] = None
    priority: Optional[int] = Field(None, ge=1, le=5)
    monthly_contribution: Optional[float] = Field(None, ge=0)
    expected_return: Optional[float] = Field(None, ge=0, le=1)
    status: Optional[GoalStatus] = None
    is_active: Optional[bool] = None
    
    @validator('target_date')
    def validate_target_date(cls, v):
        if v and v < datetime.now():
            raise ValueError("Target date must be in the future")
        return v


class GoalResponse(BaseModel):
    """Goal response model"""
    id: int
    user_id: int
    name: str
    target_value: float
    current_value: float
    initial_value: float
    target_date: Optional[datetime]
    start_date: datetime
    description: Optional[str]
    category: Optional[str]
    priority: int
    progress_pct: float
    status: str
    monthly_contribution: float
    expected_return: float
    risk_level: Optional[str]
    milestones: Optional[List[Dict]] = None
    is_active: bool
    notes: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    # Calculated fields
    amount_needed: Optional[float] = None
    months_remaining: Optional[int] = None
    days_remaining: Optional[int] = None
    projected_value: Optional[float] = None
    on_track: Optional[bool] = None
    
    class Config:
        from_attributes = True


class GoalSummary(BaseModel):
    """Summary of all goals"""
    total_goals: int
    active_goals: int
    completed_goals: int
    total_target_value: float
    total_current_value: float
    total_progress_pct: float
    goals_on_track: int
    goals_at_risk: int


class GoalProjection(BaseModel):
    """Goal projection model"""
    goal_id: int
    goal_name: str
    current_value: float
    target_value: float
    monthly_contribution: float
    expected_return: float
    months_to_goal: int
    projected_final_value: float
    will_reach_goal: bool
    shortfall_or_surplus: float
    recommendation: str


# ========================================
# HELPER FUNCTIONS
# ========================================

def calculate_goal_metrics(goal: Goal) -> Dict[str, Any]:
    """
    Calculate comprehensive metrics for a goal.
    
    Args:
        goal: Goal object
    
    Returns:
        Dictionary with calculated metrics
    """
    metrics = {}
    
    # Calculate progress percentage
    if goal.target_value > 0:
        metrics['progress_pct'] = (goal.current_value / goal.target_value) * 100
    else:
        metrics['progress_pct'] = 0
    
    # Calculate amount needed
    metrics['amount_needed'] = max(0, goal.target_value - goal.current_value)
    
    # Calculate time remaining
    if goal.target_date:
        now = datetime.utcnow()
        delta = goal.target_date - now
        metrics['days_remaining'] = max(0, delta.days)
        metrics['months_remaining'] = max(0, int(delta.days / 30))
    else:
        metrics['days_remaining'] = None
        metrics['months_remaining'] = None
    
    # Calculate if on track
    if goal.target_date and goal.start_date:
        total_days = (goal.target_date - goal.start_date).days
        elapsed_days = (datetime.utcnow() - goal.start_date).days
        
        if total_days > 0:
            expected_progress = (elapsed_days / total_days) * 100
            actual_progress = metrics['progress_pct']
            
            # On track if within 10% of expected progress
            metrics['on_track'] = actual_progress >= (expected_progress * 0.9)
        else:
            metrics['on_track'] = None
    else:
        metrics['on_track'] = None
    
    # Project future value with contributions
    if goal.target_date and goal.monthly_contribution > 0:
        months_remaining = metrics.get('months_remaining', 0)
        if months_remaining and months_remaining > 0:
            # Future value calculation with monthly contributions
            monthly_rate = goal.expected_return / 12
            
            # FV of current amount
            fv_current = goal.current_value * ((1 + monthly_rate) ** months_remaining)
            
            # FV of monthly contributions (annuity)
            if monthly_rate > 0:
                fv_contributions = goal.monthly_contribution * (
                    (((1 + monthly_rate) ** months_remaining) - 1) / monthly_rate
                )
            else:
                fv_contributions = goal.monthly_contribution * months_remaining
            
            metrics['projected_value'] = fv_current + fv_contributions
        else:
            metrics['projected_value'] = goal.current_value
    else:
        metrics['projected_value'] = goal.current_value
    
    return metrics


def update_goal_status(goal: Goal, db: Session):
    """
    Update goal status based on progress and dates.
    
    Args:
        goal: Goal object
        db: Database session
    """
    # Calculate progress
    if goal.target_value > 0:
        progress_pct = (goal.current_value / goal.target_value) * 100
    else:
        progress_pct = 0
    
    # Update progress percentage
    goal.progress_pct = progress_pct
    
    # Update status
    if progress_pct >= 100:
        goal.status = GoalStatus.COMPLETED
        if not goal.completed_at:
            goal.completed_at = datetime.utcnow()
    elif not goal.is_active:
        goal.status = GoalStatus.ABANDONED
    elif progress_pct == 0:
        goal.status = GoalStatus.NOT_STARTED
    else:
        # Check if on track
        if goal.target_date:
            total_time = (goal.target_date - goal.start_date).days
            elapsed_time = (datetime.utcnow() - goal.start_date).days
            
            if total_time > 0:
                expected_progress = (elapsed_time / total_time) * 100
                
                if progress_pct >= expected_progress * 0.9:
                    goal.status = GoalStatus.ON_TRACK
                else:
                    goal.status = GoalStatus.AT_RISK
            else:
                goal.status = GoalStatus.IN_PROGRESS
        else:
            goal.status = GoalStatus.IN_PROGRESS
    
    db.commit()


# ========================================
# ENDPOINTS
# ========================================

@router.post("/goals", response_model=GoalResponse, tags=["Goals"])
async def create_goal(
    goal: GoalCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new financial goal.
    
    **Features**:
    - Automatic progress tracking
    - Status management
    - Milestone support
    - Portfolio linking
    
    **Returns**: Created goal with calculated metrics
    """
    try:
        logger.info(f"Creating goal for user {current_user.id}: {goal.name}")
        
        # Validate portfolio_id if provided
        if goal.portfolio_id:
            portfolio = db.query(Portfolio).filter(
                Portfolio.id == goal.portfolio_id,
                Portfolio.user_id == current_user.id
            ).first()
            
            if not portfolio:
                raise HTTPException(
                    status_code=404,
                    detail="Portfolio not found"
                )
        
        # Create new goal
        new_goal = Goal(
            user_id=current_user.id,
            portfolio_id=goal.portfolio_id,
            name=goal.name,
            target_value=goal.target_value,
            target_date=goal.target_date,
            description=goal.description,
            category=goal.category.value if goal.category else None,
            priority=goal.priority,
            monthly_contribution=goal.monthly_contribution,
            expected_return=goal.expected_return,
            start_date=datetime.utcnow(),
            status=GoalStatus.NOT_STARTED,
            is_active=True
        )
        
        # Add milestones if provided
        if goal.milestones:
            milestones_data = [
                {
                    'date': m.date.isoformat(),
                    'amount': m.amount,
                    'description': m.description,
                    'completed': False
                }
                for m in goal.milestones
            ]
            new_goal.milestones = milestones_data
        
        db.add(new_goal)
        db.commit()
        db.refresh(new_goal)
        
        # Calculate metrics
        metrics = calculate_goal_metrics(new_goal)
        
        # Add metrics to response
        response = GoalResponse.from_orm(new_goal)
        for key, value in metrics.items():
            setattr(response, key, value)
        
        logger.info(f"Goal created successfully: ID {new_goal.id}")
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create goal: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create goal: {str(e)}"
        )


@router.get("/goals", response_model=List[GoalResponse], tags=["Goals"])
async def get_goals(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    category: Optional[GoalCategory] = Query(None, description="Filter by category"),
    status: Optional[GoalStatus] = Query(None, description="Filter by status"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    sort_by: str = Query("priority", description="Sort by field (priority, target_date, progress_pct)"),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    Get all goals for the current user.
    
    **Filters**:
    - `category`: Filter by goal category
    - `status`: Filter by goal status
    - `is_active`: Filter by active/inactive
    
    **Sorting**:
    - `priority`: By priority (default)
    - `target_date`: By target date
    - `progress_pct`: By progress percentage
    
    **Returns**: List of goals with calculated metrics
    """
    try:
        logger.info(f"Fetching goals for user {current_user.id}")
        
        # Build query
        query = db.query(Goal).filter(Goal.user_id == current_user.id)
        
        # Apply filters
        if category:
            query = query.filter(Goal.category == category.value)
        
        if status:
            query = query.filter(Goal.status == status)
        
        if is_active is not None:
            query = query.filter(Goal.is_active == is_active)
        
        # Apply sorting
        if sort_by == "priority":
            query = query.order_by(Goal.priority.asc())
        elif sort_by == "target_date":
            query = query.order_by(Goal.target_date.asc().nullslast())
        elif sort_by == "progress_pct":
            query = query.order_by(Goal.progress_pct.desc())
        else:
            query = query.order_by(Goal.created_at.desc())
        
        # Get goals
        goals = query.limit(limit).all()
        
        # Calculate metrics for each goal
        response_goals = []
        for goal in goals:
            metrics = calculate_goal_metrics(goal)
            goal_response = GoalResponse.from_orm(goal)
            
            for key, value in metrics.items():
                setattr(goal_response, key, value)
            
            response_goals.append(goal_response)
        
        logger.info(f"Retrieved {len(goals)} goals for user {current_user.id}")
        
        return response_goals
    
    except Exception as e:
        logger.error(f"Failed to fetch goals: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch goals: {str(e)}"
        )


@router.get("/goals/summary", response_model=GoalSummary, tags=["Goals"])
async def get_goals_summary(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get summary statistics for all user goals.
    
    **Returns**:
    - Total number of goals
    - Active vs completed goals
    - Total target and current values
    - Overall progress
    - Goals on track vs at risk
    """
    try:
        goals = db.query(Goal).filter(Goal.user_id == current_user.id).all()
        
        total_goals = len(goals)
        active_goals = sum(1 for g in goals if g.is_active)
        completed_goals = sum(1 for g in goals if g.status == GoalStatus.COMPLETED)
        
        total_target_value = sum(g.target_value for g in goals)
        total_current_value = sum(g.current_value for g in goals)
        
        total_progress_pct = (
            (total_current_value / total_target_value * 100)
            if total_target_value > 0 else 0
        )
        
        goals_on_track = sum(
            1 for g in goals
            if g.status == GoalStatus.ON_TRACK
        )
        
        goals_at_risk = sum(
            1 for g in goals
            if g.status == GoalStatus.AT_RISK
        )
        
        return GoalSummary(
            total_goals=total_goals,
            active_goals=active_goals,
            completed_goals=completed_goals,
            total_target_value=total_target_value,
            total_current_value=total_current_value,
            total_progress_pct=total_progress_pct,
            goals_on_track=goals_on_track,
            goals_at_risk=goals_at_risk
        )
    
    except Exception as e:
        logger.error(f"Failed to get goals summary: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get summary: {str(e)}"
        )


@router.get("/goals/{goal_id}", response_model=GoalResponse, tags=["Goals"])
async def get_goal(
    goal_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific goal by ID.
    
    **Returns**: Goal details with calculated metrics
    """
    try:
        goal = db.query(Goal).filter(
            Goal.id == goal_id,
            Goal.user_id == current_user.id
        ).first()
        
        if not goal:
            raise HTTPException(
                status_code=404,
                detail="Goal not found"
            )
        
        # Calculate metrics
        metrics = calculate_goal_metrics(goal)
        
        goal_response = GoalResponse.from_orm(goal)
        for key, value in metrics.items():
            setattr(goal_response, key, value)
        
        return goal_response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch goal {goal_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch goal: {str(e)}"
        )


@router.put("/goals/{goal_id}", response_model=GoalResponse, tags=["Goals"])
async def update_goal(
    goal_id: int,
    goal_update: GoalUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update an existing goal.
    
    **Updateable Fields**:
    - Basic info (name, description, target)
    - Progress (current_value)
    - Settings (priority, contributions)
    - Status
    
    **Returns**: Updated goal with recalculated metrics
    """
    try:
        goal = db.query(Goal).filter(
            Goal.id == goal_id,
            Goal.user_id == current_user.id
        ).first()
        
        if not goal:
            raise HTTPException(
                status_code=404,
                detail="Goal not found"
            )
        
        # Update fields
        update_data = goal_update.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            if field == 'category' and value:
                setattr(goal, field, value.value)
            elif field == 'status' and value:
                setattr(goal, field, value)
            else:
                setattr(goal, field, value)
        
        # Update status based on new values
        update_goal_status(goal, db)
        
        db.commit()
        db.refresh(goal)
        
        # Calculate metrics
        metrics = calculate_goal_metrics(goal)
        
        goal_response = GoalResponse.from_orm(goal)
        for key, value in metrics.items():
            setattr(goal_response, key, value)
        
        logger.info(f"Goal {goal_id} updated successfully")
        
        return goal_response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update goal {goal_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update goal: {str(e)}"
        )


@router.post("/goals/{goal_id}/update-progress", response_model=GoalResponse, tags=["Goals"])
async def update_goal_progress(
    goal_id: int,
    current_value: float = Body(..., ge=0, embed=True),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update the current value/progress of a goal.
    
    **Request Body**:
```json
    {
        "current_value": 25000.00
    }
```
    
    **Returns**: Updated goal with recalculated status
    """
    try:
        goal = db.query(Goal).filter(
            Goal.id == goal_id,
            Goal.user_id == current_user.id
        ).first()
        
        if not goal:
            raise HTTPException(
                status_code=404,
                detail="Goal not found"
            )
        
        goal.current_value = current_value
        update_goal_status(goal, db)
        
        db.commit()
        db.refresh(goal)
        
        # Calculate metrics
        metrics = calculate_goal_metrics(goal)
        
        goal_response = GoalResponse.from_orm(goal)
        for key, value in metrics.items():
            setattr(goal_response, key, value)
        
        logger.info(f"Goal {goal_id} progress updated: ${current_value:,.2f}")
        
        return goal_response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update progress for goal {goal_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update progress: {str(e)}"
        )


@router.get("/goals/{goal_id}/projection", response_model=GoalProjection, tags=["Goals"])
async def get_goal_projection(
    goal_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get projection for whether goal will be reached.
    
    **Calculates**:
    - Months to reach goal
    - Projected final value
    - Whether goal will be reached
    - Shortfall or surplus
    - Recommendations
    
    **Returns**: Detailed projection analysis
    """
    try:
        goal = db.query(Goal).filter(
            Goal.id == goal_id,
            Goal.user_id == current_user.id
        ).first()
        
        if not goal:
            raise HTTPException(
                status_code=404,
                detail="Goal not found"
            )
        
        # Calculate projection
        if goal.target_date:
            months_remaining = max(0, int((goal.target_date - datetime.utcnow()).days / 30))
        else:
            # Estimate months needed
            if goal.monthly_contribution > 0:
                amount_needed = goal.target_value - goal.current_value
                months_remaining = int(amount_needed / goal.monthly_contribution)
            else:
                months_remaining = 0
        
        # Calculate projected value
        if months_remaining > 0 and goal.monthly_contribution > 0:
            monthly_rate = goal.expected_return / 12
            
            fv_current = goal.current_value * ((1 + monthly_rate) ** months_remaining)
            
            if monthly_rate > 0:
                fv_contributions = goal.monthly_contribution * (
                    (((1 + monthly_rate) ** months_remaining) - 1) / monthly_rate
                )
            else:
                fv_contributions = goal.monthly_contribution * months_remaining
            
            projected_value = fv_current + fv_contributions
        else:
            projected_value = goal.current_value
        
        will_reach = projected_value >= goal.target_value
        shortfall_or_surplus = projected_value - goal.target_value
        
        # Generate recommendation
        if will_reach:
            if shortfall_or_surplus > goal.target_value * 0.1:
                recommendation = "Great! You're on track to exceed your goal. Consider reducing contributions or setting a more ambitious target."
            else:
                recommendation = "You're on track to reach your goal. Keep up the good work!"
        else:
            shortfall = abs(shortfall_or_surplus)
            additional_monthly = shortfall / months_remaining if months_remaining > 0 else shortfall
            recommendation = f"You may fall short by ${shortfall:,.2f}. Consider increasing monthly contributions by ${additional_monthly:,.2f}."
        
        return GoalProjection(
            goal_id=goal.id,
            goal_name=goal.name,
            current_value=goal.current_value,
            target_value=goal.target_value,
            monthly_contribution=goal.monthly_contribution,
            expected_return=goal.expected_return,
            months_to_goal=months_remaining,
            projected_final_value=projected_value,
            will_reach_goal=will_reach,
            shortfall_or_surplus=shortfall_or_surplus,
            recommendation=recommendation
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to calculate projection for goal {goal_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate projection: {str(e)}"
        )


@router.delete("/goals/{goal_id}", tags=["Goals"])
async def delete_goal(
    goal_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a goal.
    
    **Note**: This is a hard delete. Consider using status='abandoned' instead.
    
    **Returns**: Success message
    """
    try:
        goal = db.query(Goal).filter(
            Goal.id == goal_id,
            Goal.user_id == current_user.id
        ).first()
        
        if not goal:
            raise HTTPException(
                status_code=404,
                detail="Goal not found"
            )
        
        db.delete(goal)
        db.commit()
        
        logger.info(f"Goal {goal_id} deleted by user {current_user.id}")
        
        return {
            "success": True,
            "message": "Goal deleted successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete goal {goal_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete goal: {str(e)}"
        )
