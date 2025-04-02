import os

# Only import server module if not in testing environment
if os.getenv("TESTING") != "true":
    from mcp_lark_doc_manage.server import mcp, _auth_flow

from .markdown_converter import convert_markdown_to_blocks
import asyncio
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """MCP Lark Doc Server - Lark document access functionality for MCP"""
    try:
        logger.info("Starting MCP Lark Doc Server...")
        # Run MCP server
        mcp.run(transport="stdio")
        print(f"LARK_APP_ID: {os.getenv('LARK_APP_ID')}")
        print(f"LARK_APP_SECRET: {os.getenv('LARK_APP_SECRET')}")
        print(f"OAUTH_HOST: {os.getenv('OAUTH_HOST')}")
        print(f"OAUTH_PORT: {os.getenv('OAUTH_PORT')}")
        print(f"FOLDER_TOKEN: {os.getenv('FOLDER_TOKEN')}")
    except Exception as e:
        logger.error(f"Error starting server: {str(e)}", exc_info=True)
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

__all__ = ['mcp', '_auth_flow']