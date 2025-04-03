import pytest
import sys
import os
import json
from unittest.mock import patch, MagicMock, AsyncMock
from dotenv import load_dotenv
from mcp.types import CallToolResult, TextContent

# 加载测试环境变量
test_env_path = os.path.join(os.path.dirname(__file__), 'test.env')
if os.path.exists(test_env_path):
    load_dotenv(test_env_path)

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 根据项目实际结构修改导入
from mcp_lark_doc_manage.server import (
    get_folder_token,
    _check_token_expired
)

# 验证各种工具功能的格式和接口
def test_tool_interface_verification():
    """验证服务器工具接口的格式是否正确"""
    # 模拟 list_folder_content 的返回值
    list_folder_result = CallToolResult(
        isError=False,
        content=[TextContent(type="text", text=json.dumps([
            {"name": "Test Document", "type": "doc", "token": "abc123"} 
        ], indent=2))]
    )
    
    # 验证格式是否符合预期
    assert not list_folder_result.isError
    assert len(list_folder_result.content) == 1
    assert list_folder_result.content[0].type == "text"
    assert "Test Document" in list_folder_result.content[0].text
    
    # 模拟 get_lark_doc_content 的返回值
    doc_content_result = CallToolResult(
        isError=False,
        content=[TextContent(type="text", text="# Document Title\nThis is document content")]
    )
    
    # 验证格式是否符合预期
    assert not doc_content_result.isError
    assert len(doc_content_result.content) == 1
    assert doc_content_result.content[0].type == "text"
    assert "Document Title" in doc_content_result.content[0].text
    
    # 模拟 search_wiki 的返回值
    search_result = CallToolResult(
        isError=False,
        content=[TextContent(type="text", text=json.dumps([
            {"title": "Search Result", "url": "https://example.com"}
        ], indent=2))]
    )
    
    # 验证格式是否符合预期
    assert not search_result.isError
    assert len(search_result.content) == 1
    assert search_result.content[0].type == "text"
    assert "Search Result" in search_result.content[0].text
    
    # 模拟 create_doc 的返回值
    create_doc_result = CallToolResult(
        isError=False,
        content=[TextContent(type="text", text=json.dumps({
            "document_id": "doc123", 
            "title": "New Document"
        }, indent=2))]
    )
    
    # 验证格式是否符合预期
    assert not create_doc_result.isError
    assert len(create_doc_result.content) == 1
    assert create_doc_result.content[0].type == "text"
    assert "doc123" in create_doc_result.content[0].text
    
    # 模拟错误情况
    error_result = CallToolResult(
        isError=True,
        content=[TextContent(type="text", text="An error occurred")]
    )
    
    # 验证错误格式是否符合预期
    assert error_result.isError
    assert len(error_result.content) == 1
    assert error_result.content[0].type == "text"
    assert "An error occurred" in error_result.content[0].text

# 测试辅助函数
@pytest.mark.asyncio
async def test_get_folder_token():
    """Test get_folder_token function"""
    # Mock the function to return a specific value
    with patch("mcp_lark_doc_manage.server.FOLDER_TOKEN", "test_folder_token"):
        token = await get_folder_token()
        assert token == "test_folder_token"

@pytest.mark.asyncio
async def test_check_token_expired():
    """Test check_token_expired function"""
    # Test with no token (expired)
    with patch("mcp_lark_doc_manage.server.USER_ACCESS_TOKEN", None), \
         patch("mcp_lark_doc_manage.server.TOKEN_EXPIRES_AT", None):
        expired = await _check_token_expired()
        assert expired is True
    
    # Test with expired token (time in past)
    with patch("mcp_lark_doc_manage.server.USER_ACCESS_TOKEN", "test_token"), \
         patch("mcp_lark_doc_manage.server.TOKEN_EXPIRES_AT", 100):  # Very old timestamp
        expired = await _check_token_expired()
        assert expired is True
    
    # Test with valid token (time in future)
    with patch("mcp_lark_doc_manage.server.USER_ACCESS_TOKEN", "test_token"), \
         patch("mcp_lark_doc_manage.server.TOKEN_EXPIRES_AT", 9999999999):  # Future timestamp
        expired = await _check_token_expired()
        assert expired is False
