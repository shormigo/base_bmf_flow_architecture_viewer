"""BMF Flow Visualizer - Graph Builder for Flow Construction"""

from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass

from src.models.task import Task, Edge, FlowGraph, FlowAnalysis
from src.parsers.python_parser import ASTPythonParser
from src.parsers.yaml_parser import YAMLParser, YAMLAnalysis
from src.discovery.file_locator import FileLocator
from src.utils.logger import FlowVisualizerLogger


@dataclass
class GraphBuildResult:
    """Result of graph building operation."""
    graph: FlowGraph
    success: bool
    errors: List[str]
    warnings: List[str]
    metadata: Dict[str, any]


class GraphBuilder:
    """
    Build complete flow graphs from parsed components.
    
    Integrates Python parser, YAML parser, and file locator to construct
    a comprehensive FlowGraph representation of a BMF flow.
    """
    
    def __init__(self, object_path: str):
        """
        Initialize graph builder.
        
        Args:
            object_path: Path to BMF object directory
        """
        self.object_path = Path(object_path)
        self.logger = FlowVisualizerLogger.get_logger()
        
        # Try to initialize FileLocator - catch errors for invalid paths
        try:
            self.file_locator = FileLocator(str(self.object_path))
            self.locator_error = None
        except (FileNotFoundError, NotADirectoryError) as e:
            self.file_locator = None
            self.locator_error = str(e)
            self.logger.error(f"Invalid object path: {e}")
        
        # Storage for parsed components
        self.python_analysis: Optional[FlowAnalysis] = None
        self.yaml_analyses: Dict[str, YAMLAnalysis] = {}
        self.graph: Optional[FlowGraph] = None
    
    def build(self) -> GraphBuildResult:
        """
        Main entry point for building flow graph.
        
        Returns:
            GraphBuildResult with graph and status
        """
        self.logger.info(f"Building flow graph for: {self.object_path}")
        
        errors = []
        warnings = []
        metadata = {}
        
        # Check for locator initialization error
        if self.locator_error:
            errors.append(f"Invalid object path: {self.locator_error}")
            return GraphBuildResult(
                graph=FlowGraph(object_name="unknown", object_path=str(self.object_path)),
                success=False,
                errors=errors,
                warnings=warnings,
                metadata=metadata
            )
        
        try:
            # Step 1: Parse Python flow file
            self.logger.debug("Step 1: Parsing Python flow file")
            flow_path = self.file_locator.locate_creation_flow()
            
            if not flow_path:
                errors.append("creation_flow.py not found")
                return GraphBuildResult(
                    graph=FlowGraph(object_name="unknown", object_path=str(self.object_path)),
                    success=False,
                    errors=errors,
                    warnings=warnings,
                    metadata=metadata
                )
            
            parser = ASTPythonParser(str(flow_path))
            self.python_analysis = parser.parse()
            
            if self.python_analysis.errors:
                errors.extend(self.python_analysis.errors)
            if self.python_analysis.warnings:
                warnings.extend(self.python_analysis.warnings)
            
            # Step 2: Parse YAML files
            self.logger.debug("Step 2: Parsing YAML configuration files")
            self._parse_yaml_files(errors, warnings)
            
            # Step 3: Build graph from tasks and edges
            self.logger.debug("Step 3: Building graph from parsed data")
            self.graph = self._build_graph_from_analysis(errors, warnings)
            
            # Step 4: Enrich graph with YAML metadata
            self.logger.debug("Step 4: Enriching graph with YAML metadata")
            self._enrich_graph_with_yaml(errors, warnings)
            
            # Step 4.5: Link known terminal chain if edges are missing
            self._link_known_terminal_chain(warnings)

            # Step 5: Validate graph
            self.logger.debug("Step 5: Validating graph structure")
            validation_errors = self._validate_graph()
            if validation_errors:
                errors.extend(validation_errors)
            
            success = len(errors) == 0
            
            metadata = {
                'object_name': self.python_analysis.object_name,
                'task_count': len(self.graph.tasks),
                'edge_count': len(self.graph.edges),
                'yaml_files_parsed': len(self.yaml_analyses),
            }
            
            self.logger.info(
                f"Graph building {'succeeded' if success else 'failed'}: "
                f"{len(self.graph.tasks)} tasks, {len(self.graph.edges)} edges"
            )
            
            return GraphBuildResult(
                graph=self.graph,
                success=success,
                errors=errors,
                warnings=warnings,
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.error(f"Unexpected error during graph building: {e}")
            errors.append(f"Unexpected error: {e}")
            return GraphBuildResult(
                graph=FlowGraph(object_name="unknown", object_path=str(self.object_path)),
                success=False,
                errors=errors,
                warnings=warnings,
                metadata=metadata
            )
    
    def _parse_yaml_files(self, errors: List[str], warnings: List[str]):
        """Parse all YAML configuration files."""
        yaml_files_dict = self.file_locator.find_all_yaml_files()
        
        # Iterate through all categories and their files
        for category, file_list in yaml_files_dict.items():
            for yaml_path in file_list:
                try:
                    parser = YAMLParser(str(yaml_path))
                    analysis = parser.parse()
                    
                    # Store analysis by relative path
                    rel_path = yaml_path.relative_to(self.object_path)
                    self.yaml_analyses[str(rel_path)] = analysis
                    
                    if analysis.errors:
                        errors.extend([f"{rel_path}: {err}" for err in analysis.errors])
                    if analysis.warnings:
                        warnings.extend([f"{rel_path}: {warn}" for warn in analysis.warnings])
                        
                    self.logger.debug(f"Parsed YAML: {rel_path} ({analysis.file_type})")
                    
                except Exception as e:
                    yaml_name = yaml_path.name
                    warnings.append(f"Failed to parse {yaml_name}: {e}")
                    self.logger.warning(f"Failed to parse YAML {yaml_path}: {e}")
    
    def _build_graph_from_analysis(
        self, 
        errors: List[str], 
        warnings: List[str]
    ) -> FlowGraph:
        """Build FlowGraph from Python analysis."""
        graph = FlowGraph(
            object_name=self.python_analysis.object_name,
            object_path=str(self.object_path)
        )
        
        # Add all tasks to graph
        for task in self.python_analysis.tasks:
            try:
                graph.add_task(task)
            except Exception as e:
                errors.append(f"Failed to add task {task.task_id}: {e}")
        
        # Add all edges to graph
        for edge in self.python_analysis.edges:
            try:
                graph.add_edge(edge)
            except Exception as e:
                warnings.append(f"Failed to add edge {edge.source_id}->{edge.target_id}: {e}")
        
        return graph

    def _link_known_terminal_chain(self, warnings: List[str]):
        """Ensure Mapping -> CreateObjects -> GenerateReport are linked if present and unique.

        This addresses common domain-specific terminal steps that should be chained
        but may not be explicitly connected in the parsed dependencies.
        """
        if not self.graph:
            return

        # Find tasks by type
        mapping_tasks = [t for t in self.graph.tasks.values() if t.task_type in ("Mapping", "MapToSchema", "TransformMap")]
        create_tasks = [t for t in self.graph.tasks.values() if t.task_type in ("CreateObjects", "CreateVeevaObjects")]
        report_tasks = [t for t in self.graph.tasks.values() if t.task_type in ("GenerateReport", "Report", "ExportReport")]

        # Only apply when unique to avoid ambiguity
        if len(mapping_tasks) == 1 and len(create_tasks) == 1:
            m = mapping_tasks[0].task_id
            c = create_tasks[0].task_id
            if not any(e.source_id == m and e.target_id == c for e in self.graph.edges):
                try:
                    self.graph.add_edge(Edge(source_id=m, target_id=c, label="CreateObjects"))
                    warnings.append("Linked Mapping -> CreateObjects (auto)")
                except Exception:
                    pass

        if len(create_tasks) == 1 and len(report_tasks) == 1:
            c = create_tasks[0].task_id
            r = report_tasks[0].task_id
            if not any(e.source_id == c and e.target_id == r for e in self.graph.edges):
                try:
                    self.graph.add_edge(Edge(source_id=c, target_id=r, label="GenerateReport"))
                    warnings.append("Linked CreateObjects -> GenerateReport (auto)")
                except Exception:
                    pass
    
    def _enrich_graph_with_yaml(self, errors: List[str], warnings: List[str]):
        """Enrich graph tasks with YAML metadata."""
        for task_id, task in self.graph.tasks.items():
            # Find YAML files referenced by this task
            yaml_refs = self._find_yaml_references(task)
            
            for yaml_ref in yaml_refs:
                if yaml_ref in self.yaml_analyses:
                    analysis = self.yaml_analyses[yaml_ref]
                    self._add_yaml_metadata_to_task(task, analysis)
    
    def _find_yaml_references(self, task: Task) -> List[str]:
        """Find YAML files referenced in task parameters."""
        yaml_refs = []
        
        # Check common parameter names for YAML file references
        param_names = [
            'criteria_descriptions_file', 
            'merging_rules', 
            'mapping_rules',
            'rules',  # Some tasks use just 'rules'
        ]
        
        for param_name in param_names:
            if param_name in task.parameters:
                param_value = task.parameters[param_name]
                if isinstance(param_value, str):
                    # If parameters show "full_path(...)", use heuristic matching based on task name
                    if param_value == "full_path(...)":
                        # Match based on task name convention
                        # e.g., task "table_merger_gxpd_exports" -> "merging_rules/table_merger_gxpd_exports.yml"
                        for yaml_path in self.yaml_analyses.keys():
                            yaml_filename = yaml_path.split('/')[-1].replace('.yml', '').replace('.yaml', '')
                            # Check if task_id contains the yaml filename or vice versa
                            if yaml_filename in task.task_id or task.task_id in yaml_filename:
                                yaml_refs.append(yaml_path)
                    else:
                        # Try direct filename match first
                        for yaml_path in self.yaml_analyses.keys():
                            yaml_filename = yaml_path.split('/')[-1]
                            if yaml_filename in param_value:
                                yaml_refs.append(yaml_path)
                                break
                        else:
                            # Try partial path match
                            for yaml_path in self.yaml_analyses.keys():
                                if yaml_path in param_value or param_value.endswith(yaml_path):
                                    yaml_refs.append(yaml_path)
                                    break
        
        return list(set(yaml_refs))  # Remove duplicates
    
    def _add_yaml_metadata_to_task(self, task: Task, analysis: YAMLAnalysis):
        """Add YAML analysis metadata to task."""
        if 'yaml_metadata' not in task.metadata:
            task.metadata['yaml_metadata'] = {}
        
        yaml_meta = task.metadata['yaml_metadata']
        
        # Add merge rules summary
        if analysis.merge_rules:
            yaml_meta['merge_rules_count'] = len(analysis.merge_rules)
            yaml_meta['tables_merged'] = [rule.table for rule in analysis.merge_rules]
        
        # Add filter criteria summary
        if analysis.filter_criteria:
            yaml_meta['filter_count'] = len(analysis.filter_criteria)
            yaml_meta['filter_types'] = list(set(
                c.criteria_type for c in analysis.filter_criteria
            ))
        
        # Add mapping rules summary
        if analysis.mapping_rules:
            yaml_meta['mapping_count'] = len(analysis.mapping_rules)
            yaml_meta['mapping_actions'] = list(set(
                rule.action for rule in analysis.mapping_rules
            ))
    
    def _validate_graph(self) -> List[str]:
        """Validate graph structure and return errors."""
        errors = []
        
        # Check for isolated tasks
        isolated = []
        for task_id in self.graph.tasks:
            upstream = self.graph.get_upstream_tasks(task_id)
            downstream = self.graph.get_downstream_tasks(task_id)
            if not upstream and not downstream:
                isolated.append(task_id)
        
        if isolated:
            errors.append(f"Isolated tasks found: {', '.join(isolated)}")
        
        # Check for cycles
        if self._has_cycle():
            errors.append("Circular dependencies detected in flow")
        
        return errors
    
    def _has_cycle(self) -> bool:
        """Detect cycles in graph using DFS."""
        visited = set()
        rec_stack = set()
        
        def dfs(task_id: str) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)
            
            # Check all downstream tasks
            for downstream_id in self.graph.get_downstream_tasks(task_id):
                if downstream_id not in visited:
                    if dfs(downstream_id):
                        return True
                elif downstream_id in rec_stack:
                    return True
            
            rec_stack.remove(task_id)
            return False
        
        # Check from all root tasks
        for task_id in self.graph.tasks:
            if task_id not in visited:
                if dfs(task_id):
                    return True
        
        return False


