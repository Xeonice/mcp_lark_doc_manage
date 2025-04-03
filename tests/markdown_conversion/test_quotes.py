import pytest
from .conftest import load_test_data, load_expected_result
from src.mcp_lark_doc_manage.markdown_converter import convert_markdown_to_blocks

def test_quotes():
    """Test quote conversion."""
    markdown = load_test_data('quotes.md')
    expected = load_expected_result('quotes_result.json')
    result = convert_markdown_to_blocks(markdown)
    assert result == expected 