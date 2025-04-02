import pytest
from src.mcp_lark_doc_manage.markdown_converter import convert_markdown_to_blocks
from .conftest import load_test_data, load_expected_result

def test_text_styles():
    """Test text style conversion."""
    markdown = load_test_data('text_styles.md')
    expected = load_expected_result('text_styles_result.json')
    result = convert_markdown_to_blocks(markdown)
    assert result == expected 