# Gmail MCP Server for Databricks Apps

A Model Context Protocol (MCP) server for Gmail integration deployed on Databricks Apps. This server enables AI assistants to manage Gmail through natural language interactions, with full support for email management, attachments, labels, and filters.

![Test Status](https://github.com/murtihash94/Gmail-MCP-Server/actions/workflows/test.yml/badge.svg)

## Overview

This is a Python-based Gmail MCP server designed to run on Databricks Apps, providing enterprise-grade Gmail automation capabilities. It follows the Databricks MCP server template and supports streamable HTTP transport for seamless integration with AI agents.

## Features

- **Email Management**
  - Send emails with subject, content, **attachments**, and recipients
  - Create draft emails
  - Read email messages by ID with advanced MIME structure handling
  - Search emails with various criteria (subject, sender, date range)
  - Download email attachments to local filesystem
  - Support for HTML emails and multipart messages
  - Full support for international characters

- **Label Management**
  - Create, update, delete, and list labels
  - Get or create labels (find existing or create new)
  - Modify email labels (move to folders, mark read/unread)
  - Full integration with Gmail's label system

- **Batch Operations**
  - Batch modify emails (up to 50 at once)
  - Batch delete emails
  - Efficient processing for bulk operations

- **Filter Management**
  - Create custom Gmail filters
  - Use pre-built filter templates
  - List, get, and delete filters
  - Templates for common scenarios (fromSender, withSubject, withAttachments, etc.)

## Prerequisites

- Databricks CLI installed and configured
- `uv` package manager installed ([installation guide](https://docs.astral.sh/uv/getting-started/installation/))
- Google Cloud Project with Gmail API enabled
- OAuth 2.0 credentials (Desktop app or Web application)

## Gmail API Setup

Before deploying, you need to set up Gmail API access:

1. **Create a Google Cloud Project:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the Gmail API for your project

2. **Create OAuth 2.0 Credentials:**
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Choose either "Desktop app" or "Web application" as application type
   - For Web application, add `http://localhost:3000/oauth2callback` to authorized redirect URIs
   - Download the JSON file of your client's OAuth keys
   - Rename the key file to `gcp-oauth.keys.json`

3. **Authenticate Locally (Before Deployment):**
   ```bash
   # Create config directory
   mkdir -p ~/.gmail-mcp
   
   # Copy OAuth keys
   cp gcp-oauth.keys.json ~/.gmail-mcp/
   
   # Run authentication (this will open a browser)
   # You'll need to run the old TypeScript version for initial auth, or manually create credentials
   # The credentials will be saved to ~/.gmail-mcp/credentials.json
   ```

## Local Development

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Start the server locally:**
   ```bash
   uvicorn gmail_mcp_server.app:app --reload
   ```

   The server will be available at `http://localhost:8000`

3. **Test the server:**
   Open your browser to `http://localhost:8000` to see the web interface.

## Deploying to Databricks Apps

There are two ways to deploy the server on Databricks Apps: using the `databricks apps` CLI or using the `databricks bundle` CLI.

### Authentication Setup

First, configure Databricks authentication:
```bash
export DATABRICKS_CONFIG_PROFILE=<your-profile-name>  # e.g. gmail-mcp-server
databricks auth login --profile "$DATABRICKS_CONFIG_PROFILE"
```

**Important**: Before deploying, ensure you have Gmail credentials configured:
- The `~/.gmail-mcp/credentials.json` file must exist with valid OAuth tokens
- Copy this file to your Databricks workspace or configure it as a secret

### Method 1: Using `databricks apps` CLI

1. **Create a Databricks app:**
   ```bash
   databricks apps create gmail-mcp-server
   ```

2. **Upload the source code and deploy:**
   ```bash
   DATABRICKS_USERNAME=$(databricks current-user me | jq -r .userName)
   databricks sync . "/Users/$DATABRICKS_USERNAME/gmail-mcp-server"
   databricks apps deploy gmail-mcp-server --source-code-path "/Workspace/Users/$DATABRICKS_USERNAME/gmail-mcp-server"
   ```

### Method 2: Using `databricks bundle` CLI

1. **Build the wheel:**
   ```bash
   uv build --wheel
   ```

2. **Deploy and run:**
   ```bash
   databricks bundle deploy -p $DATABRICKS_CONFIG_PROFILE
   databricks bundle run gmail-mcp-server -p $DATABRICKS_CONFIG_PROFILE
   ```

## Connecting to the MCP Server

After deployment, connect to your server using the `Streamable HTTP` transport.

### Connection URL

```
https://your-app-url.usually.ends.with.databricksapps.com/mcp/
```

**Note**: The URL must end with `/mcp/` (including the trailing slash).

### Authentication

Get your Databricks access token:
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
            await session.initialize()
            
            # Send an email
            result = await session.call_tool("send_email", {
                "to": ["recipient@example.com"],
                "subject": "Hello from Databricks!",
                "body": "This email was sent via Gmail MCP Server"
            })
            print(result)
```

### Example: Claude Desktop Configuration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "gmail-databricks": {
      "transport": "streamable_http",
      "url": "https://your-app-url.databricksapps.com/mcp/",
      "headers": {
        "Authorization": "Bearer <your-databricks-token>"
      }
    }
  }
}
```

## Available Tools

The server provides the following tools:

| Tool | Description |
|------|-------------|
| `send_email` | Send an email with optional attachments |
| `draft_email` | Create a draft email |
| `read_email` | Read email content by ID |
| `search_emails` | Search emails with Gmail syntax |
| `modify_email` | Add/remove labels from emails |
| `delete_email` | Permanently delete an email |
| `list_email_labels` | List all Gmail labels |
| `batch_modify_emails` | Modify labels for multiple emails |
| `batch_delete_emails` | Delete multiple emails |
| `create_label` | Create a new Gmail label |
| `update_label` | Update an existing label |
| `delete_label` | Delete a Gmail label |
| `get_or_create_label` | Get existing or create new label |
| `download_attachment` | Download email attachment |
| `create_filter` | Create a custom Gmail filter |
| `list_filters` | List all Gmail filters |
| `get_filter` | Get filter details |
| `delete_filter` | Delete a Gmail filter |
| `create_filter_from_template` | Create filter from template |

## Configuration

### Environment Variables

- `GMAIL_OAUTH_PATH`: Path to OAuth keys file (default: `~/.gmail-mcp/gcp-oauth.keys.json`)
- `GMAIL_CREDENTIALS_PATH`: Path to credentials file (default: `~/.gmail-mcp/credentials.json`)

### Databricks Secrets

For production deployments, store Gmail credentials as Databricks secrets:

```bash
databricks secrets create-scope gmail-mcp
databricks secrets put-secret gmail-mcp credentials --string-value "$(cat ~/.gmail-mcp/credentials.json)"
```

Then modify the app to read from secrets instead of local files.

## Security Notes

- OAuth credentials are stored securely in your configured path
- Never commit credentials to version control
- Use Databricks secrets for production deployments
- Regularly review and revoke unused access in Google Account settings
- The server uses offline access to maintain persistent authentication
- Attachment files are processed locally and never stored permanently

## Troubleshooting

### OAuth Keys Not Found
- Ensure `gcp-oauth.keys.json` is in the correct location
- Check file permissions

### Invalid Credentials Format
- Verify the OAuth keys file contains either `web` or `installed` credentials
- For web applications, verify redirect URIs are configured correctly

### Deployment Fails
- Ensure you have valid Databricks credentials
- Check that the workspace path is accessible
- Verify the app name doesn't conflict with existing apps

### Server Errors
- Check Databricks app logs: `databricks apps logs gmail-mcp-server`
- Verify Gmail credentials are valid and not expired
- Ensure Gmail API is enabled in Google Cloud Project

## Development

### Project Structure

```
.
├── databricks.yml           # Databricks bundle configuration
├── app.yaml                 # Databricks app configuration
├── pyproject.toml          # Python project configuration
├── hooks/
│   └── apps_build.py       # Build hook for Databricks Apps
└── src/
    └── gmail_mcp_server/
        ├── __init__.py     # Package initialization
        ├── main.py         # Entry point
        ├── app.py          # FastMCP server implementation
        └── static/
            └── index.html  # Web interface
```

### Adding New Tools

To add a new Gmail tool:

1. Add a new function decorated with `@mcp.tool()` in `app.py`
2. Implement the Gmail API calls
3. Add appropriate error handling
4. Update this README with the new tool documentation

## Migration from TypeScript Version

This is a Python port of the original TypeScript Gmail MCP server. Key changes:

- **Language**: TypeScript → Python
- **Framework**: MCP SDK → FastMCP
- **Transport**: stdio → Streamable HTTP
- **Deployment**: npm package → Databricks Apps
- **Dependencies**: Node.js packages → Python packages

All functionality from the TypeScript version has been preserved.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

Please note that this project is provided AS-IS. For issues:

- File a GitHub issue in this repository
- Check the Databricks MCP documentation
- Review Gmail API documentation

## License

MIT

## References

- [Databricks MCP Template](https://github.com/murtihash94/custom_mcp_server_databricks)
- [Databricks Apps Documentation](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Gmail API Documentation](https://developers.google.com/gmail/api)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
