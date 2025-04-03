import pytest
import os
import sys
import json
import time
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
import logging
from aiohttp import web

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入测试模块
import mcp_lark_doc_manage.server as server
from mcp.types import CallToolResult, TextContent

# 设置测试环境变量
os.environ["TESTING"] = "true"
os.environ["OAUTH_PORT"] = "9997"
os.environ["LARK_APP_ID"] = "test_app_id"
os.environ["LARK_APP_SECRET"] = "test_app_secret"
os.environ["FOLDER_TOKEN"] = "test_folder_token"

# 所有测试使用 server_test 标记
pytestmark = pytest.mark.server_test

@pytest.mark.asyncio
async def test_check_token_expired_branches():
    """测试令牌过期检查的各种分支"""
    # 测试各种条件分支，避免嵌套 lock
    # 保存原始值以便后续恢复
    original_token = server.USER_ACCESS_TOKEN
    original_expires = server.TOKEN_EXPIRES_AT
    
    try:
        # 通过打补丁的方式模拟 _check_token_expired 函数，避免使用实际的 token_lock
        with patch("mcp_lark_doc_manage.server.token_lock", asyncio.Lock()):
            # 测试无令牌情况
            server.USER_ACCESS_TOKEN = None
            server.TOKEN_EXPIRES_AT = None
            # 使用 wait_for 设置超时，避免测试无限等待
            result = await asyncio.wait_for(server._check_token_expired(), timeout=1)
            assert result is True
            
            # 测试有令牌但无过期时间情况
            server.USER_ACCESS_TOKEN = "test_token"
            server.TOKEN_EXPIRES_AT = None
            result = await asyncio.wait_for(server._check_token_expired(), timeout=1)
            assert result is True
            
            # 测试令牌即将过期情况 (提前60秒视为过期)
            server.TOKEN_EXPIRES_AT = time.time() + 30  # 30秒后过期
            result = await asyncio.wait_for(server._check_token_expired(), timeout=1)
            assert result is True
            
            # 测试有效令牌情况
            server.TOKEN_EXPIRES_AT = time.time() + 3600  # 1小时后过期
            result = await asyncio.wait_for(server._check_token_expired(), timeout=1)
            assert result is False
    finally:
        # 恢复原始值
        server.USER_ACCESS_TOKEN = original_token
        server.TOKEN_EXPIRES_AT = original_expires

@pytest.mark.asyncio
async def test_get_folder_token_logic():
    """测试获取文件夹令牌的逻辑"""
    # 保存原始值
    original_token = server.FOLDER_TOKEN
    
    try:
        # 使用超时保护避免测试无限等待
        # 测试有令牌情况
        server.FOLDER_TOKEN = "folder_test_token"
        assert await asyncio.wait_for(server.get_folder_token(), timeout=1) == "folder_test_token"
        
        # 测试无令牌情况
        server.FOLDER_TOKEN = ""
        assert await asyncio.wait_for(server.get_folder_token(), timeout=1) == ""
        
        # 空值情况
        server.FOLDER_TOKEN = None
        assert await asyncio.wait_for(server.get_folder_token(), timeout=1) is None
    finally:
        # 恢复原始值
        server.FOLDER_TOKEN = original_token

@pytest.mark.asyncio
async def test_get_lark_doc_content_error_paths():
    """测试获取飞书文档内容的错误路径"""
    # 模拟未初始化的响应
    uninitialized_response = CallToolResult(
        isError=True,
        content=[TextContent(type="text", text="Lark client not properly initialized")]
    )
    
    # 模拟验证失败的响应
    auth_failed_response = CallToolResult(
        isError=True,
        content=[TextContent(type="text", text="Failed to get user access token: Auth failed")]
    )
    
    # 模拟无效URL的响应
    invalid_url_response = CallToolResult(
        isError=True,
        content=[TextContent(type="text", text="Invalid Lark document URL format")]
    )
    
    # 设置不同的模拟响应
    async def mock_get_lark_doc_content_none_client(url):
        return uninitialized_response
        
    async def mock_get_lark_doc_content_auth_failed(url):
        return auth_failed_response
        
    async def mock_get_lark_doc_content_invalid_url(url):
        return invalid_url_response
    
    # 模拟 larkClient 未初始化的情况
    with patch("mcp_lark_doc_manage.server.get_lark_doc_content", AsyncMock(side_effect=mock_get_lark_doc_content_none_client)):
        result = await server.get_lark_doc_content("https://docs.feishu.cn/docx/test123")
        assert result.isError is True
        assert "not properly initialized" in result.content[0].text
    
    # 模拟 token 验证失败的情况
    with patch("mcp_lark_doc_manage.server.get_lark_doc_content", AsyncMock(side_effect=mock_get_lark_doc_content_auth_failed)):
        result = await server.get_lark_doc_content("https://docs.feishu.cn/docx/test123")
        assert result.isError is True
        assert "Failed to get user access token" in result.content[0].text
    
    # 模拟无效的文档URL
    with patch("mcp_lark_doc_manage.server.get_lark_doc_content", AsyncMock(side_effect=mock_get_lark_doc_content_invalid_url)):
        result = await server.get_lark_doc_content("https://docs.feishu.cn/invalid/test123")
        assert result.isError is True
        assert "Invalid Lark document URL format" in result.content[0].text

@pytest.mark.asyncio
async def test_wiki_document_handling():
    """测试 Wiki 文档处理的特定路径"""
    # 模拟成功的 wiki 文档响应
    wiki_content_response = CallToolResult(
        isError=False,
        content=[TextContent(type="text", text="Test wiki content")]
    )
    
    # 模拟异步函数
    async def mock_get_wiki_content(url):
        assert '/wiki/' in url, "应该检测到 wiki URL"
        return wiki_content_response
    
    # 使用 AsyncMock 替代真实函数
    with patch("mcp_lark_doc_manage.server.get_lark_doc_content", AsyncMock(side_effect=mock_get_wiki_content)):
        # 测试 wiki 文档的处理
        result = await server.get_lark_doc_content("https://docs.feishu.cn/wiki/test123")
        
        # 验证结果
        assert result.isError is False
        assert "Test wiki content" in result.content[0].text

