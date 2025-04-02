import pytest
from src.mcp_lark_doc_manage.markdown_converter import convert_markdown_to_blocks
from .conftest import load_test_data, load_expected_result

def test_links():
    """Test link conversion."""
    markdown = load_test_data('links.md')
    expected = load_expected_result('links_result.json')
    result = convert_markdown_to_blocks(markdown)
    assert result == expected 