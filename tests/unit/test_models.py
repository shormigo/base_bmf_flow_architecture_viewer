"""Unit tests for data models"""

import pytest
from src.models.task import Task, Edge, FlowGraph


class TestTask:
    """Tests for Task class."""
    
    def test_task_creation(self):
        """Test creating a task."""
        task = Task(
            task_id="read_excel_1",
            task_type="ReadExcel",
            task_name="Read Main Table"
        )
        
        assert task.task_id == "read_excel_1"
        assert task.task_type == "ReadExcel"
        assert task.task_name == "Read Main Table"
    
    def test_task_parameters(self):
        """Test adding parameters to task."""
        task = Task(
            task_id="filter_1",
            task_type="Filter",
            task_name="Filter Data"
        )
        
        task.add_parameter("input_table", "data")
        task.add_parameter("output_table", "filtered_data")
        
        assert task.parameters["input_table"] == "data"
        assert task.parameters["output_table"] == "filtered_data"
    
    def test_task_metadata(self):
        """Test adding metadata to task."""
        task = Task(
            task_id="task_1",
            task_type="ReadExcel",
            task_name="Task 1"
        )
        
        task.set_metadata("color", "#E3F2FD")
        task.set_metadata("line_number", 10)
        
        assert task.metadata["color"] == "#E3F2FD"
        assert task.metadata["line_number"] == 10
    
    def test_task_equality(self):
        """Test task equality based on ID."""
        task1 = Task(task_id="task_1", task_type="Filter", task_name="T1")
        task2 = Task(task_id="task_1", task_type="Filter", task_name="T1")
        task3 = Task(task_id="task_2", task_type="Filter", task_name="T2")
        
        assert task1 == task2
        assert task1 != task3
    
    def test_task_hash(self):
        """Test task can be used in sets/dicts."""
        task1 = Task(task_id="task_1", task_type="Filter", task_name="T1")
        task2 = Task(task_id="task_2", task_type="Filter", task_name="T2")
        
        task_set = {task1, task2}
        assert len(task_set) == 2
        assert task1 in task_set


class TestEdge:
    """Tests for Edge class."""
    
    def test_edge_creation(self):
        """Test creating an edge."""
        edge = Edge(
            source_id="task_1",
            target_id="task_2",
            label="dependency"
        )
        
        assert edge.source_id == "task_1"
        assert edge.target_id == "task_2"
        assert edge.label == "dependency"
    
    def test_edge_equality(self):
        """Test edge equality."""
        edge1 = Edge(source_id="task_1", target_id="task_2")
        edge2 = Edge(source_id="task_1", target_id="task_2")
        edge3 = Edge(source_id="task_2", target_id="task_3")
        
        assert edge1 == edge2
        assert edge1 != edge3
    
    def test_edge_metadata(self):
        """Test edge metadata."""
        edge = Edge(
            source_id="merge_1",
            target_id="filter_1",
            edge_type="merge"
        )
        
        edge.metadata["merge_keys"] = ["auth_number"]
        
        assert edge.metadata["merge_keys"] == ["auth_number"]


