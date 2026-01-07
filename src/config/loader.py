"""BMF Flow Visualizer - Configuration Loader"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigLoader:
    """Load and manage configuration files."""
    
    _instance = None
    _config_cache: Dict[str, Any] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Resolve config directory from project root
        # __file__ is src/config/loader.py
        # We want to go up 3 levels to project root, then into config/
        project_root = Path(__file__).parent.parent.parent
        self.config_dir = project_root / "config"
    
    @classmethod
    def get_instance(cls):
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def load_config(self, config_name: str) -> Dict[str, Any]:
        """
        Load configuration file.
        
        Args:
            config_name: Name of config file (without .yaml)
            
        Returns:
            Configuration dictionary
        """
        if config_name in self._config_cache:
            return self._config_cache[config_name]
        
        config_path = self.config_dir / f"{config_name}.yaml"
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        self._config_cache[config_name] = config
        return config
    
    def get_task_definitions(self) -> Dict[str, Any]:
        """Get task type definitions."""
        config = self.load_config("task_definitions")
        return config.get("task_definitions", {})
    
    def get_task_def(self, task_type: str) -> Optional[Dict[str, Any]]:
        """Get definition for specific task type."""
        definitions = self.get_task_definitions()
        return definitions.get(task_type)
    
    def get_color_schemes(self) -> Dict[str, Dict[str, str]]:
        """Get color schemes."""
        config = self.load_config("task_definitions")
        return config.get("color_schemes", {})
    
    def get_color_scheme(self, scheme: str = "default") -> Dict[str, str]:
        """Get specific color scheme."""
        schemes = self.get_color_schemes()
        return schemes.get(scheme, schemes.get("default", {}))
    
    def get_default_styling(self) -> Dict[str, Any]:
        """Get default styling options."""
        config = self.load_config("task_definitions")
        return config.get("default_styling", {})
    
    def get_task_category(self, task_type: str) -> str:
        """Get category for task type."""
        task_def = self.get_task_def(task_type)
        if task_def:
            return task_def.get("category", "unknown")
        return "unknown"
    
    def get_task_color(self, task_type: str, scheme: str = "default") -> str:
        """Get color for task type."""
        task_def = self.get_task_def(task_type)
        if task_def and "color" in task_def:
            return task_def["color"]
        
        # Fallback to category color
        category = self.get_task_category(task_type)
        color_scheme = self.get_color_scheme(scheme)
        return color_scheme.get(category, "#F5F5F5")

    def get_task_shape(self, task_type: str) -> str:
        """Get shape for task type, with sensible fallbacks."""
        task_def = self.get_task_def(task_type)
        if task_def and "shape" in task_def:
            return task_def["shape"]
        # Category-based defaults
        cat = self.get_task_category(task_type)
        cat_map = {
            "input": "circle",
            "output": "rounded",
            "processing": "rect",
            "utility": "rect",
        }
        return cat_map.get(cat, "rect")
