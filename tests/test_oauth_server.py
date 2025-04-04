import pytest
import os
import sys
import asyncio
import json
from unittest.mock import patch, MagicMock, AsyncMock
from aiohttp import web
import webbrowser

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入测试模块
import mcp_lark_doc_manage.server as server
from mcp.types import CallToolResult, TextContent

# 所有测试使用 server_test 标记
pytestmark = pytest.mark.server_test

@pytest.mark.asyncio
async def test_handle_oauth_callback_success():
    """测试 OAuth 回调处理成功的情况"""
    # Mock 请求和响应
    mock_request = MagicMock()
    mock_request.query = {"code": "test_auth_code"}
    
    # Mock Lark client 请求
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.success.return_value = True
    mock_response.raw.content = json.dumps({
        "code": 0,
        "access_token": "test_access_token",
        "expires_in": 7200
    }).encode()
    
    # 注意：真实代码中 request 方法返回的是同步结果，而不是协程
    # 因此这里需要使用 MagicMock 而不是异步函数
    mock_client.request.return_value = mock_response
    
    # 保存原始值
    original_token = server.USER_ACCESS_TOKEN
    original_expires = server.TOKEN_EXPIRES_AT
    
    try:
        # 设置测试环境
        server.USER_ACCESS_TOKEN = None
        server.TOKEN_EXPIRES_AT = None
        
        with patch("mcp_lark_doc_manage.server.larkClient", mock_client):
            # 执行回调处理
            response = await server._handle_oauth_callback(mock_request)
            
            # 验证结果
            assert response.status == 200
            assert "Authorization successful" in response.text
            assert server.USER_ACCESS_TOKEN == "test_access_token"
            assert server.TOKEN_EXPIRES_AT is not None
    finally:
        # 恢复原始值
        server.USER_ACCESS_TOKEN = original_token
        server.TOKEN_EXPIRES_AT = original_expires

@pytest.mark.asyncio
async def test_handle_oauth_callback_no_code():
    """测试 OAuth 回调处理无授权码的情况"""
    # Mock 请求和响应
    mock_request = MagicMock()
    mock_request.query = {}  # 没有 code 参数
    
    # 执行回调处理
    response = await server._handle_oauth_callback(mock_request)
    
    # 验证结果
    assert response.status == 400
    assert "No authorization code received" in response.text

@pytest.mark.asyncio
async def test_handle_oauth_callback_api_error():
    """测试 OAuth 回调处理 API 错误的情况"""
    # Mock 请求和响应
    mock_request = MagicMock()
    mock_request.query = {"code": "test_auth_code"}
    
    # Mock Lark client 请求
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.success.return_value = False
    mock_response.code = 401
    mock_response.msg = "Unauthorized"
    
    # 设置同步返回值
    mock_client.request.return_value = mock_response
    
    with patch("mcp_lark_doc_manage.server.larkClient", mock_client):
        # 执行回调处理
        response = await server._handle_oauth_callback(mock_request)
        
        # 验证结果
        assert response.status == 500
        assert "Failed to get token" in response.text
        assert "401" in response.text

@pytest.mark.asyncio
async def test_handle_oauth_callback_invalid_response():
    """测试 OAuth 回调处理无效响应的情况"""
    # Mock 请求和响应
    mock_request = MagicMock()
    mock_request.query = {"code": "test_auth_code"}
    
    # Mock Lark client 请求
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.success.return_value = True
    mock_response.raw.content = json.dumps({
        "code": 1,  # 非 0 表示错误
        "error_description": "Invalid authorization code"
    }).encode()
    
    # 设置同步返回值
    mock_client.request.return_value = mock_response
    
    with patch("mcp_lark_doc_manage.server.larkClient", mock_client):
        # 执行回调处理
        response = await server._handle_oauth_callback(mock_request)
        
        # 验证结果
        assert response.status == 500
        assert "Failed to get token" in response.text
        assert "Invalid authorization code" in response.text

