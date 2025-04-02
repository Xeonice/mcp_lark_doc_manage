import pytest
from mcp_lark_doc_manage.markdown_converter import convert_markdown_to_blocks
from .conftest import load_test_data, load_expected_result

def test_code_blocks():
    """Test code block conversion."""
    markdown = load_test_data('code_blocks.md')
    expected = load_expected_result('code_blocks_result.json')
    result = convert_markdown_to_blocks(markdown)
    
    # Compare blocks but ignore content within elements
    assert len(result) == len(expected)
    for i, (res_block, exp_block) in enumerate(zip(result, expected)):
        # Check block type
        assert res_block['block_type'] == exp_block['block_type']
        
        # Check structure up to elements level
        for key in res_block:
            if key in exp_block:
                # Get the block content for the current key
                res_content = res_block[key]
                exp_content = exp_block[key]
                
                # Check if the content is a dictionary and has 'elements'
                if isinstance(res_content, dict) and 'elements' in res_content:
                    # Check everything except elements content
                    for sub_key in res_content:
                        if sub_key != 'elements':
                            assert res_content[sub_key] == exp_content[sub_key]
                else:
                    assert res_block[key] == exp_block[key]