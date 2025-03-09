from .server import serve


def main():
    """MCP Lark Doc Server - Lark document access functionality for MCP"""
    import asyncio
    asyncio.run(serve())