"""BMF Flow Visualizer - YAML Parser for Configuration Files"""

import ast
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field

import yaml

from src.utils.logger import FlowVisualizerLogger


# Custom YAML Loader that handles unknown tags
class CustomYAMLLoader(yaml.SafeLoader):
    """YAML loader that gracefully handles custom tags."""
    pass


def custom_tag_constructor(loader, tag_suffix, node):
    """Handle custom YAML tags like !env, !var, etc."""
    if isinstance(node, yaml.ScalarNode):
        return loader.construct_scalar(node)
    elif isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    elif isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node)
    return None


# Register multi-constructor for all unknown tags
CustomYAMLLoader.add_multi_constructor('', custom_tag_constructor)


@dataclass
class MergeRule:
    """Represents a merge operation in merging rules."""
    table: str
    left_on: Optional[List[str]] = None
    right_on: Optional[List[str]] = None
    merge_type: str = "left"  # left, right, inner, outer
    suffixes: Optional[Tuple[str, str]] = None
    columns: Optional[List[str]] = None
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'table': self.table,
            'left_on': self.left_on,
            'right_on': self.right_on,
            'merge_type': self.merge_type,
            'suffixes': self.suffixes,
            'columns': self.columns,
            'description': self.description,
        }


@dataclass
class FilterCriteria:
    """Represents a single filter criterion."""
    criteria_type: str  # comparison, is_unique, is_null, is_empty, custom
    criteria_id: str
    field: Optional[str] = None
    operator: Optional[str] = None  # equal, not_equal, gt, lt, etc.
    value: Optional[Any] = None
    keep: Optional[str] = None  # first, last (for is_unique)
    subset: Optional[List[str]] = None
    negate: bool = False
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'criteria_type': self.criteria_type,
            'criteria_id': self.criteria_id,
            'field': self.field,
            'operator': self.operator,
            'value': self.value,
            'keep': self.keep,
            'subset': self.subset,
            'negate': self.negate,
            'description': self.description,
        }


@dataclass
class MappingRule:
    """Represents a mapping rule."""
    rule_id: str
    description: str
    action: str  # constant, field_map, object_lookup, custom
    value: Optional[str] = None
    target: Optional[str] = None
    overwrite: bool = False
    object: Optional[str] = None  # For object_lookup
    source: Optional[List[str]] = None
    comment: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'rule_id': self.rule_id,
            'description': self.description,
            'action': self.action,
            'value': self.value,
            'target': self.target,
            'overwrite': self.overwrite,
            'object': self.object,
            'source': self.source,
            'comment': self.comment,
        }


