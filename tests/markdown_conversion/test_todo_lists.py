import pytest
from .conftest import load_test_data, load_expected_result

def test_todo_lists():
    """Test todo list conversion."""
    markdown = load_test_data('todo_lists.md')
    expected = load_expected_result('todo_lists_result.json')
    result = convert_markdown_to_blocks(markdown)
    assert result == expected 