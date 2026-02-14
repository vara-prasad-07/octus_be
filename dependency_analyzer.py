from typing import List, Dict, Set
from models import TaskInput, DependencyRisk

class DependencyAnalyzer:
    """Analyze task dependencies and propagate risk"""
    
    def __init__(self):
        self.dependency_graph = {}
        self.reverse_graph = {}
    
    def build_dependency_graph(self, tasks: List[TaskInput]) -> Dict[str, List[str]]:
        """
        Build dependency graph from tasks.
        Returns: Dict mapping task_id to list of dependency task_ids
        """
        self.dependency_graph = {}
        self.reverse_graph = {}
        
        for task in tasks:
            self.dependency_graph[task.id] = task.dependencies or []
            
            # Build reverse graph (what tasks depend on this one)
            for dep_id in (task.dependencies or []):
                if dep_id not in self.reverse_graph:
                    self.reverse_graph[dep_id] = []
                self.reverse_graph[dep_id].append(task.id)
        
        return self.dependency_graph
    
    def detect_blocked_tasks(self, tasks: List[TaskInput]) -> List[str]:
        """
        Find tasks blocked by incomplete dependencies.
        Returns: List of blocked task IDs
        """
        task_status_map = {task.id: task.status for task in tasks}
        blocked_tasks = []
        
        for task in tasks:
            if task.status == 'done':
                continue  # Completed tasks aren't blocked
            
            if task.dependencies:
                for dep_id in task.dependencies:
                    dep_status = task_status_map.get(dep_id, 'todo')
                    if dep_status != 'done':
                        blocked_tasks.append(task.id)
                        break  # Task is blocked, no need to check other deps
        
        return blocked_tasks
    
    def calculate_dependency_depth(self, task_id: str) -> int:
        """
        Calculate dependency chain depth for a task.
        Returns: Maximum depth of dependency chain
        """
        if task_id not in self.dependency_graph:
            return 0
        
        dependencies = self.dependency_graph[task_id]
        if not dependencies:
            return 0
        
        max_depth = 0
        for dep_id in dependencies:
            depth = 1 + self.calculate_dependency_depth(dep_id)
            max_depth = max(max_depth, depth)
        
        return max_depth
    
    def propagate_dependency_risk(self, task_id: str, base_risk: int,
                                  task_status_map: Dict[str, str]) -> int:
        """
        Propagate risk through dependency chain.
        Returns: Additional risk score from dependencies
        """
        if task_id not in self.dependency_graph:
            return 0
        
        dependencies = self.dependency_graph[task_id]
        if not dependencies:
            return 0
        
        # Count incomplete dependencies
        incomplete_deps = sum(
            1 for dep_id in dependencies 
            if task_status_map.get(dep_id, 'todo') != 'done'
        )
        
        if incomplete_deps == 0:
            return 0
        
        # Risk increases with number of incomplete dependencies
        dependency_risk = min(incomplete_deps * 20, 80)  # Cap at 80
        
        return dependency_risk
    
    def find_critical_path(self, tasks: List[TaskInput]) -> List[str]:
        """
        Find the critical path (longest dependency chain).
        Returns: List of task IDs in critical path
        """
        max_depth = 0
        critical_task = None
        
        for task in tasks:
            depth = self.calculate_dependency_depth(task.id)
            if depth > max_depth:
                max_depth = depth
                critical_task = task.id
        
        if not critical_task:
            return []
        
        # Trace back the critical path
        path = [critical_task]
        current = critical_task
        
        while current in self.dependency_graph and self.dependency_graph[current]:
            # Find dependency with maximum depth
            max_dep_depth = -1
            next_task = None
            
            for dep_id in self.dependency_graph[current]:
                depth = self.calculate_dependency_depth(dep_id)
                if depth > max_dep_depth:
                    max_dep_depth = depth
                    next_task = dep_id
            
            if next_task:
                path.append(next_task)
                current = next_task
            else:
                break
        
        return path
    
    def analyze_dependency_risks(self, tasks: List[TaskInput]) -> List[DependencyRisk]:
        """
        Analyze dependency risks for all tasks.
        Returns: List of dependency risk analysis
        """
        self.build_dependency_graph(tasks)
        task_map = {task.id: task for task in tasks}
        task_status_map = {task.id: task.status for task in tasks}
        
        dependency_risks = []
        
        for task in tasks:
            blocked_by = []
            if task.dependencies:
                for dep_id in task.dependencies:
                    if task_status_map.get(dep_id, 'todo') != 'done':
                        blocked_by.append(dep_id)
            
            blocks = self.reverse_graph.get(task.id, [])
            
            # Calculate dependency risk score
            risk_score = 0
            if blocked_by:
                risk_score += len(blocked_by) * 20  # 20 points per blocking dependency
            if blocks and task.status != 'done':
                risk_score += len(blocks) * 10  # 10 points per task this blocks
            
            risk_score = min(risk_score, 100)
            
            if blocked_by or blocks:
                dependency_risks.append(DependencyRisk(
                    task_id=task.id,
                    task_name=task.name,
                    blocked_by=blocked_by,
                    blocks=blocks,
                    dependency_risk_score=risk_score
                ))
        
        return dependency_risks
    
    def detect_circular_dependencies(self, tasks: List[TaskInput]) -> List[List[str]]:
        """
        Detect circular dependency chains.
        Returns: List of circular dependency chains
        """
        self.build_dependency_graph(tasks)
        visited = set()
        rec_stack = set()
        cycles = []
        
        def dfs(task_id: str, path: List[str]) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)
            path.append(task_id)
            
            if task_id in self.dependency_graph:
                for dep_id in self.dependency_graph[task_id]:
                    if dep_id not in visited:
                        if dfs(dep_id, path.copy()):
                            return True
                    elif dep_id in rec_stack:
                        # Found a cycle
                        cycle_start = path.index(dep_id)
                        cycles.append(path[cycle_start:] + [dep_id])
                        return True
            
            rec_stack.remove(task_id)
            return False
        
        for task in tasks:
            if task.id not in visited:
                dfs(task.id, [])
        
        return cycles
