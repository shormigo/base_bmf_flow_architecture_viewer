"""BMF Flow Visualizer - AST-Based Python Parser"""

import ast
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass

from src.models.task import Task, Edge, FlowAnalysis
from src.utils.logger import FlowVisualizerLogger
from src.config.loader import ConfigLoader


class ASTPythonParser:
    """
    Parse Prefect flow Python code using Abstract Syntax Tree (AST).
    
    This parser analyzes the creation_flow.py file to extract:
    - Task definitions and instantiations
    - Task dependencies (set_upstream/set_downstream calls)
    - Task parameters and configuration
    - Variable references and resolutions
    """
    
    def __init__(self, flow_py_path: str):
        """
        Initialize AST parser.
        
        Args:
            flow_py_path: Path to creation_flow.py file
        """
        self.flow_py_path = Path(flow_py_path)
        self.logger = FlowVisualizerLogger.get_logger()
        self.config = ConfigLoader.get_instance()
        
        self._validate_file()
        self._read_file()
    
    def _validate_file(self):
        """Validate that file exists and is readable."""
        if not self.flow_py_path.exists():
            raise FileNotFoundError(f"Flow file not found: {self.flow_py_path}")
        
        if not self.flow_py_path.is_file():
            raise FileNotFoundError(f"Path is not a file: {self.flow_py_path}")
        
        if not self.flow_py_path.suffix == ".py":
            raise ValueError(f"File must be .py file: {self.flow_py_path}")
    
    def _read_file(self):
        """Read and store file contents."""
        try:
            with open(self.flow_py_path, 'r', encoding='utf-8') as f:
                self.source_code = f.read()
        except IOError as e:
            raise IOError(f"Failed to read file: {e}")
    
    def parse(self) -> FlowAnalysis:
        """
        Main entry point for parsing.
        
        Returns:
            FlowAnalysis object with extracted tasks, edges, and metadata
        """
        self.logger.info(f"Parsing flow file: {self.flow_py_path}")
        
        # Extract object name: file is at <object>/flows/creation_flow.py
        # Go up 2 levels to get to <object>/
        object_name = self.flow_py_path.parent.parent.name
        
        analysis = FlowAnalysis(
            object_name=object_name,
        )
        
        try:
            # Parse Python code into AST
            tree = ast.parse(self.source_code)
            self.logger.debug("Successfully parsed Python AST")
            
            # Variable tracking for resolution
            self.variables: Dict[str, Any] = {}
            self.task_assignments: Dict[str, Tuple[int, str]] = {}  # var_name -> (line, task_type)
            
            # First pass: extract task definitions
            analysis.tasks = self._extract_task_definitions(tree)
            self.logger.info(f"Extracted {len(analysis.tasks)} tasks")
            
            # Second pass: extract dependencies
            analysis.edges = self._extract_dependencies(tree, analysis.tasks)
            self.logger.info(f"Extracted {len(analysis.edges)} dependencies")
            
            # Third pass: extract parameters and metadata
            self._enrich_tasks(tree, analysis.tasks)
            
            # Fourth pass: extract implicit dependencies from constructor arguments
            implicit_edges = self._extract_implicit_dependencies(tree, analysis.tasks)
            for edge in implicit_edges:
                if edge not in analysis.edges:
                    analysis.edges.append(edge)
            self.logger.info(f"Extracted {len(implicit_edges)} implicit dependencies from constructor args")
            
            # Validate analysis
            if not analysis.tasks:
                analysis.warnings.append("No tasks found in flow")
            
            self.logger.info("Flow analysis complete")
            
        except SyntaxError as e:
            analysis.errors.append(f"Python syntax error: {e}")
            self.logger.error(f"Syntax error in flow file: {e}")
        except Exception as e:
            analysis.errors.append(f"Unexpected error during parsing: {e}")
            self.logger.error(f"Unexpected error: {e}")
        
        return analysis
    
    def _extract_task_definitions(self, tree: ast.AST) -> List[Task]:
        """
        Extract all task definitions from the AST.
        
        Looks for patterns like:
            task_var = TaskType(parameters...)
        
        Args:
            tree: AST tree
            
        Returns:
            List of Task objects
        """
        tasks = []
        task_types = set(self.config.get_task_definitions().keys())
        
        for node in ast.walk(tree):
            # Look for assignments
            if isinstance(node, ast.Assign):
                # Get assignment target (variable name)
                if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                    var_name = node.targets[0].id
                    
                    # Check if RHS is a task instantiation
                    if isinstance(node.value, ast.Call):
                        task_type = self._get_call_name(node.value)
                        
                        if task_type in task_types:
                            task_name = self._extract_task_name(node.value)
                            
                            task = Task(
                                task_id=var_name,
                                task_type=task_type,
                                task_name=task_name or var_name,
                                line_number=node.lineno,
                                file_path=str(self.flow_py_path),
                            )
                            
                            # Extract parameters
                            params = self._extract_parameters(node.value)
                            task.parameters = params
                            
                            tasks.append(task)
                            self.task_assignments[var_name] = (node.lineno, task_type)
                            self.variables[var_name] = task
                            
                            self.logger.debug(f"Found task: {var_name} ({task_type})")
        
        return tasks
    
    def _get_call_name(self, call_node: ast.Call) -> Optional[str]:
        """
        Extract function/class name from a Call node.
        
        Handles:
        - Direct calls: ReadExcel(...)
        - Attribute calls: obj.method(...)
        """
        if isinstance(call_node.func, ast.Name):
            return call_node.func.id
        elif isinstance(call_node.func, ast.Attribute):
            return call_node.func.attr
        
        return None
    
    def _extract_task_name(self, call_node: ast.Call) -> Optional[str]:
        """
        Extract task display name from task_args(name=...).
        
        Looks for: task_args=dict(name="Display Name")
        """
        for keyword in call_node.keywords:
            if keyword.arg == "task_args":
                # task_args=dict(name="...")
                if isinstance(keyword.value, ast.Call):
                    for inner_kw in keyword.value.keywords:
                        if inner_kw.arg == "name":
                            if isinstance(inner_kw.value, ast.Constant):
                                return inner_kw.value.value
                            elif isinstance(inner_kw.value, ast.Str):  # Python 3.7 compat
                                return inner_kw.value.s
        
        return None
    
    def _extract_parameters(self, call_node: ast.Call) -> Dict[str, Any]:
        """
        Extract parameters from a function call.
        
        Handles:
        - Keyword arguments: param="value"
        - Variable references: param=variable_name
        - Function calls: param=full_path(...)
        """
        params = {}
        
        for keyword in call_node.keywords:
            param_name = keyword.arg
            param_value = self._resolve_value(keyword.value)
            params[param_name] = param_value
        
        return params
    
    def _resolve_value(self, node: ast.expr) -> Any:
        """
        Resolve a value from an AST node.
        
        Handles:
        - Constants (strings, numbers, booleans)
        - Variables
        - Function calls
        - Dictionaries
        - Lists
        """
        # Constant values
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Str):  # Python 3.7 compat
            return node.s
        elif isinstance(node, ast.Num):  # Python 3.7 compat
            return node.n
        elif isinstance(node, ast.NameConstant):  # Python 3.7 compat
            return node.value
        
        # Variable references
        elif isinstance(node, ast.Name):
            return node.id
        
        # Function calls
        elif isinstance(node, ast.Call):
            func_name = self._get_call_name(node)
            return f"{func_name}(...)"  # Simplified representation
        
        # Dictionary literals
        elif isinstance(node, ast.Dict):
            result = {}
            for k, v in zip(node.keys, node.values):
                key = self._resolve_value(k) if k else None
                val = self._resolve_value(v)
                if key:
                    result[key] = val
            return result
        
        # List literals
        elif isinstance(node, ast.List):
            return [self._resolve_value(elt) for elt in node.elts]
        
        # Tuple literals
        elif isinstance(node, ast.Tuple):
            return tuple(self._resolve_value(elt) for elt in node.elts)
        
        # Attribute access
        elif isinstance(node, ast.Attribute):
            value = self._resolve_value(node.value)
            return f"{value}.{node.attr}"
        
        # Default: return None
        return None
    
    def _extract_dependencies(self, tree: ast.AST, tasks: List[Task]) -> List[Edge]:
        """
        Extract task dependencies from set_upstream, set_downstream, and set_dependencies calls.
        
        Looks for patterns like:
            task_a.set_upstream(task=[task_b, task_c])
            task_a.set_downstream(task=task_b)
            task_a.set_dependencies(upstream_tasks=[task_b, task_c])
        
        Args:
            tree: AST tree
            tasks: List of extracted tasks
            
        Returns:
            List of Edge objects
        """
        edges = []
        task_ids = {task.task_id for task in tasks}
        
        for node in ast.walk(tree):
            # Look for method calls on task variables
            if isinstance(node, ast.Expr):
                if isinstance(node.value, ast.Call):
                    call = node.value
                    
                    # Check for .set_upstream or .set_downstream or .set_dependencies
                    if isinstance(call.func, ast.Attribute):
                        method_name = call.func.attr
                        
                        if method_name == "set_upstream":
                            # obj.set_upstream(task=...)
                            target_id = self._get_call_object(call.func)
                            
                            # Extract upstream tasks from arguments
                            upstream_ids = self._extract_task_list_from_call(call)
                            
                            for upstream_id in upstream_ids:
                                if upstream_id in task_ids and target_id in task_ids:
                                    edge = Edge(
                                        source_id=upstream_id,
                                        target_id=target_id,
                                        edge_type="dependency"
                                    )
                                    if edge not in edges:
                                        edges.append(edge)
                                    self.logger.debug(f"Found dependency: {upstream_id} -> {target_id}")
                        
                        elif method_name == "set_downstream":
                            # obj.set_downstream(task=...)
                            source_id = self._get_call_object(call.func)
                            
                            # Extract downstream tasks from arguments
                            downstream_ids = self._extract_task_list_from_call(call)
                            
                            for downstream_id in downstream_ids:
                                if source_id in task_ids and downstream_id in task_ids:
                                    edge = Edge(
                                        source_id=source_id,
                                        target_id=downstream_id,
                                        edge_type="dependency"
                                    )
                                    if edge not in edges:
                                        edges.append(edge)
                                    self.logger.debug(f"Found dependency: {source_id} -> {downstream_id}")
                        
                        elif method_name == "set_dependencies":
                            # obj.set_dependencies(upstream_tasks=[...])
                            target_id = self._get_call_object(call.func)
                            
                            # Extract upstream tasks from 'upstream_tasks' parameter
                            upstream_ids = self._extract_task_list_from_call(call, param_name="upstream_tasks")
                            
                            for upstream_id in upstream_ids:
                                if upstream_id in task_ids and target_id in task_ids:
                                    edge = Edge(
                                        source_id=upstream_id,
                                        target_id=target_id,
                                        edge_type="dependency"
                                    )
                                    if edge not in edges:
                                        edges.append(edge)
                                    self.logger.debug(f"Found dependency via set_dependencies: {upstream_id} -> {target_id}")
        
        return edges
    
    def _get_call_object(self, attr_node: ast.Attribute) -> Optional[str]:
        """Get the object that a method is called on."""
        if isinstance(attr_node.value, ast.Name):
            return attr_node.value.id
        
        return None
    
    def _extract_task_list_from_call(self, call_node: ast.Call, param_name: Optional[str] = None) -> List[str]:
        """
        Extract task IDs from method call arguments.
        
        Handles:
        - task=[task_a, task_b]
        - task=task_a
        - task_list=[...]
        - upstream_tasks=[task_a, task_b]
        
        Args:
            call_node: AST Call node
            param_name: Specific parameter name to look for (e.g., "upstream_tasks")
                       If None, looks for "task" or "task_list"
        
        Returns:
            List of task IDs found
        """
        task_ids = []
        
        # Determine which parameter names to check
        param_names = [param_name] if param_name else ("task", "task_list")
        
        for keyword in call_node.keywords:
            if keyword.arg in param_names:
                # Handle list of tasks
                if isinstance(keyword.value, ast.List):
                    for elt in keyword.value.elts:
                        if isinstance(elt, ast.Name):
                            task_ids.append(elt.id)
                
                # Handle single task
                elif isinstance(keyword.value, ast.Name):
                    task_ids.append(keyword.value.id)
        
        return task_ids
    
    def _enrich_tasks(self, tree: ast.AST, tasks: List[Task]):
        """
        Enrich task metadata with additional information.
        
        Currently adds:
        - Color based on task type
        - Category
        """
        for task in tasks:
            # Get task definition for color
            task_def = self.config.get_task_def(task.task_type)
            
            if task_def:
                task.set_metadata("color", task_def.get("color", "#F5F5F5"))
                task.set_metadata("category", task_def.get("category", "unknown"))
                task.set_metadata("icon", task_def.get("icon", ""))
            
            # Add display label
            task.set_metadata("display_label", task.get_display_label())

    def _extract_implicit_dependencies(self, tree: ast.AST, tasks: List[Task]) -> List[Edge]:
        """
        Extract implicit dependencies from constructor parameters.
        
        Looks for patterns like:
            task_a = TaskType(input_table=task_b, ...)
            task_a = TaskType(input_paths=[task_b, task_c], ...)
        
        Args:
            tree: AST tree
            tasks: List of extracted tasks
            
        Returns:
            List of Edge objects representing implicit dependencies
        """
        edges = []
        task_ids = {task.task_id for task in tasks}
        
        for node in ast.walk(tree):
            # Look for assignments: var = TaskType(...)
            if isinstance(node, ast.Assign):
                if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                    target_id = node.targets[0].id
                    
                    # Only process if this is a known task
                    if target_id not in task_ids:
                        continue
                    
                    # Check if RHS is a task instantiation
                    if isinstance(node.value, ast.Call):
                        # Extract dependencies from keyword arguments
                        for keyword in node.value.keywords:
                            if keyword.arg in ("input_table", "input_paths"):
                                source_ids = self._extract_task_references(keyword.value)
                                
                                for source_id in source_ids:
                                    if source_id in task_ids:
                                        edge = Edge(
                                            source_id=source_id,
                                            target_id=target_id,
                                            edge_type="data_dependency"
                                        )
                                        if edge not in edges:
                                            edges.append(edge)
                                            self.logger.debug(f"Found implicit dependency: {source_id} -> {target_id}")
        
        return edges
    
    def _extract_task_references(self, node: ast.expr) -> List[str]:
        """
        Extract task variable names from an AST expression.
        
        Handles:
        - Single variable: task_a
        - List of variables: [task_a, task_b]
        - Dictionary access: task_a["key"]
        
        Args:
            node: AST expression node
            
        Returns:
            List of task variable names
        """
        refs = []
        
        # Single variable reference
        if isinstance(node, ast.Name):
            refs.append(node.id)
        
        # List of variables
        elif isinstance(node, ast.List):
            for elt in node.elts:
                if isinstance(elt, ast.Name):
                    refs.append(elt.id)
        
        # Dictionary/subscript access: task_var["key"]
        elif isinstance(node, ast.Subscript):
            if isinstance(node.value, ast.Name):
                refs.append(node.value.id)
        
        return refs
