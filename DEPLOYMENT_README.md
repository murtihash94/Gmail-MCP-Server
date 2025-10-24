# Gmail MCP Server - Databricks Apps Deployment

## ✅ Conversion Status: COMPLETE

This repository has been successfully converted to support deployment on Databricks Apps while maintaining backward compatibility with the original implementation.

## 📋 What Was Done

### 1. Databricks Infrastructure Files ✅

All required files from the template have been created:

- ✅ `databricks.yml` - Databricks bundle configuration
- ✅ `app.yaml` - Application runtime configuration
- ✅ `pyproject.toml` - Python packaging metadata
- ✅ `hooks/apps_build.py` - Custom build hook for packaging
- ✅ `src_python/gmail_mcp_server/` - Python wrapper structure
- ✅ `src_python/gmail_mcp_server/static/index.html` - Landing page

### 2. HTTP/SSE Transport ✅

Added HTTP support for Databricks Apps:

- ✅ `src/http-server.ts` - Express.js HTTP server with SSE transport
- ✅ Updated `@modelcontextprotocol/sdk` to latest version (1.20.2+)
- ✅ Added `express` and `express-rate-limit` dependencies
- ✅ Implemented endpoints: `/`, `/mcp/sse`, `/mcp/messages`, `/health`
- ✅ Added rate limiting for DDoS protection

### 3. Security Hardening ✅

- ✅ Fixed npm audit vulnerabilities (form-data, nodemailer)
- ✅ Added rate limiting (100 requests/15min per IP)
- ✅ Added SRI (Subresource Integrity) hashes to CDN scripts
- ✅ CodeQL analysis: 0 security alerts
- ✅ Secure credential handling via environment variables

### 4. Build System ✅

Custom build process that:

- ✅ Compiles TypeScript to JavaScript (`npm run build`)
- ✅ Creates Python wheel (`uv build --wheel`)
- ✅ Packages Node.js dependencies in `.build/` directory
- ✅ Includes: `dist/`, `node_modules/`, `package.json`, `app.yaml`
- ✅ Compatible with both `databricks bundle` and `databricks apps` CLI

### 5. Documentation ✅

Comprehensive documentation created:

- ✅ `DATABRICKS_DEPLOYMENT.md` - Complete deployment guide with architecture diagrams
- ✅ `QUICKSTART_DATABRICKS.md` - Quick reference card
- ✅ `DATABRICKS_CONVERSION_SUMMARY.md` - Technical conversion details
- ✅ `deploy-databricks.sh` - Automated deployment script
- ✅ Updated `README.md` with Databricks section
- ✅ This file (`DEPLOYMENT_README.md`)

## 🚀 Quick Start

### Prerequisites

```bash
# Install Databricks CLI
pip install databricks-cli

# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify Node.js (>= 14.0.0)
node --version
```

### One-Command Deployment

```bash
./deploy-databricks.sh your-profile-name
```

### Manual Deployment

```bash
# 1. Authenticate
export DATABRICKS_CONFIG_PROFILE=your-profile-name
databricks auth login --profile "$DATABRICKS_CONFIG_PROFILE"

# 2. Build
npm install
npm run build
uv build --wheel

# 3. Deploy
databricks bundle deploy -p "$DATABRICKS_CONFIG_PROFILE"
databricks bundle run gmail-mcp-server -p "$DATABRICKS_CONFIG_PROFILE"
```

## 📁 Project Structure

```
Gmail-MCP-Server/
├── 🆕 databricks.yml              # Databricks bundle config
├── 🆕 app.yaml                    # App runtime config
├── 🆕 pyproject.toml              # Python packaging
├── 🆕 deploy-databricks.sh        # Deployment script
├── 🆕 DATABRICKS_DEPLOYMENT.md    # Full guide
├── 🆕 QUICKSTART_DATABRICKS.md    # Quick ref
├── 🆕 DATABRICKS_CONVERSION_SUMMARY.md
├── 🆕 hooks/
│   └── 🆕 apps_build.py           # Build hook
├── 🆕 src_python/
│   └── gmail_mcp_server/
│       ├── static/
│       │   └── 🆕 index.html      # Landing page
│       ├── __init__.py
│       ├── app.py
│       └── main.py
├── src/
│   ├── index.ts                   # Original stdio server
│   ├── 🆕 http-server.ts          # NEW: HTTP/SSE server
│   ├── label-manager.ts
│   ├── filter-manager.ts
│   └── utl.ts
├── package.json                   # Updated: +express, +rate-limit
├── README.md                      # Updated: +Databricks section
└── .gitignore                     # Updated: +.build/
```

Legend: 🆕 = New file created for Databricks

## 🏗️ Architecture

