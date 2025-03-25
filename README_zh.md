# MCP Server My Lark Doc

飞书文档访问的 Model Context Protocol 服务器。

[English Documentation](README.md)

> **重要提示**：使用此 MCP Server 之前，你需要先创建一个飞书企业应用。如果还没有创建，请按照下面的设置说明进行操作。

## 功能特性

### 文档内容访问
- 支持飞书文档和知识库两种类型
- 自动处理文档类型检测和 ID 提取
- 返回适用于 LLM 处理的文本格式内容

### 认证
- 基于 OAuth 的用户认证
- 自动的令牌刷新和过期管理
- 可自定义的 OAuth 回调服务器

### 错误处理
- 完整的认证问题错误报告
- 清晰的无效文档 URL 反馈
- 详细的故障排除错误信息

## 安装

```bash
uvx mcp-server-my-lark-doc
```

## 配置

### 创建飞书企业应用

1. 访问[飞书开放平台](https://open.larkoffice.com/)
2. 点击右上角的"开发者后台"
3. 点击"创建企业自建应用"
4. 填写基本信息：
   - 应用名称
   - 应用描述
   - 应用图标
5. 在"安全设置"部分：
   - 添加域名到"请求域名白名单"
   - 配置 OAuth 2.0 设置
6. 在"权限管理"中启用所需功能并申请权限
7. 提交审核并等待批准

详细说明请参考[自建应用开发流程](https://open.feishu.cn/document/home/introduction-to-custom-app-development/self-built-application-development-process)。

### 获取应用凭证（App ID 和 App Secret）

1. 获取 App ID：
   - 在[开发者后台](https://open.larkoffice.com/app)找到你的应用
   - 在"凭证与基础信息"中找到"App ID"（也称为"Client ID"）
   - 内部应用的 App ID 通常以"cli_"开头

2. 获取 App Secret：
   - 在同一个"凭证与基础信息"页面
   - 找到"App Secret"（也称为"Client Secret"）
   - 点击"查看"来获取密钥
   - 注意：请妥善保管你的 App Secret，切勿公开分享

### 获取文件夹 Token

获取文件夹 token 的方法：

1. 在飞书中打开目标文件夹
2. 复制文件夹 URL，例如：`https://xxx.feishu.cn/drive/folder/xxx`
3. URL 中的最后一段就是你的文件夹 token
4. 替代方法：
   - 使用云空间 API 列出文件夹
   - 在响应中找到目标文件夹的 token

注意：确保你的应用具有 `drive:drive:readonly` 权限以访问文件夹。

### 所需权限
```
wiki:wiki:readonly   # 知识库只读权限
wiki:node:read      # 知识库节点读取权限
docx:document:readonly   # 文档只读权限
search:docs:read    # 文档搜索权限
drive:drive:readonly    # 云空间只读权限
```

### 环境变量

使用此 MCP 服务器之前，你需要设置飞书应用凭证：

1. 在飞书开放平台创建应用
2. 获取应用的 App ID 和 App Secret
3. 配置环境变量:

```bash
export LARK_APP_ID="your_app_id"          # 你的应用 ID
export LARK_APP_SECRET="your_app_secret"   # 你的应用密钥
export FOLDER_TOKEN="your_folder_token"    # 指定的文件夹 token
export OAUTH_HOST="localhost"              # OAuth 回调服务器主机（默认：localhost）
export OAUTH_PORT="9997"                   # OAuth 回调服务器端口（默认：9997）
```

## 使用方法

在 Claude 桌面端配置:

```json
"mcpServers": {
    "lark_doc": {
        "command": "mcp-server-my-lark-doc",
        "env": {
            "LARK_APP_ID": "你的应用 ID",
            "LARK_APP_SECRET": "你的应用密钥",
            "FOLDER_TOKEN": "你的文件夹 token",
            "OAUTH_HOST": "localhost",   // 可选
            "OAUTH_PORT": "9997"         // 可选
        }
    }
}
```

### 可用工具

1. get_lark_doc_content（获取文档内容）
   - 用途：获取飞书文档内容
   - 参数：documentUrl (string) - 飞书文档的 URL
   - 返回：文本格式的文档内容
   - 支持：
     - 文档 URL：https://xxx.feishu.cn/docx/xxxxx
     - 知识库 URL：https://xxx.feishu.cn/wiki/xxxxx

2. search_wiki（搜索知识库）
   - 用途：搜索飞书知识库文档
   - 参数：
     - query (string) - 搜索关键词
     - page_size (int, 可选) - 返回结果数量（默认：10）
   - 返回：包含以下字段的 JSON 字符串：
     - title：文档标题
     - url：文档链接
     - create_time：创建时间
     - update_time：最后更新时间

3. list_folder_content（列出文件夹内容）
   - 用途：列出指定文件夹的内容
   - 参数：
     - page_size (int, 可选) - 返回结果数量（默认：10）
   - 返回：包含以下字段的 JSON 字符串：
     - name：文件名
     - type：文件类型
     - token：文件标识
     - url：文件链接
     - create_time：创建时间
     - edit_time：最后编辑时间
     - owner_id：所有者 ID

## 错误信息

常见错误信息及解决方案：

- "Lark client not properly initialized"：飞书客户端未正确初始化，检查你的 LARK_APP_ID 和 LARK_APP_SECRET
- "Invalid Lark document URL format"：无效的飞书文档 URL 格式，验证文档 URL 格式
- "Failed to get document content"：获取文档内容失败，检查文档权限和令牌有效性
- "Failed to get app access token"：获取应用访问令牌失败，检查应用凭证和网络连接
- "Failed to get wiki document real ID"：获取知识库文档真实 ID 失败，检查知识库文档是否存在且你有适当的权限
- "Document content is empty"：文档内容为空，文档可能为空或你可能没有访问其内容的权限
- "Authorization timeout"：授权超时，用户未在 5 分钟内完成授权
- "Folder token not configured"：文件夹令牌未配置，检查你的 FOLDER_TOKEN 环境变量

## 开发说明

### OAuth 回调服务器

默认配置：

- 主机：localhost
- 端口：9997

通过环境变量自定义：

- OAUTH_HOST：设置回调服务器主机
- OAUTH_PORT：设置回调服务器端口

## 许可证

MIT 许可证 