"""Unit tests for YAML Parser"""

import pytest
from pathlib import Path
from tempfile import NamedTemporaryFile
import yaml

from src.parsers.yaml_parser import (
    YAMLParser,
    YAMLAnalysis,
    MergeRule,
    FilterCriteria,
    MappingRule,
    parse_yaml_file,
)


class TestYAMLParser:
    """Test suite for YAMLParser class."""
    
    def test_parser_initialization_valid_file(self, tmp_path):
        """Test parser initialization with valid YAML file."""
        # Create temporary YAML file
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("key: value\n")
        
        parser = YAMLParser(str(yaml_file))
        assert parser.yaml_path == yaml_file
        assert parser.raw_content == "key: value\n"
    
    def test_parser_initialization_missing_file(self):
        """Test parser initialization with missing file."""
        with pytest.raises(FileNotFoundError):
            YAMLParser("/nonexistent/path/file.yaml")
    
    def test_parser_initialization_wrong_extension(self, tmp_path):
        """Test parser initialization with wrong file extension."""
        wrong_file = tmp_path / "test.txt"
        wrong_file.write_text("content")
        
        with pytest.raises(ValueError):
            YAMLParser(str(wrong_file))
    
    def test_parse_empty_yaml(self, tmp_path):
        """Test parsing empty YAML file."""
        yaml_file = tmp_path / "empty.yaml"
        yaml_file.write_text("")
        
        parser = YAMLParser(str(yaml_file))
        analysis = parser.parse()
        
        assert analysis.file_type == 'unknown'
        assert len(analysis.warnings) > 0
    
    def test_determine_file_type_merge(self):
        """Test file type detection for merge rules."""
        parser = YAMLParser.__new__(YAMLParser)
        data = {'merging_rules': []}
        file_type = parser._determine_file_type(data)
        
        assert file_type == 'merge'
    
    def test_determine_file_type_filter(self):
        """Test file type detection for filter rules."""
        parser = YAMLParser.__new__(YAMLParser)
        data = {'filter': [{'criteria': {}}]}
        file_type = parser._determine_file_type(data)
        
        assert file_type == 'filter'
    
    def test_determine_file_type_mapping(self):
        """Test file type detection for mapping rules."""
        parser = YAMLParser.__new__(YAMLParser)
        data = {'mapping_rules': []}
        file_type = parser._determine_file_type(data)
        
        assert file_type == 'mapping'


class TestMergeRuleParsing:
    """Test suite for merge rule parsing."""
    
    def test_parse_simple_merge_rule(self, tmp_path):
        """Test parsing simple merge rules."""
        yaml_file = tmp_path / "merge.yaml"
        yaml_content = {
            'merging_rules': [
                {
                    'table': 'gxpd_export',
                    'loading_params': {
                        'columns': ['ID', 'Name', 'Value']
                    },
                    'merging_params': {
                        'left_on': ['ID'],
                        'right_on': ['ID'],
                        'how': 'left',
                        'suffixes': ['_main', '_sec']
                    },
                    'description': 'Merge GXPD export'
                }
            ]
        }
        
        yaml_file.write_text(yaml.dump(yaml_content))
        
        parser = YAMLParser(str(yaml_file))
        analysis = parser.parse()
        
        assert analysis.file_type == 'merge'
        assert len(analysis.merge_rules) == 1
        
        rule = analysis.merge_rules[0]
        assert rule.table == 'gxpd_export'
        assert rule.left_on == ['ID']
        assert rule.merge_type == 'left'
        assert rule.suffixes == ('_main', '_sec')
    
    def test_parse_multiple_merge_rules(self, tmp_path):
        """Test parsing multiple merge rules."""
        yaml_file = tmp_path / "merge_multi.yaml"
        yaml_content = {
            'merging_rules': [
                {
                    'table': 'table1',
                    'merging_params': {'how': 'left'}
                },
                {
                    'table': 'table2',
                    'merging_params': {'how': 'inner'}
                },
                {
                    'table': 'table3',
                    'merging_params': {'how': 'outer'}
                }
            ]
        }
        
        yaml_file.write_text(yaml.dump(yaml_content))
        
        parser = YAMLParser(str(yaml_file))
        analysis = parser.parse()
        
        assert len(analysis.merge_rules) == 3
        assert analysis.merge_rules[0].merge_type == 'left'
        assert analysis.merge_rules[1].merge_type == 'inner'
        assert analysis.merge_rules[2].merge_type == 'outer'


