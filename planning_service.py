from typing import List, Dict
from datetime import datetime
from models import (PlanningRequest, PlanningResponse, TaskInput, TaskRiskAnalysis,
                   OverloadAnalysis, DependencyRisk, Recommendation, TeamMember)
from risk_engine import RiskEngine
from velocity_calculator import VelocityCalculator
from workload_analyzer import WorkloadAnalyzer
from dependency_analyzer import DependencyAnalyzer
from recommendation_engine import RecommendationEngine
from ai_summary_generator import AISummaryGenerator

class PlanningService:
    """Main orchestration service for planning analysis"""
    
    def __init__(self):
        self.risk_engine = RiskEngine()
        self.velocity_calculator = VelocityCalculator()
        self.workload_analyzer = WorkloadAnalyzer()
        self.dependency_analyzer = DependencyAnalyzer()
        self.recommendation_engine = RecommendationEngine()
        self.ai_summary_generator = AISummaryGenerator()
    
    def analyze_planning(self, request: PlanningRequest) -> PlanningResponse:
        """
        Main entry point for planning analysis.
        Orchestrates all analysis components.
        """
        
        # 1. Calculate velocity metrics
        average_velocity = self.velocity_calculator.calculate_average_velocity(
            request.velocity_history
        )
        
        sprint_capacity = self.velocity_calculator.calculate_sprint_capacity(
            [member.dict() for member in request.team_capacity]
        )
        
        remaining_points = self.velocity_calculator.calculate_remaining_story_points(
            request.tasks
        )
        
        sprints_needed = self.velocity_calculator.calculate_sprints_needed(
            remaining_points,
            average_velocity if average_velocity > 0 else sprint_capacity
        )
        
        # Assume 1 sprint planned (can be parameterized)
        predicted_delay = self.velocity_calculator.predict_release_delay(
            sprints_needed,
            planned_sprints=1
        )
        
        # 2. Analyze workload
        workload_distribution = self.workload_analyzer.calculate_workload_distribution(
            request.tasks
        )
        
        overload_analysis = self.workload_analyzer.detect_overloaded_members(
            workload_distribution,
            request.team_capacity
        )
        
        overload_risk_map = self.workload_analyzer.get_overload_risk_map(
            overload_analysis
        )
        
        # 3. Analyze dependencies
        self.dependency_analyzer.build_dependency_graph(request.tasks)
        blocked_tasks = self.dependency_analyzer.detect_blocked_tasks(request.tasks)
        dependency_risks = self.dependency_analyzer.analyze_dependency_risks(request.tasks)
        
        # 4. Calculate task risks
        task_status_map = {task.id: task.status for task in request.tasks}
        task_risk_analysis = []
        
        for task in request.tasks:
            # Calculate individual risk factors
            deadline_risk = self.risk_engine.calculate_deadline_risk(task.dueDate)
            complexity_risk = self.risk_engine.calculate_complexity_risk(task.storyPoints)
            dependency_risk = self.risk_engine.calculate_dependency_risk(
                task.id,
                task.dependencies or [],
                task_status_map
            )
            overload_risk = self.risk_engine.calculate_overload_risk(
                task.assignee,
                overload_risk_map.get(task.assignee, 0)
            )
            
            # Use average velocity for velocity risk
            current_velocity = self.velocity_calculator.calculate_completed_velocity(
                request.tasks
            )
            velocity_risk = self.risk_engine.calculate_velocity_risk(
                current_velocity,
                average_velocity if average_velocity > 0 else current_velocity
            )
            
            # Calculate total risk
            total_risk = self.risk_engine.calculate_total_risk(
                deadline_risk,
                complexity_risk,
                dependency_risk,
                overload_risk,
                velocity_risk
            )
            
            risk_level = self.risk_engine.categorize_risk_level(total_risk)
            
            # Generate task-specific recommendations
            task_recommendations = self.ai_summary_generator.generate_task_recommendations(
                TaskRiskAnalysis(
                    task_id=task.id,
                    task_name=task.name,
                    total_risk_score=total_risk,
                    risk_level=risk_level,
                    risk_factors={
                        'deadline': deadline_risk,
                        'complexity': complexity_risk,
                        'dependency': dependency_risk,
                        'overload': overload_risk,
                        'velocity': velocity_risk
                    },
                    recommendations=[]
                )
            )
            
            task_risk_analysis.append(TaskRiskAnalysis(
                task_id=task.id,
                task_name=task.name,
                total_risk_score=total_risk,
                risk_level=risk_level,
                risk_factors={
                    'deadline': deadline_risk,
                    'complexity': complexity_risk,
                    'dependency': dependency_risk,
                    'overload': overload_risk,
                    'velocity': velocity_risk
                },
                recommendations=task_recommendations
            ))
        
        # 5. Calculate overall project risk
        if task_risk_analysis:
            overall_risk_score = int(
                sum(t.total_risk_score for t in task_risk_analysis) / len(task_risk_analysis)
            )
        else:
            overall_risk_score = 0
        
        overall_risk_level = self.risk_engine.categorize_risk_level(overall_risk_score)
        
        # 6. Identify critical issues
        critical_issues = self._identify_critical_issues(
            task_risk_analysis,
            overload_analysis,
            blocked_tasks,
            predicted_delay
        )
        
        # 7. Generate recommendations
        recommendations = self.recommendation_engine.generate_all_recommendations(
            overload_analysis,
            dependency_risks,
            task_risk_analysis,
            request.tasks,
            average_velocity,
            remaining_points,
            sprints_needed
        )
        
        # 8. Generate AI health summary
        high_risk_count = sum(1 for t in task_risk_analysis if t.risk_level in ['critical', 'high'])
        overloaded_count = sum(1 for o in overload_analysis if o.is_overloaded)
        
        ai_health_summary = self.ai_summary_generator.generate_health_summary(
            overall_risk_score,
            overall_risk_level,
            len(request.tasks),
            high_risk_count,
            overloaded_count,
            len(blocked_tasks),
            predicted_delay,
            average_velocity,
            remaining_points,
            critical_issues
        )
        
        # 9. Build response
        return PlanningResponse(
            overall_risk_score=overall_risk_score,
            risk_level=overall_risk_level,
            predicted_release_delay_days=predicted_delay,
            average_velocity=average_velocity,
            sprint_capacity=sprint_capacity,
            remaining_story_points=remaining_points,
            sprints_needed=sprints_needed,
            task_analysis=task_risk_analysis,
            overload_analysis=overload_analysis,
            dependency_risks=dependency_risks,
            blocked_tasks=blocked_tasks,
            recommendations=recommendations,
            ai_health_summary=ai_health_summary,
            critical_issues=critical_issues
        )
    
    def _identify_critical_issues(self,
                                 task_risk_analysis: List[TaskRiskAnalysis],
                                 overload_analysis: List[OverloadAnalysis],
                                 blocked_tasks: List[str],
                                 predicted_delay: int) -> List[str]:
        """Identify critical issues requiring immediate attention"""
        
        issues = []
        
        # Critical risk tasks
        critical_tasks = [t for t in task_risk_analysis if t.risk_level == 'critical']
        if critical_tasks:
            issues.append(f"{len(critical_tasks)} tasks at critical risk level")
        
        # Severely overloaded members
        severe_overload = [o for o in overload_analysis if o.workload_percentage > 150]
        if severe_overload:
            issues.append(f"{len(severe_overload)} team members severely overloaded (>150% capacity)")
        
        # Blocked tasks
        if len(blocked_tasks) > 3:
            issues.append(f"{len(blocked_tasks)} tasks blocked by dependencies")
        
        # Significant delay
        if predicted_delay > 7:
            issues.append(f"Predicted release delay of {predicted_delay} days")
        
        # High complexity concentration
        high_complexity = [
            t for t in task_risk_analysis 
            if t.risk_factors.get('complexity', 0) > 70
        ]
        if len(high_complexity) > 5:
            issues.append(f"{len(high_complexity)} high-complexity tasks may need breakdown")
        
        return issues if issues else ["No critical issues detected"]
