from typing import List, Dict
from models import (TaskRiskAnalysis, OverloadAnalysis, DependencyRisk, 
                   Recommendation)
from llm import LLMS
import json

class AISummaryGenerator:
    """Generate AI-powered executive summaries using Gemini"""
    
    def __init__(self):
        self.llm = LLMS()
    
    def build_structured_prompt(self,
                               overall_risk_score: int,
                               risk_level: str,
                               task_count: int,
                               high_risk_count: int,
                               overloaded_count: int,
                               blocked_count: int,
                               predicted_delay: int,
                               average_velocity: float,
                               remaining_points: int,
                               critical_issues: List[str]) -> str:
        """Build structured prompt for Gemini"""
        
        prompt = f"""You are a senior project management AI assistant analyzing a software development project.

**Project Health Metrics:**
- Overall Risk Score: {overall_risk_score}/100 ({risk_level} risk)
- Total Tasks: {task_count}
- High-Risk Tasks: {high_risk_count}
- Overloaded Team Members: {overloaded_count}
- Blocked Tasks: {blocked_count}
- Predicted Release Delay: {predicted_delay} days
- Team Velocity: {average_velocity:.1f} story points/sprint
- Remaining Work: {remaining_points} story points

**Critical Issues Detected:**
{chr(10).join(f'- {issue}' for issue in critical_issues) if critical_issues else '- None'}

**Task:**
Generate a concise, executive-friendly project health summary (2-3 sentences) that:
1. Highlights the most critical concern
2. Provides context on project status
3. Suggests the top priority action

**Tone:** Professional, data-driven, actionable

**Output:** Plain text summary only (no JSON, no formatting)
"""
        return prompt
    
    def generate_health_summary(self,
                               overall_risk_score: int,
                               risk_level: str,
                               task_count: int,
                               high_risk_count: int,
                               overloaded_count: int,
                               blocked_count: int,
                               predicted_delay: int,
                               average_velocity: float,
                               remaining_points: int,
                               critical_issues: List[str]) -> str:
        """Generate AI health summary using Gemini"""
        
        try:
            prompt = self.build_structured_prompt(
                overall_risk_score,
                risk_level,
                task_count,
                high_risk_count,
                overloaded_count,
                blocked_count,
                predicted_delay,
                average_velocity,
                remaining_points,
                critical_issues
            )
            
            summary = self.llm.nlp(prompt)
            
            # Clean up the response
            summary = summary.strip()
            
            # Remove any markdown formatting
            summary = summary.replace('**', '').replace('*', '')
            
            return summary
            
        except Exception as e:
            # Fallback to rule-based summary if AI fails
            return self._generate_fallback_summary(
                overall_risk_score,
                risk_level,
                high_risk_count,
                overloaded_count,
                blocked_count,
                predicted_delay
            )
    
    def _generate_fallback_summary(self,
                                  overall_risk_score: int,
                                  risk_level: str,
                                  high_risk_count: int,
                                  overloaded_count: int,
                                  blocked_count: int,
                                  predicted_delay: int) -> str:
        """Generate rule-based summary as fallback"""
        
        if risk_level == "critical":
            summary = f"Project is at CRITICAL risk ({overall_risk_score}/100). "
        elif risk_level == "high":
            summary = f"Project is at HIGH risk ({overall_risk_score}/100). "
        elif risk_level == "moderate":
            summary = f"Project is at MODERATE risk ({overall_risk_score}/100). "
        else:
            summary = f"Project is at LOW risk ({overall_risk_score}/100). "
        
        concerns = []
        if high_risk_count > 0:
            concerns.append(f"{high_risk_count} high-risk tasks")
        if overloaded_count > 0:
            concerns.append(f"{overloaded_count} overloaded team members")
        if blocked_count > 0:
            concerns.append(f"{blocked_count} blocked tasks")
        
        if concerns:
            summary += f"Key concerns: {', '.join(concerns)}. "
        
        if predicted_delay > 0:
            summary += f"Predicted release delay: {predicted_delay} days. "
            summary += "Immediate action required: review task priorities and resource allocation."
        else:
            summary += "Project is on track for timely delivery."
        
        return summary
    
    def generate_task_recommendations(self,
                                     task_risk: TaskRiskAnalysis) -> List[str]:
        """Generate AI recommendations for a specific task"""
        
        recommendations = []
        
        # Deadline risk
        if task_risk.risk_factors.get('deadline', 0) > 70:
            recommendations.append("Consider extending deadline or reducing scope")
        
        # Complexity risk
        if task_risk.risk_factors.get('complexity', 0) > 70:
            recommendations.append("Break down into smaller subtasks")
        
        # Dependency risk
        if task_risk.risk_factors.get('dependency', 0) > 50:
            recommendations.append("Prioritize unblocking dependencies")
        
        # Overload risk
        if task_risk.risk_factors.get('overload', 0) > 70:
            recommendations.append("Reassign to less loaded team member")
        
        # Velocity risk
        if task_risk.risk_factors.get('velocity', 0) > 60:
            recommendations.append("Review team capacity and sprint planning")
        
        return recommendations if recommendations else ["Monitor progress closely"]
