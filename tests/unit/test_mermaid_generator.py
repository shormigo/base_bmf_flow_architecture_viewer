import re

from src.models.task import Task, Edge, FlowGraph
from src.rendering import MermaidGenerator


def build_sample_graph():
    g = FlowGraph(object_name="test", object_path="/test")
    a = Task(task_id="A", task_type="ReadExcel", task_name="Virtify Main Table")
    b = Task(task_id="B", task_type="Filter", task_name="Filtered Virtify")
    c = Task(task_id="C", task_type="MergeTables", task_name="Merged Output")
    g.add_task(a)
    g.add_task(b)
    g.add_task(c)
    g.add_edge(Edge(source_id="A", target_id="B"))
    g.add_edge(Edge(source_id="B", target_id="C"))
    return g


class TestMermaidGenerator:
    def test_generate_basic_mermaid(self):
        g = build_sample_graph()
        gen = MermaidGenerator()
        code = gen.generate(g, title="Sample")

        assert code.startswith("graph TD")
        # Nodes
        # Node labels include icon + name (task type moved to edges)
        assert 'A["' in code or 'A((("' in code
        # styling classDefs present
        assert 'classDef' in code
        # Edges now have labels (task type from source)
        assert ("A -->|" in code or "A --> B" in code)  # Edge with label or without
        assert ("B -->|" in code or "B --> C" in code)

    def test_multi_root_merge(self):
        g = FlowGraph(object_name="test", object_path="/test")
        v = Task(task_id="VIRTIFY", task_type="ReadExcel", task_name="Virtify")
        c = Task(task_id="COUNTRY", task_type="ReadExcel", task_name="Country Mapping")
        m = Task(task_id="MERGE", task_type="Merge", task_name="Merge")
        g.add_task(v); g.add_task(c); g.add_task(m)
        g.add_edge(Edge(source_id="VIRTIFY", target_id="MERGE"))
        g.add_edge(Edge(source_id="COUNTRY", target_id="MERGE"))

        gen = MermaidGenerator()
        code = gen.generate(g, label_edges=True)
        # Labeled edges
        assert 'VIRTIFY -->|Read Excel| MERGE' in code
        assert 'COUNTRY -->|Read Excel| MERGE' in code