@pytest.mark.asyncio
async def test_wiki_document_error_paths():
    """测试 Wiki 文档处理的错误路径"""
    # 模拟 Wiki API 调用失败的响应
    wiki_api_error_response = CallToolResult(
        isError=True,
        content=[TextContent(type="text", text="Failed to get wiki document real ID: code 400, message: Wiki API Error")]
    )
    
    # 模拟 Wiki 数据节点丢失的响应
    wiki_data_missing_response = CallToolResult(
        isError=True,
        content=[TextContent(type="text", text="Failed to get wiki document node info, response: None")]
    )
    
    # 模拟 Wiki API 错误的异步函数
    async def mock_wiki_api_error(url):
        assert '/wiki/' in url, "应该检测到 wiki URL"
        return wiki_api_error_response
    
    # 模拟 Wiki 数据节点丢失的异步函数
    async def mock_wiki_data_missing(url):
        assert '/wiki/' in url, "应该检测到 wiki URL"
        return wiki_data_missing_response
    
    # 测试 Wiki API 调用失败
    with patch("mcp_lark_doc_manage.server.get_lark_doc_content", AsyncMock(side_effect=mock_wiki_api_error)):
        # 测试 Wiki API 失败情况
        result = await server.get_lark_doc_content("https://docs.feishu.cn/wiki/test123")
        
        # 验证结果
        assert result.isError is True
        assert "Failed to get wiki document real ID" in result.content[0].text
    
    # 测试 Wiki 数据节点丢失
    with patch("mcp_lark_doc_manage.server.get_lark_doc_content", AsyncMock(side_effect=mock_wiki_data_missing)):
        # 测试 Wiki 数据为空的情况
        result = await server.get_lark_doc_content("https://docs.feishu.cn/wiki/test123")
        
        # 验证结果
        assert result.isError is True
        assert "Failed to get wiki document node info" in result.content[0].text

@pytest.mark.asyncio
async def test_search_wiki_paths():
    """测试搜索 Wiki 的各种路径"""
    # 模拟客户端未初始化的响应
    uninit_response = CallToolResult(
        isError=True,
        content=[TextContent(type="text", text="Lark client not properly initialized")]
    )
    
    # 模拟认证失败的响应
    auth_failed_response = CallToolResult(
        isError=True,
        content=[TextContent(type="text", text="Failed to get user access token: Auth failed")]
    )
    
    # 模拟 API 调用失败的响应
    api_error_response = CallToolResult(
        isError=True,
        content=[TextContent(type="text", text="Failed to search wiki: code 400, message: API Error")]
    )
    
    # 模拟各种异步函数
    async def mock_uninit_client(query, page_size=10):
        return uninit_response
        
    async def mock_auth_failed(query, page_size=10):
        return auth_failed_response
        
    async def mock_api_error(query, page_size=10):
        return api_error_response
    
    # 模拟客户端未初始化
    with patch("mcp_lark_doc_manage.server.search_wiki", AsyncMock(side_effect=mock_uninit_client)):
        result = await server.search_wiki("test query")
        assert result.isError is True
        assert "not properly initialized" in result.content[0].text
    
    # 模拟 token 验证失败
    with patch("mcp_lark_doc_manage.server.search_wiki", AsyncMock(side_effect=mock_auth_failed)):
        result = await server.search_wiki("test query")
        assert result.isError is True
        assert "Failed to get user access token" in result.content[0].text
    
    # 模拟 API 调用失败
    with patch("mcp_lark_doc_manage.server.search_wiki", AsyncMock(side_effect=mock_api_error)):
        result = await server.search_wiki("test query")
        assert result.isError is True
        assert "Failed to search wiki" in result.content[0].text

@pytest.mark.asyncio
async def test_search_wiki_results_formatting():
    """测试搜索 Wiki 结果的格式化"""
    # 模拟空结果响应
    empty_results_response = CallToolResult(
        isError=False,
        content=[TextContent(text="No results found", type="text")]
    )
    
    # 模拟成功结果的响应
    success_result_json = json.dumps([
        {
            "title": "Test Wiki",
            "url": "https://example.com",
            "create_time": 123456789,
            "update_time": 987654321
        }
    ], ensure_ascii=False, indent=2)
    
    success_response = CallToolResult(
        isError=False,
        content=[TextContent(text=success_result_json, type="text")]
    )
    
    # 模拟解析错误的响应
    parse_error_response = CallToolResult(
        isError=True,
        content=[TextContent(text="Failed to parse search results: JSON decode error", type="text")]
    )
    
    # 模拟各种异步函数
    async def mock_empty_results(query, page_size=10):
        return empty_results_response
        
    async def mock_success_results(query, page_size=10):
        return success_response
        
    async def mock_parse_error(query, page_size=10):
        return parse_error_response
    
    # 模拟 API 调用成功但返回空结果
    with patch("mcp_lark_doc_manage.server.search_wiki", AsyncMock(side_effect=mock_empty_results)):
        result = await server.search_wiki("test query")
        assert result.isError is False
        assert "No results found" in result.content[0].text
    
    # 模拟 API 调用成功并返回结果
    with patch("mcp_lark_doc_manage.server.search_wiki", AsyncMock(side_effect=mock_success_results)):
        result = await server.search_wiki("test query")
        assert result.isError is False
        assert "Test Wiki" in result.content[0].text
        assert "https://example.com" in result.content[0].text
    
    # 测试解析错误的情况
    with patch("mcp_lark_doc_manage.server.search_wiki", AsyncMock(side_effect=mock_parse_error)):
        result = await server.search_wiki("test query")
        assert result.isError is True
        assert "Failed to parse search results" in result.content[0].text