@dataclass
class YAMLAnalysis:
    """Complete analysis of YAML files for a flow."""
    file_path: Path
    file_type: str  # 'merge', 'filter', 'mapping', 'unknown'
    merge_rules: List[MergeRule] = field(default_factory=list)
    filter_criteria: List[FilterCriteria] = field(default_factory=list)
    mapping_rules: List[MappingRule] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class YAMLParser:
    """
    Parse YAML configuration files used in BMF flows.
    
    Handles:
    - Merge rules (table_merger_*.yml)
    - Filter criteria (filter/filters_*.yml, *_filter.yml)
    - Mapping rules (mapping/*.yml)
    """
    
    def __init__(self, yaml_path: str):
        """
        Initialize YAML parser.
        
        Args:
            yaml_path: Path to YAML file
        """
        self.yaml_path = Path(yaml_path)
        self.logger = FlowVisualizerLogger.get_logger()
        
        self._validate_file()
        self._read_file()
    
    def _validate_file(self):
        """Validate that file exists and is readable."""
        if not self.yaml_path.exists():
            raise FileNotFoundError(f"YAML file not found: {self.yaml_path}")
        
        if not self.yaml_path.is_file():
            raise FileNotFoundError(f"Path is not a file: {self.yaml_path}")
        
        if not self.yaml_path.suffix in ['.yml', '.yaml']:
            raise ValueError(f"File must be .yml or .yaml file: {self.yaml_path}")
    
    def _read_file(self):
        """Read and store YAML file contents."""
        try:
            with open(self.yaml_path, 'r', encoding='utf-8') as f:
                self.raw_content = f.read()
        except IOError as e:
            raise IOError(f"Failed to read file: {e}")
    
    def _determine_file_type(self, data: Any) -> str:
        """Determine the type of YAML file based on content."""
        # Handle list-based YAML (filter files)
        if isinstance(data, list):
            # Check if it looks like filter criteria
            if all(isinstance(item, dict) and 'criteria' in item for item in data):
                return 'filter'
            return 'unknown'
        
        # Handle dict-based YAML
        if isinstance(data, dict):
            if 'merging_rules' in data:
                return 'merge'
            elif 'filter' in data or 'filters' in data:
                return 'filter'
            elif 'mapping_rules' in data:
                return 'mapping'
        
        return 'unknown'
    
    def parse(self) -> YAMLAnalysis:
        """
        Main entry point for parsing.
        
        Returns:
            YAMLAnalysis object with extracted rules and criteria
        """
        self.logger.info(f"Parsing YAML file: {self.yaml_path}")
        
        analysis = YAMLAnalysis(file_path=self.yaml_path, file_type='unknown')
        
        try:
            # Parse YAML using custom loader that handles unknown tags
            data = yaml.load(self.raw_content, Loader=CustomYAMLLoader)
            
            if data is None:
                analysis.warnings.append("YAML file is empty")
                return analysis
            
            analysis.raw_data = data if isinstance(data, dict) else {}
            
            # Determine file type
            analysis.file_type = self._determine_file_type(data)
            self.logger.debug(f"Detected YAML file type: {analysis.file_type}")
            
            # Parse based on file type
            if analysis.file_type == 'merge':
                self._parse_merge_rules(data, analysis)
            elif analysis.file_type == 'filter':
                self._parse_filter_criteria(data, analysis)
            elif analysis.file_type == 'mapping':
                self._parse_mapping_rules(data, analysis)
            else:
                analysis.warnings.append(f"Unknown YAML file type: {self.yaml_path.name}")
            
            self.logger.info(
                f"Extracted {len(analysis.merge_rules)} merge rules, "
                f"{len(analysis.filter_criteria)} filters, "
                f"{len(analysis.mapping_rules)} mappings"
            )
            
        except yaml.YAMLError as e:
            analysis.errors.append(f"YAML parse error: {e}")
            self.logger.error(f"YAML parse error: {e}")
        except Exception as e:
            analysis.errors.append(f"Unexpected error during YAML parsing: {e}")
            self.logger.error(f"Unexpected error: {e}")
        
        return analysis
    
    def _parse_merge_rules(self, data: Dict[str, Any], analysis: YAMLAnalysis):
        """Parse merge rules from YAML data."""
        merge_rules_data = data.get('merging_rules', [])
        
        if not isinstance(merge_rules_data, list):
            analysis.errors.append("merging_rules must be a list")
            return
        
        for idx, rule_data in enumerate(merge_rules_data):
            try:
                # Handle simple table reference
                if isinstance(rule_data, dict) and 'table' in rule_data:
                    table_ref = rule_data.get('table')
                    
                    # Extract table name from environment variable reference
                    if isinstance(table_ref, str):
                        table_name = table_ref.replace('!env', '').strip()
                    else:
                        table_name = str(table_ref)
                    
                    # Get loading and merging parameters
                    loading_params = rule_data.get('loading_params', {})
                    merging_params = rule_data.get('merging_params', {})
                    
                    rule = MergeRule(
                        table=table_name,
                        left_on=merging_params.get('left_on'),
                        right_on=merging_params.get('right_on'),
                        merge_type=merging_params.get('how', 'left'),
                        suffixes=tuple(merging_params.get('suffixes', ['', ''])),
                        columns=loading_params.get('columns'),
                        description=rule_data.get('description', ''),
                    )
                    
                    analysis.merge_rules.append(rule)
                    self.logger.debug(f"Extracted merge rule: {table_name}")
                    
            except Exception as e:
                analysis.warnings.append(f"Failed to parse merge rule {idx}: {e}")
                self.logger.warning(f"Failed to parse merge rule {idx}: {e}")
    
    def _parse_filter_criteria(self, data: Any, analysis: YAMLAnalysis):
        """Parse filter criteria from YAML data."""
        # Find filter data (could be under 'filters' key, 'filter' key, or as top-level list)
        if isinstance(data, list):
            filter_list = data
        else:
            filter_list = data.get('filters', data.get('filter', []))
        
        if not isinstance(filter_list, list):
            analysis.errors.append("Filter rules must be a list")
            return
        
        for idx, filter_data in enumerate(filter_list):
            try:
                if not isinstance(filter_data, dict):
                    analysis.warnings.append(f"Filter {idx} is not a dictionary")
                    continue
                
                # Extract common fields
                criteria_id = filter_data.get('criteria_id', f'filter_{idx}')
                description = filter_data.get('description', '')
                
                # Extract criteria definition
                criteria_def = filter_data.get('criteria', {})
                
                if isinstance(criteria_def, dict):
                    criteria_type = criteria_def.get('criteria', 'unknown')
                    
                    # Create appropriate filter criterion based on type
                    if criteria_type == 'comparison':
                        criterion = FilterCriteria(
                            criteria_type='comparison',
                            criteria_id=criteria_id,
                            field=criteria_def.get('field'),
                            operator=criteria_def.get('operator'),
                            value=criteria_def.get('value'),
                            description=description,
                        )
                    elif criteria_type == 'is_unique':
                        criterion = FilterCriteria(
                            criteria_type='is_unique',
                            criteria_id=criteria_id,
                            keep=criteria_def.get('keep', 'first'),
                            subset=criteria_def.get('subset'),
                            description=description,
                        )
                    elif criteria_type == 'is_null':
                        criterion = FilterCriteria(
                            criteria_type='is_null',
                            criteria_id=criteria_id,
                            field=criteria_def.get('field'),
                            negate=criteria_def.get('negate', False),
                            description=description,
                        )
                    elif criteria_type == 'is_empty':
                        criterion = FilterCriteria(
                            criteria_type='is_empty',
                            criteria_id=criteria_id,
                            field=criteria_def.get('field'),
                            negate=criteria_def.get('negate', False),
                            description=description,
                        )
                    else:
                        criterion = FilterCriteria(
                            criteria_type=criteria_type,
                            criteria_id=criteria_id,
                            description=description,
                        )
                    
                    analysis.filter_criteria.append(criterion)
                    self.logger.debug(f"Extracted filter criterion: {criteria_id}")
                    
            except Exception as e:
                analysis.warnings.append(f"Failed to parse filter {idx}: {e}")
                self.logger.warning(f"Failed to parse filter {idx}: {e}")
    
    def _parse_mapping_rules(self, data: Dict[str, Any], analysis: YAMLAnalysis):
        """Parse mapping rules from YAML data."""
        mapping_rules_data = data.get('mapping_rules', [])
        
        if not isinstance(mapping_rules_data, list):
            analysis.errors.append("mapping_rules must be a list")
            return
        
        for idx, rule_data in enumerate(mapping_rules_data):
            try:
                if not isinstance(rule_data, dict):
                    analysis.warnings.append(f"Mapping rule {idx} is not a dictionary")
                    continue
                
                rule = MappingRule(
                    rule_id=rule_data.get('id', f'mapping_{idx}'),
                    description=rule_data.get('description', ''),
                    action=rule_data.get('action', 'unknown'),
                    value=rule_data.get('value'),
                    target=rule_data.get('target'),
                    overwrite=rule_data.get('overwrite', False),
                    object=rule_data.get('object'),
                    source=rule_data.get('source'),
                    comment=rule_data.get('comment', ''),
                )
                
                analysis.mapping_rules.append(rule)
                self.logger.debug(f"Extracted mapping rule: {rule.rule_id}")
                
            except Exception as e:
                analysis.warnings.append(f"Failed to parse mapping rule {idx}: {e}")
                self.logger.warning(f"Failed to parse mapping rule {idx}: {e}")


def parse_yaml_file(yaml_path: str) -> YAMLAnalysis:
    """
    Convenience function to parse a YAML file.
    
    Args:
        yaml_path: Path to YAML file
        
    Returns:
        YAMLAnalysis object
    """
    parser = YAMLParser(yaml_path)
    return parser.parse()
