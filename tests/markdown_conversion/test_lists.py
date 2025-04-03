import pytest
import sys
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# 直接从模块导入
from src.mcp_lark_doc_manage.markdown_converter import convert_markdown_to_blocks
# 使用绝对导入替代相对导入
from tests.markdown_conversion.conftest import load_test_data, load_expected_result

def test_lists():
    """Test list conversion."""
    markdown = load_test_data('lists.md')
    expected = load_expected_result('lists_result.json')
    result = convert_markdown_to_blocks(markdown)
    assert result == expected 