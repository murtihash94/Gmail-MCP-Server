# Deploying Gmail MCP Server on Databricks Apps

This guide explains how to deploy the Gmail MCP Server as a Databricks App, enabling AI agents to access Gmail functionality through the Model Context Protocol (MCP) over HTTP.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Local Development](#local-development)
- [Deployment Methods](#deployment-methods)
  - [Method 1: Using databricks bundle CLI](#method-1-using-databricks-bundle-cli)
  - [Method 2: Using databricks apps CLI](#method-2-using-databricks-apps-cli)
- [Connecting to the MCP Server](#connecting-to-the-mcp-server)
- [Authentication Setup](#authentication-setup)
- [Troubleshooting](#troubleshooting)

## Overview

This deployment converts the Gmail MCP Server to run on Databricks Apps using:
- **FastAPI** for HTTP transport (required by Databricks Apps)
- **MCP StreamableHTTP** protocol for client connections
- The original **Node.js/TypeScript** implementation for Gmail operations
- **Python wrapper** to provide the Databricks-compatible entry point

## Prerequisites

Before deploying, ensure you have:

1. **Databricks CLI** installed and configured
   ```bash
   pip install databricks-cli
   ```

2. **uv** (Python package installer) installed
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Node.js and npm** (for the Gmail MCP implementation)
   ```bash
   # The server requires Node.js >= 14.0.0
   ```

4. **Google Cloud OAuth credentials** configured for Gmail API access
   - See the main [README.md](README.md) for instructions on setting up Google Cloud credentials
   - You'll need `gcp-oauth.keys.json` and completed OAuth authentication

5. **Databricks workspace** with permissions to deploy apps

## Local Development

To test the server locally before deploying:

1. Install Python dependencies:
   ```bash
   uv sync
   ```

2. Install Node.js dependencies:
   ```bash
   npm install
   ```

3. Build the TypeScript code:
   ```bash
   npm run build
   ```

4. Start the server locally (changes will trigger a reload):
   ```bash
   uvicorn gmail_mcp_server.app:app --reload
   ```

5. Access the server at `http://localhost:8000`

## Deployment Methods

There are two ways to deploy the Gmail MCP Server on Databricks Apps. Choose the method that best fits your workflow.

### Common Setup Steps

First, configure Databricks authentication:

```bash
export DATABRICKS_CONFIG_PROFILE=<your-profile-name>  # e.g., gmail-mcp-server
databricks auth login --profile "$DATABRICKS_CONFIG_PROFILE"
```

### Method 1: Using `databricks bundle` CLI

This method uses Databricks Asset Bundles for deployment.

1. **Build the Python wheel:**
   ```bash
   uv build --wheel
   ```

2. **Deploy the bundle:**
   ```bash
   databricks bundle deploy -p $DATABRICKS_CONFIG_PROFILE
   ```

3. **Run the app:**
   ```bash
   databricks bundle run gmail-mcp-server -p $DATABRICKS_CONFIG_PROFILE
   ```

The app will be deployed with the name `gmail-mcp-server-bundle` as configured in `databricks.yml`.

**For iterative development:** Repeat steps 1-3 to push your latest modifications to the Databricks app.

### Method 2: Using `databricks apps` CLI

This method provides more direct control over the deployment.

1. **Create a Databricks app:**
   ```bash
   databricks apps create gmail-mcp-server -p $DATABRICKS_CONFIG_PROFILE
   ```

2. **Build the wheel:**
   ```bash
   uv build --wheel
   ```

3. **Upload source code and deploy:**
   ```bash
   DATABRICKS_USERNAME=$(databricks current-user me -p $DATABRICKS_CONFIG_PROFILE | jq -r .userName)
   databricks sync . "/Users/$DATABRICKS_USERNAME/gmail-mcp-server" -p $DATABRICKS_CONFIG_PROFILE
   databricks apps deploy gmail-mcp-server --source-code-path "/Workspace/Users/$DATABRICKS_USERNAME/gmail-mcp-server" -p $DATABRICKS_CONFIG_PROFILE
   ```

4. **Start the app:**
   ```bash
   databricks apps start gmail-mcp-server -p $DATABRICKS_CONFIG_PROFILE
   ```

## Connecting to the MCP Server

After deploying, you can connect to the server using the **Streamable HTTP** transport.

### Connection URL

The server endpoint URL follows this pattern:
```
https://your-app-url.databricksapps.com/mcp/
```

**Important:** The URL must end with `/mcp/` (including the trailing slash).

### Authentication

You need to provide a Bearer token for authentication. Get your token by running:

```bash
databricks auth token -p $DATABRICKS_CONFIG_PROFILE
```

### Example: Python Client

```python
from databricks.sdk import WorkspaceClient
from databricks_mcp import DatabricksOAuthClientProvider
from mcp.client.streamable_http import streamablehttp_client as connect
from mcp import ClientSession

client = WorkspaceClient()

async def main():
    app_url = "https://your-app-url.databricksapps.com/mcp/"
    
    async with connect(app_url, auth=DatabricksOAuthClientProvider(client)) as (
        read_stream,
        write_stream,
        _,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            # Initialize the connection
            await session.initialize()
            
            # List available tools
            tools = await session.list_tools()
            print(f"Available tools: {tools}")
            
            # Send an email
            result = await session.call_tool("send_email", {
                "to": ["recipient@example.com"],
                "subject": "Hello from Databricks",
                "body": "This email was sent via MCP on Databricks Apps!"
            })
            print(f"Email sent: {result}")
```

### Example: Claude Desktop Configuration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "gmail-databricks": {
      "url": "https://your-app-url.databricksapps.com/mcp/",
      "transport": {
        "type": "streamableHttp",
        "headers": {
          "Authorization": "Bearer YOUR_DATABRICKS_TOKEN"
        }
      }
    }
  }
}
```

Replace `YOUR_DATABRICKS_TOKEN` with the token from `databricks auth token`.

## Authentication Setup

The Gmail MCP Server requires Google OAuth credentials to access Gmail. You must configure these credentials before the server can function.

### Setting Up Gmail Credentials

1. **Create Google Cloud Project and OAuth credentials** (see main [README.md](README.md) for detailed instructions)

2. **Configure credentials in Databricks:**

   Since the server runs in Databricks, you need to make your Gmail credentials available:

   **Option A: Environment Variables**
   
   Set these in your Databricks app configuration:
   ```yaml
   env:
     - name: GMAIL_OAUTH_PATH
       value: /path/to/gcp-oauth.keys.json
     - name: GMAIL_CREDENTIALS_PATH
       value: /path/to/credentials.json
   ```

   **Option B: Databricks Secrets**
   
   Store credentials in Databricks Secrets and reference them:
   ```bash
   databricks secrets create-scope gmail-mcp
   databricks secrets put-secret gmail-mcp oauth-keys --json-file gcp-oauth.keys.json
   databricks secrets put-secret gmail-mcp credentials --json-file credentials.json
   ```

   Then reference in your app configuration.

3. **Permissions:**

   Ensure the app service principal has the necessary permissions to:
   - Access the credentials
   - Make external HTTP requests (to Gmail API)

## Troubleshooting

### Build Issues

**Problem:** `uv build` fails with missing dependencies

**Solution:** Ensure you have the correct Python version (>= 3.11):
```bash
uv python install 3.12
```

### Deployment Issues

**Problem:** App fails to start on Databricks

**Solution:** 
1. Check app logs:
   ```bash
   databricks apps logs gmail-mcp-server -p $DATABRICKS_CONFIG_PROFILE
   ```

2. Verify the `app.yaml` command is correct:
   ```yaml
   command: ["uv", "run", "gmail-mcp-server"]
   ```

### Connection Issues

**Problem:** Cannot connect to the MCP server

**Solution:**
1. Verify the URL ends with `/mcp/` (trailing slash is required)
2. Check that your bearer token is valid:
   ```bash
   databricks auth token -p $DATABRICKS_CONFIG_PROFILE
   ```
3. Ensure the app is running:
   ```bash
   databricks apps get gmail-mcp-server -p $DATABRICKS_CONFIG_PROFILE
   ```

### Gmail Authentication Issues

**Problem:** Server cannot access Gmail API

**Solution:**
1. Verify Gmail credentials are properly configured
2. Check that OAuth scopes include Gmail access
3. Ensure the service principal has permission to access credentials
4. Test authentication locally first before deploying

### Port/Network Issues

**Problem:** Server can't be reached

**Solution:**
1. Verify Databricks Apps networking configuration
2. Check if your workspace has the necessary network policies
3. Ensure the app is exposed on the correct port (8000 by default)

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
