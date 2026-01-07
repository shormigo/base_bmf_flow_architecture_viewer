"""Unit tests for AST Python parser"""

import pytest
from pathlib import Path
from src.parsers.python_parser import ASTPythonParser


class TestASTPythonParser:
    """Tests for ASTPythonParser class."""
    
    def test_parser_initialization_valid_file(self, valid_object_path):
        """Test parser initialization with valid file."""
        flow_path = Path(valid_object_path) / "flows" / "creation_flow.py"
        parser = ASTPythonParser(str(flow_path))
        
        assert parser.flow_py_path == flow_path
        assert len(parser.source_code) > 0
    
    def test_parser_initialization_missing_file(self):
        """Test parser initialization with missing file."""
        with pytest.raises(FileNotFoundError):
            ASTPythonParser("/nonexistent/file.py")
    
    def test_parser_initialization_not_python_file(self, tmp_path):
        """Test parser initialization with non-Python file."""
        txt_file = tmp_path / "file.txt"
        txt_file.write_text("test")
        
        with pytest.raises(ValueError):
            ASTPythonParser(str(txt_file))
    
    def test_parse_gxpd_flow(self, valid_object_path):
        """Test parsing actual GxPD creation_flow.py."""
        flow_path = Path(valid_object_path) / "flows" / "creation_flow.py"
        parser = ASTPythonParser(str(flow_path))
        
        analysis = parser.parse()
        
        # Should have found tasks
        assert len(analysis.tasks) > 0, "Should extract multiple tasks from GxPD flow"
        
        # Should have no errors
        assert len(analysis.errors) == 0, f"Parsing errors: {analysis.errors}"
        
        # Check for expected tasks
        task_types = {task.task_type for task in analysis.tasks}
        expected_types = {"ReadExcel", "Filter", "MergeTables", "Explode", "AggregateV2"}
        assert expected_types.issubset(task_types), f"Missing task types. Found: {task_types}"
    
    def test_parse_extracts_task_count(self, valid_object_path):
        """Test that parsing extracts reasonable number of tasks."""
        flow_path = Path(valid_object_path) / "flows" / "creation_flow.py"
        parser = ASTPythonParser(str(flow_path))
        
        analysis = parser.parse()
        
        # GxPD flow should have 20+ tasks (based on the structure we saw)
        assert len(analysis.tasks) >= 15, f"Expected 15+ tasks, got {len(analysis.tasks)}"
    
    def test_parse_extracts_dependencies(self, valid_object_path):
        """Test that parsing extracts task dependencies."""
        flow_path = Path(valid_object_path) / "flows" / "creation_flow.py"
        parser = ASTPythonParser(str(flow_path))
        
        analysis = parser.parse()
        
        # Should have dependencies between tasks
        assert len(analysis.edges) > 0, "Should extract dependencies"
        
        # Each edge should connect valid tasks
        task_ids = {task.task_id for task in analysis.tasks}
        for edge in analysis.edges:
            assert edge.source_id in task_ids, f"Source task not found: {edge.source_id}"
            assert edge.target_id in task_ids, f"Target task not found: {edge.target_id}"
    
    def test_parse_extracts_parameters(self, valid_object_path):
        """Test that task parameters are extracted."""
        flow_path = Path(valid_object_path) / "flows" / "creation_flow.py"
        parser = ASTPythonParser(str(flow_path))
        
        analysis = parser.parse()
        
        # At least some tasks should have parameters
        tasks_with_params = [t for t in analysis.tasks if t.parameters]
        assert len(tasks_with_params) > 0, "Should extract task parameters"
        
        # Check for expected parameter keys
        all_params = set()
        for task in tasks_with_params:
            all_params.update(task.parameters.keys())
        
        expected_params = {"input_table", "output_table", "task_args"}
        found_params = expected_params.intersection(all_params)
        assert len(found_params) > 0, f"Expected parameters not found. Found: {all_params}"
    
    def test_parse_sets_metadata(self, valid_object_path):
        """Test that task metadata is set."""
        flow_path = Path(valid_object_path) / "flows" / "creation_flow.py"
        parser = ASTPythonParser(str(flow_path))
        
        analysis = parser.parse()
        
        # At least some tasks should have metadata
        tasks_with_metadata = [t for t in analysis.tasks if t.metadata]
        assert len(tasks_with_metadata) > 0, "Should set task metadata"
        
        # Check for color metadata
        colored_tasks = [t for t in tasks_with_metadata if "color" in t.metadata]
        assert len(colored_tasks) > 0, "Should set color in metadata"
    
    def test_parse_identifies_task_types(self, valid_object_path):
        """Test that task types are correctly identified."""
        flow_path = Path(valid_object_path) / "flows" / "creation_flow.py"
        parser = ASTPythonParser(str(flow_path))
        
        analysis = parser.parse()
        
        # Group tasks by type
        task_types = {}
        for task in analysis.tasks:
            if task.task_type not in task_types:
                task_types[task.task_type] = []
            task_types[task.task_type].append(task)
        
        # Should have multiple task types
        assert len(task_types) >= 3, f"Should have 3+ task types, got {len(task_types)}"
        
        # ReadExcel should be present
        assert "ReadExcel" in task_types, "Should find ReadExcel tasks"
    
    def test_parse_preserves_task_names(self, valid_object_path):
        """Test that task names are preserved."""
        flow_path = Path(valid_object_path) / "flows" / "creation_flow.py"
        parser = ASTPythonParser(str(flow_path))
        
        analysis = parser.parse()
        
        # All tasks should have non-empty names
        for task in analysis.tasks:
            assert task.task_name, f"Task {task.task_id} has empty name"
            assert len(task.task_name) > 0, f"Task {task.task_id} has empty name"
    
    def test_parse_graph_is_valid(self, valid_object_path):
        """Test that parsed graph structure is valid."""
        flow_path = Path(valid_object_path) / "flows" / "creation_flow.py"
        parser = ASTPythonParser(str(flow_path))
        
        analysis = parser.parse()
        
        # All dependencies should reference existing tasks
        task_ids = {task.task_id for task in analysis.tasks}
        
        for edge in analysis.edges:
            assert edge.source_id in task_ids, \
                f"Edge references non-existent source: {edge.source_id}"
            assert edge.target_id in task_ids, \
                f"Edge references non-existent target: {edge.target_id}"
    
    def test_parse_handles_error_gracefully(self, tmp_path):
        """Test that parser handles malformed Python gracefully."""
        # Create a file with syntax error
        bad_py = tmp_path / "bad_flow.py"
        bad_py.write_text("this is not valid python syntax {{}")
        
        parser = ASTPythonParser(str(bad_py))
        analysis = parser.parse()
        
        # Should have errors, not exceptions
        assert len(analysis.errors) > 0, "Should report parsing errors"
        assert len(analysis.tasks) == 0, "Should not extract tasks from bad syntax"


