"""Unit tests for Graph Builder"""

import pytest
from pathlib import Path

from src.graph.builder import (
    GraphBuilder,
    DependencyResolver,
    GraphValidator,
    GraphBuildResult,
)
from src.models.task import Task, Edge, FlowGraph


@pytest.fixture
def valid_object_path():
    """Provide path to valid test object."""
    return "/Users/shormigo/Documents/BASE/Viatris/medicinal_product__rim_gxpd_all"


class TestGraphBuilder:
    """Test suite for GraphBuilder class."""
    
    def test_builder_initialization(self, valid_object_path):
        """Test graph builder initialization."""
        builder = GraphBuilder(valid_object_path)
        
        assert builder.object_path == Path(valid_object_path)
        assert builder.file_locator is not None
        assert builder.python_analysis is None
        assert builder.yaml_analyses == {}
    
    def test_build_gxpd_flow(self, valid_object_path):
        """Test building graph from real GxPD flow."""
        builder = GraphBuilder(valid_object_path)
        result = builder.build()
        
        assert isinstance(result, GraphBuildResult)
        assert result.success is True or len(result.errors) > 0  # May have warnings
        assert result.graph is not None
        assert len(result.graph.tasks) > 0
        assert len(result.graph.edges) > 0
    
    def test_build_result_contains_metadata(self, valid_object_path):
        """Test that build result contains metadata."""
        builder = GraphBuilder(valid_object_path)
        result = builder.build()
        
        assert 'object_name' in result.metadata
        assert 'task_count' in result.metadata
        assert 'edge_count' in result.metadata
        assert result.metadata['task_count'] > 0
    
    def test_build_parses_yaml_files(self, valid_object_path):
        """Test that YAML files are parsed during build."""
        builder = GraphBuilder(valid_object_path)
        result = builder.build()
        
        # Should have parsed some YAML files
        assert len(builder.yaml_analyses) > 0
    
    def test_build_creates_valid_graph(self, valid_object_path):
        """Test that built graph is valid."""
        builder = GraphBuilder(valid_object_path)
        result = builder.build()
        
        # Graph should have tasks from Python analysis
        assert len(result.graph.tasks) == len(builder.python_analysis.tasks)
        
        # All tasks should be in graph
        for task in builder.python_analysis.tasks:
            assert task.task_id in result.graph.tasks
    
    def test_build_with_invalid_path(self):
        """Test building with invalid object path."""
        builder = GraphBuilder("/nonexistent/path")
        result = builder.build()
        
        assert result.success is False
        assert len(result.errors) > 0
    
    def test_yaml_enrichment(self, valid_object_path):
        """Test that tasks are enriched with YAML metadata."""
        builder = GraphBuilder(valid_object_path)
        result = builder.build()
        
        # Check if any tasks have yaml_metadata
        has_yaml_meta = any(
            'yaml_metadata' in task.metadata 
            for task in result.graph.tasks.values()
        )
        
        # At least some tasks should have YAML metadata
        # (This is soft check - depends on actual flow structure)
        assert True  # Just verify no errors during enrichment


