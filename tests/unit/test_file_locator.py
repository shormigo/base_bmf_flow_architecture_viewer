"""Unit tests for file discovery module"""

import pytest
from pathlib import Path
from src.discovery.file_locator import FileLocator, ObjectValidator


class TestFileLocator:
    """Tests for FileLocator class."""
    
    def test_initialization_valid_path(self, valid_object_path):
        """Test FileLocator initialization with valid path."""
        locator = FileLocator(valid_object_path)
        assert locator.object_path == Path(valid_object_path)
    
    def test_initialization_invalid_path(self):
        """Test FileLocator initialization with non-existent path."""
        with pytest.raises(FileNotFoundError):
            FileLocator("/non/existent/path")
    
    def test_locate_creation_flow(self, valid_object_path):
        """Test locating creation_flow.py file."""
        locator = FileLocator(valid_object_path)
        flow_path = locator.locate_creation_flow()
        
        assert flow_path.exists()
        assert flow_path.name == "creation_flow.py"
        assert flow_path.parent.name == "flows"
    
    def test_locate_creation_flow_missing(self, tmp_path):
        """Test locating creation_flow.py when it doesn't exist."""
        # Create a minimal valid object structure without creation_flow.py
        obj_path = tmp_path / "test_object"
        obj_path.mkdir()
        (obj_path / "flows").mkdir()
        (obj_path / "filter").mkdir()
        (obj_path / "mapping").mkdir()
        (obj_path / "merging_rules").mkdir()
        
        locator = FileLocator(str(obj_path))
        with pytest.raises(FileNotFoundError):
            locator.locate_creation_flow()
    
    def test_get_object_name(self, valid_object_path):
        """Test getting object name from path."""
        locator = FileLocator(valid_object_path)
        name = locator.get_object_name()
        
        assert name == "medicinal_product__rim_gxpd_all"
    
    def test_find_all_yaml_files(self, valid_object_path):
        """Test finding all YAML files."""
        locator = FileLocator(valid_object_path)
        yaml_files = locator.find_all_yaml_files()
        
        assert "filter" in yaml_files
        assert "mapping" in yaml_files
        assert "merging_rules" in yaml_files
        
        # Should have files in each category
        assert len(yaml_files["filter"]) > 0
        assert len(yaml_files["mapping"]) > 0
        assert len(yaml_files["merging_rules"]) > 0
    
    def test_locate_yaml_file(self, valid_object_path):
        """Test locating a specific YAML file."""
        locator = FileLocator(valid_object_path)
        
        # Test with relative path
        yaml_path = locator.locate_yaml_file("filter/filtered_gxpd_export.yml")
        assert yaml_path is not None
        assert yaml_path.exists()
    
    def test_get_structure_summary(self, valid_object_path):
        """Test getting structure summary."""
        locator = FileLocator(valid_object_path)
        summary = locator.get_structure_summary()
        
        assert summary["object_name"] == "medicinal_product__rim_gxpd_all"
        assert summary["creation_flow_exists"] is True
        assert summary["yaml_files_count"] > 0
        assert summary["python_files_count"] >= 2  # creation_flow.py and deletion_flow.py


class TestObjectValidator:
    """Tests for ObjectValidator class."""
    
    def test_validate_valid_object(self, valid_object_path):
        """Test validating a valid object structure."""
        validator = ObjectValidator(valid_object_path)
        results = validator.validate()
        
        assert results["valid"] is True
        assert len(results["errors"]) == 0
    
    def test_validate_missing_directory(self, tmp_path):
        """Test validation with missing required directory."""
        # Create partial object structure
        obj_path = tmp_path / "test_object"
        obj_path.mkdir()
        (obj_path / "flows").mkdir()
        
        validator = ObjectValidator(str(obj_path))
        results = validator.validate()
        
        assert results["valid"] is False
        assert len(results["errors"]) > 0
    
    def test_validate_warnings(self, tmp_path):
        """Test validation warnings for missing YAML files."""
        # Create minimal valid structure
        obj_path = tmp_path / "test_object"
        obj_path.mkdir()
        
        for dir_name in ["flows", "filter", "mapping", "merging_rules"]:
            (obj_path / dir_name).mkdir()
        
        # Create a minimal creation_flow.py
        (obj_path / "flows" / "creation_flow.py").write_text(
            "# Minimal flow\npass"
        )
        
        validator = ObjectValidator(str(obj_path))
        results = validator.validate()
        
        assert results["valid"] is True
        assert len(results["warnings"]) > 0
        assert any("YAML" in w for w in results["warnings"])