class TestFilterCriteriaParsing:
    """Test suite for filter criteria parsing."""
    
    def test_parse_comparison_filter(self, tmp_path):
        """Test parsing comparison filter criteria."""
        yaml_file = tmp_path / "filter.yaml"
        yaml_content = {
            'filters': [
                {
                    'criteria': {
                        'criteria': 'comparison',
                        'field': 'Status',
                        'operator': 'equal',
                        'value': 'Active'
                    },
                    'criteria_id': 'keep_active',
                    'description': 'Keep only active records'
                }
            ]
        }
        
        yaml_file.write_text(yaml.dump(yaml_content))
        
        parser = YAMLParser(str(yaml_file))
        analysis = parser.parse()
        
        assert analysis.file_type == 'filter'
        assert len(analysis.filter_criteria) == 1
        
        criterion = analysis.filter_criteria[0]
        assert criterion.criteria_type == 'comparison'
        assert criterion.criteria_id == 'keep_active'
        assert criterion.field == 'Status'
        assert criterion.operator == 'equal'
        assert criterion.value == 'Active'
    
    def test_parse_is_unique_filter(self, tmp_path):
        """Test parsing is_unique filter criteria."""
        yaml_file = tmp_path / "filter_unique.yaml"
        yaml_content = {
            'filters': [
                {
                    'criteria': {
                        'criteria': 'is_unique',
                        'keep': 'first',
                        'subset': ['ID']
                    },
                    'criteria_id': 'keep_unique',
                    'description': 'Keep unique IDs'
                }
            ]
        }
        
        yaml_file.write_text(yaml.dump(yaml_content))
        
        parser = YAMLParser(str(yaml_file))
        analysis = parser.parse()
        
        assert len(analysis.filter_criteria) == 1
        
        criterion = analysis.filter_criteria[0]
        assert criterion.criteria_type == 'is_unique'
        assert criterion.keep == 'first'
        assert criterion.subset == ['ID']
    
    def test_parse_is_null_filter(self, tmp_path):
        """Test parsing is_null filter criteria."""
        yaml_file = tmp_path / "filter_null.yaml"
        yaml_content = {
            'filters': [
                {
                    'criteria': {
                        'criteria': 'is_null',
                        'field': 'Authorization Number',
                        'negate': True
                    },
                    'criteria_id': 'remove_null_auth',
                    'description': 'Remove records with null Authorization Number'
                }
            ]
        }
        
        yaml_file.write_text(yaml.dump(yaml_content))
        
        parser = YAMLParser(str(yaml_file))
        analysis = parser.parse()
        
        assert len(analysis.filter_criteria) == 1
        
        criterion = analysis.filter_criteria[0]
        assert criterion.criteria_type == 'is_null'
        assert criterion.field == 'Authorization Number'
        assert criterion.negate is True
    
    def test_parse_multiple_filters(self, tmp_path):
        """Test parsing multiple filter criteria."""
        yaml_file = tmp_path / "filters_multi.yaml"
        yaml_content = {
            'filters': [
                {
                    'criteria': {'criteria': 'comparison', 'field': 'Status'},
                    'criteria_id': 'filter1'
                },
                {
                    'criteria': {'criteria': 'is_unique', 'keep': 'first'},
                    'criteria_id': 'filter2'
                },
                {
                    'criteria': {'criteria': 'is_null', 'field': 'Value'},
                    'criteria_id': 'filter3'
                }
            ]
        }
        
        yaml_file.write_text(yaml.dump(yaml_content))
        
        parser = YAMLParser(str(yaml_file))
        analysis = parser.parse()
        
        assert len(analysis.filter_criteria) == 3
        assert analysis.filter_criteria[0].criteria_type == 'comparison'
        assert analysis.filter_criteria[1].criteria_type == 'is_unique'
        assert analysis.filter_criteria[2].criteria_type == 'is_null'