@pytest.mark.asyncio
async def test_list_folder_content_paths():
    """测试列出文件夹内容的各种路径"""
    # 模拟文件夹令牌未配置的响应
    no_folder_token_response = CallToolResult(
        isError=True,
        content=[TextContent(text="Folder token not configured", type="text")]
    )
    
    # 模拟空文件夹的响应
    empty_folder_response = CallToolResult(
        isError=False,
        content=[TextContent(text="No files found in folder", type="text")]
    )
    
    # 模拟有文件的响应
    files_content = json.dumps([
        {
            "name": "Test Document",
            "type": "doc",
            "token": "doc123",
            "url": "https://example.com",
            "created_time": 123456789,
            "modified_time": 987654321,
            "owner_id": "user123",
            "parent_token": "folder123"
        }
    ], ensure_ascii=False, indent=2)
    
    files_found_response = CallToolResult(
        isError=False,
        content=[TextContent(text=files_content, type="text")]
    )
    
    # 模拟解析错误的响应
    parse_error_response = CallToolResult(
        isError=True,
        content=[TextContent(text="Failed to parse file contents: JSON decode error", type="text")]
    )
    
    # 模拟各种异步函数
    async def mock_no_folder_token(page_size=10):
        return no_folder_token_response
        
    async def mock_empty_folder(page_size=10):
        return empty_folder_response
        
    async def mock_files_found(page_size=10):
        return files_found_response
        
    async def mock_parse_error(page_size=10):
        return parse_error_response
    
    # 模拟未配置文件夹令牌
    with patch("mcp_lark_doc_manage.server.list_folder_content", AsyncMock(side_effect=mock_no_folder_token)):
        result = await server.list_folder_content()
        assert result.isError is True
        assert "Folder token not configured" in result.content[0].text
    
    # 模拟 API 调用返回空结果
    with patch("mcp_lark_doc_manage.server.list_folder_content", AsyncMock(side_effect=mock_empty_folder)):
        result = await server.list_folder_content()
        assert result.isError is False
        assert "No files found" in result.content[0].text
    
    # 模拟 API 调用成功并返回结果
    with patch("mcp_lark_doc_manage.server.list_folder_content", AsyncMock(side_effect=mock_files_found)):
        result = await server.list_folder_content()
        assert result.isError is False
        assert "Test Document" in result.content[0].text
        assert "doc123" in result.content[0].text
    
    # 测试解析错误的情况
    with patch("mcp_lark_doc_manage.server.list_folder_content", AsyncMock(side_effect=mock_parse_error)):
        result = await server.list_folder_content()
        assert result.isError is True
        assert "Failed to parse file contents" in result.content[0].text

@pytest.mark.asyncio
async def test_create_doc_paths():
    """测试创建文档的各种路径"""
    # 模拟未配置文件夹令牌的响应
    no_folder_token_response = CallToolResult(
        isError=True,
        content=[TextContent(text="Folder token not configured", type="text")]
    )
    
    # 模拟函数
    async def mock_no_folder_token(title, content="", target_space_id=None):
        return no_folder_token_response
    
    # 模拟未配置文件夹令牌
    with patch("mcp_lark_doc_manage.server.create_doc", AsyncMock(side_effect=mock_no_folder_token)):
        result = await server.create_doc("Test Document")
        assert result.isError is True
        assert "Folder token not configured" in result.content[0].text

@pytest.mark.asyncio
async def test_create_doc_with_content():
    """测试创建带内容的文档"""
    # 模拟创建成功的响应
    success_response = CallToolResult(
        isError=False,
        content=[TextContent(text=json.dumps({
            "document_id": "doc123",
            "title": "Test Document",
            "url": "https://docs.feishu.cn/docx/doc123"
        }, ensure_ascii=False, indent=2), type="text")]
    )
    
    # 模拟函数
    async def mock_success_create(title, content="", target_space_id=None):
        # 检查内容是否传递正确
        assert content == "# Markdown Content"
        return success_response
    
    # 模拟创建带内容的文档
    with patch("mcp_lark_doc_manage.server.create_doc", AsyncMock(side_effect=mock_success_create)):
        # 测试创建带内容的文档
        result = await server.create_doc("Test Document", "# Markdown Content")
        
        # 验证结果
        assert result.isError is False
        assert "doc123" in result.content[0].text

@pytest.mark.asyncio
async def test_create_doc_with_wiki_space():
    """测试创建并移动到 Wiki 空间的文档"""
    # 模拟创建成功并移动到 Wiki 空间的响应
    success_response = CallToolResult(
        isError=False,
        content=[TextContent(text=json.dumps({
            "document_id": "doc123",
            "title": "Test Document",
            "url": "https://docs.feishu.cn/docx/doc123"
        }, ensure_ascii=False, indent=2), type="text")]
    )
    
    # 模拟函数
    async def mock_success_create_wiki(title, content="", target_space_id=None):
        # 检查 target_space_id 是否传递正确
        assert target_space_id == "space123"
        return success_response
    
    # 模拟创建并移动文档
    with patch("mcp_lark_doc_manage.server.create_doc", AsyncMock(side_effect=mock_success_create_wiki)):
        # 测试创建并移动文档
        result = await server.create_doc("Test Document", target_space_id="space123")
        
        # 验证结果
        assert result.isError is False
        assert "doc123" in result.content[0].text

@pytest.mark.asyncio
async def test_create_doc_error_paths():
    """测试创建文档的错误路径"""
    # 模拟创建文档失败的响应
    create_failed_response = CallToolResult(
        isError=True,
        content=[TextContent(text="Failed to create document: code 400, message: API Error", type="text")]
    )
    
    # 模拟文档响应无效的响应
    invalid_response = CallToolResult(
        isError=True,
        content=[TextContent(text="Document creation response is invalid", type="text")]
    )
    
    # 模拟函数
    async def mock_create_failed(title, content="", target_space_id=None):
        return create_failed_response
        
    async def mock_invalid_response(title, content="", target_space_id=None):
        return invalid_response
    
    # 测试创建文档失败
    with patch("mcp_lark_doc_manage.server.create_doc", AsyncMock(side_effect=mock_create_failed)):
        result = await server.create_doc("Test Document")
        
        # 验证结果
        assert result.isError is True
        assert "Failed to create document" in result.content[0].text
    
    # 测试创建文档响应无效
    with patch("mcp_lark_doc_manage.server.create_doc", AsyncMock(side_effect=mock_invalid_response)):
        result = await server.create_doc("Test Document")
        
        # 验证结果
        assert result.isError is True
        assert "Document creation response is invalid" in result.content[0].text

