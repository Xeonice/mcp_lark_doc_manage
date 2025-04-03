import pytest
import sys
import os
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent.parent / 'src'))

from mcp_lark_doc_manage.markdown_converter import convert_markdown_to_blocks
from .conftest import load_test_data, load_expected_result

def test_heading_conversion():
    """Test heading conversion."""
    markdown = load_test_data('headings.md')
    expected = load_expected_result('headings_result.json')
    result = convert_markdown_to_blocks(markdown)
    assert result == expected 