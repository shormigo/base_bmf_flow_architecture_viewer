"""Pytest configuration and shared fixtures"""

import pytest
from pathlib import Path


@pytest.fixture
def test_object_path():
    """Path to the test GxPD object."""
    return Path("/Users/shormigo/Documents/BASE/Viatris/medicinal_product__rim_gxpd_all")


@pytest.fixture
def valid_object_path(test_object_path):
    """Valid object path fixture."""
    return str(test_object_path)