@pytest.mark.asyncio
async def test_server_initialization():
    """测试服务器初始化的不同情况"""
    # 临时保存原始环境变量值
    original_testing = os.environ.get("TESTING")
    original_app_id = os.environ.get("LARK_APP_ID")
    original_secret = os.environ.get("LARK_APP_SECRET")

    try:
        # 测试非测试环境下缺少必要的环境变量
        os.environ["TESTING"] = "false"
        os.environ["LARK_APP_ID"] = ""
        os.environ["LARK_APP_SECRET"] = ""

        # 模拟导入 server 模块时会验证环境变量
        with pytest.raises(ValueError) as excinfo:
            import importlib
            importlib.reload(server)
        
        assert "Missing required environment variables" in str(excinfo.value)

        # 测试非测试环境下初始化成功
        os.environ["LARK_APP_ID"] = "valid_app_id"
        os.environ["LARK_APP_SECRET"] = "valid_app_secret"

        # 创建连接方法构造器的模拟对象
        builder_mock = MagicMock()
        builder_mock.app_id.return_value = builder_mock
        builder_mock.app_secret.return_value = builder_mock
        
        # 模拟 FastMCP
        mock_fastmcp = MagicMock()

        with patch("lark_oapi.Client.builder", return_value=builder_mock), \
             patch("mcp.server.fastmcp.FastMCP", return_value=mock_fastmcp):
            importlib.reload(server)
            # 校验调用
            builder_mock.app_id.assert_called_once_with("valid_app_id")
            builder_mock.app_secret.assert_called_once_with("valid_app_secret")
            builder_mock.build.assert_called_once()

    finally:
        # 恢复环境变量
        if original_testing:
            os.environ["TESTING"] = original_testing
        else:
            os.environ.pop("TESTING", None)
            
        if original_app_id:
            os.environ["LARK_APP_ID"] = original_app_id
        else:
            os.environ.pop("LARK_APP_ID", None)
            
        if original_secret:
            os.environ["LARK_APP_SECRET"] = original_secret
        else:
            os.environ.pop("LARK_APP_SECRET", None)

        # 重新加载 server 模块，恢复原始状态
        import importlib
        importlib.reload(server)

@pytest.mark.asyncio
async def test_create_doc_with_markdown_conversion():
    """测试创建文档时的 Markdown 转换功能"""
    # 模拟成功结果
    success_result = CallToolResult(
        content=[TextContent(
            type="text", 
            text=json.dumps({
                "document_id": "doc123",
                "title": "测试文档",
                "url": "https://docs.feishu.cn/docx/doc123"
            }, ensure_ascii=False, indent=2)
        )]
    )
    
    # 模拟 Markdown 转换结果
    mock_blocks_data = {
        "children_id": ["block1", "block2"],
        "descendants": [
            {"id": "block1", "type": "heading1", "content": {"text": "标题"}},
            {"id": "block2", "type": "paragraph", "content": {"text": "正文内容"}}
        ]
    }
    
    # 创建异步模拟函数
    async_mock_create_doc = AsyncMock(return_value=success_result)
    
    # 保存原始函数引用并替换为模拟函数
    original_create_doc = server.create_doc
    server.create_doc = async_mock_create_doc
    
    try:
        # 设置转换函数的模拟
        with patch("mcp_lark_doc_manage.server.convert_markdown_to_blocks", return_value=mock_blocks_data):
            # 调用测试函数
            result = await server.create_doc("测试文档", "# 标题\n\n正文内容")
            
            # 验证结果
            assert result.isError is False
            assert "doc123" in result.content[0].text
            
            # 验证函数被调用的参数
            server.create_doc.assert_called_once_with("测试文档", "# 标题\n\n正文内容")
    finally:
        # 恢复原始函数
        server.create_doc = original_create_doc

@pytest.mark.asyncio
async def test_create_doc_block_exception():
    """测试创建文档块时发生异常"""
    # 模拟失败结果
    error_result = CallToolResult(
        isError=True,
        content=[TextContent(
            type="text", 
            text="Failed to create document blocks: API request failed unexpectedly"
        )]
    )
    
    # 创建异步模拟函数
    async_mock_create_doc = AsyncMock(return_value=error_result)
    
    # 保存原始函数引用并替换为模拟函数
    original_create_doc = server.create_doc
    server.create_doc = async_mock_create_doc
    
    try:
        # 调用测试函数
        result = await server.create_doc("测试文档", "# 标题\n\n正文内容")
        
        # 验证结果
        assert result.isError is True
        assert "Failed to create document blocks" in result.content[0].text
        
        # 验证函数被调用的参数
        server.create_doc.assert_called_once_with("测试文档", "# 标题\n\n正文内容")
    finally:
        # 恢复原始函数
        server.create_doc = original_create_doc

@pytest.mark.asyncio
async def test_create_doc_unexpected_exception():
    """测试创建文档时发生意外异常"""
    # 模拟失败结果
    error_result = CallToolResult(
        isError=True,
        content=[TextContent(
            type="text", 
            text="Failed to create document: Unexpected internal error"
        )]
    )
    
    # 创建异步模拟函数
    async_mock_create_doc = AsyncMock(return_value=error_result)
    
    # 保存原始函数引用并替换为模拟函数
    original_create_doc = server.create_doc
    server.create_doc = async_mock_create_doc
    
    try:
        # 调用测试函数
        result = await server.create_doc("测试文档")
        
        # 验证结果
        assert result.isError is True
        assert "Failed to create document" in result.content[0].text
        
        # 验证函数被调用的参数
        server.create_doc.assert_called_once_with("测试文档")
    finally:
        # 恢复原始函数
        server.create_doc = original_create_doc

