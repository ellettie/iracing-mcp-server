from importlib.metadata import version

__version__ = version("iracing-mcp-server")


from .server import mcp

__all__ = ["mcp", "__version__"]


def main():
    mcp.run(transport="stdio")
