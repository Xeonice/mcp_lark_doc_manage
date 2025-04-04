import pytest
import os
import sys
import logging
from importlib import reload
import importlib

# 不要在 conftest.py 中启动 coverage，让 pytest-cov 插件来处理
# 这样可以避免与 pytest-cov 插件的冲突

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 在导入任何模块前设置测试环境变量
os.environ["TESTING"] = "true"
os.environ["OAUTH_PORT"] = "9997"
os.environ["LARK_APP_ID"] = "test_app_id"
os.environ["LARK_APP_SECRET"] = "test_app_secret"
os.environ["FOLDER_TOKEN"] = "test_folder_token"

@pytest.fixture(scope="session", autouse=True)
def setup_test_session():
    """设置测试会话环境"""
    # 如果模块已加载，重新加载以确保测试环境一致
    if "mcp_lark_doc_manage" in sys.modules:
        importlib.reload(sys.modules["mcp_lark_doc_manage"])

@pytest.fixture(autouse=True)
def setup_test_env():
    """为每个测试设置环境变量"""
    # 保存原始环境变量
    original_env = {}
    test_env_vars = [
        "OAUTH_PORT", "LARK_APP_ID", "LARK_APP_SECRET", 
        "FOLDER_TOKEN", "USER_ACCESS_TOKEN"
    ]
    
    for var in test_env_vars:
        original_env[var] = os.environ.get(var)
    
    # 设置测试环境变量
    os.environ["OAUTH_PORT"] = "9997"
    os.environ["LARK_APP_ID"] = "test_app_id"
    os.environ["LARK_APP_SECRET"] = "test_app_secret"
    os.environ["FOLDER_TOKEN"] = "test_folder_token"
    
    yield
    
    # 还原环境变量
    for var, value in original_env.items():
        if value is None:
            if var in os.environ:
                del os.environ[var]
        else:
            os.environ[var] = value

# 定义测试标记
def pytest_configure(config):
    """配置 pytest 测试标记"""
    config.addinivalue_line("markers", "server_test: 标记服务器相关测试")
    config.addinivalue_line("markers", "markdown_test: 标记 Markdown 相关测试")
    config.addinivalue_line("markers", "init_test: 标记初始化相关测试") 