from .server import mcp, _auth_flow
import asyncio

def main():
    """MCP Lark Doc Server - Lark document access functionality for MCP"""
    
    # Run MCP server
    mcp.run(transport="stdio")