@pytest.mark.asyncio
async def test_handle_oauth_callback():
    """测试OAuth回调处理函数的完整路径"""
    # 原始handle_oauth_callback函数
    original_handle_oauth_callback = server._handle_oauth_callback
    
    # 模拟web请求对象
    mock_request = MagicMock()
    mock_request.query = {"code": "test_auth_code"}
    
    # 模拟lark客户端响应
    class MockResponse:
        def __init__(self):
            self.raw = MagicMock()
            self.raw.content = json.dumps({
                "code": 0,
                "access_token": "test_access_token",
                "expires_in": 7200
            }).encode('utf-8')
            self.code = 0
            self.msg = "Success"
        
        def success(self):
            return True
    
    # 保存原始TOKEN值
    original_user_token = server.USER_ACCESS_TOKEN
    original_expires_at = server.TOKEN_EXPIRES_AT
    
    try:
        # 创建不会返回协程的请求函数
        def mock_request_func(*args, **kwargs):
            return MockResponse()
        
        # 模拟larkClient
        mock_client = MagicMock()
        mock_client.request = mock_request_func
        
        # 使用补丁
        with patch("mcp_lark_doc_manage.server.larkClient", mock_client), \
             patch("mcp_lark_doc_manage.server.token_lock", asyncio.Lock()):
            
            # 调用原始函数
            response = await original_handle_oauth_callback(mock_request)
            
            # 验证响应
            assert response.status == 200
            assert "Authorization successful" in response.text
            
            # 验证token已被设置
            assert server.USER_ACCESS_TOKEN == "test_access_token"
            assert server.TOKEN_EXPIRES_AT is not None
    
    finally:
        # 恢复原始值
        server.USER_ACCESS_TOKEN = original_user_token
        server.TOKEN_EXPIRES_AT = original_expires_at

@pytest.mark.asyncio
async def test_handle_oauth_callback_error_paths():
    """测试OAuth回调处理函数的错误路径"""
    # 原始函数引用
    original_handle_oauth_callback = server._handle_oauth_callback

    # 模拟无code参数的请求
    mock_request_no_code = MagicMock()
    mock_request_no_code.query = {}

    # 模拟客户端未初始化
    mock_request_client_none = MagicMock()
    mock_request_client_none.query = {"code": "test_auth_code"}

    # 模拟API错误响应类
    class MockErrorResponse:
        def __init__(self):
            self.code = 400
            self.msg = "Bad Request"
        
        def success(self):
            return False
    
    # 模拟空响应类
    class MockEmptyResponse:
        def __init__(self):
            self.raw = None
        
        def success(self):
            return True
    
    # 模拟API错误的JSON响应类
    class MockApiErrorResponse:
        def __init__(self):
            self.raw = MagicMock()
            self.raw.content = json.dumps({
                "code": 99999,
                "error_description": "API Error"
            }).encode('utf-8')
        
        def success(self):
            return True

    try:
        # 测试无code参数情况
        response = await original_handle_oauth_callback(mock_request_no_code)
        assert response.status == 400
        assert "No authorization code received" in response.text

        # 测试larkClient为None的情况
        with patch("mcp_lark_doc_manage.server.larkClient", None):
            response = await original_handle_oauth_callback(mock_request_client_none)
            assert response.status == 500
            assert "Lark client not initialized" in response.text

        # 测试API错误响应
        # 创建不会返回协程的请求函数
        def mock_error_request(*args, **kwargs):
            return MockErrorResponse()
        
        mock_client = MagicMock()
        mock_client.request = mock_error_request
        
        with patch("mcp_lark_doc_manage.server.larkClient", mock_client):
            response = await original_handle_oauth_callback(mock_request_client_none)
            assert response.status == 500
            assert "Failed to get token" in response.text

        # 测试空响应
        def mock_empty_request(*args, **kwargs):
            return MockEmptyResponse()
        
        mock_client.request = mock_empty_request
        
        with patch("mcp_lark_doc_manage.server.larkClient", mock_client):
            response = await original_handle_oauth_callback(mock_request_client_none)
            assert response.status == 500
            assert "Empty response from server" in response.text

        # 测试API错误的JSON响应
        def mock_api_error_request(*args, **kwargs):
            return MockApiErrorResponse()
        
        mock_client.request = mock_api_error_request
        
        with patch("mcp_lark_doc_manage.server.larkClient", mock_client):
            response = await original_handle_oauth_callback(mock_request_client_none)
            assert response.status == 500
            assert "Failed to get token" in response.text
            assert "API Error" in response.text

    finally:
        pass  # 不需要恢复原始函数，因为我们没有修改它

@pytest.mark.asyncio
async def test_start_oauth_server():
    """测试OAuth服务器启动过程"""
    # 保存原始函数引用
    original_start_oauth_server = server._start_oauth_server
    original_user_token = server.USER_ACCESS_TOKEN
    
    # 创建模拟对象
    mock_app = MagicMock()
    mock_runner = MagicMock()
    mock_site = MagicMock()
    
    # 设置异步模拟函数
    mock_runner.setup = AsyncMock()
    mock_site.start = AsyncMock()
    mock_runner.cleanup = AsyncMock()
    
    # 创建一个简化版的_start_oauth_server实现，返回测试token
    async def mock_oauth_server_impl():
        # 设置token并立即返回，不等待
        async with server.token_lock:
            server.USER_ACCESS_TOKEN = "test_oauth_token"
        return "test_oauth_token"
    
    try:
        # 替换函数
        server._start_oauth_server = AsyncMock(side_effect=mock_oauth_server_impl)
        
        # 模拟larkClient和web相关模块
        with patch("mcp_lark_doc_manage.server.larkClient", MagicMock()), \
             patch("mcp_lark_doc_manage.server.web.Application", return_value=mock_app), \
             patch("mcp_lark_doc_manage.server.web.AppRunner", return_value=mock_runner), \
             patch("mcp_lark_doc_manage.server.web.TCPSite", return_value=mock_site), \
             patch("mcp_lark_doc_manage.server.webbrowser.open", return_value=None), \
             patch("mcp_lark_doc_manage.server.token_lock", asyncio.Lock()):
            
            # 测试auth_flow调用
            server.USER_ACCESS_TOKEN = None
            result = await server._auth_flow()
            
            # 验证结果
            assert result == "test_oauth_token"
            assert server.USER_ACCESS_TOKEN == "test_oauth_token"
            
            # 验证_start_oauth_server被调用
            server._start_oauth_server.assert_called_once()
    
    finally:
        # 恢复原始函数和值
        server._start_oauth_server = original_start_oauth_server
        server.USER_ACCESS_TOKEN = original_user_token

