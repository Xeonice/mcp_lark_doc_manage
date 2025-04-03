import pytest
import os
import sys
import json

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from mcp_lark_doc_manage.markdown_converter import (
    convert_markdown_to_blocks,
    generate_unique_id,
    create_text_element_style,
    create_text_run
)

# 所有测试使用 markdown_test 标记
pytestmark = pytest.mark.markdown_test

def test_markdown_converter_basic_functionality():
    """测试转换器的基本功能"""
    # 测试生成唯一ID
    id1 = generate_unique_id()
    id2 = generate_unique_id()
    assert id1 != id2
    assert len(id1) == 22  # 修正为实际长度22
    
    # 测试文本样式创建
    style = create_text_element_style(bold=True)
    assert style["bold"] is True
    assert style["italic"] is False
    
    # 测试链接样式
    link_style = create_text_element_style(link="https://example.com")
    assert "link" in link_style
    assert "url" in link_style["link"]
    
    # 测试文本运行创建
    text_run = create_text_run("Test content")
    assert text_run["text_run"]["content"] == "Test content"
    assert "text_element_style" in text_run["text_run"]

def test_convert_markdown_to_blocks():
    """测试完整的 Markdown 到块的转换"""
    markdown_text = """# Heading 1
## Heading 2

Paragraph text

- Item 1
- Item 2

> Quote

```python
print("Hello, world!")
```

| Column 1 | Column 2 |
|----------|----------|
| Cell 1   | Cell 2   |
"""
    result = convert_markdown_to_blocks(markdown_text)
    
    # 验证基本结构
    assert "children_id" in result
    assert "descendants" in result
    assert len(result["descendants"]) > 0
    
    # 检查生成的块的类型
    block_types = [block.get("block_type") for block in result["descendants"]]
    
    # 验证代码块存在
    assert 14 in block_types  # 代码块
    assert 3 in block_types   # 列表
    assert 4 in block_types   # 引用
    assert 2 in block_types   # 段落
    
    # 查找代码块
    code_blocks = [block for block in result["descendants"] if block.get("block_type") == 14]
    assert len(code_blocks) > 0
    code_block = code_blocks[0]
    assert "code" in code_block
    # 检查 style 下的 language 属性
    assert "style" in code_block["code"]
    assert "language" in code_block["code"]["style"]
    assert "elements" in code_block["code"]

def test_text_element_functions():
    """测试文本元素处理函数"""
    # 测试粗体样式
    bold_style = create_text_element_style(bold=True)
    assert bold_style["bold"] is True
    assert bold_style["italic"] is False
    
    # 测试斜体样式
    italic_style = create_text_element_style(italic=True)
    assert italic_style["italic"] is True
    
    # 测试链接样式
    link_style = create_text_element_style(link="https://example.com")
    assert "link" in link_style
    assert "url" in link_style["link"]
    
    # 测试复合样式 (粗体+斜体)
    complex_style = create_text_element_style(bold=True, italic=True)
    assert complex_style["bold"] is True
    assert complex_style["italic"] is True
    
    # 测试文本运行
    text_run = create_text_run("Test content", create_text_element_style(bold=True))
    assert text_run["text_run"]["content"] == "Test content"
    assert text_run["text_run"]["text_element_style"]["bold"] is True

def test_convert_markdown_with_various_types():
    """测试转换各种类型的 Markdown 内容"""
    # 带有各种元素的 Markdown
    markdown_text = """
# 标题 1
## 标题 2
### 标题 3

普通段落文本

**粗体文本** *斜体文本* ~~删除线文本~~

> 引用文本

- 无序列表项 1
- 无序列表项 2
  - 嵌套列表项

1. 有序列表项 1
2. 有序列表项 2

```python
def hello():
    print("Hello, world!")
```

[链接文本](https://example.com)

| 表格标题 1 | 表格标题 2 |
|------------|------------|
| 单元格 1   | 单元格 2   |
"""
    result = convert_markdown_to_blocks(markdown_text)
    
    # 验证结果
    assert "children_id" in result
    assert "descendants" in result
    assert len(result["children_id"]) > 0
    assert len(result["descendants"]) > 0

def test_process_code_block():
    """测试代码块处理"""
    # 使用完整转换器处理包含代码块的 Markdown
    markdown_text = """```python
print("Hello, world!")
```"""
    result = convert_markdown_to_blocks(markdown_text)
    
    # 验证代码块
    assert len(result["descendants"]) > 0
    code_blocks = [block for block in result["descendants"] if block.get("block_type") == 14]
    assert len(code_blocks) > 0
    
    # 检查代码块的结构
    code_block = code_blocks[0]
    assert code_block["block_type"] == 14
    assert "code" in code_block
    # 检查结构中的 style 和 language
    assert "style" in code_block["code"]
    assert "language" in code_block["code"]["style"]
    assert code_block["code"]["style"]["language"] == 49  # Python
    assert "elements" in code_block["code"]
    
    # 确认代码内容
    elements = code_block["code"]["elements"]
    content = ''.join([element.get("text_run", {}).get("content", "") for element in elements])
    assert 'print("Hello, world!")' in content 