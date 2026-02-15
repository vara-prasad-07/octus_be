from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict
from datetime import datetime, date
from date_utils import parse_date, validate_date_string

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
        """Validate and normalize date format, handling Excel serial dates"""
        if not v:
            return None
        
        # Parse the date using our utility function
        parsed_date = parse_date(v)
        
        if parsed_date:
            return parsed_date
        
        # If parsing failed, return None instead of raising error
        print(f"Warning: Could not parse date '{v}', setting to None")
        return None
    
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

class InsightsRequest(BaseModel):
    """Request model for insights endpoint"""
    testGenerationHistory: Dict
    uiValidations: Dict
    uxValidations: Dict

class DefectTrend(BaseModel):
    """Defect trend analysis"""
    trend: str
    summary: str

class QualityHotspot(BaseModel):
    """Quality hotspot by module"""
    module: str
    defect_count: int
    severity: str

class ReleaseReadiness(BaseModel):
    """Release readiness assessment"""
    score: int
    decision: str
    reasoning: List[str]

class InsightsResponse(BaseModel):
    """Response model for insights endpoint"""
    defect_trends: DefectTrend
    hotspots: List[QualityHotspot]
    release_readiness: ReleaseReadiness
    recommendation: str


