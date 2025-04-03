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
import logging
from mcp_lark_doc_manage.markdown_converter import convert_markdown_to_blocks
from mcp.types import CallToolResult, TextContent

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get configuration from environment variables
# Add global variables below imports
LARK_APP_ID = os.getenv("LARK_APP_ID", "")
LARK_APP_SECRET = os.getenv("LARK_APP_SECRET", "")
OAUTH_HOST = os.getenv("OAUTH_HOST", "localhost")  # OAuth host configuration
OAUTH_PORT = int(os.getenv("OAUTH_PORT", "9997"))  # OAuth port configuration
REDIRECT_URI = f"http://{OAUTH_HOST}:{OAUTH_PORT}/oauth/callback"
USER_ACCESS_TOKEN = None  # Global variable for user access token
TOKEN_EXPIRES_AT = None  # Token expiration timestamp
FEISHU_AUTHORIZE_URL = "https://accounts.feishu.cn/open-apis/authen/v1/authorize"
FOLDER_TOKEN = os.getenv("FOLDER_TOKEN", "")  # Global folder token
token_lock = asyncio.Lock()  # Token lock for thread safety

# Validate required environment variables
if not LARK_APP_ID or not LARK_APP_SECRET:
    logger.error("Missing required environment variables: LARK_APP_ID or LARK_APP_SECRET")
    raise ValueError("Missing required environment variables: LARK_APP_ID or LARK_APP_SECRET")

try:
    logger.info("Initializing Lark client...")
    larkClient = lark.Client.builder() \
        .app_id(LARK_APP_ID) \
        .app_secret(LARK_APP_SECRET) \
        .build()
    logger.info("Lark client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Lark client: {str(e)}", exc_info=True)
    raise

# Initialize FastMCP server
try:
    logger.info("Initializing FastMCP server...")
    mcp = FastMCP("lark_doc")
    logger.info("FastMCP server initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize FastMCP server: {str(e)}", exc_info=True)
    raise

@mcp.tool()
async def get_lark_doc_content(documentUrl: str) -> CallToolResult:
    """Get Lark document content
    
    Args:
        documentUrl: Lark document URL
    """
    try:
        if not larkClient or not larkClient.auth or not larkClient.docx or not larkClient.wiki:
            return CallToolResult(
                isError=True,
                content=[TextContent(type="text", text="Lark client not properly initialized")]
            )
                    
        async with token_lock:
            current_token = USER_ACCESS_TOKEN
        if not current_token or await _check_token_expired():
            try:
                current_token = await _auth_flow()
            except Exception as e:
                return CallToolResult(
                    isError=True,
                    content=[TextContent(type="text", text=f"Failed to get user access token: {str(e)}")]
                )

        # 1. Extract document ID
        docMatch = re.search(r'/(?:docx|wiki)/([A-Za-z0-9]+)', documentUrl)
        if not docMatch:
            return CallToolResult(
                isError=True,
                content=[TextContent(type="text", text="Invalid Lark document URL format")]
            )

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
                return CallToolResult(
                    isError=True,
                    content=[TextContent(type="text", text=f"Failed to get wiki document real ID: code {wikiResponse.code}, message: {wikiResponse.msg}")]
                )
                
            if not wikiResponse.data or not wikiResponse.data.node or not wikiResponse.data.node.obj_token:
                return CallToolResult(
                    isError=True,
                    content=[TextContent(type="text", text=f"Failed to get wiki document node info, response: {wikiResponse.data}")]
                )
            docID = wikiResponse.data.node.obj_token    

        # 4. Get actual document content
        contentRequest: RawContentDocumentRequest = RawContentDocumentRequest.builder() \
            .document_id(docID) \
            .lang(0) \
            .build()
            
        contentResponse: RawContentDocumentResponse = larkClient.docx.v1.document.raw_content(contentRequest, option)

        if not contentResponse.success():
            return CallToolResult(
                isError=True,
                content=[TextContent(type="text", text=f"Failed to get document content: code {contentResponse.code}, message: {contentResponse.msg}")]
            )
     
        if not contentResponse.data or not contentResponse.data.content:
            return CallToolResult(
                isError=True,
                content=[TextContent(type="text", text=f"Document content is empty, {contentResponse}")]
            )
            
        return CallToolResult(
            content=[TextContent(type="text", text=contentResponse.data.content)]
        )
    except Exception as e:
        return CallToolResult(
            isError=True,
            content=[TextContent(type="text", text=f"Error getting document content: {str(e)}")]
        )


