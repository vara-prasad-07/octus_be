from datetime import datetime, timedelta
from typing import List, Dict
import math
from date_utils import parse_date, days_until_date

class RiskEngine:
    """Core risk calculation engine"""
    
    def __init__(self):
        self.risk_weights = {
            'deadline': 0.25,
            'complexity': 0.25,
            'dependency': 0.20,
            'overload': 0.20,
            'velocity': 0.10
        }
    
    def calculate_deadline_risk(self, due_date: str, current_date: datetime = None) -> int:
        """
        Calculate risk based on deadline proximity.
        Handles various date formats including Excel serial dates.
        Returns: 0-100 risk score
        """
        if not due_date:
            return 30  # No deadline = moderate risk
        
        # Use our date utility to calculate days until due
        days_until_due = days_until_date(due_date, current_date)
        
        if days_until_due is None:
            return 30  # Invalid date = moderate risk
        
        if days_until_due < 0:
            return 100  # Overdue = critical
        elif days_until_due <= 2:
            return 90  # 2 days or less = very high risk
        elif days_until_due <= 5:
            return 70  # 3-5 days = high risk
        elif days_until_due <= 10:
            return 50  # 6-10 days = moderate risk
        elif days_until_due <= 20:
            return 30  # 11-20 days = low-moderate risk
        else:
            return 10  # 20+ days = low risk
    
    def calculate_complexity_risk(self, story_points: int) -> int:
        """
        Calculate risk based on task complexity (story points).
        Returns: 0-100 risk score
        """
        if story_points <= 1:
            return 5
        elif story_points <= 3:
            return 20
        elif story_points <= 5:
            return 40
        elif story_points <= 8:
            return 60
        elif story_points <= 13:
            return 80
        else:
            return 95  # 13+ points = very high complexity
    
    def calculate_dependency_risk(self, task_id: str, dependencies: List[str], 
                                  task_status_map: Dict[str, str]) -> int:
        """
        Calculate risk based on task dependencies.
        Returns: 0-100 risk score
        """
        if not dependencies:
            return 0  # No dependencies = no risk
        
        blocked_count = 0
        for dep_id in dependencies:
            dep_status = task_status_map.get(dep_id, 'todo')
            if dep_status != 'done':
                blocked_count += 1
        
        if blocked_count == 0:
            return 0  # All dependencies resolved
        
        # Risk increases with number of unresolved dependencies
        risk_per_dep = 100 / len(dependencies)
        return min(int(blocked_count * risk_per_dep), 100)
    
    def calculate_overload_risk(self, assignee: str, workload_percentage: int) -> int:
        """
        Calculate risk based on assignee workload.
        Returns: 0-100 risk score
        """
        if not assignee:
            return 40  # Unassigned = moderate risk
        
        if workload_percentage <= 70:
            return 10  # Under capacity = low risk
        elif workload_percentage <= 90:
            return 30  # Near capacity = low-moderate risk
        elif workload_percentage <= 100:
            return 50  # At capacity = moderate risk
        elif workload_percentage <= 120:
            return 75  # Overloaded = high risk
        else:
            return 95  # Severely overloaded = critical risk
    
    def calculate_velocity_risk(self, current_velocity: float, 
                                average_velocity: float) -> int:
        """
        Calculate risk based on velocity deviation.
        Returns: 0-100 risk score
        """
        if average_velocity == 0:
            return 20  # No history = low-moderate risk
        
        velocity_ratio = current_velocity / average_velocity
        
        if velocity_ratio >= 1.0:
            return 0  # On track or ahead
        elif velocity_ratio >= 0.8:
            return 30  # Slightly behind
        elif velocity_ratio >= 0.6:
            return 60  # Significantly behind
        else:
            return 90  # Critically behind
    
    def calculate_total_risk(self, deadline_risk: int, complexity_risk: int,
                            dependency_risk: int, overload_risk: int,
                            velocity_risk: int) -> int:
        """
        Calculate weighted total risk score.
        Returns: 0-100 risk score
        """
        total = (
            deadline_risk * self.risk_weights['deadline'] +
            complexity_risk * self.risk_weights['complexity'] +
            dependency_risk * self.risk_weights['dependency'] +
            overload_risk * self.risk_weights['overload'] +
            velocity_risk * self.risk_weights['velocity']
        )
        return min(int(total), 100)
    
    def categorize_risk_level(self, risk_score: int) -> str:
        """Categorize risk score into levels"""
        if risk_score >= 70:
            return "critical"
        elif risk_score >= 50:
            return "high"
        elif risk_score >= 30:
            return "moderate"
        else:
            return "low"
