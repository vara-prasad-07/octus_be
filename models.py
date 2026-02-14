from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict
from datetime import datetime, date

class TaskInput(BaseModel):
    """Task input model for validation"""
    id: str
    name: str
    assignee: Optional[str] = None
    dueDate: Optional[str] = None
    storyPoints: int = Field(default=0, ge=0, le=100)
    status: str = Field(default="todo")
    dependencies: Optional[List[str]] = Field(default_factory=list)
    
    @validator('status')
    def validate_status(cls, v):
        allowed = ['todo', 'in-progress', 'done']
        if v not in allowed:
            return 'todo'  # Default to todo instead of raising error
        return v
    
    @validator('dueDate')
    def validate_date(cls, v):
        if v and v.strip():
            try:
                # Try to parse the date
                datetime.fromisoformat(v.replace('Z', '+00:00'))
            except:
                # If invalid, return None instead of raising error
                return None
        return v
    
    @validator('storyPoints', pre=True)
    def validate_story_points(cls, v):
        try:
            points = int(v) if v else 0
            return max(0, min(100, points))
        except:
            return 0

class TeamMember(BaseModel):
    """Team member capacity model"""
    name: str
    capacity: int = Field(ge=0, description="Story points capacity per sprint")
    velocity_multiplier: float = Field(default=1.0, ge=0.5, le=2.0, description="Speed multiplier: 1.0=average, 1.5=fast, 0.8=slower")

class PlanningRequest(BaseModel):
    """Main request model for planning analysis"""
    projectId: str
    tasks: List[TaskInput]
    team_capacity: List[TeamMember] = Field(default_factory=list)
    sprint_duration_days: int = Field(default=14, ge=1, le=30)
    velocity_history: List[int] = Field(default_factory=list)

class TaskRiskAnalysis(BaseModel):
    """Risk analysis for a single task"""
    task_id: str
    task_name: str
    total_risk_score: int = Field(ge=0, le=100)
    risk_level: str
    risk_factors: Dict[str, int]
    recommendations: List[str]

class OverloadAnalysis(BaseModel):
    """Workload analysis for team members"""
    assignee: str
    assigned_points: int
    capacity: int
    workload_percentage: int
    is_overloaded: bool
    overload_severity: str

class DependencyRisk(BaseModel):
    """Dependency risk analysis"""
    task_id: str
    task_name: str
    blocked_by: List[str]
    blocks: List[str]
    dependency_risk_score: int

class Recommendation(BaseModel):
    """Action recommendation"""
    type: str
    priority: str
    description: str
    affected_tasks: List[str]
    expected_impact: str

class PlanningResponse(BaseModel):
    """Complete planning analysis response"""
    overall_risk_score: int
    risk_level: str
    predicted_release_delay_days: int
    average_velocity: float
    sprint_capacity: int
    remaining_story_points: int
    sprints_needed: float
    task_analysis: List[TaskRiskAnalysis]
    overload_analysis: List[OverloadAnalysis]
    dependency_risks: List[DependencyRisk]
    blocked_tasks: List[str]
    recommendations: List[Recommendation]
    ai_health_summary: str
    critical_issues: List[str]