@mcp.tool()
async def search_wiki(query: str, page_size: int = 10) -> CallToolResult:
    """Search Lark Wiki
    
    Args:
        query: Search keywords
        page_size: Number of results to return (default: 10)
    """
    try:
        if not larkClient or not larkClient.auth or not larkClient.wiki:
            return CallToolResult(
                isError=True,
                content=[TextContent(type="text", text="Lark client not properly initialized")]
            )

        # Check if user token exists
        async with token_lock:
            current_token = USER_ACCESS_TOKEN

        # Check token existence and expiration
        if not current_token or await _check_token_expired():
            try:
                current_token = await _auth_flow()
            except Exception as e:
                return CallToolResult(
                    isError=True,
                    content=[TextContent(type="text", text=f"Failed to get user access token: {str(e)}")]
                )

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
            return CallToolResult(
                isError=True,
                content=[TextContent(type="text", text=f"Failed to search wiki: code {response.code}, message: {response.msg}")]
            )

        if not response.raw or not response.raw.content:
            return CallToolResult(
                isError=True,
                content=[TextContent(type="text", text=f"Search response content is empty, {response}")]
            )

        # Parse response content
        try:
            result = json.loads(response.raw.content.decode('utf-8'))
            if not result.get("data") or not result["data"].get("items"):
                return CallToolResult(
                    content=[TextContent(type="text", text="No results found")]
                )
            
            # Format search results
            results = []
            for item in result["data"]["items"]:
                results.append({
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "create_time": item.get("create_time"),
                    "update_time": item.get("update_time")
                })
            
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(results, ensure_ascii=False, indent=2))]
            )
        except Exception as e:
            return CallToolResult(
                isError=True,
                content=[TextContent(type="text", text=f"Failed to parse search results: {str(e)}")]
            )
    except Exception as e:
        return CallToolResult(
            isError=True,
            content=[TextContent(type="text", text=f"Error searching wiki: {str(e)}")]
        )
    


# Add a function to check if token has expired
async def _check_token_expired() -> bool:
    """Check if the current token has expired"""
    async with token_lock:
        if not TOKEN_EXPIRES_AT or not USER_ACCESS_TOKEN:
            return True
        # Consider token expired 60 seconds early to avoid edge cases
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
            
    # Use an empty RequestOption object instead of None for the request method
    # Create an empty RequestOption object to replace None
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
            "state": state,
            "scope": "wiki:wiki:readonly drive:drive space:document:retrieve drive:drive.search:readonly docx:document docx:document:readonly"  # 移除 %20，使用普通空格
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

async def get_folder_token() -> str:
    """Get the folder token from environment or fetch from API if needed"""
    global FOLDER_TOKEN
    
    if FOLDER_TOKEN:
        return FOLDER_TOKEN
        
    # 如果环境变量中没有设置 FOLDER_TOKEN，可以在这里添加获取逻辑
    # 比如从 API 获取根目录或特定目录的 token
    return FOLDER_TOKEN
