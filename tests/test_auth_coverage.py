import pytest
import os
import sys
import asyncio
import json
import time
from unittest.mock import patch, MagicMock, AsyncMock
from aiohttp import web

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入测试模块
import mcp_lark_doc_manage.server as server
from mcp.types import CallToolResult, TextContent

# 所有测试使用 server_test 标记
pytestmark = pytest.mark.server_test

@pytest.mark.asyncio
async def test_auth_flow():
    """测试鉴权流程"""
    # 保存原始值
    original_token = server.USER_ACCESS_TOKEN
    original_expires = server.TOKEN_EXPIRES_AT
    
    auth_code = "test_auth_code"  # 这是 _start_oauth_server 会返回的值
    
    try:
        # 设置测试环境
        server.USER_ACCESS_TOKEN = None
        server.TOKEN_EXPIRES_AT = None
        
        # 模拟 _start_oauth_server 返回授权码
        with patch("mcp_lark_doc_manage.server.larkClient", MagicMock()), \
             patch("mcp_lark_doc_manage.server._start_oauth_server", AsyncMock(return_value=auth_code)):
            # 执行鉴权流程
            result = await server._auth_flow()
            
            # 验证结果 - 函数返回 _start_oauth_server 的结果
            assert result == auth_code
            
            # 验证函数调用
            server._start_oauth_server.assert_called_once()
    finally:
        # 恢复原始值
        server.USER_ACCESS_TOKEN = original_token
        server.TOKEN_EXPIRES_AT = original_expires

@pytest.mark.asyncio
async def test_auth_flow_client_not_initialized():
    """测试鉴权流程中客户端未初始化的情况"""
    # 保存原始值
    original_client = server.larkClient
    
    try:
        # 设置测试环境，模拟客户端未初始化
        server.larkClient = None
        
        # 预期抛出异常
        with pytest.raises(Exception) as excinfo:
            await server._auth_flow()
        
        # 验证异常信息
        assert "Lark client not properly initialized" in str(excinfo.value)
    finally:
        # 恢复原始值
        server.larkClient = original_client

@pytest.mark.asyncio
async def test_auth_flow_no_auth_code():
    """测试鉴权流程中未获取到授权码的情况"""
    # 保存原始值
    original_token = server.USER_ACCESS_TOKEN
    original_expires = server.TOKEN_EXPIRES_AT
    original_ci = os.environ.get('CI')
    original_pytest = os.environ.get('PYTEST_RUNNING')
    
    try:
        # 设置测试环境
        server.USER_ACCESS_TOKEN = None
        server.TOKEN_EXPIRES_AT = None
        
        # 确保CI环境变量被移除，这样_start_oauth_server不会自动生成token
        if 'CI' in os.environ:
            del os.environ['CI']
        if 'PYTEST_RUNNING' in os.environ:
            del os.environ['PYTEST_RUNNING']
        
        # 模拟 _start_oauth_server 返回 None
        with patch("mcp_lark_doc_manage.server.larkClient", MagicMock()), \
             patch("mcp_lark_doc_manage.server._start_oauth_server", AsyncMock(return_value=None)):
            # 预期抛出异常
            with pytest.raises(Exception) as excinfo:
                await server._auth_flow()
            
            # 验证异常信息
            assert "Failed to get user access token" in str(excinfo.value)
    finally:
        # 恢复原始值
        server.USER_ACCESS_TOKEN = original_token
        server.TOKEN_EXPIRES_AT = original_expires
        
        # 恢复环境变量
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
async def test_start_oauth_server():
    """测试 OAuth 服务器启动"""
    # 保存原始值
    original_token = server.USER_ACCESS_TOKEN
    original_ci = os.environ.get('CI')
    original_pytest = os.environ.get('PYTEST_RUNNING')
    
    # 模拟 web 应用、运行器和站点
    mock_app = MagicMock()
    mock_app.router.add_get = MagicMock()
    
    mock_runner = MagicMock()
    mock_runner.setup = AsyncMock()
    mock_runner.cleanup = AsyncMock()
    
    mock_site = MagicMock()
    mock_site.start = AsyncMock()
    
    # 模拟 webbrowser.open
    mock_webbrowser_open = MagicMock()
    
    try:
        # 第一部分：测试CI环境下的行为
        # 设置测试环境
        server.USER_ACCESS_TOKEN = None
        # 设置CI环境变量，模拟CI运行环境
        os.environ['CI'] = 'true'
        os.environ['PYTEST_RUNNING'] = 'true'
        
        # 执行OAuth服务器启动函数
        token = await server._start_oauth_server()
        
        # 在CI环境中，应该直接返回模拟token而不启动服务器
        assert token is not None
        assert "mock_oauth_token" in token
        assert server.USER_ACCESS_TOKEN is not None
        
        # 只有在非CI环境下才测试真正的OAuth服务器行为
        # 如果当前在CI环境中运行，跳过后续测试
        is_real_ci = os.environ.get('CI') == 'true' and 'GITHUB_ACTIONS' in os.environ
        
        if not is_real_ci:
            # 复位环境变量，测试非CI环境
            os.environ.pop('CI', None)
            os.environ.pop('PYTEST_RUNNING', None)
            server.USER_ACCESS_TOKEN = None
            
            # 模拟环境
            with patch("mcp_lark_doc_manage.server.web.Application", return_value=mock_app), \
                 patch("mcp_lark_doc_manage.server.web.AppRunner", return_value=mock_runner), \
                 patch("mcp_lark_doc_manage.server.web.TCPSite", return_value=mock_site), \
                 patch("mcp_lark_doc_manage.server.webbrowser.open", mock_webbrowser_open), \
                 patch("mcp_lark_doc_manage.server.asyncio.sleep", AsyncMock()):
                
                # 模拟设置 token 的任务
                async def set_token_after_delay():
                    # 模拟短暂延迟后设置 token
                    server.USER_ACCESS_TOKEN = "test_token_from_callback"
                
                # 立即执行 token 设置任务
                asyncio.create_task(set_token_after_delay())
                
                # 使用 asyncio.wait_for 设置超时，避免测试无限等待
                token = await asyncio.wait_for(server._start_oauth_server(), timeout=2)
                
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
            os.environ.pop('CI', None) if 'CI' in os.environ else None
        else:
            os.environ['CI'] = original_ci
            
        if original_pytest is None:
            os.environ.pop('PYTEST_RUNNING', None) if 'PYTEST_RUNNING' in os.environ else None
        else:
            os.environ['PYTEST_RUNNING'] = original_pytest

