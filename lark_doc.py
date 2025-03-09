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

# 从环境变量获取配置
LARK_APP_ID = os.getenv("LARK_APP_ID", "")
LARK_APP_SECRET = os.getenv("LARK_APP_SECRET", "")

try:
    larkClient = lark.Client.builder() \
        .app_id(LARK_APP_ID) \
        .app_secret(LARK_APP_SECRET) \
        .build()
except Exception as e:
    print(f"飞书客户端初始化失败: {str(e)}")
    larkClient = None

# 初始化 FastMCP 服务器
mcp = FastMCP("lark_doc")

@mcp.tool()
async def get_lark_doc_content(documentUrl: str) -> str:
    """获取飞书文档内容
    
    Args:
        documentUrl: 飞书文档URL
    """

    if not larkClient or not larkClient.auth or not larkClient.docx or not larkClient.wiki:
        return "飞书客户端未正确初始化"
    
    # 1. 先拿到鉴权token
    authRequest: InternalAppAccessTokenRequest = InternalAppAccessTokenRequest.builder() \
        .request_body(InternalAppAccessTokenRequestBody.builder()
            .app_id(LARK_APP_ID)
            .app_secret(LARK_APP_SECRET)
            .build()) \
        .build()

    authResponse: InternalAppAccessTokenResponse = larkClient.auth.v3.app_access_token.internal(authRequest)

    if not authResponse.success():
        return f"获取app访问令牌失败: 错误码 {authResponse.code}, 信息: {authResponse.msg}"

    # 获取 tenant_access_token
    if not authResponse.raw or not authResponse.raw.content:
        return f"获取app访问令牌响应内容失败, {authResponse}"
        
    authContent = json.loads(authResponse.raw.content.decode('utf-8'))
    tenantAccessToken = authContent.get("tenant_access_token")
    
    if not tenantAccessToken:
        return f"获取tenant_access_token失败, {authContent}"
        
     # 2. 提取文档ID
    docMatch = re.search(r'/(?:docx|wiki)/([A-Za-z0-9]+)', documentUrl)
    if not docMatch:
        return "无效的飞书文档URL格式"

    docID = docMatch.group(1)
    isWiki = '/wiki/' in documentUrl
    option = lark.RequestOption.builder().tenant_access_token(tenantAccessToken).build()

    # 3. 如果是wiki文档,需要额外请求一个接口获取实际的docID
    if isWiki:
        # 构造请求对象
        wikiRequest: GetNodeSpaceRequest = GetNodeSpaceRequest.builder() \
            .token(docID) \
            .obj_type("wiki") \
            .build()
        wikiResponse: GetNodeSpaceResponse = larkClient.wiki.v2.space.get_node(wikiRequest, option)    
        if not wikiResponse.success():
            return f"获取wiki文档的真实ID失败: 错误码 {wikiResponse.code}, 信息: {wikiResponse.msg}"
            
        if not wikiResponse.data or not wikiResponse.data.node or not wikiResponse.data.node.obj_token:
            return f"获取wiki文档节点信息失败, 响应{wikiResponse.data}"
        docID = wikiResponse.data.node.obj_token    


    # 4. 获取文档实际内容
    contentRequest: RawContentDocumentRequest = RawContentDocumentRequest.builder() \
        .document_id(docID) \
        .lang(0) \
        .build()
        
    contentResponse: RawContentDocumentResponse = larkClient.docx.v1.document.raw_content(contentRequest, option)

    if not contentResponse.success():
        return f"获取文档内容失败: 错误码 {contentResponse.code}, 信息: {contentResponse.msg}"
 
    if not contentResponse.data or not contentResponse.data.content:
        return f"文档内容为空, {contentResponse}"
        
    return contentResponse.data.content  # 确保返回字符串类型

if __name__ == "__main__":
    mcp.run(transport="stdio")