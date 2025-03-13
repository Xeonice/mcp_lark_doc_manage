import time
from typing import Any
import webbrowser
import httpx
from mcp.server.fastmcp import FastMCP
import re
import lark_oapi as lark
from lark_oapi.api.docx.v1 import *
from lark_oapi.api.auth.v3 import *
from lark_oapi.api.wiki.v2 import *
import json
import os
import asyncio  # Add to imports at the beginning
from lark_oapi.api.search.v2 import *
from aiohttp import web
import secrets
from urllib.parse import quote

# Get configuration from environment variables
# Add global variables below imports
LARK_APP_ID = os.getenv("LARK_APP_ID", "")
LARK_APP_SECRET = os.getenv("LARK_APP_SECRET", "")
USER_ACCESS_TOKEN = None  # Add global variable
TOKEN_EXPIRES_AT = None  # 添加过期时间存储
FEISHU_AUTHORIZE_URL = "https://accounts.feishu.cn/open-apis/authen/v1/authorize"
REDIRECT_URI = "http://localhost:9997/oauth/callback"
token_lock = asyncio.Lock()  # Add token lock

try:
    larkClient = lark.Client.builder() \
        .app_id(LARK_APP_ID) \
        .app_secret(LARK_APP_SECRET) \
        .build()
except Exception as e:
    print(f"Failed to initialize Lark client: {str(e)}")
    larkClient = None

# Initialize FastMCP server
mcp = FastMCP("lark_doc")

@mcp.tool()
async def get_lark_doc_content(documentUrl: str) -> str:
    """Get Lark document content
    
    Args:
        documentUrl: Lark document URL
    """
    if not larkClient or not larkClient.auth or not larkClient.docx or not larkClient.wiki:
        return "Lark client not properly initialized"
                
    async with token_lock:
        current_token = USER_ACCESS_TOKEN
    if not current_token or await _check_token_expired():
        try:
            current_token = await _auth_flow()
        except Exception as e:
            return f"Failed to get user access token: {str(e)}"

    # 1. Extract document ID
    docMatch = re.search(r'/(?:docx|wiki)/([A-Za-z0-9]+)', documentUrl)
    if not docMatch:
        return "Invalid Lark document URL format"

    docID = docMatch.group(1)
    isWiki = '/wiki/' in documentUrl
    
    option = lark.RequestOption.builder().user_access_token(current_token).build()

    # 3. For wiki documents, need to make an additional request to get the actual docID
    if isWiki:
        # Construct request object
        wikiRequest: GetNodeSpaceRequest = GetNodeSpaceRequest.builder() \
            .token(docID) \
            .obj_type("wiki") \
            .build()
        wikiResponse: GetNodeSpaceResponse = larkClient.wiki.v2.space.get_node(wikiRequest, option)    
        if not wikiResponse.success():
            return f"Failed to get wiki document real ID: code {wikiResponse.code}, message: {wikiResponse.msg}"
            
        if not wikiResponse.data or not wikiResponse.data.node or not wikiResponse.data.node.obj_token:
            return f"Failed to get wiki document node info, response: {wikiResponse.data}"
        docID = wikiResponse.data.node.obj_token    

    # 4. Get actual document content
    contentRequest: RawContentDocumentRequest = RawContentDocumentRequest.builder() \
        .document_id(docID) \
        .lang(0) \
        .build()
        
    contentResponse: RawContentDocumentResponse = larkClient.docx.v1.document.raw_content(contentRequest, option)

    if not contentResponse.success():
        return f"Failed to get document content: code {contentResponse.code}, message: {contentResponse.msg}"
 
    if not contentResponse.data or not contentResponse.data.content:
        return f"Document content is empty, {contentResponse}"
        
    return contentResponse.data.content  # Ensure return string type