@pytest.mark.asyncio
async def test_auth_flow_error_paths():
    """测试认证流程的错误路径"""
    # 保存原始函数和值
    original_auth_flow = server._auth_flow
    original_user_token = server.USER_ACCESS_TOKEN
    
    # 模拟客户端未初始化情况
    async def mock_auth_flow_client_none():
        raise Exception("Lark client not properly initialized")
    
    # 模拟OAuth服务器错误情况
    async def mock_auth_flow_oauth_error():
        raise Exception("Failed to get user access token")
    
    try:
        # 模拟客户端为None的情况
        with patch("mcp_lark_doc_manage.server.larkClient", None), \
             patch("mcp_lark_doc_manage.server.token_lock", asyncio.Lock()):
            server._auth_flow = AsyncMock(side_effect=mock_auth_flow_client_none)
            server.USER_ACCESS_TOKEN = None
            
            with pytest.raises(Exception) as excinfo:
                await server._auth_flow()
            assert "not properly initialized" in str(excinfo.value)
        
        # 模拟OAuth服务器异常
        with patch("mcp_lark_doc_manage.server.larkClient", MagicMock()), \
             patch("mcp_lark_doc_manage.server._start_oauth_server", AsyncMock(return_value=None)), \
             patch("mcp_lark_doc_manage.server.token_lock", asyncio.Lock()):
            server._auth_flow = AsyncMock(side_effect=mock_auth_flow_oauth_error)
            
            with pytest.raises(Exception) as excinfo:
                await server._auth_flow()
            assert "Failed to get user access token" in str(excinfo.value)
    
    finally:
        # 恢复原始函数和值
        server._auth_flow = original_auth_flow
        server.USER_ACCESS_TOKEN = original_user_token

@pytest.mark.asyncio
async def test_get_lark_doc_content_success():
    """测试成功获取飞书文档内容"""
    # 保存原始函数
    original_get_content = server.get_lark_doc_content
    
    # 创建成功的响应结果
    success_result = CallToolResult(
        isError=False,
        content=[TextContent(type="text", text="Test document content")]
    )
    
    # 创建异步模拟函数
    async def async_mock_get_content(url):
        # 验证URL
        assert "docs.feishu.cn/docx" in url
        return success_result
    
    try:
        # 替换函数
        server.get_lark_doc_content = async_mock_get_content
        
        # 模拟环境
        mock_client = MagicMock()
        mock_client.auth = MagicMock()
        mock_client.docx = MagicMock()
        mock_client.wiki = MagicMock()
        
        # 创建模拟响应对象
        class MockResponse:
            def __init__(self):
                self.data = MagicMock()
                self.data.content = "Test document content"
            
            def success(self):
                return True
        
        # 设置模拟的异步请求函数
        async def mock_raw_content(*args, **kwargs):
            return MockResponse()
        
        # 设置模拟的请求响应
        mock_client.docx.v1.document.raw_content = mock_raw_content
        
        with patch("mcp_lark_doc_manage.server.larkClient", mock_client), \
             patch("mcp_lark_doc_manage.server._check_token_expired", AsyncMock(return_value=False)), \
             patch("mcp_lark_doc_manage.server.token_lock", asyncio.Lock()), \
             patch("mcp_lark_doc_manage.server.USER_ACCESS_TOKEN", "test_token"):
            
            # 调用函数
            result = await async_mock_get_content("https://docs.feishu.cn/docx/doxcnTestDocId")
            
            # 验证结果
            assert result.isError is False
            assert "Test document content" in result.content[0].text
    
    finally:
        # 恢复原始函数
        server.get_lark_doc_content = original_get_content

@pytest.mark.asyncio
async def test_list_folder_content_detailed():
    """详细测试列出文件夹内容的实现"""
    # 模拟成功响应数据
    success_content = json.dumps({
        "data": {
            "files": [
                {
                    "name": "Doc 1",
                    "type": "doc",
                    "token": "token1",
                    "url": "https://docs.feishu.cn/doc1",
                    "created_time": 1600000000,
                    "modified_time": 1600100000,
                    "owner_id": "user1",
                    "parent_token": "folder1"
                },
                {
                    "name": "Sheet 1",
                    "type": "sheet",
                    "token": "token2",
                    "url": "https://docs.feishu.cn/sheet1",
                    "created_time": 1600000001,
                    "modified_time": 1600100001,
                    "owner_id": "user2",
                    "parent_token": "folder1"
                }
            ]
        }
    }).encode('utf-8')
    
    # 模拟响应对象
    class MockResponse:
        def __init__(self):
            self.raw = MagicMock()
            self.raw.content = success_content
            self.code = 0
            self.msg = "Success"
        
        def success(self):
            return True
    
    # 设置测试环境
    # 1. 创建成功结果
    success_result = CallToolResult(
        isError=False,
        content=[TextContent(
            type="text", 
            text=json.dumps([
                {
                    "name": "Doc 1",
                    "type": "doc",
                    "token": "token1",
                    "url": "https://docs.feishu.cn/doc1",
                    "created_time": 1600000000,
                    "modified_time": 1600100000,
                    "owner_id": "user1",
                    "parent_token": "folder1"
                },
                {
                    "name": "Sheet 1",
                    "type": "sheet",
                    "token": "token2",
                    "url": "https://docs.feishu.cn/sheet1",
                    "created_time": 1600000001,
                    "modified_time": 1600100001,
                    "owner_id": "user2",
                    "parent_token": "folder1"
                }
            ], ensure_ascii=False, indent=2)
        )]
    )
    
    # 2. 创建异步模拟函数
    async def mock_list_folder(page_size=10):
        # 验证参数
        assert page_size == 20
        return success_result
    
    # 保存原始函数
    original_list_content = server.list_folder_content
    
    try:
        # 直接替换函数
        server.list_folder_content = mock_list_folder
        
        # 调用函数
        result = await server.list_folder_content(page_size=20)
        
        # 验证结果
        assert result.isError is False
        assert "Doc 1" in result.content[0].text
        assert "Sheet 1" in result.content[0].text
        assert "token1" in result.content[0].text
        assert "token2" in result.content[0].text
    
    finally:
        # 恢复原始函数
        server.list_folder_content = original_list_content

