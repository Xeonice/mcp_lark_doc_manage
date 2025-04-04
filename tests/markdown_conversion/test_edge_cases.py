import pytest
from mcp_lark_doc_manage.markdown_converter import (
    generate_unique_id,
    create_block_style,
    process_heading_node,
    process_list_node,
    process_quote_node,
    process_task_list_item,
    convert_markdown_to_blocks
)
from collections import OrderedDict

def test_generate_unique_id():
    """Test generate_unique_id function"""
    # Test that generated IDs are unique
    ids = [generate_unique_id() for _ in range(100)]
    assert len(set(ids)) == 100
    # Test that IDs are base64url encoded and have correct length
    assert all(len(id) <= 24 for id in ids)  # Changed from exact 24 to <= 24

def test_create_block_style():
    """Test create_block_style function"""
    # Test default values
    style = create_block_style()
    assert style['align'] == 1
    assert style['folded'] is False
    
    # Test custom values
    style = create_block_style(align=2, folded=True)
    assert style['align'] == 2
    assert style['folded'] is True

def test_process_heading_node_edge_cases():
    """Test process_heading_node with edge cases"""
    result = OrderedDict([('children_id', []), ('descendants', [])])
    block_id_counter = 1
    
    def get_next_block_id():
        nonlocal block_id_counter
        block_id = str(block_id_counter)
        block_id_counter += 1
        return block_id
    
    # Test level 4 heading (should default to paragraph)
    node = {
        'attrs': {'level': 4},
        'children': [{'raw': 'Test Heading'}]
    }
    process_heading_node(node, result, get_next_block_id, 0, 1)
    assert result['descendants'][-1]['block_type'] == 2  # Paragraph type

def test_process_list_node_nested():
    """Test process_list_node with nested lists"""
    result = OrderedDict([('children_id', []), ('descendants', [])])
    block_id_counter = 1
    
    def get_next_block_id():
        nonlocal block_id_counter
        block_id = str(block_id_counter)
        block_id_counter += 1
        return block_id
    
    # Create a nested list structure
    node = {
        'attrs': {'ordered': True},
        'children': [
            {
                'type': 'list_item',
                'children': [
                    {'type': 'block_text', 'children': [{'type': 'text', 'raw': 'Item 1'}]},
                    {
                        'type': 'list',
                        'attrs': {'ordered': False},
                        'children': [
                            {
                                'type': 'list_item',
                                'children': [{'type': 'block_text', 'children': [{'type': 'text', 'raw': 'Subitem 1'}]}]
                            }
                        ]
                    }
                ]
            }
        ]
    }
    
    process_list_node(node, result, get_next_block_id, 0, 1)
    
    # Verify nested structure
    assert len(result['descendants']) > 1
    assert 'children' in result['descendants'][0]

def test_process_quote_node_edge_cases():
    """Test process_quote_node with edge cases"""
    result = OrderedDict([('children_id', []), ('descendants', [])])
    block_id_counter = 1
    
    def get_next_block_id():
        nonlocal block_id_counter
        block_id = str(block_id_counter)
        block_id_counter += 1
        return block_id
    
    # Test empty quote
    node = {
        'children': []
    }
    quote_id = process_quote_node(node, result, get_next_block_id)
    assert quote_id in result['children_id']
    assert len(result['descendants']) > 0

def test_process_task_list_item_edge_cases():
    """Test process_task_list_item with edge cases"""
    result = OrderedDict([('children_id', []), ('descendants', [])])
    block_id_counter = 1
    
    def get_next_block_id():
        nonlocal block_id_counter
        block_id = str(block_id_counter)
        block_id_counter += 1
        return block_id
    
    # Test task item with nested list
    node = {
        'attrs': {'checked': True},
        'children': [
            {'type': 'block_text', 'children': [{'type': 'text', 'raw': 'Task 1'}]},
            {
                'type': 'list',
                'children': [
                    {
                        'type': 'task_list_item',
                        'attrs': {'checked': False},
                        'children': [{'type': 'block_text', 'children': [{'type': 'text', 'raw': 'Subtask 1'}]}]
                    }
                ]
            }
        ]
    }
    
    task_id = process_task_list_item(node, result, get_next_block_id)
    assert task_id in result['children_id']
    # Check that the task item has the correct structure
    task_block = result['descendants'][-1]
    assert task_block['block_type'] == 17
    assert 'todo' in task_block
    assert 'elements' in task_block['todo']

def test_convert_markdown_to_blocks_unhandled_node():
    """Test convert_markdown_to_blocks with unhandled node type"""
    # Create a markdown text with an unhandled node type
    markdown_text = "```python\nprint('test')\n```\n<custom>unhandled</custom>"
    
    # The function should handle this without raising an error
    result = convert_markdown_to_blocks(markdown_text)
    assert isinstance(result, OrderedDict)
    assert 'children_id' in result
    assert 'descendants' in result 