@mcp.tool()
async def list_folder_content(page_size: int = 10) -> CallToolResult:
    """List contents of a Lark folder
    
    Args:
        page_size: Number of results to return (default: 10)
    """
    try:
        if not larkClient or not larkClient.auth:
            return CallToolResult(
                isError=True,
                content=[TextContent(type="text", text="Lark client not properly initialized")]
            )

        # Check if user token exists
        async with token_lock:
            current_token = USER_ACCESS_TOKEN

        # Check token existence and expiration
        if not current_token or await _check_token_expired():
            try:
                current_token = await _auth_flow()
            except Exception as e:
                return CallToolResult(
                    isError=True,
                    content=[TextContent(type="text", text=f"Failed to get user access token: {str(e)}")]
                )
                
        # Get folder token
        folder_token = await get_folder_token()
        if not folder_token:
            return CallToolResult(
                isError=True,
                content=[TextContent(type="text", text="Folder token not configured")]
            )

        # Construct file list request using SDK
        request: lark.BaseRequest = lark.BaseRequest.builder() \
            .http_method(lark.HttpMethod.GET) \
            .uri("/open-apis/drive/v1/files") \
            .token_types({lark.AccessTokenType.USER}) \
            .queries([("folder_token", folder_token), ("page_size", page_size)]) \
            .build()

        option = lark.RequestOption.builder().user_access_token(current_token).build()
        
        # Send list request
        response: lark.BaseResponse = larkClient.request(request, option)

        if not response.success():
            return CallToolResult(
                isError=True,
                content=[TextContent(type="text", text=f"Failed to list files: code {response.code}, message: {response.msg}")]
            )

        # Parse response content
        try:
            result = json.loads(response.raw.content.decode('utf-8'))
            if not result.get("data") or not result["data"].get("files"):
                return CallToolResult(
                    content=[TextContent(type="text", text="No files found in folder")]
                )
            
            # Format file contents
            items = []
            for item in result["data"]["files"]:
                items.append({
                    "name": item.get("name"),
                    "type": item.get("type"),  # "doc"/"sheet"/"file" etc
                    "token": item.get("token"),
                    "url": item.get("url"),
                    "created_time": item.get("created_time"),
                    "modified_time": item.get("modified_time"),
                    "owner_id": item.get("owner_id"),
                    "parent_token": item.get("parent_token")
                })
            
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(items, ensure_ascii=False, indent=2))]
            )
        except Exception as e:
            return CallToolResult(
                isError=True,
                content=[TextContent(type="text", text=f"Failed to parse file contents: {str(e)}")]
            )
    except Exception as e:
        return CallToolResult(
            isError=True,
            content=[TextContent(type="text", text=f"Error listing folder content: {str(e)}")]
        )