class DependencyResolver:
    """
    Resolve and analyze task dependencies.
    
    Provides utilities for analyzing dependency relationships,
    finding execution order, and detecting problematic patterns.
    """
    
    def __init__(self, graph: FlowGraph):
        """
        Initialize dependency resolver.
        
        Args:
            graph: FlowGraph to analyze
        """
        self.graph = graph
        self.logger = FlowVisualizerLogger.get_logger()
    
    def get_execution_order(self) -> List[List[str]]:
        """
        Get topological execution order (layers).
        
        Returns:
            List of layers, where each layer contains tasks that can execute in parallel
        """
        layers = []
        processed = set()
        
        while len(processed) < len(self.graph.tasks):
            # Find tasks with all dependencies satisfied
            current_layer = []
            for task_id in self.graph.tasks:
                if task_id in processed:
                    continue
                
                # Check if all upstream tasks are processed
                upstream = self.graph.get_upstream_tasks(task_id)
                upstream_ids = [u.task_id for u in upstream]
                if all(u_id in processed for u_id in upstream_ids):
                    current_layer.append(task_id)
            
            if not current_layer:
                # No progress possible - likely a cycle
                break
            
            layers.append(current_layer)
            processed.update(current_layer)
        
        return layers
    
    def find_critical_path(self) -> List[str]:
        """Find the longest path through the graph (critical path)."""
        # Use dynamic programming to find longest path
        memo = {}
        
        def longest_path_from(task_id: str) -> int:
            if task_id in memo:
                return memo[task_id]
            
            downstream = self.graph.get_downstream_tasks(task_id)
            if not downstream:
                memo[task_id] = 1
                return 1
            
            downstream_ids = [d.task_id for d in downstream]
            max_length = 1 + max(longest_path_from(d_id) for d_id in downstream_ids)
            memo[task_id] = max_length
            return max_length
        
        # Find task with longest path
        max_length = 0
        start_task = None
        root_tasks = self.graph.get_root_tasks()
        for task in root_tasks:
            length = longest_path_from(task.task_id)
            if length > max_length:
                max_length = length
                start_task = task.task_id
        
        if not start_task:
            return []
        
        # Reconstruct path
        path = [start_task]
        current = start_task
        while True:
            downstream = self.graph.get_downstream_tasks(current)
            if not downstream:
                break
            
            # Choose downstream task with longest remaining path
            downstream_ids = [d.task_id for d in downstream]
            next_task = max(downstream_ids, key=lambda t_id: memo.get(t_id, 0))
            path.append(next_task)
            current = next_task
        
        return path
    
    def get_dependency_depth(self, task_id: str) -> int:
        """Get maximum dependency depth for a task."""
        def depth_from(tid: str, visited: Set[str]) -> int:
            if tid in visited:
                return 0
            
            visited.add(tid)
            upstream = self.graph.get_upstream_tasks(tid)
            
            if not upstream:
                return 0
            
            upstream_ids = [u.task_id for u in upstream]
            return 1 + max(depth_from(u_id, visited.copy()) for u_id in upstream_ids)
        
        return depth_from(task_id, set())


