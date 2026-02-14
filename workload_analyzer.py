from typing import List, Dict
from models import TaskInput, TeamMember, OverloadAnalysis

class WorkloadAnalyzer:
    """Analyze team workload and detect overload"""
    
    def __init__(self):
        pass
    
    def calculate_workload_distribution(self, tasks: List[TaskInput]) -> Dict[str, int]:
        """
        Calculate story points assigned to each team member.
        Returns: Dict mapping assignee name to total story points
        """
        workload = {}
        
        for task in tasks:
            if task.status == 'done':
                continue  # Skip completed tasks
            
            assignee = task.assignee or 'Unassigned'
            workload[assignee] = workload.get(assignee, 0) + task.storyPoints
        
        return workload
    
    def calculate_capacity_percentage(self, assigned_points: int, 
                                     capacity: int) -> int:
        """
        Calculate workload as percentage of capacity.
        Returns: Percentage (can exceed 100%)
        """
        if capacity == 0:
            return 0 if assigned_points == 0 else 999  # Infinite overload
        
        return int((assigned_points / capacity) * 100)
    
    def detect_overloaded_members(self, workload: Dict[str, int],
                                  team_capacity: List[TeamMember]) -> List[OverloadAnalysis]:
        """
        Identify overloaded team members.
        Returns: List of overload analysis for each member
        """
        capacity_map = {member.name: member.capacity for member in team_capacity}
        overload_analysis = []
        
        for assignee, assigned_points in workload.items():
            if assignee == 'Unassigned':
                continue
            
            capacity = capacity_map.get(assignee, 40)  # Default 40 points capacity
            workload_pct = self.calculate_capacity_percentage(assigned_points, capacity)
            is_overloaded = workload_pct > 100
            
            # Determine overload severity
            if workload_pct <= 100:
                severity = "none"
            elif workload_pct <= 120:
                severity = "moderate"
            elif workload_pct <= 150:
                severity = "high"
            else:
                severity = "critical"
            
            overload_analysis.append(OverloadAnalysis(
                assignee=assignee,
                assigned_points=assigned_points,
                capacity=capacity,
                workload_percentage=workload_pct,
                is_overloaded=is_overloaded,
                overload_severity=severity
            ))
        
        return overload_analysis
    
    def get_overload_risk_map(self, overload_analysis: List[OverloadAnalysis]) -> Dict[str, int]:
        """
        Create a map of assignee to overload risk score.
        Returns: Dict mapping assignee to risk score (0-100)
        """
        risk_map = {}
        
        for analysis in overload_analysis:
            workload_pct = analysis.workload_percentage
            
            if workload_pct <= 70:
                risk = 10
            elif workload_pct <= 90:
                risk = 30
            elif workload_pct <= 100:
                risk = 50
            elif workload_pct <= 120:
                risk = 75
            else:
                risk = 95
            
            risk_map[analysis.assignee] = risk
        
        return risk_map
    
    def find_underutilized_members(self, overload_analysis: List[OverloadAnalysis],
                                   threshold: int = 70) -> List[str]:
        """
        Find team members with workload below threshold.
        Returns: List of underutilized member names
        """
        return [
            analysis.assignee 
            for analysis in overload_analysis 
            if analysis.workload_percentage < threshold
        ]
    
    def suggest_reassignments(self, overload_analysis: List[OverloadAnalysis]) -> List[Dict]:
        """
        Suggest task reassignments to balance workload.
        Returns: List of reassignment suggestions
        """
        overloaded = [a for a in overload_analysis if a.is_overloaded]
        underutilized = [a for a in overload_analysis if a.workload_percentage < 80]
        
        suggestions = []
        
        for overloaded_member in overloaded:
            for underutilized_member in underutilized:
                # Calculate how many points to move
                excess_points = overloaded_member.assigned_points - overloaded_member.capacity
                available_capacity = underutilized_member.capacity - underutilized_member.assigned_points
                
                if available_capacity > 0:
                    points_to_move = min(excess_points, available_capacity)
                    
                    suggestions.append({
                        'from': overloaded_member.assignee,
                        'to': underutilized_member.assignee,
                        'story_points': points_to_move,
                        'reason': f'Balance workload: {overloaded_member.assignee} at {overloaded_member.workload_percentage}%, {underutilized_member.assignee} at {underutilized_member.workload_percentage}%'
                    })
        
        return suggestions