@pytest.mark.asyncio
@pytest.mark.skip(reason="TENANT_ACCESS_TOKEN 不再使用，已迁移到 USER_ACCESS_TOKEN")
async def test_tenant_access_token():
    """测试获取租户访问令牌"""
    # 模拟 API 响应
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.success.return_value = True
    mock_response.data = {
        "tenant_access_token": "test_tenant_token",
        "expire": 7200
    }
    mock_client.auth.v3.tenant_access_token.internal = AsyncMock(return_value=mock_response)
    
    # 保存原始值
    original_token = server.TENANT_ACCESS_TOKEN
    original_env = {
        "LARK_APP_ID": os.environ.get("LARK_APP_ID"),
        "LARK_APP_SECRET": os.environ.get("LARK_APP_SECRET")
    }
    
    try:
        # 设置测试环境
        server.TENANT_ACCESS_TOKEN = None
        os.environ["LARK_APP_ID"] = "test_app_id"
        os.environ["LARK_APP_SECRET"] = "test_app_secret"
        
        with patch("mcp_lark_doc_manage.server.larkClient", mock_client):
            # 执行函数
            await server._get_tenant_access_token()
            
            # 验证结果
            assert server.TENANT_ACCESS_TOKEN == "test_tenant_token"
            
            # 验证函数调用
            mock_client.auth.v3.tenant_access_token.internal.assert_called_once()
    finally:
        # 恢复原始值
        server.TENANT_ACCESS_TOKEN = original_token
        for key, value in original_env.items():
            if value is None:
                if key in os.environ:
                    del os.environ[key]
            else:
                os.environ[key] = value

@pytest.mark.asyncio
@pytest.mark.skip(reason="TENANT_ACCESS_TOKEN 不再使用，已迁移到 USER_ACCESS_TOKEN")
async def test_tenant_access_token_errors():
    """测试获取租户访问令牌的错误处理"""
    # 模拟 API 错误
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.success.return_value = False
    mock_response.code = 401
    mock_response.msg = "App ID or App Secret is incorrect"
    mock_client.auth.v3.tenant_access_token.internal = AsyncMock(return_value=mock_response)
    
    # 保存原始值
    original_token = server.TENANT_ACCESS_TOKEN
    
    try:
        # 设置测试环境
        server.TENANT_ACCESS_TOKEN = None
        
        with patch("mcp_lark_doc_manage.server.larkClient", mock_client), \
             pytest.raises(Exception) as excinfo:
            # 执行函数，预期抛出异常
            await server._get_tenant_access_token()
        
        # 验证异常信息
        assert "Failed to get tenant access token" in str(excinfo.value)
        
        # 模拟响应中缺少令牌
        mock_response.success.return_value = True
        mock_response.data = {}  # 空数据
        
        with patch("mcp_lark_doc_manage.server.larkClient", mock_client), \
             pytest.raises(Exception) as excinfo:
            # 执行函数，预期抛出异常
            await server._get_tenant_access_token()
        
        # 验证异常信息
        assert "Invalid tenant token response" in str(excinfo.value)
    finally:
        # 恢复原始值
        server.TENANT_ACCESS_TOKEN = original_token 