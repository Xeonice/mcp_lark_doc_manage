"""
Main entry point for MCP Lark Doc Server.

This allows the package to be executed directly using:
    python -m mcp_lark_doc_manage

Which is different from running as a script using:
    python mcp_lark_doc_manage/__init__.py
"""

import sys
from mcp_lark_doc_manage import main

def module_main():
    """Main entry point when run as a module."""
    sys.exit(main(sys.argv[1:]))

if __name__ == "__main__":
    module_main()