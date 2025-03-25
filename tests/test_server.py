import pytest
import os
import json
from unittest.mock import patch, MagicMock
from mcp_server_my_lark_doc.server import (
    get_lark_doc_content,
    search_wiki,
    list_folder_content,
    get_folder_token,
    _check_token_expired,
    larkClient
)

# Mock response for successful API calls
MOCK_SUCCESS_RESPONSE = MagicMock(
    success=lambda: True,
    raw=MagicMock(
        content=json.dumps({
            "code": 0,
            "data": {
                "files": [
                    {
                        "name": "Test Doc",
                        "type": "doc",
                        "token": "test_token",
                        "url": "https://example.com/doc",
                        "created_time": 1616733296,
                        "modified_time": 1616733296,
                        "owner_id": "test_owner",
                        "parent_token": "test_parent"
                    }
                ]
            }
        }).encode()
    )
)

# Mock response for failed API calls
MOCK_FAIL_RESPONSE = MagicMock(
    success=lambda: False,
    code=400,
    msg="Test error message"
)

@pytest.fixture
def mock_env_vars():
    """Fixture to set up environment variables for testing"""
    original_env = dict(os.environ)
    os.environ.update({
        "LARK_APP_ID": "test_app_id",
        "LARK_APP_SECRET": "test_app_secret",
        "FOLDER_TOKEN": "test_folder_token",
        "OAUTH_HOST": "localhost",
        "OAUTH_PORT": "9997"
    })
    yield
    os.environ.clear()
    os.environ.update(original_env)

@pytest.fixture
def mock_lark_client():
    """Fixture to mock Lark client"""
    with patch("mcp_server_my_lark_doc.server.larkClient") as mock_client:
        mock_client.request.return_value = MOCK_SUCCESS_RESPONSE
        yield mock_client

@pytest.mark.asyncio
async def test_list_folder_content_success(mock_env_vars, mock_lark_client):
    """Test successful folder content listing"""
    # Mock folder token
    with patch("mcp_server_my_lark_doc.server.FOLDER_TOKEN", "test_folder_token"):
        # Mock user access token
        with patch("mcp_server_my_lark_doc.server.USER_ACCESS_TOKEN", "test_token"):
            with patch("mcp_server_my_lark_doc.server._check_token_expired", return_value=False):
                result = await list_folder_content()
                
                # Parse result
                result_data = json.loads(result)
                assert isinstance(result_data, list)
                assert len(result_data) == 1
                assert result_data[0]["name"] == "Test Doc"
                assert result_data[0]["type"] == "doc"

@pytest.mark.asyncio
async def test_list_folder_content_failure(mock_env_vars, mock_lark_client):
    """Test folder content listing failure"""
    # Mock folder token
    with patch("mcp_server_my_lark_doc.server.FOLDER_TOKEN", "test_folder_token"):
        mock_lark_client.request.return_value = MOCK_FAIL_RESPONSE
        
        with patch("mcp_server_my_lark_doc.server.USER_ACCESS_TOKEN", "test_token"):
            with patch("mcp_server_my_lark_doc.server._check_token_expired", return_value=False):
                result = await list_folder_content()
                assert "Failed to list files" in result

@pytest.mark.asyncio
async def test_get_folder_token():
    """Test get_folder_token function"""
    # Mock environment variable
    with patch.dict(os.environ, {"FOLDER_TOKEN": "test_folder_token"}):
        # Mock global variable
        with patch("mcp_server_my_lark_doc.server.FOLDER_TOKEN", "test_folder_token"):
            token = await get_folder_token()
            assert token == "test_folder_token"

@pytest.mark.asyncio
async def test_check_token_expired():
    """Test token expiration check"""
    with patch("mcp_server_my_lark_doc.server.TOKEN_EXPIRES_AT", None):
        with patch("mcp_server_my_lark_doc.server.USER_ACCESS_TOKEN", None):
            is_expired = await _check_token_expired()
            assert is_expired == True

@pytest.mark.asyncio
async def test_get_lark_doc_content(mock_lark_client):
    """Test get_lark_doc_content function"""
    mock_response = MagicMock(
        success=lambda: True,
        data=MagicMock(content="Test content")
    )
    mock_lark_client.docx.v1.document.raw_content.return_value = mock_response
    
    with patch("mcp_server_my_lark_doc.server.USER_ACCESS_TOKEN", "test_token"):
        with patch("mcp_server_my_lark_doc.server._check_token_expired", return_value=False):
            result = await get_lark_doc_content("https://example.feishu.cn/docx/test123")
            assert result == "Test content"

@pytest.mark.asyncio
async def test_search_wiki(mock_lark_client):
    """Test search_wiki function"""
    mock_response = MagicMock(
        success=lambda: True,
        raw=MagicMock(
            content=json.dumps({
                "data": {
                    "items": [
                        {
                            "title": "Test Wiki",
                            "url": "https://example.com/wiki",
                            "create_time": 1616733296,
                            "update_time": 1616733296
                        }
                    ]
                }
            }).encode()
        )
    )
    mock_lark_client.request.return_value = mock_response
    
    with patch("mcp_server_my_lark_doc.server.USER_ACCESS_TOKEN", "test_token"):
        with patch("mcp_server_my_lark_doc.server._check_token_expired", return_value=False):
            result = await search_wiki("test")
            result_data = json.loads(result)
            assert isinstance(result_data, list)
            assert len(result_data) == 1
            assert result_data[0]["title"] == "Test Wiki" 