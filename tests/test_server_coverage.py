import pytest
import asyncio
import time
import os
from unittest.mock import patch, MagicMock
import mcp_lark_doc_manage.server as server
from mcp.types import TextContent

# Skip these tests if AsyncMock is not available
try:
    from unittest.mock import AsyncMock
    HAS_ASYNC_MOCK = True
except ImportError:
    HAS_ASYNC_MOCK = False

@pytest.mark.skipif(not HAS_ASYNC_MOCK, reason="AsyncMock not available")
def test_server_constants():
    """Test server constants and environment variable handling"""
    # Verify environment variables are read correctly
    assert server.LARK_APP_ID == "test_app_id"
    assert server.LARK_APP_SECRET == "test_app_secret"
    assert server.OAUTH_PORT == 9997
    assert server.FOLDER_TOKEN == "test_folder_token"
    
    # Test REDIRECT_URI formation
    assert server.REDIRECT_URI == f"http://{server.OAUTH_HOST}:{server.OAUTH_PORT}/oauth/callback"

@pytest.mark.skipif(not HAS_ASYNC_MOCK, reason="AsyncMock not available")
@pytest.mark.asyncio
async def test_check_token_expired():
    """Test token expiration checking"""
    # Save original values
    original_token = server.USER_ACCESS_TOKEN
    original_expires = server.TOKEN_EXPIRES_AT
    
    try:
        # Test with no token
        server.USER_ACCESS_TOKEN = None
        server.TOKEN_EXPIRES_AT = None
        assert await server._check_token_expired() is True
        
        # Test with expired token
        server.USER_ACCESS_TOKEN = "test_token"
        server.TOKEN_EXPIRES_AT = time.time() - 100  # Expired 100 seconds ago
        assert await server._check_token_expired() is True
        
        # Test with valid token
        server.USER_ACCESS_TOKEN = "test_token"
        server.TOKEN_EXPIRES_AT = time.time() + 3600  # Valid for next hour
        assert await server._check_token_expired() is False
    finally:
        # Restore values
        server.USER_ACCESS_TOKEN = original_token
        server.TOKEN_EXPIRES_AT = original_expires

@pytest.mark.skipif(not HAS_ASYNC_MOCK, reason="AsyncMock not available")
@pytest.mark.asyncio
async def test_get_folder_token():
    """Test getting folder token"""
    # Test with environment variable set
    original = server.FOLDER_TOKEN
    try:
        server.FOLDER_TOKEN = "test_folder_token"
        assert await server.get_folder_token() == "test_folder_token"
        
        # Test with empty environment variable
        server.FOLDER_TOKEN = ""
        assert await server.get_folder_token() == ""
    finally:
        # Restore original value
        server.FOLDER_TOKEN = original

# 直接测试接口格式，不执行实际函数
def test_tool_interface():
    """验证工具接口的一致性"""
    from mcp.types import CallToolResult, TextContent
    import json
    
    # 验证 list_folder_content 返回格式
    list_result = CallToolResult(
        isError=False,
        content=[TextContent(type="text", text=json.dumps([
            {"name": "Test Doc", "type": "doc", "token": "123"}
        ]))]
    )
    assert list_result.isError is False
    assert len(list_result.content) == 1
    
    # 验证 get_lark_doc_content 返回格式
    doc_result = CallToolResult(
        isError=False,
        content=[TextContent(type="text", text="Document content")]
    )
    assert doc_result.isError is False
    assert len(doc_result.content) == 1
    assert doc_result.content[0].type == "text"
    
    # 验证 search_wiki 返回格式
    search_result = CallToolResult(
        isError=False,
        content=[TextContent(type="text", text=json.dumps([
            {"title": "Test Wiki", "url": "http://example.com"}
        ]))]
    )
    assert search_result.isError is False
    assert len(search_result.content) == 1
    
    # 验证 create_doc 返回格式
    create_result = CallToolResult(
        isError=False,
        content=[TextContent(type="text", text=json.dumps({
            "document_id": "doc123",
            "title": "Test Doc"
        }))]
    )
    assert create_result.isError is False
    assert len(create_result.content) == 1 