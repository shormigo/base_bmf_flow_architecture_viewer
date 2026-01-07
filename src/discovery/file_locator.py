"""BMF Flow Visualizer - File Discovery and Validation"""

from pathlib import Path
from typing import Dict, Optional, List
import os


class FileLocator:
    """Locate and validate files in a BMF object structure."""
    
    REQUIRED_DIRS = ["flows", "filter", "mapping", "merging_rules"]
    OPTIONAL_DIRS = ["tmp", "deletion"]
    MAIN_FLOW_FILE = "creation_flow.py"
    
    def __init__(self, object_path: str):
        """
        Initialize file locator.
        
        Args:
            object_path: Path to BMF object directory
        """
        self.object_path = Path(object_path)
        self._validate_path()
    
    def _validate_path(self):
        """Validate that object path exists and is a directory."""
        if not self.object_path.exists():
            raise FileNotFoundError(f"Object path does not exist: {self.object_path}")
        
        if not self.object_path.is_dir():
            raise NotADirectoryError(f"Object path is not a directory: {self.object_path}")
    
    def locate_creation_flow(self) -> Path:
        """
        Locate creation_flow.py file.
        
        Returns:
            Path to creation_flow.py
            
        Raises:
            FileNotFoundError: If creation_flow.py not found
        """
        flow_path = self.object_path / "flows" / self.MAIN_FLOW_FILE
        
        if not flow_path.exists():
            raise FileNotFoundError(
                f"creation_flow.py not found in {self.object_path / 'flows'}"
            )
        
        return flow_path
    
    def locate_yaml_file(self, yaml_reference: str) -> Optional[Path]:
        """
        Locate a YAML file referenced in the Python code.
        
        Handles various reference patterns:
        - full_path("migrations/object_name/filter/something.yml")
        - migrations/{object_name}/filter/something.yml
        - relative paths
        - absolute paths
        
        Args:
            yaml_reference: Reference string from Python code
            
        Returns:
            Path to YAML file if found, None otherwise
        """
        if not yaml_reference:
            return None
        
        # Clean up the reference
        ref = yaml_reference.strip('"\'')
        
        # Handle full_path() calls
        if ref.startswith("full_path("):
            ref = ref.replace("full_path(", "").replace(")", "").strip('"\'')
        
        # Remove leading slashes for relative path handling
        ref = ref.lstrip("/")
        
        # Try to find the file in common locations
        potential_paths = [
            self.object_path / ref,
            self.object_path / "filter" / Path(ref).name,
            self.object_path / "mapping" / Path(ref).name,
            self.object_path / "merging_rules" / Path(ref).name,
        ]
        
        for path in potential_paths:
            if path.exists() and path.is_file():
                return path
        
        return None
    
    def find_all_yaml_files(self) -> Dict[str, List[Path]]:
        """
        Find all YAML files in the object.
        
        Returns:
            Dictionary with categories as keys and lists of paths as values
        """
        yaml_files = {
            "filter": [],
            "mapping": [],
            "merging_rules": [],
        }
        
        for category in yaml_files.keys():
            category_path = self.object_path / category
            if category_path.exists():
                yaml_files[category] = list(category_path.glob("*.yml"))
        
        return yaml_files
    
    def get_object_name(self) -> str:
        """
        Get the object name from directory name.
        
        Returns:
            Object name
        """
        return self.object_path.name
    
    def get_structure_summary(self) -> Dict[str, any]:
        """
        Get a summary of the object structure.
        
        Returns:
            Dictionary with structure information
        """
        summary = {
            "object_name": self.get_object_name(),
            "object_path": str(self.object_path),
            "creation_flow_exists": (self.object_path / "flows" / self.MAIN_FLOW_FILE).exists(),
            "directories": [],
            "yaml_files_count": 0,
            "python_files_count": 0,
        }
        
        # Count files in each directory
        for item in self.object_path.iterdir():
            if item.is_dir():
                summary["directories"].append(item.name)
                
                # Count YAML files
                yaml_count = len(list(item.glob("*.yml")))
                summary["yaml_files_count"] += yaml_count
                
                # Count Python files
                py_count = len(list(item.glob("*.py")))
                summary["python_files_count"] += py_count
        
        return summary


class ObjectValidator:
    """Validate BMF object structure."""
    
    def __init__(self, object_path: str):
        """Initialize validator."""
        self.object_path = Path(object_path)
        self.locator = FileLocator(object_path)
    
    def validate(self) -> Dict[str, any]:
        """
        Validate object structure.
        
        Returns:
            Dictionary with validation results
        """
        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "info": [],
        }
        
        # Check required directories
        for req_dir in FileLocator.REQUIRED_DIRS:
            dir_path = self.object_path / req_dir
            if not dir_path.exists():
                results["errors"].append(f"Required directory missing: {req_dir}")
                results["valid"] = False
            elif not dir_path.is_dir():
                results["errors"].append(f"Required path is not a directory: {req_dir}")
                results["valid"] = False
        
        # Check creation_flow.py exists
        try:
            creation_flow = self.locator.locate_creation_flow()
            results["info"].append(f"Found creation_flow.py: {creation_flow}")
        except FileNotFoundError as e:
            results["errors"].append(str(e))
            results["valid"] = False
        
        # Check for YAML files
        yaml_files = self.locator.find_all_yaml_files()
        total_yaml = sum(len(files) for files in yaml_files.values())
        
        if total_yaml == 0:
            results["warnings"].append("No YAML files found in expected directories")
        else:
            results["info"].append(f"Found {total_yaml} YAML files")
        
        return results