class TestASTParserIntegration:
    """Integration tests with actual flow structures."""
    
    def test_parse_matches_flow_structure(self, valid_object_path):
        """Test that parsed structure matches actual flow structure."""
        flow_path = Path(valid_object_path) / "flows" / "creation_flow.py"
        parser = ASTPythonParser(str(flow_path))
        
        analysis = parser.parse()
        
        # Should have both input and output tasks
        task_types = {task.task_type for task in analysis.tasks}
        
        # Most flows should have ReadExcel (input) and CreateObjects (output)
        assert "ReadExcel" in task_types, "Flow should have input tasks"
        assert "CreateObjects" in task_types or "GenerateReport" in task_types, \
            "Flow should have output tasks"
    
    def test_parse_handles_multiple_scenarios(self, valid_object_path):
        """Test parsing flows with multiple scenarios."""
        flow_path = Path(valid_object_path) / "flows" / "creation_flow.py"
        parser = ASTPythonParser(str(flow_path))
        
        analysis = parser.parse()
        
        # Count Filter tasks (often used for scenarios)
        filter_tasks = [t for t in analysis.tasks if t.task_type == "Filter"]
        
        # GxPD has multiple scenario filters
        assert len(filter_tasks) >= 2, "Should extract multiple filter tasks"
    
    def test_parse_object_name_extraction(self, valid_object_path):
        """Test that object name is correctly extracted."""
        flow_path = Path(valid_object_path) / "flows" / "creation_flow.py"
        parser = ASTPythonParser(str(flow_path))
        
        analysis = parser.parse()
        
        # Object name should be the parent directory name
        expected_name = Path(valid_object_path).name
        assert analysis.object_name == expected_name, \
            f"Expected object name {expected_name}, got {analysis.object_name}"
