from typing import List, Dict
from models import TaskInput

class VelocityCalculator:
    """Calculate team velocity and capacity metrics"""
    
    def __init__(self):
        pass
    
    def calculate_average_velocity(self, velocity_history: List[int]) -> float:
        """
        Calculate rolling average velocity from history.
        Returns: Average story points per sprint
        """
        if not velocity_history or len(velocity_history) == 0:
            return 0.0
        
        # Use last 3 sprints for rolling average (or all if less than 3)
        recent_sprints = velocity_history[-3:]
        return sum(recent_sprints) / len(recent_sprints)
    
    def calculate_velocity_trend(self, velocity_history: List[int]) -> str:
        """
        Determine if velocity is increasing, decreasing, or stable.
        Returns: 'increasing', 'decreasing', 'stable', or 'unknown'
        """
        if not velocity_history or len(velocity_history) < 2:
            return 'unknown'
        
        if len(velocity_history) < 3:
            # Compare last two sprints
            if velocity_history[-1] > velocity_history[-2]:
                return 'increasing'
            elif velocity_history[-1] < velocity_history[-2]:
                return 'decreasing'
            else:
                return 'stable'
        
        # Compare last sprint to average of previous sprints
        last_sprint = velocity_history[-1]
        previous_avg = sum(velocity_history[:-1]) / len(velocity_history[:-1])
        
        threshold = previous_avg * 0.1  # 10% threshold
        
        if last_sprint > previous_avg + threshold:
            return 'increasing'
        elif last_sprint < previous_avg - threshold:
            return 'decreasing'
        else:
            return 'stable'
    
    def calculate_sprint_capacity(self, team_capacity: List[Dict]) -> int:
        """
        Calculate total team capacity for a sprint.
        Returns: Total story points capacity
        """
        if not team_capacity:
            return 0
        
        return sum(member.get('capacity', 0) for member in team_capacity)
    
    def calculate_capacity_delta(self, assigned_points: int, 
                                 sprint_capacity: int) -> int:
        """
        Calculate difference between assigned work and capacity.
        Returns: Positive = over capacity, Negative = under capacity
        """
        return assigned_points - sprint_capacity
    
    def detect_velocity_drop(self, velocity_history: List[int], 
                            threshold: float = 0.2) -> bool:
        """
        Detect if velocity has dropped significantly.
        Returns: True if velocity dropped by threshold percentage
        """
        if not velocity_history or len(velocity_history) < 2:
            return False
        
        last_sprint = velocity_history[-1]
        previous_avg = sum(velocity_history[:-1]) / len(velocity_history[:-1])
        
        if previous_avg == 0:
            return False
        
        drop_percentage = (previous_avg - last_sprint) / previous_avg
        return drop_percentage >= threshold
    
    def calculate_completed_velocity(self, tasks: List[TaskInput]) -> int:
        """
        Calculate velocity from completed tasks.
        Returns: Total story points completed
        """
        completed_points = sum(
            task.storyPoints for task in tasks 
            if task.status == 'done'
        )
        return completed_points
    
    def calculate_remaining_story_points(self, tasks: List[TaskInput]) -> int:
        """
        Calculate remaining story points (not done).
        Returns: Total story points remaining
        """
        remaining_points = sum(
            task.storyPoints for task in tasks 
            if task.status != 'done'
        )
        return remaining_points
    
    def calculate_sprints_needed(self, remaining_points: int, 
                                average_velocity: float) -> float:
        """
        Estimate number of sprints needed to complete remaining work.
        Returns: Number of sprints (can be fractional)
        """
        if average_velocity == 0:
            return float('inf')  # Cannot estimate without velocity
        
        return remaining_points / average_velocity
    
    def predict_release_delay(self, sprints_needed: float, 
                             planned_sprints: int) -> int:
        """
        Predict release delay in days (assuming 14-day sprints).
        Returns: Delay in days (0 if on track)
        """
        if sprints_needed <= planned_sprints:
            return 0  # On track
        
        extra_sprints = sprints_needed - planned_sprints
        return int(extra_sprints * 14)  # 14 days per sprint
