from .server import mcp

def main():
    """MCP Lark Doc Server - Lark document access functionality for MCP"""
    mcp.run(transport="stdio")