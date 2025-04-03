import os
import sys
import pytest
import logging
from unittest.mock import patch, MagicMock

# 设置测试环境变量
os.environ["TESTING"] = "true"
os.environ["OAUTH_PORT"] = "9997"
os.environ["LARK_APP_ID"] = "test_app_id"
os.environ["LARK_APP_SECRET"] = "test_app_secret"
os.environ["FOLDER_TOKEN"] = "test_folder_token"

# 导入模块
from importlib import reload
import mcp_lark_doc_manage
from mcp_lark_doc_manage import main

def test_main_success():
    """Test successful main execution"""
    with patch("mcp_lark_doc_manage.server.mcp") as mock_mcp:
        mock_mcp.run.return_value = None
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
        mock_mcp.run.assert_called_once_with(transport="stdio")

def test_file_not_found_handling():
    """直接测试文件未找到异常处理"""
    with patch("sys.exit") as mock_exit:
        with patch("logging.Logger.error") as mock_log:
            # 在 __init__.py 中直接调用异常处理逻辑
            import mcp_lark_doc_manage.__init__ as init_module
            error = FileNotFoundError("测试文件未找到")
            with patch.object(init_module, "mcp") as mock_mcp:
                mock_mcp.run.side_effect = error
                init_module.main([])
            
            # 检查日志记录
            mock_log.assert_called()
            # 检查 sys.exit 调用
            mock_exit.assert_called_with(1)

def test_import_error_handling():
    """直接测试导入错误异常处理"""
    with patch("sys.exit") as mock_exit:
        with patch("logging.Logger.error") as mock_log:
            # 在 __init__.py 中直接调用异常处理逻辑
            import mcp_lark_doc_manage.__init__ as init_module
            error = ImportError("测试模块未找到")
            with patch.object(init_module, "mcp") as mock_mcp:
                mock_mcp.run.side_effect = error
                init_module.main([])
            
            # 检查日志记录
            mock_log.assert_called()
            # 检查 sys.exit 调用
            mock_exit.assert_called_with(1)

def test_general_error_handling():
    """直接测试一般错误异常处理"""
    with patch("sys.exit") as mock_exit:
        with patch("logging.Logger.error") as mock_log:
            # 在 __init__.py 中直接调用异常处理逻辑
            import mcp_lark_doc_manage.__init__ as init_module
            error = Exception("测试一般错误")
            with patch.object(init_module, "mcp") as mock_mcp:
                mock_mcp.run.side_effect = error
                init_module.main([])
            
            # 检查日志记录
            mock_log.assert_called()
            # 检查 sys.exit 调用
            mock_exit.assert_called_with(1)

def test_module_main():
    """Test module main execution"""
    with patch("mcp_lark_doc_manage.main") as mock_main:
        # Save original argv
        original_argv = sys.argv[:]
        sys.argv = ["script.py", "arg1", "arg2"]
        try:
            from mcp_lark_doc_manage.__main__ import module_main
            mock_main.return_value = 0  # Set return value for main function
            with pytest.raises(SystemExit) as exc_info:
                module_main()
            assert exc_info.value.code == 0
            mock_main.assert_called_once_with(["arg1", "arg2"])
        finally:
            # Restore original argv
            sys.argv = original_argv

def test_init_imports():
    """Test imports in __init__.py"""
    # Test non-testing environment
    os.environ["TESTING"] = "false"
    with patch("mcp_lark_doc_manage.__init__.logger") as mock_logger:
        reload(mcp_lark_doc_manage)
    
    # Test testing environment
    os.environ["TESTING"] = "true"
    with patch("mcp_lark_doc_manage.__init__.logger") as mock_logger:
        reload(mcp_lark_doc_manage)

def test_init_logging():
    """Test logging setup in __init__.py"""
    # 使用 patch 来避免对全局状态的修改
    with patch("logging.getLogger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        # 重新导入模块以触发日志设置
        reload(mcp_lark_doc_manage)
        
        # 验证日志配置
        mock_get_logger.assert_called_with("mcp_lark_doc_manage")
        # 因为我们使用 mock 对象，所以不需要验证 handlers 