class GraphValidator:
    """
    Validate graph structure and properties.
    
    Provides comprehensive validation for flow graphs including
    structural checks, reachability analysis, and completeness verification.
    """
    
    def __init__(self, graph: FlowGraph):
        """
        Initialize graph validator.
        
        Args:
            graph: FlowGraph to validate
        """
        self.graph = graph
        self.logger = FlowVisualizerLogger.get_logger()
    
    def validate(self) -> Tuple[bool, List[str], List[str]]:
        """
        Perform comprehensive graph validation.
        
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        errors = []
        warnings = []
        
        # Check 1: Non-empty graph
        if not self.graph.tasks:
            errors.append("Graph has no tasks")
            return False, errors, warnings
        
        # Check 2: All edges reference existing tasks
        edge_errors = self._validate_edges()
        errors.extend(edge_errors)
        
        # Check 3: Check for isolated tasks
        isolated = self._find_isolated_tasks()
        if isolated:
            warnings.append(f"Isolated tasks: {', '.join(isolated)}")
        
        # Check 4: Check for cycles
        if self._has_cycles():
            errors.append("Graph contains cycles")
        
        # Check 5: Check reachability from roots
        unreachable = self._find_unreachable_tasks()
        if unreachable:
            # Backward-compatible warning text for tests
            warnings.append(f"Unreachable tasks: {', '.join(unreachable)}")
            # Also inform about disconnected components explicitly
            components = self._find_disconnected_components()
            for comp in components:
                size = len(comp)
                head = comp[0] if comp else 'unknown'
                warnings.append(f"Disconnected component (size {size}) starting at {head}: {', '.join(comp)}")
        
        # Check 6: Validate task IDs
        invalid_ids = self._validate_task_ids()
        if invalid_ids:
            errors.extend(invalid_ids)
        
        is_valid = len(errors) == 0
        
        return is_valid, errors, warnings
    
    def _validate_edges(self) -> List[str]:
        """Validate that all edges reference existing tasks."""
        errors = []
        
        for edge in self.graph.edges:
            if edge.source_id not in self.graph.tasks:
                errors.append(f"Edge references non-existent source: {edge.source_id}")
            if edge.target_id not in self.graph.tasks:
                errors.append(f"Edge references non-existent target: {edge.target_id}")
        
        return errors
    
    def _find_isolated_tasks(self) -> List[str]:
        """Find tasks with no connections."""
        isolated = []
        
        for task_id in self.graph.tasks:
            upstream = self.graph.get_upstream_tasks(task_id)
            downstream = self.graph.get_downstream_tasks(task_id)
            if not upstream and not downstream:
                isolated.append(task_id)
        
        return isolated
    
    def _has_cycles(self) -> bool:
        """Check for cycles using DFS."""
        visited = set()
        rec_stack = set()
        
        def dfs(task_id: str) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)
            
            downstream_tasks = self.graph.get_downstream_tasks(task_id)
            for downstream in downstream_tasks:
                downstream_id = downstream.task_id
                if downstream_id not in visited:
                    if dfs(downstream_id):
                        return True
                elif downstream_id in rec_stack:
                    return True
            
            rec_stack.remove(task_id)
            return False
        
        for task_id in self.graph.tasks:
            if task_id not in visited:
                if dfs(task_id):
                    return True
        
        return False
    
    def _find_unreachable_tasks(self) -> List[str]:
        """
        Find tasks that are part of disconnected components.
        
        A valid flow can have:
        - Multiple roots that merge (e.g., main data + country lookup feeding mapping/merge)
        - Lookup resources feeding any downstream task (merge, mapping, etc.)
        
        We only warn when there are truly separate paths that never connect
        (i.e., multiple weakly-disconnected components).
        Returns a flat list of task IDs that belong to non-primary components
        for backward compatibility with existing warnings/tests.
        """
        if not self.graph.tasks:
            return []
        
        components = self._find_disconnected_components()
        if not components:
            return []
        # Flatten components to a single list of task IDs for legacy callers
        unreachable: List[str] = []
        for comp in components:
            unreachable.extend(comp)
        return unreachable

    def _find_disconnected_components(self) -> List[List[str]]:
        """Return list of disconnected components (excluding primary)."""
        if not self.graph.tasks:
            return []
        
        # Undirected adjacency for weak connectivity
        adjacency = {task_id: set() for task_id in self.graph.tasks}
        for edge in self.graph.edges:
            # Guard against invalid edges referencing missing tasks
            if edge.source_id in adjacency and edge.target_id in adjacency:
                adjacency[edge.source_id].add(edge.target_id)
                adjacency[edge.target_id].add(edge.source_id)
        
        visited: Set[str] = set()
        components: List[List[str]] = []
        
        def bfs(start_id: str) -> List[str]:
            comp: List[str] = []
            q = [start_id]
            visited.add(start_id)
            while q:
                cur = q.pop(0)
                comp.append(cur)
                for nb in adjacency[cur]:
                    if nb not in visited:
                        visited.add(nb)
                        q.append(nb)
            return comp
        
        for tid in self.graph.tasks:
            if tid not in visited:
                components.append(bfs(tid))
        
        if len(components) <= 1:
            return []
        
        # Primary component is the largest by node count
        primary = max(components, key=len)
        return [c for c in components if c is not primary]
    
    def _validate_task_ids(self) -> List[str]:
        """Validate task IDs are non-empty and unique."""
        errors = []
        
        seen_ids = set()
        for task_id in self.graph.tasks:
            if not task_id:
                errors.append("Empty task ID found")
            if task_id in seen_ids:
                errors.append(f"Duplicate task ID: {task_id}")
            seen_ids.add(task_id)
        
        return errors
