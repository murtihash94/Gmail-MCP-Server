# Quick Start Guide

## Testing the Python/FastMCP Version Locally

1. **Install dependencies:**
   ```bash
   # Using pip (recommended for testing)
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   
   # OR using uv (for Databricks deployment)
   uv sync
   ```

2. **Set up Gmail credentials:**
   
   Follow the Gmail API setup instructions in `DATABRICKS_DEPLOYMENT.md` to create OAuth credentials and authenticate.

3. **Run the server locally:**
   ```bash
   # Method 1: Using uvicorn directly
   uvicorn gmail_mcp_server.app:app --reload
   
   # Method 2: Using the entry point
   python -m gmail_mcp_server.main
   ```

4. **Access the server:**
   - Web interface: http://localhost:8000
   - MCP endpoint: http://localhost:8000/mcp/

5. **Test with MCP Inspector:**
   ```bash
   npx @modelcontextprotocol/inspector http://localhost:8000/mcp/
   ```

## Testing the TypeScript/Node.js Version Locally

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Build:**
   ```bash
   npm run build
   ```

3. **Authenticate:**
   ```bash
   npm run auth
   ```

4. **Configure Claude Desktop:**
   
   Add to your `claude_desktop_config.json`:
   ```json
   {
     "mcpServers": {
       "gmail": {
         "command": "node",
         "args": ["/path/to/Gmail-MCP-Server/dist/index.js"]
       }
     }
   }
   ```

## Comparing the Two Versions

| Feature | TypeScript (stdio) | Python (HTTP) |
|---------|-------------------|---------------|
| Transport | stdio | Streamable HTTP |
| Deployment | Local only | Databricks Apps |
| Authentication | OAuth with browser | Pre-configured OAuth |
| Use Case | Desktop AI assistants | Enterprise/Cloud |
| Entry Point | `dist/index.js` | `gmail_mcp_server.app:app` |

Both versions provide the same Gmail functionality through different transports.
