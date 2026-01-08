from typing import List, Optional
import re

from src.models.task import Task, Edge, FlowGraph
from src.config.loader import ConfigLoader


class MermaidGenerator:
    """
    Generate Mermaid (flowchart) syntax from a FlowGraph.
    
    Usage:
        gen = MermaidGenerator()
        code = gen.generate(graph, title="My Flow")
    """

    def __init__(self, direction: Optional[str] = None, color_scheme: str = "default", hide_utility_tasks: bool = False):
        # Direction: TD (top-down), LR (left-right), BT (bottom-top)
        self.config = ConfigLoader.get_instance()
        default_dir = self.config.get_default_styling().get("diagram_direction", "TD")
        self.direction = direction or default_dir
        self.color_scheme = color_scheme
        self.hide_utility_tasks = hide_utility_tasks

    def generate(self, graph: FlowGraph, title: Optional[str] = None, label_edges: bool = False, show_params: bool = True, png_safe: bool = False) -> str:
        lines: List[str] = []
        lines.append(f"graph {self.direction}")

        if title:
            # Mermaid ignores comments; add readable header
            lines.append(f"%% {title}")

        # Filter utility tasks if requested
        visible_tasks = self._get_visible_tasks(graph)
        
        # Nodes
        for task_id in visible_tasks:
            task = graph.tasks[task_id]
            lines.append(self._render_node(task, show_params, png_safe))

        # Edges (with utility task bypass)
        edges_to_render = self._get_visible_edges(graph, visible_tasks)
        for edge in edges_to_render:
            lines.append(self._render_edge(edge, graph, use_task_type_labels=label_edges))

        # Styling via classDef/class based on task categories/colors
        # Keep styles for both .mmd and PNG so themes are consistent
        # Only style visible tasks
        class_defs, class_assignments = self._render_styles(graph, visible_tasks)
        lines.extend(class_defs)
        lines.extend(class_assignments)
        
        # Add arrow styling for dark mode
        if self.color_scheme == "dark":
            # Style all arrows (edges) to be white for dark mode
            lines.append("linkStyle default stroke:#FFFFFF,stroke-width:2px;")

        return "\n".join(lines) + "\n"

    def _render_node(self, task: Task, show_params: bool = True, png_safe: bool = False) -> str:
        # Build label with task name and optional details
        task_def = self.config.get_task_def(task.task_type) or {}
        icon = task_def.get("icon", "")
        name = task.get_display_label()

        # In detailed mode, add metadata details to node labels
        if show_params:
            details = self._get_task_details(task)
            if details:
                label = f"{icon} {name}<br/>{details}".strip() if icon else f"{name}<br/>{details}"
            else:
                label = f"{icon} {name}".strip() if icon else name
        else:
            # Overview mode: simple label
            label = f"{icon} {name}".strip() if icon else name

        if png_safe:
            # Sanitize for mmdc fallback: strip emojis/HTML and simplify
            clean = self._strip_emojis(label)
            clean = clean.replace("<br/>", " ").replace("\n", " ")
            clean = re.sub(r"\s+", " ", clean).strip()
            safe_label = clean.replace("\"", "'")
            shape = "rect"
        else:
            safe_label = label.replace("\"", "'").replace("\n", "<br/>")
            shape = self._shape_for_task(task)

        return self._node_shape_syntax(task.task_id, safe_label, shape, png_safe=png_safe)

    def _render_edge(self, edge: Edge, graph: Optional[FlowGraph], use_task_type_labels: bool = False) -> str:
        label = None
        if edge.label:
            label = edge.label
        elif graph is not None:
            # Derive label from source task type/metadata
            src = graph.tasks.get(edge.source_id)
            if src:
                if use_task_type_labels:
                    # Use display name of task type as edge label
                    task_def = self.config.get_task_def(src.task_type) or {}
                    label = task_def.get("display_name", src.task_type)
                else:
                    label = self._derive_edge_label(src)
        if label:
            return f"{edge.source_id} -->|{label}| {edge.target_id}"
        return f"{edge.source_id} --> {edge.target_id}"

    def _derive_edge_label(self, src: Task) -> str:
        t = src.task_type
        meta = src.metadata.get("yaml_metadata", {}) if src.metadata else {}
        
        # Enhanced labels with details from metadata
        if t in ("Filter",):
            kinds = meta.get("filter_types") or []
            if kinds:
                # Show filter types in detail
                return f"Filter {', '.join(sorted(kinds))}"
            return "Filter"
        
        if t in ("Merge", "MergeTables"):
            cnt = meta.get("merge_rules_count")
            tables = meta.get("tables_merged", [])
            if cnt and cnt > 0:
                # Show merge key count
                return f"MergeTables<br/>{cnt} rule{'s' if cnt > 1 else ''}"
            return "MergeTables"
        
        if t in ("Mapping",):
            cnt = meta.get("mapping_count")
            if cnt:
                return f"Mapping<br/>{cnt} rule{'s' if cnt > 1 else ''}"
            return "Mapping"
        
        if t in ("Aggregate", "AggregateV2"):
            # Could extract groupby columns from parameters
            return "Aggregate"
        
        # Default to display name
        task_def = self.config.get_task_def(t) or {}
        return task_def.get("display_name", t)

    def _render_styles(self, graph: FlowGraph, visible_tasks: Optional[List[str]] = None):
        # Collect categories used and their colors (only for visible tasks)
        tasks_to_style = visible_tasks if visible_tasks is not None else list(graph.tasks.keys())
        cats = {}
        for task_id in tasks_to_style:
            task = graph.tasks[task_id]
            cat = self.config.get_task_category(task.task_type)
            color = self.config.get_task_color(task.task_type, self.color_scheme)
            cats[cat] = color
        class_defs = []
        for cat, color in cats.items():
            class_defs.append(f"classDef {cat} fill:{color},stroke:#333,stroke-width:1px;")
        class_assignments = []
        for task_id in tasks_to_style:
            task = graph.tasks[task_id]
            cat = self.config.get_task_category(task.task_type)
            class_assignments.append(f"class {task.task_id} {cat};")
        return class_defs, class_assignments

    def _get_task_details(self, task: Task) -> str:
        """Extract detailed information about task operation for node labels."""
        t = task.task_type
        meta = task.metadata.get("yaml_metadata", {}) if task.metadata else {}
        params = task.parameters if task.parameters else {}
        
        details = []
        
        # Filter details
        if t in ("Filter",):
            filter_types = meta.get("filter_types", [])
            if filter_types:
                details.append(f"Filter: {', '.join(filter_types[:2])}")
        
        # Merge details
        elif t in ("Merge", "MergeTables"):
            cnt = meta.get("merge_rules_count")
            tables = meta.get("tables_merged", [])
            if cnt:
                details.append(f"{cnt} merge rule{'s' if cnt > 1 else ''}")
            if tables and len(tables) <= 2:
                details.append(f"Tables: {', '.join(tables)}")
        
        # Mapping details
        elif t in ("Mapping",):
            cnt = meta.get("mapping_count")
            if cnt:
                details.append(f"{cnt} mapping{'s' if cnt > 1 else ''}")
        
        # Aggregate details - extract from parameters
        elif t in ("Aggregate", "AggregateV2"):
            groupby = params.get("columns_to_groupby", [])
            if groupby and isinstance(groupby, list) and len(groupby) <= 3:
                details.append(f"Group by: {', '.join(groupby)}")
            elif groupby and isinstance(groupby, list):
                details.append(f"Group by {len(groupby)} cols")
        
        return "<br/>".join(details) if details else ""

    def _shape_for_task(self, task: Task) -> str:
        # Prefer config-defined shape; fallback to category mapping (handled in loader)
        return self.config.get_task_shape(task.task_type)

    def _node_shape_syntax(self, node_id: str, label: str, shape: str, png_safe: bool = False) -> str:
        # Map semantic shape to Mermaid syntax
        if png_safe:
            # Force simple rectangle for maximum compatibility with mmdc
            return f"{node_id}[\"{label}\"]"
        if shape == "circle":
            return f"{node_id}(((\"{label}\")))"
        if shape == "rounded":
            return f"{node_id}(\"{label}\")"
        if shape == "subroutine":
            return f"{node_id}([[\"{label}\"]])"
        if shape == "hexagon":
            return f"{node_id}({{\"{label}\"}})"
        # default rect
        return f"{node_id}[\"{label}\"]"

    def _get_visible_tasks(self, graph: FlowGraph) -> List[str]:
        """Filter out utility tasks if hide_utility_tasks is enabled."""
        if not self.hide_utility_tasks:
            return list(graph.tasks.keys())
        
        # Hide SetEnvironmentVariables and similar utility tasks
        utility_types = {"SetEnvironmentVariables", "SetEnv"}
        visible = []
        for task_id, task in graph.tasks.items():
            if task.task_type not in utility_types:
                visible.append(task_id)
        return visible
    
    def _get_visible_edges(self, graph: FlowGraph, visible_tasks: List[str]) -> List[Edge]:
        """Generate edges, bypassing hidden utility tasks."""
        if not self.hide_utility_tasks:
            return graph.edges
        
        visible_set = set(visible_tasks)
        new_edges = []
        
        for edge in graph.edges:
            src_visible = edge.source_id in visible_set
            tgt_visible = edge.target_id in visible_set
            
            if src_visible and tgt_visible:
                # Both visible, keep edge as-is
                new_edges.append(edge)
            elif not src_visible and tgt_visible:
                # Source hidden, find upstream visible tasks
                upstream = self._find_upstream_visible(graph, edge.source_id, visible_set)
                for up_id in upstream:
                    new_edges.append(Edge(source_id=up_id, target_id=edge.target_id, label=edge.label))
            elif src_visible and not tgt_visible:
                # Target hidden, find downstream visible tasks
                downstream = self._find_downstream_visible(graph, edge.target_id, visible_set)
                for down_id in downstream:
                    new_edges.append(Edge(source_id=edge.source_id, target_id=down_id, label=edge.label))
            # If both hidden, skip edge entirely
        
        # Remove duplicates
        unique_edges = []
        seen = set()
        for edge in new_edges:
            key = (edge.source_id, edge.target_id)
            if key not in seen:
                seen.add(key)
                unique_edges.append(edge)
        
        return unique_edges
    
    def _find_upstream_visible(self, graph: FlowGraph, task_id: str, visible_set: set) -> List[str]:
        """Find upstream visible tasks, traversing through hidden tasks."""
        upstream = []
        for edge in graph.edges:
            if edge.target_id == task_id:
                if edge.source_id in visible_set:
                    upstream.append(edge.source_id)
                else:
                    # Recurse through hidden task
                    upstream.extend(self._find_upstream_visible(graph, edge.source_id, visible_set))
        return upstream
    
    def _find_downstream_visible(self, graph: FlowGraph, task_id: str, visible_set: set) -> List[str]:
        """Find downstream visible tasks, traversing through hidden tasks."""
        downstream = []
        for edge in graph.edges:
            if edge.source_id == task_id:
                if edge.target_id in visible_set:
                    downstream.append(edge.target_id)
                else:
                    # Recurse through hidden task
                    downstream.extend(self._find_downstream_visible(graph, edge.target_id, visible_set))
        return downstream

    @staticmethod
    def _strip_emojis(text: str) -> str:
        # Remove most emoji codepoints
        return re.sub(r"[\U0001F300-\U0001FFFF]", "", text)
