from typing import Any
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

# Get configuration from environment variables
# Add global variables below imports
LARK_APP_ID = os.getenv("LARK_APP_ID", "")
LARK_APP_SECRET = os.getenv("LARK_APP_SECRET", "")
USER_ACCESS_TOKEN = None  # Add global variable
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
async def set_user_access_token(token: str) -> str:
    """Set Lark user access token
    
    Args:
        token: Lark user access token
    """
    global USER_ACCESS_TOKEN
    async with token_lock:  # Use lock to protect token writing
        USER_ACCESS_TOKEN = token
        return f"Successfully set user access token: {token[:8]}..."

@mcp.tool()
async def get_lark_doc_content(documentUrl: str) -> str:
    """Get Lark document content
    
    Args:
        documentUrl: Lark document URL
    """
    if not larkClient or not larkClient.auth or not larkClient.docx or not larkClient.wiki:
        return "Lark client not properly initialized"
        
    # 1. Get authentication token
    authRequest: InternalAppAccessTokenRequest = InternalAppAccessTokenRequest.builder() \
        .request_body(InternalAppAccessTokenRequestBody.builder()
            .app_id(LARK_APP_ID)
            .app_secret(LARK_APP_SECRET)
            .build()) \
        .build()

    authResponse: InternalAppAccessTokenResponse = larkClient.auth.v3.app_access_token.internal(authRequest)

    if not authResponse.success():
        return f"Failed to get app access token: code {authResponse.code}, message: {authResponse.msg}"

    # Get tenant_access_token
    if not authResponse.raw or not authResponse.raw.content:
        return f"Failed to get app access token response content, {authResponse}"
        
    authContent = json.loads(authResponse.raw.content.decode('utf-8'))
    tenantAccessToken = authContent.get("tenant_access_token")
    
    if not tenantAccessToken:
        return f"Failed to get tenant_access_token, {authContent}"
        
     # 2. Extract document ID
    docMatch = re.search(r'/(?:docx|wiki)/([A-Za-z0-9]+)', documentUrl)
    if not docMatch:
        return "Invalid Lark document URL format"

    docID = docMatch.group(1)
    isWiki = '/wiki/' in documentUrl
    # If user token exists, use it preferentially
    async with token_lock:  # Use lock to protect token reading
        current_token = USER_ACCESS_TOKEN
        
    if current_token:
        option = lark.RequestOption.builder().user_access_token(current_token).build()
    else:
        option = lark.RequestOption.builder().tenant_access_token(tenantAccessToken).build()
    
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
        
    if not current_token:
        return f"User access token not found, please use set_user_access_token create first."
    option = lark.RequestOption.builder().user_access_token(current_token).build()

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