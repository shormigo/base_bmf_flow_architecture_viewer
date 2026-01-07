import os
from pathlib import Path

from click.testing import CliRunner

from src.cli import main
from src.models.task import Task, Edge, FlowGraph


def test_cli_generates_mmd(tmp_path: Path, monkeypatch):
    # Build a tiny flow directory structure and monkeypatch GraphBuilder
    obj_dir = tmp_path / "obj"
    (obj_dir / "flows").mkdir(parents=True)
    # a fake creation_flow.py just to satisfy locator logic if needed
    (obj_dir / "flows" / "creation_flow.py").write_text("# placeholder", encoding="utf-8")

    # Monkeypatch GraphBuilder.build to return a simple graph without reading files
    from src.graph import builder as builder_mod

    class DummyResult:
        def __init__(self, graph):
            self.graph = graph
            self.success = True
            self.errors = []
            self.warnings = []
            self.metadata = {"object_name": "dummy"}

    def fake_build(self):
        g = FlowGraph(object_name="dummy", object_path=str(obj_dir))
        a = Task(task_id="A", task_type="ReadExcel", task_name="Input")
        b = Task(task_id="B", task_type="Filter", task_name="Filtered")
        g.add_task(a); g.add_task(b)
        g.add_edge(Edge(source_id="A", target_id="B"))
        return DummyResult(g)

    monkeypatch.setattr(builder_mod.GraphBuilder, "build", fake_build)

    out_path = tmp_path / "out.mmd"
    runner = CliRunner()
    result = runner.invoke(main, [str(obj_dir), "--out", str(out_path), "--no-png", "--labels"]) 
    assert result.exit_code == 0
    # New naming: {object_name}_flow_architecture_{scheme}_{variant}_{timestamp}.mmd
    # Check for generated file with pattern
    generated_files = list(tmp_path.glob("dummy_flow_architecture_default_detailed_*.mmd"))
    assert len(generated_files) == 1, f"Expected 1 file, found {len(generated_files)}: {generated_files}"
    actual_file = generated_files[0]
    content = actual_file.read_text(encoding="utf-8")
    assert "graph" in content and "A -->|Read Excel| B" in content
