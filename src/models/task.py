"""
BMF Flow Visualizer - Core Models

Data structures for representing Prefect flow components.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from pydantic import BaseModel, Field


# ============================================================================
# Task Model
# ============================================================================

@dataclass
class Task:
    """
    Represents a single task in a Prefect flow.
    
    Attributes:
        task_id: Unique identifier (usually variable name)
        task_type: Type of task (ReadExcel, Filter, MergeTables, etc.)
        task_name: Display name from task_args(name=...)
        parameters: Dictionary of task parameters
        line_number: Line number in source code
        file_path: Path to source file
        metadata: Additional metadata (color, shape, etc.)
    """
    task_id: str
    task_type: str
    task_name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    line_number: Optional[int] = None
    file_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __hash__(self):
        return hash(self.task_id)
    
    def __eq__(self, other):
        if isinstance(other, Task):
            return self.task_id == other.task_id
        return False
    
    def add_parameter(self, key: str, value: Any):
        """Add or update a parameter."""
        self.parameters[key] = value
    
    def set_metadata(self, key: str, value: Any):
        """Add or update metadata."""
        self.metadata[key] = value
    
    def get_display_label(self) -> str:
        """Get formatted display label for diagram."""
        return f"{self.task_name}"


# ============================================================================
# Edge Model
# ============================================================================

@dataclass
class Edge:
    """
    Represents a dependency edge between two tasks.
    
    Attributes:
        source_id: ID of source task
        target_id: ID of target task
        label: Edge label (for diagram)
        edge_type: Type of relationship (dependency, merge, etc.)
        metadata: Additional metadata
    """
    source_id: str
    target_id: str
    label: Optional[str] = None
    edge_type: str = "dependency"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __hash__(self):
        return hash((self.source_id, self.target_id))
    
    def __eq__(self, other):
        if isinstance(other, Edge):
            return self.source_id == other.source_id and self.target_id == other.target_id
        return False


# ============================================================================
# Flow Graph Model
# ============================================================================

class FlowGraph:
    """
    Represents the complete dependency graph of a Prefect flow.
    
    Attributes:
        object_name: Name of the Veeva object
        object_path: Path to the object directory
        tasks: Dictionary of task_id -> Task
        edges: List of edges
        metadata: Flow-level metadata
    """
    
    def __init__(self, object_name: str, object_path: str):
        self.object_name = object_name
        self.object_path = object_path
        self.tasks: Dict[str, Task] = {}
        self.edges: List[Edge] = []
        self.metadata: Dict[str, Any] = {}
    
    def add_task(self, task: Task):
        """Add a task to the graph."""
        if task.task_id in self.tasks:
            raise ValueError(f"Task {task.task_id} already exists")
        self.tasks[task.task_id] = task
    
    def add_edge(self, edge: Edge):
        """Add an edge to the graph."""
        # Check if source and target tasks exist
        if edge.source_id not in self.tasks:
            raise ValueError(f"Source task {edge.source_id} not found")
        if edge.target_id not in self.tasks:
            raise ValueError(f"Target task {edge.target_id} not found")
        
        # Avoid duplicate edges
        if edge not in self.edges:
            self.edges.append(edge)
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return self.tasks.get(task_id)
    
    def get_upstream_tasks(self, task_id: str) -> List[Task]:
        """Get all upstream tasks."""
        upstream_ids = set()
        for edge in self.edges:
            if edge.target_id == task_id:
                upstream_ids.add(edge.source_id)
        return [self.tasks[tid] for tid in upstream_ids if tid in self.tasks]
    
    def get_downstream_tasks(self, task_id: str) -> List[Task]:
        """Get all downstream tasks."""
        downstream_ids = set()
        for edge in self.edges:
            if edge.source_id == task_id:
                downstream_ids.add(edge.target_id)
        return [self.tasks[tid] for tid in downstream_ids if tid in self.tasks]
    
    def get_root_tasks(self) -> List[Task]:
        """Get all root tasks (no upstream dependencies)."""
        target_ids = set(edge.target_id for edge in self.edges)
        return [task for task in self.tasks.values() if task.task_id not in target_ids]
    
    def get_leaf_tasks(self) -> List[Task]:
        """Get all leaf tasks (no downstream dependencies)."""
        source_ids = set(edge.source_id for edge in self.edges)
        return [task for task in self.tasks.values() if task.task_id not in source_ids]
    
    def validate(self) -> List[str]:
        """
        Validate graph integrity.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check for orphaned tasks
        all_edge_task_ids = set()
        for edge in self.edges:
            all_edge_task_ids.add(edge.source_id)
            all_edge_task_ids.add(edge.target_id)
        
        task_ids = set(self.tasks.keys())
        
        # Tasks with no edges are okay (independent tasks)
        # But we should warn about them
        isolated = task_ids - all_edge_task_ids
        if isolated:
            errors.append(f"Isolated tasks (no dependencies): {', '.join(isolated)}")
        
        # Check for edges with non-existent tasks
        for edge in self.edges:
            if edge.source_id not in task_ids:
                errors.append(f"Edge references non-existent source task: {edge.source_id}")
            if edge.target_id not in task_ids:
                errors.append(f"Edge references non-existent target task: {edge.target_id}")
        
        return errors
    
    def __repr__(self):
        return f"FlowGraph(object_name='{self.object_name}', tasks={len(self.tasks)}, edges={len(self.edges)})"


# ============================================================================
# Analysis Result Model
# ============================================================================

@dataclass
class FlowAnalysis:
    """
    Complete analysis result from parsing a flow.
    
    Attributes:
        object_name: Name of the Veeva object
        tasks: List of extracted tasks
        edges: List of extracted edges
        raw_metadata: Raw metadata from parsing
        errors: List of parsing errors (if any)
        warnings: List of warnings (if any)
    """
    object_name: str
    tasks: List[Task] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)
    raw_metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def has_errors(self) -> bool:
        """Check if analysis has errors."""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """Check if analysis has warnings."""
        return len(self.warnings) > 0
