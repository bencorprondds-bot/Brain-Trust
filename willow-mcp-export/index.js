#!/usr/bin/env node

/**
 * Willow MCP Server
 *
 * A Model Context Protocol server that gives Claude Desktop access to:
 * - Google Drive (read/write documents)
 * - Persistent memory (Supabase-backed)
 * - Editorial chorus (multi-perspective feedback)
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

// Import tools
import { driveTools, handleDriveTool } from './tools/drive.js';
import { memoryTools, handleMemoryTool } from './tools/memory.js';
import { chorusTools, handleChorusTool } from './tools/chorus.js';

// Create server instance
const server = new Server(
  {
    name: 'willow-mcp',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Combine all tools
const allTools = [...driveTools, ...memoryTools, ...chorusTools];

// List available tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return { tools: allTools };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    // Route to appropriate handler
    if (name.startsWith('drive_')) {
      return await handleDriveTool(name, args);
    } else if (name.startsWith('memory_')) {
      return await handleMemoryTool(name, args);
    } else if (name.startsWith('chorus_')) {
      return await handleChorusTool(name, args);
    } else {
      throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: `Error: ${error.message}`,
        },
      ],
      isError: true,
    };
  }
});

// Start the server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('Willow MCP server running');
}

main().catch(console.error);