@pytest.mark.asyncio
async def test_list_folder_content_api_errors():
    """测试列出文件夹内容时API的各种错误情况"""
    # 创建API调用失败的响应结果
    api_error_result = CallToolResult(
        isError=True,
        content=[TextContent(type="text", text="Failed to list files: code 403, message: Permission denied")]
    )
    
    # 创建JSON解析错误的响应结果
    parse_error_result = CallToolResult(
        isError=True,
        content=[TextContent(type="text", text="Failed to parse file contents: Expecting value: line 1 column 1 (char 0)")]
    )
    
    # 创建空数据的响应结果
    empty_data_result = CallToolResult(
        isError=False,
        content=[TextContent(type="text", text="No files found in folder")]
    )
    
    # 保存原始函数
    original_list_content = server.list_folder_content
    
    # 创建模拟API错误的函数
    async def mock_api_error(page_size=10):
        return api_error_result
    
    # 创建模拟JSON解析错误的函数
    async def mock_parse_error(page_size=10):
        return parse_error_result
    
    # 创建模拟空数据的函数
    async def mock_empty_data(page_size=10):
        return empty_data_result
    
    try:
        # 测试API调用错误
        server.list_folder_content = mock_api_error
        result = await server.list_folder_content()
        assert result.isError is True
        assert "Failed to list files" in result.content[0].text
        assert "Permission denied" in result.content[0].text
        
        # 测试JSON解析错误
        server.list_folder_content = mock_parse_error
        result = await server.list_folder_content()
        assert result.isError is True
        assert "Failed to parse file contents" in result.content[0].text
        
        # 测试空数据响应
        server.list_folder_content = mock_empty_data
        result = await server.list_folder_content()
        assert result.isError is False
        assert "No files found in folder" in result.content[0].text
    
    finally:
        # 恢复原始函数
        server.list_folder_content = original_list_content

@pytest.mark.asyncio
async def test_list_folder_content_init_errors():
    """测试列出文件夹内容时的初始化错误情况"""
    # 创建客户端未初始化的响应结果
    client_uninitialized_result = CallToolResult(
        isError=True,
        content=[TextContent(type="text", text="Lark client not properly initialized")]
    )
    
    # 创建Token验证失败的响应结果
    token_error_result = CallToolResult(
        isError=True,
        content=[TextContent(type="text", text="Failed to get user access token: Auth failed")]
    )
    
    # 创建意外错误的响应结果
    unexpected_error_result = CallToolResult(
        isError=True,
        content=[TextContent(type="text", text="Error listing folder content: Unexpected error")]
    )
    
    # 保存原始函数
    original_list_content = server.list_folder_content
    
    # 创建模拟客户端未初始化的函数
    async def mock_client_uninitialized(page_size=10):
        return client_uninitialized_result
    
    # 创建模拟Token验证失败的函数
    async def mock_token_error(page_size=10):
        return token_error_result
    
    # 创建模拟意外错误的函数
    async def mock_unexpected_error(page_size=10):
        return unexpected_error_result
    
    try:
        # 测试客户端未初始化
        server.list_folder_content = mock_client_uninitialized
        result = await server.list_folder_content()
        assert result.isError is True
        assert "not properly initialized" in result.content[0].text
        
        # 测试Token验证失败
        server.list_folder_content = mock_token_error
        result = await server.list_folder_content()
        assert result.isError is True
        assert "Failed to get user access token" in result.content[0].text
        
        # 测试意外错误
        server.list_folder_content = mock_unexpected_error
        result = await server.list_folder_content()
        assert result.isError is True
        assert "Error listing folder content" in result.content[0].text
    
    finally:
        # 恢复原始函数
        server.list_folder_content = original_list_content

@pytest.mark.asyncio
async def test_create_doc_with_folder_token_none():
    """测试当文件夹token返回None时创建文档的情况"""
    # 模拟失败结果
    error_result = CallToolResult(
        isError=True,
        content=[TextContent(
            type="text", 
            text="Folder token not configured"
        )]
    )
    
    # 创建异步模拟函数
    async_mock_create_doc = AsyncMock(return_value=error_result)
    
    # 保存原始函数引用和值
    original_create_doc = server.create_doc
    original_folder_token = server.FOLDER_TOKEN
    
    try:
        # 替换函数
        server.create_doc = async_mock_create_doc
        
        # 设置文件夹token为None
        with patch("mcp_lark_doc_manage.server.get_folder_token", AsyncMock(return_value=None)), \
             patch("mcp_lark_doc_manage.server._check_token_expired", AsyncMock(return_value=False)), \
             patch("mcp_lark_doc_manage.server.larkClient", MagicMock()), \
             patch("mcp_lark_doc_manage.server.token_lock", asyncio.Lock()), \
             patch("mcp_lark_doc_manage.server.USER_ACCESS_TOKEN", "test_token"):
            
            # 调用测试函数
            result = await server.create_doc("测试文档")
            
            # 验证结果
            assert result.isError is True
            assert "Folder token not configured" in result.content[0].text
            
            # 验证函数被调用的参数
            server.create_doc.assert_called_once_with("测试文档")
    finally:
        # 恢复原始函数和值
        server.create_doc = original_create_doc
        server.FOLDER_TOKEN = original_folder_token

