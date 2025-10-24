#!/usr/bin/env node

/**
 * HTTP Server Entry Point for Gmail MCP Server (Databricks Apps)
 * 
 * This provides HTTP/SSE transport for the Gmail MCP Server,
 * suitable for deployment on Databricks Apps.
 */

import express from 'express';
import { Server as MCPServer } from '@modelcontextprotocol/sdk/server/index.js';
import { SSEServerTransport } from '@modelcontextprotocol/sdk/server/sse.js';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const app = express();
const PORT = process.env.PORT || 8000;

// Parse JSON bodies
app.use(express.json());

// Serve static landing page
app.get('/', (req, res) => {
    const indexPath = path.join(__dirname, '../src_python/gmail_mcp_server/static/index.html');
    if (fs.existsSync(indexPath)) {
        res.sendFile(indexPath);
    } else {
        res.send(`
            <html>
                <head><title>Gmail MCP Server</title></head>
                <body>
                    <h1>Gmail MCP Server on Databricks Apps</h1>
                    <p>Server is running. Connect via MCP SSE endpoint at <code>/mcp/sse</code></p>
                </body>
            </html>
        `);
    }
});

// Store active MCP server sessions
const sessions = new Map();

// SSE endpoint for MCP
app.get('/mcp/sse', async (req, res) => {
    console.log('New SSE connection request');
    
    // Set headers for SSE
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    
    // Create SSE transport
    const transport = new SSEServerTransport('/mcp/messages', res);
    const sessionId = transport.sessionId;
    
    // Create MCP server instance
    const server = new MCPServer(
        {
            name: 'gmail-mcp-server',
            version: '1.1.11',
        },
        {
            capabilities: {
                tools: {},
            },
        }
    );
    
    // Store session
    sessions.set(sessionId, { transport, server });
    
    // Setup server handlers (simplified - full implementation would import from index.ts)
    const { ListToolsRequestSchema } = await import('@modelcontextprotocol/sdk/types.js');
    server.setRequestHandler(ListToolsRequestSchema, async () => ({
        tools: [
            {
                name: 'send_email',
                description: 'Send an email via Gmail',
                inputSchema: {
                    type: 'object',
                    properties: {
                        to: { type: 'array', items: { type: 'string' } },
                        subject: { type: 'string' },
                        body: { type: 'string' }
                    },
                    required: ['to', 'subject', 'body']
                }
            }
            // More tools would be added here from the main implementation
        ]
    }));
    
    transport.onclose = () => {
        console.log(`Session ${sessionId} closed`);
        sessions.delete(sessionId);
    };
    
    // Connect server to transport
    await server.connect(transport);
    await transport.start();
});

// POST endpoint for MCP messages
app.post('/mcp/messages', async (req, res) => {
    const sessionId = req.headers['x-session-id'];
    
    if (!sessionId || typeof sessionId !== 'string') {
        res.status(400).json({ error: 'Missing x-session-id header' });
        return;
    }
    
    const session = sessions.get(sessionId);
    if (!session) {
        res.status(404).json({ error: 'Session not found' });
        return;
    }
    
    try {
        await session.transport.handlePostMessage(req, res);
    } catch (error) {
        console.error('Error handling message:', error);
        if (!res.headersSent) {
            res.status(500).json({ error: 'Internal server error' });
        }
    }
});

// Health check endpoint
app.get('/health', (req, res) => {
    res.json({ status: 'ok', sessions: sessions.size });
});

// Start server
app.listen(PORT, () => {
    console.log(`Gmail MCP Server (HTTP) running on port ${PORT}`);
    console.log(`Landing page: http://localhost:${PORT}/`);
    console.log(`MCP SSE endpoint: http://localhost:${PORT}/mcp/sse`);
    console.log(`Health check: http://localhost:${PORT}/health`);
});
