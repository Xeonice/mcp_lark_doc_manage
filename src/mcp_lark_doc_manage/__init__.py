import os
import asyncio
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize mcp as None
mcp = None

# Only import server module if not in testing environment
if os.getenv("TESTING") != "true":
    try:
        # Try relative import first (when imported as a module)
        from .server import mcp, _auth_flow
    except ImportError:
        # Fall back to absolute import (when run as a script)
        from mcp_lark_doc_manage.server import mcp, _auth_flow

# Use try-except to handle both when run as a script and when imported as a module
try:
    # Try relative import first (when imported as a module)
    from .markdown_converter import convert_markdown_to_blocks
except ImportError:
    # Fall back to absolute import (when run as a script)
    from mcp_lark_doc_manage.markdown_converter import convert_markdown_to_blocks

def main(args=None):
    """MCP Lark Doc Server - Lark document access functionality for MCP
    
    Args:
        args: Command line arguments (used when called as an entry point)
        
    Returns:
        int: Exit code (0 for success, 1 for error)
        
    Raises:
        SystemExit: Always raises SystemExit with appropriate exit code
    """
    if args is None:
        args = sys.argv[1:]
        
    try:
        logger.info("Starting MCP Lark Doc Server...")
        # Log environment variables for debugging
        print(f"LARK_APP_ID: {os.getenv('LARK_APP_ID')}")
        print(f"LARK_APP_SECRET: {os.getenv('LARK_APP_SECRET')}")
        print(f"OAUTH_HOST: {os.getenv('OAUTH_HOST')}")
        print(f"OAUTH_PORT: {os.getenv('OAUTH_PORT')}")
        print(f"FOLDER_TOKEN: {os.getenv('FOLDER_TOKEN')}")
        
        # Import mcp in testing environment
        global mcp
        if mcp is None:
            from mcp_lark_doc_manage.server import mcp
        
        # Run MCP server - this may close standard I/O streams
        mcp.run(transport="stdio")
        # This code will never be reached when running with stdio transport
        sys.exit(0)
    except FileNotFoundError as e:
        # Handle missing file errors specifically
        error_msg = f"File not found error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        print(f"Error: {error_msg}", file=sys.stderr)
        sys.exit(1)
    except ImportError as e:
        # Handle import errors specifically
        error_msg = f"Import error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        print(f"Error: {error_msg}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        # Handle all other errors
        error_msg = f"Error starting server: {str(e)}"
        logger.error(error_msg, exc_info=True)
        print(f"Error: {error_msg}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    sys.exit(main())

__all__ = ['mcp', '_auth_flow']