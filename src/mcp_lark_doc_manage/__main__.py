"""
Main entry point for running the package as a module with 'python -m mcp_lark_doc_manage'.

This allows the package to be executed directly using:
    python -m mcp_lark_doc_manage

Which is different from running as a script using:
    python mcp_lark_doc_manage/__init__.py
"""

import sys
from mcp_lark_doc_manage import main

if __name__ == "__main__":
    sys.exit(main())