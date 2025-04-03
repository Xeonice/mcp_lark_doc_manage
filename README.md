# MCP Lark Doc Manage

A Model Context Protocol server for searching and accessing Lark(Feishu) documents.

[中文文档](README_zh.md)

> **Important**: Before using this MCP Server, you need to have a Lark Enterprise Application. If you haven't created one yet, please follow the setup instructions below.

## Features

### Document Content Access
- Supports both Lark Doc and Wiki document types
- Automatically handles document type detection and ID extraction
- Returns raw content in text format for LLM processing

### Authentication
- OAuth-based user authentication
- Automatic token refresh and expiration management
- Customizable OAuth callback server

### Error Handling
- Comprehensive error reporting for authentication issues
- Clear feedback for invalid document URLs
- Detailed error messages for troubleshooting

## Installation

```bash
uvx mcp-lark-doc-manage
```

## Configuration

### Create Your Lark Enterprise Application

1. Visit [Lark Open Platform](https://open.larkoffice.com/)
2. Click "Developer Console" in the top right corner
3. Click "Create Custom App"
4. Fill in the basic information:
   - App Name
   - App Description
   - App Icon
5. In the "Security Settings" section:
   - Add your domain to "Request Domain Name Whitelist"
   - Configure OAuth 2.0 settings
6. Enable required capabilities and apply for permissions in "Permission Management"
7. Submit for review and wait for approval

For detailed instructions, see [Custom App Development Process](https://open.feishu.cn/document/home/introduction-to-custom-app-development/self-built-application-development-process).

### Get App ID and App Secret

1. Get App ID:
   - Go to your app in [Developer Console](https://open.larkoffice.com/app)
   - Find "App ID" (also called "Client ID") in "Credentials & Basic Info"
   - It usually starts with "cli_" for internal apps

2. Get App Secret:
   - In the same "Credentials & Basic Info" page
   - Find "App Secret" (also called "Client Secret")
   - Click "View" to see the secret
   - Note: Keep your App Secret secure and never share it publicly

### Get Folder Token

To get a folder token:

1. Open the target folder in Lark
2. Copy the folder URL, for example: `https://xxx.feishu.cn/drive/folder/xxx`
3. The last segment in the URL is your folder token
4. Alternative method:
   - Use the Drive API to list folders
   - Find the target folder's token in the response

Note: Make sure your app has the `drive:drive:readonly` permission to access folders.

### Required Permissions
```wiki:wiki:readonly   # Wiki read-only access
wiki:node:read      # Wiki node read access
docx:document:readonly   # Document read-only access
search:docs:read    # Document search access
drive:drive:readonly    # Drive read-only access
```

### Environment Variables

Before using this MCP server, you need to set up your Lark application credentials:

1. Create a Lark application in Lark Open Platform
2. Get your App ID and App Secret
3. Configure environment variables:

```bash
export LARK_APP_ID="your_app_id"
export LARK_APP_SECRET="your_app_secret"
export FOLDER_TOKEN="your_folder_token"    # Specified folder token
export OAUTH_HOST="localhost"              # OAuth callback server host (default: localhost)
export OAUTH_PORT="9997"                   # OAuth callback server port (default: 9997)
```

## Usage

Configure in Claude desktop:

```json
"mcpServers": {
    "lark_doc": {
        "command": "/path/to/your/uvx",
        "args": [
            "mcp-lark-doc-manage"
        ],
        "env": {
            "LARK_APP_ID": "your_app_id",
            "LARK_APP_SECRET": "your_app_secret",
            "OAUTH_HOST": "localhost",
            "OAUTH_PORT": "9997",
            "FOLDER_TOKEN": "your_folder_token",
            "DEBUG": "1"  // optional, enable debug mode
        }
    }
}
```

Note: Replace `/path/to/your/uvx` with your actual uvx path (e.g., `/Users/username/anaconda3/bin/uvx`).

### Available Tools

1. get_lark_doc_content
   - Purpose: Retrieve document content from Lark
   - Args: documentUrl (string) - The URL of the Lark document
   - Returns: Document content in text format
   - Supports:
     - Doc URLs: https://xxx.feishu.cn/docx/xxxxx
     - Wiki URLs: https://xxx.feishu.cn/wiki/xxxxx

2. search_wiki
   - Purpose: Search documents in Lark Wiki
   - Args: 
     - query (string) - Search keywords
     - page_size (int, optional) - Number of results to return (default: 10)
   - Returns: JSON string containing search results with following fields:
     - title: Document title
     - url: Document URL
     - create_time: Document creation time
     - update_time: Document last update time

3. list_folder_content
   - Purpose: List contents of a specified folder
   - Args:
     - page_size (int, optional) - Number of results to return (default: 10)
   - Returns: JSON string containing file list with following fields:
     - name: File name
     - type: File type
     - token: File token
     - url: File URL
     - create_time: Creation time
     - edit_time: Last edit time
     - owner_id: Owner ID

4. create_doc
   - Purpose: Create a new Lark document with content
   - Args:
     - title (string) - Document title
     - content (string, optional) - Document content in Markdown format
     - target_space_id (string, optional) - Target wiki space ID to move the document to
   - Returns: JSON string containing:
     - document_id: Created document ID
     - title: Document title
     - url: Document URL
   - Features:
     - Supports Markdown content conversion
     - Optional wiki space integration
     - Automatic folder placement

## Error Messages

Common error messages and their solutions:

- "Lark client not properly initialized": Check your LARK_APP_ID and LARK_APP_SECRET
- "Invalid Lark document URL format": Verify the document URL format
- "Failed to get document content": Check document permissions and token validity
- "Failed to get app access token": Check your application credentials and network connection
- "Failed to get wiki document real ID": Check if the wiki document exists and you have proper permissions
- "Document content is empty": The document might be empty or you might not have access to its content
- "Authorization timeout": User didn't complete authorization within 5 minutes
- "Folder token not configured": Check your FOLDER_TOKEN environment variable

## Development Notes

### OAuth Callback Server

Default configuration:

- Host: localhost
- Port: 9997

Customize via environment variables:

- OAUTH_HOST: Set callback server host
- OAUTH_PORT: Set callback server port

## License

MIT License