@mcp.tool()
async def create_doc(title: str, content: str = "", target_space_id: str = None) -> CallToolResult:
    """Create a new Lark document and optionally move it to a specified wiki space4712478312748178842371
    
    Args:
        title: Document title
        content: Document content (optional)
        target_space_id: Target wiki space ID to move the document to (optional)
    """
    try:
        if not larkClient or not larkClient.auth or not larkClient.docx:
            logger.error("Lark client not properly initialized")
            return CallToolResult(
                isError=True,
                content=[TextContent(type="text", text="Lark client not properly initialized")]
            )
                    
        async with token_lock:
            current_token = USER_ACCESS_TOKEN
        if not current_token or await _check_token_expired():
            try:
                logger.info("Token expired or not found, starting auth flow")
                current_token = await _auth_flow()
                logger.info("Successfully obtained new token")
            except Exception as e:
                logger.error(f"Failed to get user access token: {str(e)}", exc_info=True)
                return CallToolResult(
                    isError=True,
                    content=[TextContent(type="text", text=f"Failed to get user access token: {str(e)}")]
                )

        # Get folder token
        folder_token = await get_folder_token()
        if not folder_token:
            logger.error("Folder token not configured")
            return CallToolResult(
                isError=True,
                content=[TextContent(type="text", text="Folder token not configured")]
            )

        try:
            # Step 1: Create document
            logger.info(f"Creating document with title: {title}")
            create_request: lark.BaseRequest = lark.BaseRequest.builder() \
                .http_method(lark.HttpMethod.POST) \
                .uri("/open-apis/docx/v1/documents") \
                .token_types({lark.AccessTokenType.USER}) \
                .body({
                    "folder_token": folder_token,
                    "title": title
                }) \
                .build()

            option = lark.RequestOption.builder().user_access_token(current_token).build()

            # Send create document request
            create_response: lark.BaseResponse = larkClient.request(create_request, option)

            if not create_response.success():
                logger.error(f"Failed to create document: code {create_response.code}, message: {create_response.msg}")
                return CallToolResult(
                    isError=True,
                    content=[TextContent(type="text", text=f"Failed to create document: code {create_response.code}, message: {create_response.msg}")]
                )

            if not create_response.raw or not create_response.raw.content:
                logger.error(f"Document creation response is empty, {create_response}")
                return CallToolResult(
                    isError=True,
                    content=[TextContent(type="text", text=f"Document creation response is empty, {create_response}")]
                )

            create_result = json.loads(create_response.raw.content.decode('utf-8'))
            if not create_result.get("data") or not create_result["data"].get("document"):
                logger.error(f"Document creation response is invalid, {create_result}")
                return CallToolResult(
                    isError=True,
                    content=[TextContent(type="text", text=f"Document creation response is invalid, {create_result}")]
                )

            doc_id = create_result["data"]["document"]["document_id"]
            logger.info(f"Successfully created document with ID: {doc_id}")

            # Step 2: Move document to wiki space if target_space_id is provided
            if target_space_id:
                try:
                    logger.info(f"Moving document {doc_id} to wiki space {target_space_id}")
                    move_request: lark.BaseRequest = lark.BaseRequest.builder() \
                        .http_method(lark.HttpMethod.POST) \
                        .uri("/open-apis/wiki/v2/space-node/move") \
                        .token_types({lark.AccessTokenType.USER}) \
                        .body({
                            "space_id": target_space_id,
                            "node_token": doc_id
                        }) \
                        .build()

                    move_response: lark.BaseResponse = larkClient.request(move_request, option)

                    if not move_response.success():
                        logger.error(f"Failed to move document: code {move_response.code}, message: {move_response.msg}")
                        return CallToolResult(
                            isError=True,
                            content=[TextContent(type="text", text=f"Failed to move document: code {move_response.code}, message: {move_response.msg}")]
                        )

                    logger.info(f"Successfully moved document {doc_id} to wiki space {target_space_id}")

                except Exception as e:
                    logger.error(f"Failed to move document to wiki space: {str(e)}", exc_info=True)
                    return CallToolResult(
                        isError=True,
                        content=[TextContent(type="text", text=f"Failed to move document to wiki space: {str(e)}")]
                    )

            # Step 3: Create document blocks
            if content:
                try:
                    logger.info(f"Creating document blocks for document {doc_id}")
                    blocks_data = convert_markdown_to_blocks(content)
                    
                    # Extract the descendants list that contains all the blocks to create
                    if not isinstance(blocks_data, dict) or 'descendants' not in blocks_data:
                        logger.error(f"Invalid blocks structure: {blocks_data}")
                        return CallToolResult(
                            isError=True,
                            content=[TextContent(type="text", text=f"Invalid blocks structure returned from markdown converter")]
                        )
                    
                    # Use the document-block-descendant/create API to create blocks in one request
                    create_blocks_request: lark.BaseRequest = lark.BaseRequest.builder() \
                        .http_method(lark.HttpMethod.POST) \
                        .uri(f"/open-apis/docx/v1/documents/{doc_id}/blocks/{doc_id}/descendant") \
                        .queries([("document_revision_id", "-1")]) \
                        .token_types({lark.AccessTokenType.USER}) \
                        .body({
                            "index": 0,  # Insert at the beginning of the block
                            "children_id": blocks_data.get('children_id', []),
                            "descendants": blocks_data['descendants']
                        }) \
                        .build()

                    create_blocks_response: lark.BaseResponse = larkClient.request(create_blocks_request, option)

                    if not create_blocks_response.success():
                        logger.error(f"Failed to create blocks: code {create_blocks_response.code}, message: {create_blocks_response.msg}, create_blocks_response: {create_blocks_response}")
                        return CallToolResult(
                            isError=True,
                            content=[TextContent(type="text", text=f"Failed to create blocks: code {create_blocks_response.code}, message: {create_blocks_response.msg}, create_blocks_response: {create_blocks_response}")]
                        )

                    logger.info(f"Successfully created document blocks for document {doc_id}")

                except Exception as e:
                    logger.error(f"Failed to create document blocks: {str(e)}", exc_info=True)
                    return CallToolResult(
                        isError=True,
                        content=[TextContent(type="text", text=f"Failed to create document blocks: {str(e)}")]
                    )

            # Format response
            result = {
                "document_id": doc_id,
                "title": title,
                "url": f"https://docs.feishu.cn/docx/{doc_id}"
            }
            
            logger.info(f"Successfully completed document creation process for {title}")
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
            )
        except Exception as e:
            logger.error(f"Failed to create document: {str(e)}", exc_info=True)
            return CallToolResult(
                isError=True,
                content=[TextContent(type="text", text=f"Failed to create document: {str(e)}")]
            )
    except Exception as e:
        logger.error(f"Unexpected error in create_doc: {str(e)}", exc_info=True)
        return CallToolResult(
            isError=True,
            content=[TextContent(type="text", text=f"Unexpected error in create_doc: {str(e)}")]
        )