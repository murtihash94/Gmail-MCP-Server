# Deploying Gmail MCP Server on Databricks Apps

This guide explains how to deploy the Gmail MCP Server as a Databricks App, enabling AI agents to access Gmail functionality through the Model Context Protocol (MCP) over HTTP.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Architecture](#architecture)
- [Deployment Steps](#deployment-steps)
  - [Method 1: Using databricks bundle CLI](#method-1-using-databricks-bundle-cli)
  - [Method 2: Using databricks apps CLI](#method-2-using-databricks-apps-cli)
- [Connecting to the MCP Server](#connecting-to-the-mcp-server)
- [Authentication Setup](#authentication-setup)
- [Troubleshooting](#troubleshooting)

## Overview

This deployment converts the Gmail MCP Server to run on Databricks Apps using:
- **Node.js/TypeScript** implementation (unchanged from original)
- **Express.js** with **Server-Sent Events (SSE)** for HTTP transport
- **Databricks Apps** infrastructure files (databricks.yml, app.yaml, pyproject.toml)
- **Python build tools** for packaging compatibility with Databricks

The implementation keeps the Gmail MCP server's Node.js/TypeScript core intact while adding HTTP/SSE transport and the Databricks deployment structure.

## Prerequisites

Before deploying, ensure you have:

1. **Databricks CLI** installed and configured
   ```bash
   pip install databricks-cli
   ```

2. **uv** (Python package installer) installed for build tools
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Node.js** >= 14.0.0 (the server is implemented in TypeScript/Node.js)
   ```bash
   node --version  # Should be >= v14.0.0
   ```

4. **npm** for Node.js dependencies
   ```bash
   npm --version
   ```

5. **Google Cloud OAuth credentials** configured for Gmail API access
   - See the main [README.md](README.md) for instructions on setting up Google Cloud credentials
   - You'll need `gcp-oauth.keys.json` and completed OAuth authentication

6. **Databricks workspace** with permissions to deploy apps

## Architecture

```
┌─────────────────────────────────────┐
│   Databricks Apps Environment       │
│                                     │
│  ┌──────────────────────────────┐  │
│  │  Node.js HTTP Server         │  │
│  │  (src/http-server.ts)        │  │
│  │                               │  │
│  │  ┌────────────────────────┐  │  │
│  │  │  Express.js + SSE      │  │  │
│  │  │  Transport Layer       │  │  │
│  │  └────────┬───────────────┘  │  │
│  │           │                   │  │
│  │  ┌────────▼───────────────┐  │  │
│  │  │  Gmail MCP Server      │  │  │
│  │  │  (Core Implementation) │  │  │
│  │  │  • Send Email          │  │  │
│  │  │  • Read Email          │  │  │
│  │  │  • Labels, Filters...  │  │  │
│  │  └────────┬───────────────┘  │  │
│  │           │                   │  │
│  │  ┌────────▼───────────────┐  │  │
│  │  │  Google Gmail API      │  │  │
│  │  └────────────────────────┘  │  │
│  └──────────────────────────────┘  │
│                                     │
│  Accessed via: /mcp/sse endpoint    │
└─────────────────────────────────────┘
```

## Deployment Steps

### Common Setup

1. **Configure Databricks authentication:**
   ```bash
   export DATABRICKS_CONFIG_PROFILE=gmail-mcp-server
   databricks auth login --profile "$DATABRICKS_CONFIG_PROFILE"
   ```

2. **Install Node.js dependencies:**
   ```bash
   npm install
   ```

3. **Build the TypeScript code:**
   ```bash
   npm run build
   ```

4. **Install Python build dependencies:**
   ```bash
   uv sync
   ```

### Method 1: Using `databricks bundle` CLI

This method uses Databricks Asset Bundles for deployment.

1. **Build the Python wheel (this triggers the build hook):**
   ```bash
   uv build --wheel
   ```
   
   This will:
   - Create a `.build` directory
   - Copy `dist/` (compiled TypeScript)
   - Copy `node_modules/` (Node.js dependencies)
   - Copy `package.json`
   - Copy `app.yaml` configuration

2. **Deploy the bundle:**
   ```bash
   databricks bundle deploy -p $DATABRICKS_CONFIG_PROFILE
   ```

3. **Run the app:**
   ```bash
   databricks bundle run gmail-mcp-server -p $DATABRICKS_CONFIG_PROFILE
   ```

The app will be deployed with the name configured in `databricks.yml`.

**For iterative development:** Rebuild the wheel and repeat steps 2-3 to push updates.

### Method 2: Using `databricks apps` CLI

This method provides more direct control over the deployment.

1. **Build the wheel:**
   ```bash
   npm run build
   uv build --wheel
   ```

2. **Create a Databricks app:**
   ```bash
   databricks apps create gmail-mcp-server -p $DATABRICKS_CONFIG_PROFILE
   ```

3. **Upload and deploy:**
   ```bash
   DATABRICKS_USERNAME=$(databricks current-user me -p $DATABRICKS_CONFIG_PROFILE | jq -r .userName)
   databricks sync .build "/Users/$DATABRICKS_USERNAME/gmail-mcp-server" -p $DATABRICKS_CONFIG_PROFILE
   databricks apps deploy gmail-mcp-server \
     --source-code-path "/Workspace/Users/$DATABRICKS_USERNAME/gmail-mcp-server" \
     -p $DATABRICKS_CONFIG_PROFILE
   ```

4. **Start the app:**
   ```bash
   databricks apps start gmail-mcp-server -p $DATABRICKS_CONFIG_PROFILE
   ```

## Connecting to the MCP Server

After deploying, you can connect to the server using the **SSE (Server-Sent Events)** transport.

### Connection URL

The server provides these endpoints:
- **Landing page**: `https://your-app-url.databricksapps.com/`
- **MCP SSE endpoint**: `https://your-app-url.databricksapps.com/mcp/sse`
- **Health check**: `https://your-app-url.databricksapps.com/health`

### Authentication

You need to provide a Bearer token for authentication. Get your token:

```bash
databricks auth token -p $DATABRICKS_CONFIG_PROFILE
```

### Example: Python Client with SSE

```python
from mcp import ClientSession
from mcp.client.sse import sse_client
import httpx

# Create HTTP client with auth
async with httpx.AsyncClient(
    headers={"Authorization": f"Bearer {your_databricks_token}"}
) as http_client:
    # Connect to SSE endpoint
    async with sse_client(
        "https://your-app-url.databricksapps.com/mcp/sse",
        http_client=http_client
    ) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize
            await session.initialize()
            
            # List available tools
            tools = await session.list_tools()
            print(f"Available tools: {tools}")
            
            # Send an email
            result = await session.call_tool("send_email", {
                "to": ["recipient@example.com"],
                "subject": "Hello from Databricks",
                "body": "This email was sent via MCP!"
            })
            print(f"Result: {result}")
```

### Example: MCP Inspector

```bash
# Install MCP inspector
npx @modelcontextprotocol/inspector

# Connect to your deployed server
# URL: https://your-app-url.databricksapps.com/mcp/sse
# Add Authorization header: Bearer YOUR_TOKEN
```

## Authentication Setup

The Gmail MCP Server requires Google OAuth credentials to access Gmail.

### Option 1: Use Databricks Secrets (Recommended)

1. **Create a secret scope:**
   ```bash
   databricks secrets create-scope gmail-mcp -p $DATABRICKS_CONFIG_PROFILE
   ```

2. **Store credentials:**
   ```bash
   # Store OAuth keys
   databricks secrets put-secret gmail-mcp oauth-keys \
     --string-value "$(cat ~/.gmail-mcp/gcp-oauth.keys.json)" \
     -p $DATABRICKS_CONFIG_PROFILE
   
   # Store credentials
   databricks secrets put-secret gmail-mcp credentials \
     --string-value "$(cat ~/.gmail-mcp/credentials.json)" \
     -p $DATABRICKS_CONFIG_PROFILE
   ```

3. **Update app.yaml to reference secrets:**
   ```yaml
   command: ["node", "dist/http-server.js"]
   env:
     - name: PORT
       value: "8000"
     - name: GMAIL_OAUTH_PATH
       valueFrom:
         secretKeyRef:
           name: oauth-keys
           scope: gmail-mcp
     - name: GMAIL_CREDENTIALS_PATH
       valueFrom:
         secretKeyRef:
           name: credentials
           scope: gmail-mcp
   ```

### Option 2: Use DBFS

1. **Upload credentials to DBFS:**
   ```bash
   databricks fs mkdirs /gmail-mcp -p $DATABRICKS_CONFIG_PROFILE
   databricks fs cp ~/.gmail-mcp/gcp-oauth.keys.json dbfs:/gmail-mcp/ -p $DATABRICKS_CONFIG_PROFILE
   databricks fs cp ~/.gmail-mcp/credentials.json dbfs:/gmail-mcp/ -p $DATABRICKS_CONFIG_PROFILE
   ```

2. **The app.yaml already references these paths:**
   ```yaml
   env:
     - name: GMAIL_OAUTH_PATH
       value: /dbfs/gmail-mcp/gcp-oauth.keys.json
     - name: GMAIL_CREDENTIALS_PATH
       value: /dbfs/gmail-mcp/credentials.json
   ```

## Troubleshooting

### Build Issues

**Problem:** `npm run build` fails

**Solution:** 
```bash
# Clean and reinstall
rm -rf node_modules package-lock.json dist
npm install
npm run build
```

**Problem:** `uv build` fails

**Solution:**
```bash
# Ensure you have Python 3.11+
uv python install 3.12
uv sync
uv build --wheel
```

### Deployment Issues

**Problem:** App fails to start on Databricks

**Solution:**
1. Check app logs:
   ```bash
   databricks apps logs gmail-mcp-server -p $DATABRICKS_CONFIG_PROFILE
   ```

2. Verify Node.js is available in the Databricks environment
3. Check that all files were copied to .build:
   ```bash
   ls -la .build/
   # Should contain: dist/, node_modules/, package.json, app.yaml
   ```

### Connection Issues

**Problem:** Cannot connect to SSE endpoint

**Solution:**
1. Verify the endpoint URL is correct: `https://your-app.databricksapps.com/mcp/sse`
2. Check bearer token is valid:
   ```bash
   curl -H "Authorization: Bearer $(databricks auth token -p $DATABRICKS_CONFIG_PROFILE)" \
     https://your-app.databricksapps.com/health
   ```
3. Ensure app is running:
   ```bash
   databricks apps get gmail-mcp-server -p $DATABRICKS_CONFIG_PROFILE
   ```

### Gmail Authentication Issues

**Problem:** Server cannot access Gmail API

**Solution:**
1. Verify credentials are accessible by the app
2. Check OAuth scopes include Gmail access
3. Test authentication locally first:
   ```bash
   npm run auth  # Run authentication flow locally
   ```
4. Ensure credentials are in the correct format (JSON)

### Memory/Resource Issues

**Problem:** App crashes due to memory limits

**Solution:**
- The Node.js implementation is lightweight, but `node_modules` can be large
- Consider using a `.npmignore` to exclude unnecessary packages from deployment
- Monitor app resource usage in Databricks Apps console

## Project Structure

```
Gmail-MCP-Server/
├── src/
│   ├── index.ts              # Main MCP server (stdio transport)
│   ├── http-server.ts        # HTTP/SSE server entry point ← NEW
│   ├── label-manager.ts      # Gmail label management
│   ├── filter-manager.ts     # Gmail filter management
│   └── utl.ts                # Utility functions
├── src_python/
│   └── gmail_mcp_server/     # Python wrapper (minimal)
│       ├── static/
│       │   └── index.html    # Landing page ← NEW
│       ├── __init__.py
│       ├── app.py            # FastAPI wrapper (unused in Node.js mode)
│       └── main.py
├── hooks/
│   └── apps_build.py         # Build hook for Databricks ← NEW
├── dist/                     # Compiled TypeScript (generated)
├── .build/                   # Databricks deployment package (generated)
├── databricks.yml            # Databricks bundle config ← NEW
├── app.yaml                  # App runtime config ← NEW
├── pyproject.toml            # Python packaging config ← NEW
├── package.json              # Node.js dependencies
└── tsconfig.json             # TypeScript config
```

## Additional Resources

- [Main README](README.md) - Full feature list and Gmail setup
- [Databricks MCP Labs](https://github.com/databrickslabs/mcp) - Reference implementations
- [MCP Documentation](https://modelcontextprotocol.io/) - Model Context Protocol specification
- [Databricks Apps Documentation](https://docs.databricks.com/apps/) - Databricks Apps guide

## Support

For issues specific to:
- **Gmail MCP Server**: Open an issue on [GitHub](https://github.com/murtihash94/Gmail-MCP-Server/issues)
- **Databricks Apps**: Consult Databricks documentation or support
- **MCP Protocol**: See [MCP GitHub](https://github.com/modelcontextprotocol)

