#!/bin/bash

# Gmail MCP Server - Databricks Deployment Script
#
# This script helps deploy the Gmail MCP Server to Databricks Apps
# Usage: ./deploy-databricks.sh [profile-name]

set -e

# Configuration
PROFILE="${1:-gmail-mcp-server}"
APP_NAME="gmail-mcp-server"

echo "========================================"
echo "Gmail MCP Server - Databricks Deployment"
echo "========================================"
echo ""
echo "Profile: $PROFILE"
echo "App Name: $APP_NAME"
echo ""

# Check prerequisites
echo "Checking prerequisites..."

# Check for databricks CLI
if ! command -v databricks &> /dev/null; then
    echo "❌ Error: databricks CLI not found"
    echo "   Install: pip install databricks-cli"
    exit 1
fi

# Check for uv
if ! command -v uv &> /dev/null; then
    echo "❌ Error: uv not found"
    echo "   Install: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Check for node
if ! command -v node &> /dev/null; then
    echo "❌ Error: node not found"
    echo "   Install Node.js >= 14.0.0"
    exit 1
fi

# Check for npm
if ! command -v npm &> /dev/null; then
    echo "❌ Error: npm not found"
    echo "   Install npm"
    exit 1
fi

echo "✅ All prerequisites satisfied"
echo ""

# Step 1: Install Node.js dependencies
echo "Step 1: Installing Node.js dependencies..."
npm install
echo "✅ Node.js dependencies installed"
echo ""

# Step 2: Build TypeScript
echo "Step 2: Building TypeScript..."
npm run build
echo "✅ TypeScript built successfully"
echo ""

# Step 3: Install Python dependencies
echo "Step 3: Installing Python build dependencies..."
uv sync
echo "✅ Python dependencies installed"
echo ""

# Step 4: Build wheel
echo "Step 4: Building Python wheel..."
uv build --wheel
echo "✅ Wheel built successfully"
echo ""

# Step 5: Deploy using databricks bundle
echo "Step 5: Deploying to Databricks..."
databricks bundle deploy -p "$PROFILE"
echo "✅ Bundle deployed"
echo ""

# Step 6: Run the app
echo "Step 6: Starting the app..."
databricks bundle run "$APP_NAME" -p "$PROFILE"
echo "✅ App started"
echo ""

# Get app URL
echo "Getting app URL..."
APP_URL=$(databricks apps get "$APP_NAME" -p "$PROFILE" --output json | jq -r '.url' 2>/dev/null || echo "")

if [ -n "$APP_URL" ]; then
    echo ""
    echo "========================================="
    echo "Deployment Successful! 🎉"
    echo "========================================="
    echo ""
    echo "App URL: $APP_URL"
    echo "Landing Page: $APP_URL/"
    echo "MCP Endpoint: $APP_URL/mcp/sse"
    echo "Health Check: $APP_URL/health"
    echo ""
    echo "To get your auth token:"
    echo "  databricks auth token -p $PROFILE"
    echo ""
else
    echo ""
    echo "========================================="
    echo "Deployment Successful! 🎉"
    echo "========================================="
    echo ""
    echo "Check your app status with:"
    echo "  databricks apps get $APP_NAME -p $PROFILE"
    echo ""
fi

echo "See DATABRICKS_DEPLOYMENT.md for connection examples."
echo ""
