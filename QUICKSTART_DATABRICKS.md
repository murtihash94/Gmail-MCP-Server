# Quick Start: Databricks Deployment

## Prerequisites Checklist
- [ ] Databricks CLI installed (`pip install databricks-cli`)
- [ ] `uv` installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- [ ] Node.js >= 14.0.0 installed
- [ ] Databricks workspace access
- [ ] Gmail OAuth credentials configured (see main README.md)

## One-Command Deployment

```bash
./deploy-databricks.sh your-profile-name
```

## Manual Deployment Steps

### 1. Setup
```bash
export DATABRICKS_CONFIG_PROFILE=your-profile-name
databricks auth login --profile "$DATABRICKS_CONFIG_PROFILE"
```

### 2. Build
```bash
npm install
npm run build
uv build --wheel
```

### 3. Deploy
```bash
databricks bundle deploy -p "$DATABRICKS_CONFIG_PROFILE"
databricks bundle run gmail-mcp-server -p "$DATABRICKS_CONFIG_PROFILE"
```

### 4. Connect
```bash
# Get your app URL
databricks apps get gmail-mcp-server -p "$DATABRICKS_CONFIG_PROFILE"

# Get auth token
databricks auth token -p "$DATABRICKS_CONFIG_PROFILE"
```

## Connection Example

```python
from mcp import ClientSession
from mcp.client.sse import sse_client
import httpx

token = "YOUR_DATABRICKS_TOKEN"
url = "https://your-app.databricksapps.com/mcp/sse"

async with httpx.AsyncClient(
    headers={"Authorization": f"Bearer {token}"}
) as client:
    async with sse_client(url, http_client=client) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print(tools)
```

## Key Files

- `databricks.yml` - Bundle configuration
- `app.yaml` - App runtime configuration
- `pyproject.toml` - Python packaging
- `hooks/apps_build.py` - Build process
- `src/http-server.ts` - HTTP/SSE entry point

## Endpoints

- `/` - Landing page with documentation
- `/mcp/sse` - MCP Server-Sent Events endpoint
- `/mcp/messages` - POST endpoint for messages
- `/health` - Health check

## Troubleshooting

**App won't start?**
```bash
databricks apps logs gmail-mcp-server -p "$DATABRICKS_CONFIG_PROFILE"
```

**Build fails?**
```bash
rm -rf node_modules dist .build
npm install && npm run build
uv build --wheel
```

**Can't connect?**
- Verify URL ends with `/mcp/sse`
- Check auth token is valid
- Confirm app is running

## Full Documentation

See [DATABRICKS_DEPLOYMENT.md](DATABRICKS_DEPLOYMENT.md) for complete instructions.
