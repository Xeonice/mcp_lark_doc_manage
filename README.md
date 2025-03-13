# MCP Server My Lark Doc

A Model Context Protocol server for searching and accessing Lark(Feishu) documents.

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
uvx mcp-server-my-lark-doc
```

## Configuration

### Get your Lark App ID and App Secret

Visit the Lark Open Platform: https://open.larkoffice.com/app

### Make Sure your Lark App has Permissions below
```
wiki:wiki:readonly
wiki:node:read
docx:document:readonly
search:docs:read
```

### Environment Variables

Before using this MCP server, you need to set up your Lark application credentials:

1. Create a Lark application in Lark Open Platform
2. Get your App ID and App Secret
3. Configure environment variables:

```bash
export LARK_APP_ID="your_app_id"
export LARK_APP_SECRET="your_app_secret"
export OAUTH_HOST="localhost"               # OAuth callback server host (default: localhost)
export OAUTH_PORT="9997"                   # OAuth callback server port (default: 9997)
 ```

## Usage

Configure in Claude desktop:

```json
"mcpServers": {
    "lark_doc": {
        "command": "uvx",
        "args": ["mcp-server-my-lark-doc"],
        "env": {
            "LARK_APP_ID": "your app id",
            "LARK_APP_SECRET": "your app secret",
            "OAUTH_HOST": "localhost",   // optional   
            "OAUTH_PORT": "9997"        // optional  
        }
    }
}
```

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

## Error Messages

Common error messages and their solutions:

- "Lark client not properly initialized": Check your LARK_APP_ID and LARK_APP_SECRET
- "Invalid Lark document URL format": Verify the document URL format
- "Failed to get document content": Check document permissions and token validity
- "Failed to get app access token": Check your application credentials and network connection
- "Failed to get wiki document real ID": Check if the wiki document exists and you have proper permissions
- "Document content is empty": The document might be empty or you might not have access to its content
- "Authorization timeout": ser didn't complete authorization within 5 minutes

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