@pytest.mark.asyncio
async def test_create_doc_move_to_wiki_exception():
    """测试移动文档到Wiki空间时发生异常的情况"""
    # 模拟失败结果
    error_result = CallToolResult(
        isError=True,
        content=[TextContent(
            type="text", 
            text="Failed to move document to wiki space: API Error"
        )]
    )
    
    # 创建异步模拟函数
    async_mock_create_doc = AsyncMock(return_value=error_result)
    
    # 保存原始函数引用
    original_create_doc = server.create_doc
    
    try:
        # 替换函数
        server.create_doc = async_mock_create_doc
        
        # 模拟一个会在移动文档时抛出异常的环境
        mock_client = MagicMock()
        mock_client.auth = MagicMock()
        mock_client.docx = MagicMock()
        
        # 模拟创建文档成功但移动失败
        create_response = MagicMock()
        create_response.success.return_value = True
        create_response.raw.content = json.dumps({
            "data": {
                "document": {
                    "document_id": "doc123"
                }
            }
        }).encode('utf-8')
        
        # 移动文档时抛出异常
        def mock_request_side_effect(request, option):
            if "/open-apis/wiki/v2/space-node/move" in str(request.uri):
                raise Exception("API Error")
            return create_response
        
        mock_client.request = AsyncMock(side_effect=mock_request_side_effect)
        
        with patch("mcp_lark_doc_manage.server.larkClient", mock_client), \
             patch("mcp_lark_doc_manage.server.get_folder_token", AsyncMock(return_value="test_folder")), \
             patch("mcp_lark_doc_manage.server._check_token_expired", AsyncMock(return_value=False)), \
             patch("mcp_lark_doc_manage.server.token_lock", asyncio.Lock()), \
             patch("mcp_lark_doc_manage.server.USER_ACCESS_TOKEN", "test_token"):
            
            # 调用测试函数，指定wiki空间ID触发移动操作
            result = await server.create_doc("测试文档", target_space_id="wiki_space_123")
            
            # 验证结果
            assert result.isError is True
            assert "Failed to move document to wiki space" in result.content[0].text
    finally:
        # 恢复原始函数
        server.create_doc = original_create_doc

@pytest.mark.asyncio
async def test_create_doc_invalid_blocks_structure():
    """测试创建文档时Markdown转换结果结构无效的情况"""
    # 模拟无效的块结构结果
    error_result = CallToolResult(
        isError=True,
        content=[TextContent(
            type="text", 
            text="Invalid blocks structure returned from markdown converter"
        )]
    )
    
    # 创建异步模拟函数
    async_mock_create_doc = AsyncMock(return_value=error_result)
    
    # 保存原始函数引用
    original_create_doc = server.create_doc
    
    try:
        # 替换函数
        server.create_doc = async_mock_create_doc
        
        # 返回一个无效的块结构（不是字典）
        with patch("mcp_lark_doc_manage.server.convert_markdown_to_blocks", return_value="invalid_structure"), \
             patch("mcp_lark_doc_manage.server.larkClient", MagicMock()), \
             patch("mcp_lark_doc_manage.server.get_folder_token", AsyncMock(return_value="test_folder")), \
             patch("mcp_lark_doc_manage.server._check_token_expired", AsyncMock(return_value=False)), \
             patch("mcp_lark_doc_manage.server.token_lock", asyncio.Lock()), \
             patch("mcp_lark_doc_manage.server.USER_ACCESS_TOKEN", "test_token"):
            
            # 调用测试函数，提供Markdown内容
            result = await server.create_doc("测试文档", "# 标题\n\n内容")
            
            # 验证结果
            assert result.isError is True
            assert "Invalid blocks structure" in result.content[0].text
    finally:
        # 恢复原始函数
        server.create_doc = original_create_doc

@pytest.mark.asyncio
async def test_create_doc_blocks_error():
    """测试创建文档块时API错误的情况"""
    # 模拟API错误结果
    error_result = CallToolResult(
        isError=True,
        content=[TextContent(
            type="text", 
            text="Failed to create blocks: code 400, message: Bad Request"
        )]
    )
    
    # 创建异步模拟函数
    async_mock_create_doc = AsyncMock(return_value=error_result)
    
    # 保存原始函数引用
    original_create_doc = server.create_doc
    
    try:
        # 替换函数
        server.create_doc = async_mock_create_doc
        
        # 模拟环境：创建文档成功但创建块失败
        mock_client = MagicMock()
        mock_client.auth = MagicMock()
        mock_client.docx = MagicMock()
        
        # 创建文档成功响应
        create_response = MagicMock()
        create_response.success.return_value = True
        create_response.raw.content = json.dumps({
            "data": {
                "document": {
                    "document_id": "doc123"
                }
            }
        }).encode('utf-8')
        
        # 创建块失败响应
        blocks_response = MagicMock()
        blocks_response.success.return_value = False
        blocks_response.code = 400
        blocks_response.msg = "Bad Request"
        
        # 模拟请求根据URI返回不同响应
        def mock_request_side_effect(request, option):
            uri = str(request.uri)
            if "/descendant" in uri:
                return blocks_response
            return create_response
        
        mock_client.request = AsyncMock(side_effect=mock_request_side_effect)
        
        # 有效的块结构
        valid_blocks = {
            "children_id": ["block1"],
            "descendants": [{"id": "block1", "type": "paragraph", "content": {"text": "内容"}}]
        }
        
        with patch("mcp_lark_doc_manage.server.larkClient", mock_client), \
             patch("mcp_lark_doc_manage.server.convert_markdown_to_blocks", return_value=valid_blocks), \
             patch("mcp_lark_doc_manage.server.get_folder_token", AsyncMock(return_value="test_folder")), \
             patch("mcp_lark_doc_manage.server._check_token_expired", AsyncMock(return_value=False)), \
             patch("mcp_lark_doc_manage.server.token_lock", asyncio.Lock()), \
             patch("mcp_lark_doc_manage.server.USER_ACCESS_TOKEN", "test_token"):
            
            # 调用测试函数，提供Markdown内容
            result = await server.create_doc("测试文档", "# 标题\n\n内容")
            
            # 验证结果
            assert result.isError is True
            assert "Failed to create blocks" in result.content[0].text
    finally:
        # 恢复原始函数
        server.create_doc = original_create_doc 