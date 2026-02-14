from typing import List, Dict
from models import (TaskInput, OverloadAnalysis, DependencyRisk, 
                   Recommendation, TaskRiskAnalysis)

class RecommendationEngine:
    """Generate actionable recommendations with smart work distribution"""
    
    def __init__(self):
        pass
    
    def generate_work_distribution_recommendations(self,
                                                   overload_analysis: List[OverloadAnalysis],
                                                   tasks: List[TaskInput],
                                                   task_risk_analysis: List[TaskRiskAnalysis],
                                                   team_capacity: List = None) -> List[Recommendation]:
        """
        Generate optimal work distribution recommendations.
        Assigns work to ALL employees, prioritizing high-velocity workers with available capacity.
        Goal: Complete tasks faster by leveraging the most effective team members.
        """
        recommendations = []
        
        # Create velocity map (if provided, otherwise assume equal velocity)
        velocity_map = {}
        if team_capacity:
            for member in team_capacity:
                velocity_map[member.get('name')] = member.get('velocity_multiplier', 1.0)
        
        # Find overloaded members (>90% capacity)
        overloaded = [a for a in overload_analysis if a.workload_percentage > 90]
        
        # Find ALL available team members sorted by effectiveness
        # Effectiveness = (available capacity) * (velocity multiplier)
        available_members = []
        for member in overload_analysis:
            if member.workload_percentage < 95:  # Has some capacity
                available_capacity = member.capacity - member.assigned_points
                velocity = velocity_map.get(member.assignee, 1.0)
                effectiveness_score = available_capacity * velocity
                
                available_members.append({
                    'name': member.assignee,
                    'available_capacity': available_capacity,
                    'current_load_pct': member.workload_percentage,
                    'velocity': velocity,
                    'effectiveness': effectiveness_score,
                    'capacity': member.capacity,
                    'assigned': member.assigned_points
                })
        
        # Sort by effectiveness (high velocity + available capacity = most effective)
        available_members.sort(key=lambda x: x['effectiveness'], reverse=True)
        
        if not overloaded or not available_members:
            return recommendations
        
        for overloaded_member in overloaded:
            # Find large tasks assigned to overloaded person
            member_tasks = [
                task for task in tasks 
                if task.assignee == overloaded_member.assignee 
                and task.status != 'done'
                and task.storyPoints >= 8
            ]
            
            if not member_tasks:
                continue
            
            for task in member_tasks[:3]:  # Top 3 tasks
                task_risk = next(
                    (t for t in task_risk_analysis if t.task_id == task.id),
                    None
                )
                
                if not task_risk:
                    continue
                
                # Find best helpers (high velocity + available capacity)
                potential_helpers = [
                    m for m in available_members 
                    if m['name'] != overloaded_member.assignee
                    and m['available_capacity'] >= 3
                ]
                
                if not potential_helpers:
                    continue
                
                # Distribute work optimally
                # Strategy: Give more work to faster employees
                total_points = task.storyPoints
                original_keeps = max(2, int(total_points * 0.25))  # Original keeps only 25%
                to_distribute = total_points - original_keeps
                
                split_suggestions = []
                remaining = to_distribute
                
                # Distribute to top 3 most effective helpers
                for helper in potential_helpers[:3]:
                    if remaining <= 0:
                        break
                    
                    # Calculate allocation based on velocity and capacity
                    # Faster workers get more work
                    base_allocation = min(
                        int(remaining * 0.5),  # Up to 50% of remaining
                        helper['available_capacity']
                    )
                    
                    # Adjust by velocity: fast workers can take more
                    velocity_adjusted = int(base_allocation * helper['velocity'])
                    points_to_allocate = min(
                        max(3, velocity_adjusted),
                        helper['available_capacity'],
                        remaining
                    )
                    
                    if points_to_allocate >= 3:
                        new_load = int((helper['assigned'] + points_to_allocate) / helper['capacity'] * 100)
                        velocity_label = "⚡ Fast" if helper['velocity'] >= 1.3 else "→ Average" if helper['velocity'] >= 0.9 else "Steady"
                        
                        split_suggestions.append({
                            'name': helper['name'],
                            'points': points_to_allocate,
                            'current_load': helper['current_load_pct'],
                            'new_load': new_load,
                            'velocity': helper['velocity'],
                            'velocity_label': velocity_label
                        })
                        remaining -= points_to_allocate
                
                if split_suggestions:
                    # Build recommendation
                    helpers_text = " + ".join([
                        f"{s['points']}pts → {s['name']} {s['velocity_label']} ({s['current_load']}%→{s['new_load']}%)"
                        for s in split_suggestions
                    ])
                    
                    total_distributed = sum(s['points'] for s in split_suggestions)
                    new_overloaded_load = int(
                        (overloaded_member.assigned_points - total_distributed) / 
                        overloaded_member.capacity * 100
                    )
                    
                    # Calculate time saved by using faster workers
                    avg_velocity = sum(s['velocity'] for s in split_suggestions) / len(split_suggestions)
                    time_saved_pct = int((avg_velocity - 1.0) * 100) if avg_velocity > 1.0 else 0
                    
                    recommendations.append(Recommendation(
                        type="work_distribution",
                        priority="high",
                        description=f"Redistribute '{task.name}' ({task.storyPoints}pts): {original_keeps}pts with {overloaded_member.assignee} + {helpers_text}",
                        affected_tasks=[task.id],
                        expected_impact=f"Reduces {overloaded_member.assignee} from {overloaded_member.workload_percentage}%→{new_overloaded_load}%. Assigns to high-velocity team members. Estimated {time_saved_pct}% faster completion. Risk reduction: {min(40, task_risk.total_risk_score)}%"
                    ))
        
        return recommendations
    
    def generate_reassignment_recommendations(self, 
                                             overload_analysis: List[OverloadAnalysis],
                                             tasks: List[TaskInput]) -> List[Recommendation]:
        """Generate full task reassignment recommendations for smaller tasks"""
        recommendations = []
        
        overloaded = [a for a in overload_analysis if a.workload_percentage > 120]
        underutilized = [a for a in overload_analysis if a.workload_percentage < 60]
        
        if overloaded and underutilized:
            for overloaded_member in overloaded:
                # Find small-medium tasks (3-5 points) that can be fully moved
                member_tasks = [
                    task for task in tasks 
                    if task.assignee == overloaded_member.assignee 
                    and task.status == 'todo'
                    and 3 <= task.storyPoints <= 5
                ]
                
                if member_tasks and underutilized:
                    target_member = underutilized[0]
                    task_to_move = member_tasks[0]
                    
                    recommendations.append(Recommendation(
                        type="reassignment",
                        priority="medium",
                        description=f"Reassign '{task_to_move.name}' ({task_to_move.storyPoints} pts) from {overloaded_member.assignee} ({overloaded_member.workload_percentage}% loaded) to {target_member.assignee} ({target_member.workload_percentage}% loaded)",
                        affected_tasks=[task_to_move.id],
                        expected_impact=f"Better workload balance. {target_member.assignee} has {target_member.capacity - target_member.assigned_points} pts available capacity"
                    ))
        
        return recommendations
    
    def generate_priority_recommendations(self,
                                         dependency_risks: List[DependencyRisk],
                                         task_risk_analysis: List[TaskRiskAnalysis]) -> List[Recommendation]:
        """Generate task prioritization recommendations"""
        recommendations = []
        
        # Find high-risk tasks that block others
        blocking_high_risk = []
        for dep_risk in dependency_risks:
            if dep_risk.blocks and dep_risk.dependency_risk_score > 50:
                task_risk = next(
                    (t for t in task_risk_analysis if t.task_id == dep_risk.task_id),
                    None
                )
                if task_risk and task_risk.total_risk_score > 60:
                    blocking_high_risk.append(dep_risk)
        
        if blocking_high_risk:
            for dep_risk in blocking_high_risk[:3]:
                recommendations.append(Recommendation(
                    type="prioritization",
                    priority="critical",
                    description=f"Prioritize '{dep_risk.task_name}' - blocks {len(dep_risk.blocks)} other tasks and has high risk. Consider adding more resources or splitting this task",
                    affected_tasks=[dep_risk.task_id] + dep_risk.blocks,
                    expected_impact=f"Unblock {len(dep_risk.blocks)} dependent tasks and reduce cascade risk by up to 40%"
                ))
        
        return recommendations
    
    def generate_complexity_recommendations(self,
                                           task_risk_analysis: List[TaskRiskAnalysis]) -> List[Recommendation]:
        """Generate recommendations for high-complexity tasks"""
        recommendations = []
        
        high_complexity_tasks = [
            task for task in task_risk_analysis
            if task.risk_factors.get('complexity', 0) > 70
        ]
        
        if high_complexity_tasks:
            for task in high_complexity_tasks[:2]:
                recommendations.append(Recommendation(
                    type="task_breakdown",
                    priority="medium",
                    description=f"Break down '{task.task_name}' into 2-3 smaller subtasks. Current complexity risk: {task.risk_factors.get('complexity', 0)}. Suggested split: Core functionality (5-8 pts) + Testing (3 pts) + Documentation (2 pts)",
                    affected_tasks=[task.task_id],
                    expected_impact="Reduce complexity risk by 30-40%, improve estimation accuracy, and enable parallel work by multiple team members"
                ))
        
        return recommendations
    
    def generate_deadline_recommendations(self,
                                         task_risk_analysis: List[TaskRiskAnalysis]) -> List[Recommendation]:
        """Generate recommendations for deadline-related risks"""
        recommendations = []
        
        urgent_tasks = [
            task for task in task_risk_analysis
            if task.risk_factors.get('deadline', 0) > 70
        ]
        
        if urgent_tasks:
            recommendations.append(Recommendation(
                type="deadline_adjustment",
                priority="high",
                description=f"{len(urgent_tasks)} tasks have critical deadline risk. Recommend: 1) Extend sprint by 2-3 days, OR 2) Reduce scope by deferring {len(urgent_tasks)//2} lower-priority tasks, OR 3) Add temporary resources to critical path",
                affected_tasks=[task.task_id for task in urgent_tasks],
                expected_impact="Reduce deadline pressure by 40%, improve delivery quality, and prevent team burnout"
            ))
        
        return recommendations
    
    def generate_velocity_recommendations(self,
                                         average_velocity: float,
                                         remaining_points: int,
                                         sprints_needed: float) -> List[Recommendation]:
        """Generate recommendations based on velocity analysis"""
        recommendations = []
        
        if sprints_needed > 2:
            recommendations.append(Recommendation(
                type="scope_adjustment",
                priority="critical",
                description=f"Current velocity ({average_velocity:.1f} pts/sprint) requires {sprints_needed:.1f} sprints to complete {remaining_points} remaining points. Recommend: 1) Prioritize MVP features (reduce scope by 30%), OR 2) Add 1-2 team members, OR 3) Extend timeline by {int(sprints_needed - 1)} sprints",
                affected_tasks=[],
                expected_impact="Align expectations with realistic delivery timeline. Prevents over-commitment and improves team morale"
            ))
        
        return recommendations
    
    def generate_all_recommendations(self,
                                    overload_analysis: List[OverloadAnalysis],
                                    dependency_risks: List[DependencyRisk],
                                    task_risk_analysis: List[TaskRiskAnalysis],
                                    tasks: List[TaskInput],
                                    average_velocity: float,
                                    remaining_points: int,
                                    sprints_needed: float) -> List[Recommendation]:
        """Generate all recommendations with smart work distribution"""
        recommendations = []
        
        # Priority 1: Smart work distribution (split large tasks)
        recommendations.extend(self.generate_work_distribution_recommendations(
            overload_analysis, tasks, task_risk_analysis, 
            [{'name': m.assignee, 'velocity_multiplier': 1.0, 'capacity': m.capacity} for m in overload_analysis]
        ))
        
        # Priority 2: Full reassignments (small tasks)
        recommendations.extend(self.generate_reassignment_recommendations(
            overload_analysis, tasks
        ))
        
        # Priority 3: Prioritization
        recommendations.extend(self.generate_priority_recommendations(
            dependency_risks, task_risk_analysis
        ))
        
        # Priority 4: Complexity breakdown
        recommendations.extend(self.generate_complexity_recommendations(
            task_risk_analysis
        ))
        
        # Priority 5: Deadline adjustments
        recommendations.extend(self.generate_deadline_recommendations(
            task_risk_analysis
        ))
        
        # Priority 6: Velocity-based recommendations
        recommendations.extend(self.generate_velocity_recommendations(
            average_velocity, remaining_points, sprints_needed
        ))
        
        # Sort by priority
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        recommendations.sort(key=lambda r: priority_order.get(r.priority, 4))
        
        return recommendations
