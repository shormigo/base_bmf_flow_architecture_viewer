"""BMF Flow Visualizer - Logging Utilities"""

import logging
from typing import Optional


class FlowVisualizerLogger:
    """Centralized logging for the flow visualizer."""
    
    _logger: Optional[logging.Logger] = None
    
    @classmethod
    def get_logger(cls, name: str = "bmf_flow_visualizer") -> logging.Logger:
        """Get or create logger instance."""
        if cls._logger is None:
            cls._logger = logging.getLogger(name)
            
            # Configure if not already configured
            if not cls._logger.handlers:
                handler = logging.StreamHandler()
                formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                handler.setFormatter(formatter)
                cls._logger.addHandler(handler)
                cls._logger.setLevel(logging.INFO)
        
        return cls._logger
    
    @classmethod
    def debug(cls, message: str):
        """Log debug message."""
        cls.get_logger().debug(message)
    
    @classmethod
    def info(cls, message: str):
        """Log info message."""
        cls.get_logger().info(message)
    
    @classmethod
    def warning(cls, message: str):
        """Log warning message."""
        cls.get_logger().warning(message)
    
    @classmethod
    def error(cls, message: str):
        """Log error message."""
        cls.get_logger().error(message)
    
    @classmethod
    def set_level(cls, level: int):
        """Set logging level."""
        cls.get_logger().setLevel(level)