class TestMappingRuleParsing:
    """Test suite for mapping rule parsing."""
    
    def test_parse_constant_mapping_rule(self, tmp_path):
        """Test parsing constant mapping rule."""
        yaml_file = tmp_path / "mapping.yaml"
        yaml_content = {
            'mapping_rules': [
                {
                    'id': 'set_object_name',
                    'description': 'Set object name',
                    'action': 'constant',
                    'value': 'medicinal_product__rim',
                    'target': 'object_name',
                    'overwrite': True,
                    'comment': 'Sets the object name for migration'
                }
            ]
        }
        
        yaml_file.write_text(yaml.dump(yaml_content))
        
        parser = YAMLParser(str(yaml_file))
        analysis = parser.parse()
        
        assert analysis.file_type == 'mapping'
        assert len(analysis.mapping_rules) == 1
        
        rule = analysis.mapping_rules[0]
        assert rule.rule_id == 'set_object_name'
        assert rule.action == 'constant'
        assert rule.value == 'medicinal_product__rim'
        assert rule.target == 'object_name'
        assert rule.overwrite is True
    
    def test_parse_object_lookup_mapping_rule(self, tmp_path):
        """Test parsing object lookup mapping rule."""
        yaml_file = tmp_path / "mapping_lookup.yaml"
        yaml_content = {
            'mapping_rules': [
                {
                    'id': 'lookup_cv',
                    'description': 'Lookup controlled vocabulary',
                    'action': 'object_lookup',
                    'object': 'controlled_vocabulary__rim',
                    'source': ['lookup_constant', 'value_constant']
                }
            ]
        }
        
        yaml_file.write_text(yaml.dump(yaml_content))
        
        parser = YAMLParser(str(yaml_file))
        analysis = parser.parse()
        
        assert len(analysis.mapping_rules) == 1
        
        rule = analysis.mapping_rules[0]
        assert rule.action == 'object_lookup'
        assert rule.object == 'controlled_vocabulary__rim'
        assert rule.source == ['lookup_constant', 'value_constant']
    
    def test_parse_multiple_mapping_rules(self, tmp_path):
        """Test parsing multiple mapping rules."""
        yaml_file = tmp_path / "mapping_multi.yaml"
        yaml_content = {
            'mapping_rules': [
                {
                    'id': 'rule1',
                    'action': 'constant',
                    'value': 'val1',
                    'target': 'target1'
                },
                {
                    'id': 'rule2',
                    'action': 'field_map',
                    'target': 'target2'
                },
                {
                    'id': 'rule3',
                    'action': 'object_lookup',
                    'object': 'obj3'
                }
            ]
        }
        
        yaml_file.write_text(yaml.dump(yaml_content))
        
        parser = YAMLParser(str(yaml_file))
        analysis = parser.parse()
        
        assert len(analysis.mapping_rules) == 3


