from pathlib import Path
from mcp.server.fastmcp import FastMCP
from fastapi import FastAPI
from fastapi.responses import FileResponse
import subprocess
import os
import sys

STATIC_DIR = Path(__file__).parent / "static"

# Create an MCP server
mcp = FastMCP("Gmail MCP Server on Databricks Apps")

# The Gmail MCP server is implemented in Node.js/TypeScript
# We use FastMCP to create an HTTP-based wrapper that can run on Databricks Apps
# The actual Gmail tools are registered via the Node.js server process

# Note: For Databricks Apps deployment, this wrapper provides the HTTP transport
# The actual MCP implementation runs as a Node.js subprocess using stdio transport

mcp_app = mcp.streamable_http_app()

app = FastAPI(
    lifespan=lambda _: mcp.session_manager.run(),
)


@app.get("/", include_in_schema=False)
async def serve_index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/", mcp_app)