class TestFlowGraph:
    """Tests for FlowGraph class."""
    
    def test_graph_creation(self):
        """Test creating a flow graph."""
        graph = FlowGraph(
            object_name="medicinal_product",
            object_path="/path/to/object"
        )
        
        assert graph.object_name == "medicinal_product"
        assert len(graph.tasks) == 0
        assert len(graph.edges) == 0
    
    def test_add_task(self):
        """Test adding tasks to graph."""
        graph = FlowGraph("test_obj", "/path")
        
        task1 = Task(task_id="t1", task_type="ReadExcel", task_name="T1")
        task2 = Task(task_id="t2", task_type="Filter", task_name="T2")
        
        graph.add_task(task1)
        graph.add_task(task2)
        
        assert len(graph.tasks) == 2
        assert graph.get_task("t1") == task1
        assert graph.get_task("t2") == task2
    
    def test_add_duplicate_task(self):
        """Test that duplicate tasks are rejected."""
        graph = FlowGraph("test_obj", "/path")
        task = Task(task_id="t1", task_type="ReadExcel", task_name="T1")
        
        graph.add_task(task)
        
        with pytest.raises(ValueError):
            graph.add_task(task)
    
    def test_add_edge(self):
        """Test adding edges to graph."""
        graph = FlowGraph("test_obj", "/path")
        
        task1 = Task(task_id="t1", task_type="ReadExcel", task_name="T1")
        task2 = Task(task_id="t2", task_type="Filter", task_name="T2")
        
        graph.add_task(task1)
        graph.add_task(task2)
        
        edge = Edge(source_id="t1", target_id="t2")
        graph.add_edge(edge)
        
        assert len(graph.edges) == 1
    
    def test_add_edge_nonexistent_task(self):
        """Test that edges require both tasks to exist."""
        graph = FlowGraph("test_obj", "/path")
        
        task1 = Task(task_id="t1", task_type="ReadExcel", task_name="T1")
        graph.add_task(task1)
        
        # Try to create edge to non-existent task
        edge = Edge(source_id="t1", target_id="nonexistent")
        
        with pytest.raises(ValueError):
            graph.add_edge(edge)
    
    def test_get_upstream_tasks(self):
        """Test getting upstream tasks."""
        graph = FlowGraph("test_obj", "/path")
        
        tasks = [
            Task(task_id=f"t{i}", task_type="Filter", task_name=f"T{i}")
            for i in range(3)
        ]
        
        for task in tasks:
            graph.add_task(task)
        
        graph.add_edge(Edge(source_id="t0", target_id="t2"))
        graph.add_edge(Edge(source_id="t1", target_id="t2"))
        
        upstream = graph.get_upstream_tasks("t2")
        
        assert len(upstream) == 2
        assert tasks[0] in upstream
        assert tasks[1] in upstream
    
    def test_get_downstream_tasks(self):
        """Test getting downstream tasks."""
        graph = FlowGraph("test_obj", "/path")
        
        tasks = [
            Task(task_id=f"t{i}", task_type="Filter", task_name=f"T{i}")
            for i in range(3)
        ]
        
        for task in tasks:
            graph.add_task(task)
        
        graph.add_edge(Edge(source_id="t0", target_id="t1"))
        graph.add_edge(Edge(source_id="t0", target_id="t2"))
        
        downstream = graph.get_downstream_tasks("t0")
        
        assert len(downstream) == 2
        assert tasks[1] in downstream
        assert tasks[2] in downstream
    
    def test_get_root_tasks(self):
        """Test getting root tasks."""
        graph = FlowGraph("test_obj", "/path")
        
        tasks = [
            Task(task_id=f"t{i}", task_type="Filter", task_name=f"T{i}")
            for i in range(3)
        ]
        
        for task in tasks:
            graph.add_task(task)
        
        graph.add_edge(Edge(source_id="t0", target_id="t1"))
        graph.add_edge(Edge(source_id="t1", target_id="t2"))
        
        roots = graph.get_root_tasks()
        
        assert len(roots) == 1
        assert tasks[0] in roots
    
    def test_get_leaf_tasks(self):
        """Test getting leaf tasks."""
        graph = FlowGraph("test_obj", "/path")
        
        tasks = [
            Task(task_id=f"t{i}", task_type="Filter", task_name=f"T{i}")
            for i in range(3)
        ]
        
        for task in tasks:
            graph.add_task(task)
        
        graph.add_edge(Edge(source_id="t0", target_id="t1"))
        graph.add_edge(Edge(source_id="t1", target_id="t2"))
        
        leaves = graph.get_leaf_tasks()
        
        assert len(leaves) == 1
        assert tasks[2] in leaves
    
    def test_validate_graph(self):
        """Test graph validation."""
        graph = FlowGraph("test_obj", "/path")
        
        tasks = [
            Task(task_id=f"t{i}", task_type="Filter", task_name=f"T{i}")
            for i in range(3)
        ]
        
        for task in tasks:
            graph.add_task(task)
        
        graph.add_edge(Edge(source_id="t0", target_id="t1"))
        
        # Valid graph
        errors = graph.validate()
        assert len([e for e in errors if "non-existent" in e]) == 0
    
    def test_validate_isolated_task(self):
        """Test validation warns about isolated tasks."""
        graph = FlowGraph("test_obj", "/path")
        
        task1 = Task(task_id="t1", task_type="Filter", task_name="T1")
        task2 = Task(task_id="t2", task_type="Filter", task_name="T2")
        
        graph.add_task(task1)
        graph.add_task(task2)
        
        graph.add_edge(Edge(source_id="t1", target_id="t2"))
        
        # Add isolated task
        task3 = Task(task_id="t3", task_type="Filter", task_name="T3")
        graph.add_task(task3)
        
        errors = graph.validate()
        
        # Should have warning about isolated task
        assert any("Isolated" in e for e in errors)