class TestYAMLIntegration:
    """Integration tests with real YAML structures."""
    
    def test_parse_gxpd_merge_file(self):
        """Test parsing actual GXPD merge rules file."""
        merge_file = Path("/Users/shormigo/Documents/BASE/Viatris/medicinal_product__rim_gxpd_all/merging_rules/table_merger_gxpd_exports.yml")
        
        if not merge_file.exists():
            pytest.skip("Real GXPD merge file not available")
        
        parser = YAMLParser(str(merge_file))
        analysis = parser.parse()
        
        assert analysis.file_type == 'merge'
        assert len(analysis.merge_rules) > 0
        # Verify first rule has expected structure
        assert all(hasattr(rule, 'table') for rule in analysis.merge_rules)
    
    def test_parse_gxpd_filter_file(self):
        """Test parsing actual GXPD filter file."""
        filter_file = Path("/Users/shormigo/Documents/BASE/Viatris/medicinal_product__rim_gxpd_all/filter/filtered_gxpd_export.yml")
        
        if not filter_file.exists():
            pytest.skip("Real GXPD filter file not available")
        
        parser = YAMLParser(str(filter_file))
        analysis = parser.parse()
        
        assert analysis.file_type == 'filter'
        assert len(analysis.filter_criteria) > 0
        # Verify filters have expected structure
        assert all(hasattr(c, 'criteria_id') for c in analysis.filter_criteria)
    
    def test_parse_gxpd_mapping_file(self):
        """Test parsing actual GXPD mapping file."""
        mapping_file = Path("/Users/shormigo/Documents/BASE/Viatris/medicinal_product__rim_gxpd_all/mapping/create_new.yml")
        
        if not mapping_file.exists():
            pytest.skip("Real GXPD mapping file not available")
        
        parser = YAMLParser(str(mapping_file))
        analysis = parser.parse()
        
        assert analysis.file_type == 'mapping'
        assert len(analysis.mapping_rules) > 0
        # Verify mappings have expected structure
        assert all(hasattr(rule, 'rule_id') for rule in analysis.mapping_rules)


class TestDataClasses:
    """Test data classes for YAML structures."""
    
    def test_merge_rule_to_dict(self):
        """Test MergeRule to_dict conversion."""
        rule = MergeRule(
            table='test_table',
            left_on=['ID'],
            right_on=['ID'],
            merge_type='left',
            suffixes=('_a', '_b')
        )
        
        rule_dict = rule.to_dict()
        assert rule_dict['table'] == 'test_table'
        assert rule_dict['left_on'] == ['ID']
        assert rule_dict['merge_type'] == 'left'
    
    def test_filter_criteria_to_dict(self):
        """Test FilterCriteria to_dict conversion."""
        criterion = FilterCriteria(
            criteria_type='comparison',
            criteria_id='test_filter',
            field='Status',
            operator='equal',
            value='Active'
        )
        
        crit_dict = criterion.to_dict()
        assert crit_dict['criteria_type'] == 'comparison'
        assert crit_dict['criteria_id'] == 'test_filter'
        assert crit_dict['field'] == 'Status'
    
    def test_mapping_rule_to_dict(self):
        """Test MappingRule to_dict conversion."""
        rule = MappingRule(
            rule_id='test_rule',
            description='Test mapping',
            action='constant',
            value='test_value',
            target='test_target'
        )
        
        rule_dict = rule.to_dict()
        assert rule_dict['rule_id'] == 'test_rule'
        assert rule_dict['action'] == 'constant'
        assert rule_dict['value'] == 'test_value'


class TestErrorHandling:
    """Test error handling in YAML parser."""
    
    def test_parse_malformed_yaml(self, tmp_path):
        """Test parsing malformed YAML that breaks YAML parser."""
        yaml_file = tmp_path / "malformed.yaml"
        # Use actual YAML that causes parse error
        yaml_file.write_text("key: [invalid\n  - broken")
        
        parser = YAMLParser(str(yaml_file))
        analysis = parser.parse()
        
        # Either has errors or warnings for malformed content
        assert len(analysis.errors) > 0 or len(analysis.warnings) > 0
    
    def test_parse_invalid_merge_structure(self, tmp_path):
        """Test parsing invalid merge rule structure."""
        yaml_file = tmp_path / "invalid_merge.yaml"
        yaml_content = {
            'merging_rules': "not_a_list"
        }
        
        yaml_file.write_text(yaml.dump(yaml_content))
        
        parser = YAMLParser(str(yaml_file))
        analysis = parser.parse()
        
        assert len(analysis.errors) > 0
    
    def test_convenience_function(self, tmp_path):
        """Test parse_yaml_file convenience function."""
        yaml_file = tmp_path / "test.yaml"
        yaml_content = {'mapping_rules': [{'id': 'test'}]}
        yaml_file.write_text(yaml.dump(yaml_content))
        
        analysis = parse_yaml_file(str(yaml_file))
        
        assert analysis.file_type == 'mapping'
        assert len(analysis.mapping_rules) == 1
