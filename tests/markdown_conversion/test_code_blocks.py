import pytest
from src.mcp_lark_doc_manage.markdown_converter import convert_markdown_to_blocks
from .conftest import load_test_data, load_expected_result

def test_code_blocks():
    """Test code block conversion."""
    markdown = load_test_data('code_blocks.md')
    expected = load_expected_result('code_blocks_result.json')
    result = convert_markdown_to_blocks(markdown)
    
    # 确保result和expected有相同的结构
    assert isinstance(result, dict), f"Result is not a dict but {type(result)}"
    assert isinstance(expected, dict), f"Expected is not a dict but {type(expected)}"
    
    assert "descendants" in result, "Result missing 'descendants' key"
    assert "descendants" in expected, "Expected missing 'descendants' key"
    
    # 获取块列表
    result_blocks = result.get('descendants', [])
    expected_blocks = expected.get('descendants', [])
    
    # 检查块的数量
    assert len(result_blocks) == len(expected_blocks), f"Block count mismatch: {len(result_blocks)} != {len(expected_blocks)}"
    
    # 比较每个块的结构和类型，但忽略具体内容
    for i, (res_block, exp_block) in enumerate(zip(result_blocks, expected_blocks)):
        assert res_block.get('block_type') == exp_block.get('block_type'), f"Block type mismatch at index {i}"
        
        # 根据块类型检查对应的内容
        block_type = res_block.get('block_type')
        
        if block_type == 3:  # heading1
            assert 'heading1' in res_block, f"Missing 'heading1' in result block at index {i}"
        elif block_type == 4:  # heading2
            assert 'heading2' in res_block, f"Missing 'heading2' in result block at index {i}"
        elif block_type == 14:  # code
            assert 'code' in res_block, f"Missing 'code' in result block at index {i}"
            
            # 检查代码块的结构
            assert 'style' in res_block['code'], f"Missing 'style' in code block at index {i}"
            assert 'language' in res_block['code']['style'], f"Missing 'language' in code style at index {i}"
            assert 'elements' in res_block['code'], f"Missing 'elements' in code block at index {i}"
        elif block_type == 2:  # text
            assert 'text' in res_block, f"Missing 'text' in result block at index {i}"
            
            # 检查是否为最后一个文本块（包含行内代码的块）
            if i == len(result_blocks) - 1:
                # 检查行内代码部分
                assert 'elements' in res_block['text'], f"Missing 'elements' in text block at index {i}"
                elements = res_block['text']['elements']
                
                # 预期有三个元素：前缀文本、行内代码、后缀文本
                assert len(elements) == 3, f"Expected 3 elements in last text block, got {len(elements)}"
                
                # 检查第一个元素 - "这是一个"
                assert 'text_run' in elements[0], f"Missing 'text_run' in first element of last text block"
                assert elements[0]['text_run']['content'] == "这是一个", f"Unexpected content in first element: {elements[0]['text_run']['content']}"
                
                # 检查第二个元素 - 行内代码
                assert 'text_run' in elements[1], f"Missing 'text_run' in second element of last text block"
                assert elements[1]['text_run']['content'] == "行内代码", f"Unexpected content in second element: {elements[1]['text_run']['content']}"
                assert elements[1]['text_run']['text_element_style']['inline_code'] == True, f"Inline code style not set correctly"
                
                # 检查第三个元素 - 后缀文本
                assert 'text_run' in elements[2], f"Missing 'text_run' in third element of last text block"
                assert "的例子，可以在文本中嵌入代码片段" in elements[2]['text_run']['content'], f"Unexpected content in third element: {elements[2]['text_run']['content']}"