@pytest.mark.asyncio
async def test_start_oauth_server_with_mocks():
    """测试 OAuth 服务器启动"""
    # 保存原始值
    original_token = server.USER_ACCESS_TOKEN
    original_ci = os.environ.get('CI')
    original_pytest = os.environ.get('PYTEST_RUNNING')
    
    try:
        # 设置测试环境
        server.USER_ACCESS_TOKEN = None
        
        # 检查是否在CI环境中
        is_ci_env = original_ci is not None or original_pytest is not None
        
        # 模拟 web 应用
        mock_app = MagicMock()
        mock_app.router.add_get = MagicMock()
        
        # 模拟 AppRunner
        mock_runner = MagicMock()
        mock_runner.setup = AsyncMock()
        mock_runner.cleanup = AsyncMock()
        
        # 模拟 TCPSite
        mock_site = MagicMock()
        mock_site.start = AsyncMock()
        
        # 模拟 webbrowser 模块
        mock_webbrowser_open = MagicMock()
        
        with patch("mcp_lark_doc_manage.server.web.Application", return_value=mock_app), \
             patch("mcp_lark_doc_manage.server.web.AppRunner", return_value=mock_runner), \
             patch("mcp_lark_doc_manage.server.web.TCPSite", return_value=mock_site), \
             patch("mcp_lark_doc_manage.server.webbrowser.open", mock_webbrowser_open):
            
            # 如果在CI环境中，模拟设置环境变量
            if is_ci_env:
                os.environ['CI'] = 'true'
                os.environ['PYTEST_RUNNING'] = 'true'
                token = await server._start_oauth_server()
                # 在CI环境中应该返回模拟token
                assert token is not None
                assert "mock_oauth_token" in token
            else:
                # 为了避免无限等待，模拟在 2 秒后设置 token
                async def set_token_after_delay():
                    await asyncio.sleep(2)
                    server.USER_ACCESS_TOKEN = "test_token_from_callback"
                
                # 启动后台任务来设置 token
                task = asyncio.create_task(set_token_after_delay())
                
                # 执行函数
                token = await asyncio.wait_for(server._start_oauth_server(), timeout=5)
                
                # 确保任务完成
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                
                # 验证结果
                assert token == "test_token_from_callback"
                
                # 验证函数调用
                mock_app.router.add_get.assert_called_once()
                mock_runner.setup.assert_called_once()
                mock_site.start.assert_called_once()
                mock_webbrowser_open.assert_called_once()
                mock_runner.cleanup.assert_called_once()
    finally:
        # 恢复原始值
        server.USER_ACCESS_TOKEN = original_token
        if original_ci is None:
            if 'CI' in os.environ:
                del os.environ['CI']
        else:
            os.environ['CI'] = original_ci
            
        if original_pytest is None:
            if 'PYTEST_RUNNING' in os.environ:
                del os.environ['PYTEST_RUNNING']
        else:
            os.environ['PYTEST_RUNNING'] = original_pytest

@pytest.mark.asyncio
async def test_oauth_server_timeout():
    """测试 OAuth 服务器超时"""
    # 保存原始值
    original_token = server.USER_ACCESS_TOKEN
    original_ci = os.environ.get('CI')
    original_pytest = os.environ.get('PYTEST_RUNNING')
    
    try:
        # 设置测试环境
        server.USER_ACCESS_TOKEN = None
        
        # 清除CI环境变量确保测试可以运行
        if 'CI' in os.environ:
            del os.environ['CI']
        if 'PYTEST_RUNNING' in os.environ:
            del os.environ['PYTEST_RUNNING']
        
        # 模拟 web 应用、runner 和 site
        mock_app = MagicMock()
        mock_app.router.add_get = MagicMock()
        
        mock_runner = MagicMock()
        mock_runner.setup = AsyncMock()
        mock_runner.cleanup = AsyncMock()
        
        mock_site = MagicMock()
        mock_site.start = AsyncMock()
        
        with patch("mcp_lark_doc_manage.server.web.Application", return_value=mock_app), \
             patch("mcp_lark_doc_manage.server.web.AppRunner", return_value=mock_runner), \
             patch("mcp_lark_doc_manage.server.web.TCPSite", return_value=mock_site), \
             patch("mcp_lark_doc_manage.server.webbrowser.open", MagicMock()), \
             patch("mcp_lark_doc_manage.server.asyncio.get_event_loop") as mock_loop:
            
            # 模拟时间流逝以触发超时
            start_time = 0
            
            def mock_time():
                nonlocal start_time
                start_time += 600  # 每次调用增加 10 分钟
                return start_time
            
            mock_loop.return_value.time = mock_time
            
            # 预期函数会抛出超时异常
            with pytest.raises(TimeoutError) as excinfo:
                await server._start_oauth_server()
            
            # 验证异常信息
            assert "Authorization timeout" in str(excinfo.value)
            
            # 验证函数调用
            mock_runner.cleanup.assert_called_once()
    finally:
        # 恢复原始值
        server.USER_ACCESS_TOKEN = original_token
        if original_ci is None:
            if 'CI' in os.environ:
                del os.environ['CI']
        else:
            os.environ['CI'] = original_ci
            
        if original_pytest is None:
            if 'PYTEST_RUNNING' in os.environ:
                del os.environ['PYTEST_RUNNING']
        else:
            os.environ['PYTEST_RUNNING'] = original_pytest

@pytest.mark.asyncio
async def test_run_oauth_flow_with_mocks():
    """使用 mock 测试完整的 OAuth 流程"""
    # 保存原始值
    original_token = server.USER_ACCESS_TOKEN
    original_expires = server.TOKEN_EXPIRES_AT
    
    try:
        # 设置测试环境
        server.USER_ACCESS_TOKEN = None
        server.TOKEN_EXPIRES_AT = None
        
        # 模拟 _start_oauth_server 直接返回访问令牌
        mock_access_token = "test_access_token"
        
        with patch("mcp_lark_doc_manage.server._start_oauth_server", AsyncMock(return_value=mock_access_token)):
            # 执行函数
            token = await server._auth_flow()
            
            # 验证结果
            assert token == "test_access_token"
            
            # 验证函数调用
            server._start_oauth_server.assert_called_once()
    finally:
        # 恢复原始值
        server.USER_ACCESS_TOKEN = original_token
        server.TOKEN_EXPIRES_AT = original_expires 