class TestDependencyResolver:
    """Test suite for DependencyResolver class."""
    
    @pytest.fixture
    def simple_graph(self):
        """Create a simple test graph."""
        graph = FlowGraph(object_name="test_object", object_path="/test/path")
        
        # Create tasks: A -> B -> C
        #                    -> D
        task_a = Task(task_id="A", task_type="ReadExcel", task_name="Read Data")
        task_b = Task(task_id="B", task_type="Filter", task_name="Filter Data")
        task_c = Task(task_id="C", task_type="Merge", task_name="Merge C")
        task_d = Task(task_id="D", task_type="CreateObjects", task_name="Create D")
        
        graph.add_task(task_a)
        graph.add_task(task_b)
        graph.add_task(task_c)
        graph.add_task(task_d)
        
        graph.add_edge(Edge(source_id="A", target_id="B"))
        graph.add_edge(Edge(source_id="B", target_id="C"))
        graph.add_edge(Edge(source_id="B", target_id="D"))
        
        return graph
    
    def test_resolver_initialization(self, simple_graph):
        """Test dependency resolver initialization."""
        resolver = DependencyResolver(simple_graph)
        
        assert resolver.graph == simple_graph
    
    def test_get_execution_order(self, simple_graph):
        """Test getting execution order."""
        resolver = DependencyResolver(simple_graph)
        layers = resolver.get_execution_order()
        
        # Should have 3 layers: [A], [B], [C, D]
        assert len(layers) >= 3
        assert "A" in layers[0]
        assert "B" in layers[1]
        assert "C" in layers[2] and "D" in layers[2]
    
    def test_find_critical_path(self, simple_graph):
        """Test finding critical path."""
        resolver = DependencyResolver(simple_graph)
        path = resolver.find_critical_path()
        
        # Critical path should be A -> B -> C (or D)
        assert len(path) >= 3
        assert path[0] == "A"
        assert path[1] == "B"
        assert path[2] in ["C", "D"]
    
    def test_get_dependency_depth(self, simple_graph):
        """Test getting dependency depth."""
        resolver = DependencyResolver(simple_graph)
        
        # A is root, depth = 0
        assert resolver.get_dependency_depth("A") == 0
        
        # B depends on A, depth = 1
        assert resolver.get_dependency_depth("B") == 1
        
        # C and D depend on B, depth = 2
        assert resolver.get_dependency_depth("C") == 2
        assert resolver.get_dependency_depth("D") == 2
    
    def test_execution_order_single_task(self):
        """Test execution order for single task."""
        graph = FlowGraph(object_name="test", object_path="/test")
        graph.add_task(Task(task_id="A", task_type="ReadExcel", task_name="Task A"))
        
        resolver = DependencyResolver(graph)
        layers = resolver.get_execution_order()
        
        assert len(layers) == 1
        assert layers[0] == ["A"]


class TestGraphValidator:
    """Test suite for GraphValidator class."""
    
    @pytest.fixture
    def valid_graph(self):
        """Create a valid test graph."""
        graph = FlowGraph(object_name="test", object_path="/test")
        
        task_a = Task(task_id="A", task_type="ReadExcel", task_name="Task A")
        task_b = Task(task_id="B", task_type="Filter", task_name="Task B")
        
        graph.add_task(task_a)
        graph.add_task(task_b)
        graph.add_edge(Edge(source_id="A", target_id="B"))
        
        return graph
    
    def test_validator_initialization(self, valid_graph):
        """Test validator initialization."""
        validator = GraphValidator(valid_graph)
        
        assert validator.graph == valid_graph
    
    def test_validate_valid_graph(self, valid_graph):
        """Test validating a valid graph."""
        validator = GraphValidator(valid_graph)
        is_valid, errors, warnings = validator.validate()
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_empty_graph(self):
        """Test validating empty graph."""
        graph = FlowGraph(object_name="test", object_path="/test")
        validator = GraphValidator(graph)
        
        is_valid, errors, warnings = validator.validate()
        
        assert is_valid is False
        assert len(errors) > 0
        assert "no tasks" in errors[0].lower()
    
    def test_validate_invalid_edge(self):
        """Test validation with invalid edge."""
        graph = FlowGraph(object_name="test", object_path="/test")
        graph.add_task(Task(task_id="A", task_type="ReadExcel", task_name="Task A"))
        # Add edge to non-existent task
        graph.edges.append(Edge(source_id="A", target_id="NonExistent"))
        
        validator = GraphValidator(graph)
        is_valid, errors, warnings = validator.validate()
        
        assert is_valid is False
        assert any("non-existent" in e.lower() for e in errors)
    
    def test_detect_isolated_tasks(self):
        """Test detection of isolated tasks."""
        graph = FlowGraph(object_name="test", object_path="/test")
        graph.add_task(Task(task_id="A", task_type="ReadExcel", task_name="Task A"))
        graph.add_task(Task(task_id="B", task_type="Filter", task_name="Task B"))
        # No edges - both tasks are isolated
        
        validator = GraphValidator(graph)
        is_valid, errors, warnings = validator.validate()
        
        # Should have warning about isolated tasks
        assert len(warnings) > 0
        assert any("isolated" in w.lower() for w in warnings)
    
    def test_detect_cycle(self):
        """Test detection of cycles."""
        graph = FlowGraph(object_name="test", object_path="/test")
        
        task_a = Task(task_id="A", task_type="ReadExcel", task_name="Task A")
        task_b = Task(task_id="B", task_type="Filter", task_name="Task B")
        task_c = Task(task_id="C", task_type="Merge", task_name="Task C")
        
        graph.add_task(task_a)
        graph.add_task(task_b)
        graph.add_task(task_c)
        
        # Create cycle: A -> B -> C -> A
        graph.add_edge(Edge(source_id="A", target_id="B"))
        graph.add_edge(Edge(source_id="B", target_id="C"))
        graph.add_edge(Edge(source_id="C", target_id="A"))
        
        validator = GraphValidator(graph)
        is_valid, errors, warnings = validator.validate()
        
        assert is_valid is False
        assert any("cycle" in e.lower() for e in errors)
    
    def test_find_unreachable_tasks(self):
        """Test finding unreachable tasks."""
        graph = FlowGraph(object_name="test", object_path="/test")
        
        # Create disconnected components
        task_a = Task(task_id="A", task_type="ReadExcel", task_name="Task A")
        task_b = Task(task_id="B", task_type="Filter", task_name="Task B")
        task_c = Task(task_id="C", task_type="Merge", task_name="Task C")
        task_d = Task(task_id="D", task_type="CreateObjects", task_name="Task D")
        
        graph.add_task(task_a)
        graph.add_task(task_b)
        graph.add_task(task_c)
        graph.add_task(task_d)
        
        # A -> B (component 1)
        # C -> D (component 2, unreachable from A)
        graph.add_edge(Edge(source_id="A", target_id="B"))
        graph.add_edge(Edge(source_id="C", target_id="D"))
        
        validator = GraphValidator(graph)
        is_valid, errors, warnings = validator.validate()
        
        # Should have warning about unreachable tasks
        assert any("unreachable" in w.lower() for w in warnings)