@mcp.tool()
async def search_wiki(query: str, page_size: int = 10) -> str:
    """Search Lark Wiki
    
    Args:
        query: Search keywords
        page_size: Number of results to return (default: 10)
    """
    if not larkClient or not larkClient.auth or not larkClient.wiki:
        return "Lark client not properly initialized"

    # Check if user token exists
    async with token_lock:
        current_token = USER_ACCESS_TOKEN

    # Check token existence and expiration
    if not current_token or await _check_token_expired():
        try:
            current_token = await _auth_flow()
        except Exception as e:
            return f"Failed to get user access token: {str(e)}"

    # Construct search request using raw API mode
    request: lark.BaseRequest = lark.BaseRequest.builder() \
        .http_method(lark.HttpMethod.POST) \
        .uri("/open-apis/wiki/v1/nodes/search") \
        .token_types({lark.AccessTokenType.USER}) \
        .body({
            "page_size": page_size,
            "query": query
        }) \
        .build()

    option = lark.RequestOption.builder().user_access_token(current_token).build()
    
    # Send search request
    response: lark.BaseResponse = larkClient.request(request, option)

    if not response.success():
        return f"Failed to search wiki: code {response.code}, message: {response.msg}"

    if not response.raw or not response.raw.content:
        return f"Search response content is empty, {response}"

    # Parse response content
    try:
        result = json.loads(response.raw.content.decode('utf-8'))
        if not result.get("data") or not result["data"].get("items"):
            return "No results found"
        
        # Format search results
        results = []
        for item in result["data"]["items"]:
            results.append({
                "title": item.get("title"),
                "url": item.get("url"),
                "create_time": item.get("create_time"),
                "update_time": item.get("update_time")
            })
        
        return json.dumps(results, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Failed to parse search results: {str(e)}"

# 添加一个检查 token 是否过期的函数
async def _check_token_expired() -> bool:
    """Check if the current token has expired"""
    async with token_lock:
        if not TOKEN_EXPIRES_AT or not USER_ACCESS_TOKEN:
            return True
        # 提前 60 秒认为 token 过期，以避免边界情况
        return time.time() + 60 >= TOKEN_EXPIRES_AT

async def _handle_oauth_callback(webReq: web.Request) -> web.Response:
    """Handle OAuth callback from Feishu"""
    code = webReq.query.get('code')
    if not code:
        return web.Response(text="No authorization code received", status=400)
        
    # Exchange code for user_access_token using raw API mode
    request_body = {
        "grant_type": "authorization_code",
        "client_id": LARK_APP_ID,
        "client_secret": LARK_APP_SECRET,
        "code": code,
        "redirect_uri": REDIRECT_URI
    }
    
    request: lark.BaseRequest  = lark.BaseRequest.builder() \
        .http_method(lark.HttpMethod.POST) \
        .uri("/open-apis/authen/v2/oauth/token") \
        .body(request_body) \
        .headers({
            "content-type": "application/json"
        }) \
        .build()
            
    # 使用 None 作为 option 参数调用 request 方法
    # 创建一个空的 RequestOption 对象来替代 None
    option = lark.RequestOption.builder().build()
    
    if not larkClient:
        return web.Response(text="Lark client not initialized", status=500)

    response: lark.BaseResponse = larkClient.request(request, option)
    
    if not response.success():
        # print(f"OAuth token request failed:")
        # print(f"Response code: {response.code}")
        # print(f"Response msg: {response.msg}")
        # print(f"Raw response: {response.raw.content if response.raw else 'No raw content'}")
        return web.Response(text=f"Failed to get token: {response.msg} (code: {response.code})", status=500)
        
    # Parse response
    if not response.raw or not response.raw.content:
        return web.Response(text="Empty response from server", status=500)
        
    result = json.loads(response.raw.content.decode('utf-8'))
    if result.get("code") != 0:
        return web.Response(
            text=f"Failed to get token: {result.get('error_description', 'Unknown error')}",
            status=500
        )
    
    # Store token
    global USER_ACCESS_TOKEN, TOKEN_EXPIRES_AT
    async with token_lock:
        USER_ACCESS_TOKEN = result.get("access_token")
        expires_in = result.get("expires_in", 0)
        TOKEN_EXPIRES_AT = time.time() + expires_in if expires_in else None
        
    return web.Response(text="Authorization successful! You can close this window.")

async def _start_oauth_server() -> str:
    """Start local server to handle OAuth callback"""
    app = web.Application()
    app.router.add_get('/oauth/callback', _handle_oauth_callback)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 9997)
    await site.start()
    
    try:
        # Generate state for CSRF protection
        state = secrets.token_urlsafe(16)
        
        # Generate authorization URL with state
        params = {
            "client_id": LARK_APP_ID,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "state": state
        }
        
        query = "&".join([f"{k}={quote(str(v))}" for k, v in params.items()])
        auth_url = f"{FEISHU_AUTHORIZE_URL}?{query}"
        
        # Open browser for authorization
        webbrowser.open(auth_url)
        
        # Wait for callback to set the token with timeout
        start_time = asyncio.get_event_loop().time()
        while True:
            if asyncio.get_event_loop().time() - start_time > 300:  # 5分钟超时
                raise TimeoutError("Authorization timeout after 5 minutes")
                
            await asyncio.sleep(1)
            async with token_lock:
                if USER_ACCESS_TOKEN:
                    return USER_ACCESS_TOKEN
    finally:
        # 确保服务器总是被清理
        await runner.cleanup()
        
    return None

# Update _auth_flow to use the server
async def _auth_flow() -> str:
    """Internal method to handle Feishu authentication flow"""
    global USER_ACCESS_TOKEN
    
    async with token_lock:
        if USER_ACCESS_TOKEN and not await _check_token_expired():
            return USER_ACCESS_TOKEN

    if not larkClient or not larkClient.auth:
        raise Exception("Lark client not properly initialized")
        
    # Start OAuth flow
    token = await _start_oauth_server()
    if not token:
        raise Exception("Failed to get user access token")
        
    return token