```
┌─────────────────────────────────────┐
│   Databricks Apps Environment       │
│                                     │
│  ┌──────────────────────────────┐  │
│  │  Node.js HTTP Server         │  │
│  │  dist/http-server.js         │  │
│  │                               │  │
│  │  Express + SSE Transport     │  │
│  │  ├─ /            Landing     │  │
│  │  ├─ /mcp/sse     MCP SSE     │  │
│  │  ├─ /mcp/messages  Messages  │  │
│  │  └─ /health       Health     │  │
│  │           ↓                   │  │
│  │  Gmail MCP Server Core       │  │
│  │  • 18 Gmail tools             │  │
│  │  • OAuth2 authentication      │  │
│  │  • Full Gmail API access      │  │
│  └──────────────────────────────┘  │
│                                     │
│  Access via: https://app.url/mcp/sse│
└─────────────────────────────────────┘
```

## ✅ Validation Checklist

### Template Compliance
- [x] `databricks.yml` exists and is properly configured
- [x] `app.yaml` exists with correct command
- [x] `pyproject.toml` exists with build configuration
- [x] `hooks/apps_build.py` implements build hook
- [x] Static landing page exists
- [x] Python wrapper structure present

### Implementation
- [x] Original TypeScript/Node.js code preserved
- [x] HTTP/SSE transport added
- [x] Express.js server configured
- [x] Rate limiting enabled
- [x] Health check endpoint available

### Build System
- [x] `npm install` works
- [x] `npm run build` compiles TypeScript
- [x] `uv build --wheel` creates wheel
- [x] `.build/` directory created with all dependencies

### Security
- [x] npm audit shows only dev dependency issues
- [x] CodeQL analysis passes (0 alerts)
- [x] Rate limiting configured
- [x] CDN scripts have integrity hashes
- [x] Credentials via environment variables

### Documentation
- [x] DATABRICKS_DEPLOYMENT.md complete
- [x] QUICKSTART_DATABRICKS.md created
- [x] DATABRICKS_CONVERSION_SUMMARY.md created
- [x] README.md updated
- [x] Deployment script created

## 🔗 Key Endpoints

When deployed, your server will be available at:

- **Landing Page**: `https://your-app.databricksapps.com/`
- **MCP SSE**: `https://your-app.databricksapps.com/mcp/sse`
- **Health Check**: `https://your-app.databricksapps.com/health`

## 📚 Documentation

- **Full Deployment Guide**: [DATABRICKS_DEPLOYMENT.md](DATABRICKS_DEPLOYMENT.md)
- **Quick Start**: [QUICKSTART_DATABRICKS.md](QUICKSTART_DATABRICKS.md)
- **Conversion Details**: [DATABRICKS_CONVERSION_SUMMARY.md](DATABRICKS_CONVERSION_SUMMARY.md)
- **Main README**: [README.md](README.md)

## 🎯 Key Features

### For Databricks Apps
- ✅ HTTP/SSE transport for MCP protocol
- ✅ Landing page with connection instructions
- ✅ Health check endpoint for monitoring
- ✅ Rate limiting for production use
- ✅ Secure credential management

### Original Features (Preserved)
- ✅ Send/receive emails with attachments
- ✅ Gmail label management
- ✅ Email filtering and organization
- ✅ Advanced search capabilities
- ✅ Batch operations
- ✅ OAuth2 authentication

## 🔒 Security Notes

1. **Gmail Credentials**: Store in Databricks Secrets or DBFS
2. **Rate Limiting**: 100 requests per 15 minutes per IP
3. **CDN Resources**: All scripts include integrity hashes
4. **Dependencies**: Security vulnerabilities fixed (except dev deps)
5. **Authentication**: Bearer token required for MCP access

## 🧪 Testing

### Local Testing
```bash
npm install
npm run build
node dist/http-server.js
# Visit http://localhost:8000
```

### Build Testing
```bash
uv build --wheel
ls -la .build/
# Should contain: dist/, node_modules/, package.json, app.yaml, *.whl
```

## 🆘 Support

- **Deployment Issues**: See [DATABRICKS_DEPLOYMENT.md](DATABRICKS_DEPLOYMENT.md#troubleshooting)
- **Gmail Setup**: See main [README.md](README.md#installation--authentication)
- **GitHub Issues**: https://github.com/murtihash94/Gmail-MCP-Server/issues
- **Databricks Docs**: https://docs.databricks.com/apps/

## 📝 Summary

The Gmail MCP Server has been successfully converted for Databricks Apps deployment while:
- ✅ Following the template structure exactly
- ✅ Preserving the original TypeScript/Node.js implementation
- ✅ Adding HTTP/SSE transport for Databricks compatibility
- ✅ Maintaining backward compatibility with stdio transport
- ✅ Passing all security checks
- ✅ Providing comprehensive documentation

**The server is ready for deployment to Databricks Apps!** 🎉