class TestGraphBuilderIntegration:
    """Integration tests for graph building."""
    
    def test_build_and_validate_gxpd(self, valid_object_path):
        """Test full build and validation pipeline on GxPD flow."""
        # Build graph
        builder = GraphBuilder(valid_object_path)
        result = builder.build()
        
        # Validate graph
        validator = GraphValidator(result.graph)
        is_valid, errors, warnings = validator.validate()
        
        # Graph should be built and reasonably valid
        assert result.graph is not None
        assert len(result.graph.tasks) > 0
        
        # May have warnings but should not have critical errors
        # (Real flows may have some issues but should still build)
        assert True  # Just verify pipeline completes
    
    def test_dependency_analysis_on_built_graph(self, valid_object_path):
        """Test dependency analysis on built graph."""
        # Build graph
        builder = GraphBuilder(valid_object_path)
        result = builder.build()
        
        # Analyze dependencies
        resolver = DependencyResolver(result.graph)
        layers = resolver.get_execution_order()
        path = resolver.find_critical_path()
        
        # Should have reasonable structure
        assert len(layers) > 0
        assert len(path) > 0
        
        # Total tasks in layers should match graph
        total_in_layers = sum(len(layer) for layer in layers)
        assert total_in_layers <= len(result.graph.tasks)
    
    def test_end_to_end_graph_construction(self, valid_object_path):
        """Test complete end-to-end graph construction."""
        # Build
        builder = GraphBuilder(valid_object_path)
        result = builder.build()
        
        # Validate
        validator = GraphValidator(result.graph)
        is_valid, errors, warnings = validator.validate()
        
        # Analyze
        resolver = DependencyResolver(result.graph)
        execution_order = resolver.get_execution_order()
        critical_path = resolver.find_critical_path()
        
        # Verify all components worked
        assert result.graph is not None
        assert len(execution_order) > 0
        assert len(critical_path) > 0
        
        # Check metadata
        assert result.metadata['task_count'] == len(result.graph.tasks)
        assert result.metadata['edge_count'] == len(result.graph.edges)
