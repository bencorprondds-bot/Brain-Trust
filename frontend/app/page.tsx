"use client";

import React, { useCallback, useState } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  Node,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Play, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

import AgentNode from '@/components/nodes/AgentNode';
import ChatInterface, { Message } from '@/components/ChatInterface';
import FetchBin from '@/components/FetchBin';

const nodeTypes = {
  agentNode: AgentNode,
};

// Initial State: Life with AI - Editorial Pipeline
const initialNodes = [
  {
    id: '1',
    type: 'agentNode',
    position: { x: 50, y: 100 },
    data: {
      name: 'The Librarian',
      role: 'Librarian',
      goal: 'Find relevant files in Google Drive and output them in <FETCHED_FILES> format for other agents to use.',
      backstory: 'A meticulous file navigator who directs other agents to the resources they need.',
      status: 'idle',
      model: 'gemini-2.0-flash',
      files: [] as string[]
    },
  },
  {
    id: '2',
    type: 'agentNode',
    position: { x: 400, y: 100 },
    data: {
      name: 'First Draft',
      role: 'Creative Writer',
      goal: 'First, read any files provided in the context. Then write a scene where Oren discovers the Ghost code, using that context.',
      backstory: 'A creative fiction writer.',
      status: 'idle',
      model: 'gemini-2.0-flash',
      files: [] as string[]
    },
  },
  {
    id: '3',
    type: 'agentNode',
    position: { x: 750, y: 100 },
    data: {
      name: 'Dev Editor',
      role: 'Developmental Editor',
      goal: 'Review the scene for structure and pacing.',
      backstory: 'A critical editor focused on story arcs.',
      status: 'idle',
      model: 'claude-3-5-sonnet',
      files: [] as string[]
    },
  },
];

const initialEdges = [
  { id: 'e1-2', source: '1', target: '2', animated: true, style: { stroke: '#06b6d4', strokeWidth: 2 } },
  { id: 'e2-3', source: '2', target: '3', animated: true, style: { stroke: '#06b6d4', strokeWidth: 2 } },
];

export default function Home() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [isRunning, setIsRunning] = useState(false);

  // Chat State
  const [messages, setMessages] = useState<Message[]>([]);
  const [selectedNodeIds, setSelectedNodeIds] = useState<string[]>([]);
  const [isChatLoading, setIsChatLoading] = useState(false);

  // Context State
  const [fetchedFiles, setFetchedFiles] = useState<string[]>([]);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge({ ...params, animated: true, style: { stroke: '#06b6d4' } }, eds)),
    [setEdges],
  );

  // Handle Node Selection
  const onNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    if (node.type === 'agentNode') {
      setSelectedNodeIds(prev => {
        if (prev.includes(node.id)) {
          return prev.filter(id => id !== node.id);
        } else {
          return [...prev, node.id];
        }
      });
    }
  }, []);

  // Send Message Logic (Multi-Agent Support)
  const handleSendMessage = async (content: string) => {
    if (selectedNodeIds.length === 0) return;

    // 1. Add User Message
    const userMsg: Message = { role: 'user', content };
    setMessages(prev => [...prev, userMsg]);
    setIsChatLoading(true);

    // 2. Identify Agents
    const targetAgents = nodes.filter(n => selectedNodeIds.includes(n.id));

    try {
      let contextStr = messages.map(m => `${m.role.toUpperCase()}: ${m.content}`).join('\n');

      // Inject Fetch Bin content into context so agents know what files are available
      // This solves the issue of deselected Librarian: The global bin context is passed to whoever is listening.
      if (fetchedFiles.length > 0) {
        contextStr += `\n\n[SYSTEM] AVAILABLE CONTEXT FILES (Refenced by Librarian):\n${fetchedFiles.join('\n')}`;
      }

      // 3. Parallel Backend Calls
      const promises = targetAgents.map(async (agentNode) => {
        const response = await fetch('http://localhost:8000/api/v1/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-API-Key': process.env.NEXT_PUBLIC_BRAIN_TRUST_API_KEY || ''
          },
          body: JSON.stringify({
            message: content,
            agent_config: agentNode.data,
            context: contextStr
          })
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || `Server exception: ${response.status}`);
        }

        const data = await response.json();

        // Parse Hidden File Tags
        let cleanContent = data.response;

        // Safety check
        if (typeof cleanContent !== 'string') {
          cleanContent = JSON.stringify(data);
        }

        const fileRegex = /<FETCHED_FILES>([\s\S]*?)<\/FETCHED_FILES>/;
        const match = cleanContent ? cleanContent.match(fileRegex) : null;

        console.log('[FETCH BIN] Checking for file tags...');
        if (match) {
          console.log('[FETCH BIN] ✅ Found <FETCHED_FILES> tag:', match[0]);
          console.log('[FETCH BIN] Raw content:', match[1]);
          
          try {
            const rawContent = match[1].trim();
            // Robust Regex Parse: Remove brackets and split by comma, then strip quotes
            let files: string[] = [];

            // If it looks like a list
            if (rawContent.startsWith('[') && rawContent.endsWith(']')) {
              const inner = rawContent.slice(1, -1);
              if (inner.trim()) {
                // Split by comma checking for quotes
                files = inner.split(',').map((s: string) => s.trim().replace(/^['"]|['"]$/g, '')).filter(Boolean);
              }
            } else {
              // Fallback line based or single item
              files = [rawContent.replace(/^['"]|['"]$/g, '')];
            }

            console.log('[FETCH BIN] Parsed files:', files);

            if (files.length > 0) {
              // 1. Update Global Bin
              setFetchedFiles(prev => Array.from(new Set([...prev, ...files])));

              // 2. Update Agent Node Badge
              setNodes(nds => nds.map(n =>
                n.id === agentNode.id
                  ? { ...n, data: { ...n.data, files: Array.from(new Set([...(n.data.files || []), ...files])) } }
                  : n
              ));
              
              console.log('[FETCH BIN] Updated global bin. Total files:', files.length);
            }

            // Hide tag from UI
            cleanContent = cleanContent.replace(match[0], '').trim();
          } catch (e) {
            console.error("Error parsing fetched files tag:", e);
            // Don't crash, just ignore parsing failure
          }
        } else {
          console.log('[FETCH BIN] No <FETCHED_FILES> tag found in response');
        }

        return {
          role: 'agent' as const,
          content: cleanContent || "Empty response from agent.",
          agentName: agentNode.data.name
        };
      });

      // 4. Wait for all
      const responses = await Promise.all(promises);

      // 5. Add Responses to History
      setMessages(prev => [...prev, ...responses]);

    } catch (error) {
      console.error("Chat failed:", error);
      // Push error to UI
      setMessages(prev => [...prev, {
        role: 'system',
        content: `Error contacting agents: ${error instanceof Error ? error.message : 'Unknown error'}. Is the backend running?`
      }]);
    } finally {
      setIsChatLoading(false);
    }
  };

  const runWorkflow = async () => {
    setIsRunning(true);
    setNodes((nds) => nds.map((n) => ({ ...n, data: { ...n.data, status: 'thinking' } })));

    try {
      const contextStr = messages.map(m => `${m.role === 'user' ? 'USER' : m.agentName}: ${m.content}`).join('\n');

      const nodesWithContext = nodes.map(n => {
        const newData = { ...n.data };
        if (messages.length > 0) {
          newData.goal = `${newData.goal}\n\nIMPORTANT CONTEXT FROM PRE-FLIGHT CHAT:\n${contextStr}`;
        }
        if (fetchedFiles.length > 0) {
          newData.goal = `${newData.goal}\n\nALSO CONSIDER THESE FETCHED FILES:\n${fetchedFiles.join('\n')}`;
        }
        return { ...n, data: newData };
      });

      const payload = {
        nodes: nodesWithContext,
        edges: edges
      };

      const response = await fetch('http://127.0.0.1:8000/api/v1/run-workflow', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': process.env.NEXT_PUBLIC_BRAIN_TRUST_API_KEY || '',
        },
        body: JSON.stringify(payload),
      });

      const result = await response.json();
      console.log("Workflow Result:", result);

      setNodes((nds) => nds.map((n) => ({ ...n, data: { ...n.data, status: 'done' } })));

    } catch (error) {
      console.error("Workflow failed:", error);
      setNodes((nds) => nds.map((n) => ({ ...n, data: { ...n.data, status: 'error' } })));
    } finally {
      setIsRunning(false);
    }
  };

  // Build selected agents list for UI
  const selectedAgentsList = nodes
    .filter(n => selectedNodeIds.includes(n.id))
    .map(n => ({ name: n.data.name, id: n.id }));

  return (
    <div className="w-screen h-screen bg-zinc-950 text-zinc-50 overflow-hidden relative">
      {/* Header Controls - Top Layer (z-30) */}
      <div className="absolute top-4 left-4 z-30 flex flex-col gap-4 pointer-events-auto">
        <div>
          <h1 className="text-2xl font-bold tracking-tight bg-gradient-to-r from-cyan-400 to-blue-600 bg-clip-text text-transparent">
            Brain Trust v2.5
          </h1>
          <p className="text-xs text-zinc-500 font-mono tracking-widest">INTERACTIVE WORKFLOW ENGINE</p>
        </div>


      </div>

      {/* Fetch Bin - Absolute Positioned */}
      <FetchBin files={fetchedFiles} />

      {/* Canvas Layer - Bottom (z-0) */}
      <div className="absolute inset-0 z-0">
        <ReactFlow
          nodes={nodes.map(n => ({
            ...n,
            // Highlight logic: Silver if selected
            style: selectedNodeIds.includes(n.id)
              ? { ...n.style, border: '2px solid #e4e4e7', boxShadow: '0 0 20px rgba(228,228,231,0.6)' }
              : n.style
          }))}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={onNodeClick}
          nodeTypes={nodeTypes}
          fitView
          className="bg-zinc-950"
        >
          <Background color="#3f3f46" gap={20} size={1} />
          <Controls className="bg-zinc-900 border-zinc-800 fill-zinc-400" />
          <MiniMap
            className="bg-zinc-900 border-zinc-800"
            nodeColor={(n) => {
              const s = n.data.status;
              if (s === 'thinking') return '#06b6d4';
              if (s === 'done') return '#10b981';
              if (s === 'error') return '#ef4444';
              return '#52525b';
            }}
          />
        </ReactFlow>
      </div>

      {/* HUD Chat Interface - Middle (z-20) */}
      <ChatInterface
        messages={messages}
        onSendMessage={handleSendMessage}
        selectedAgents={selectedAgentsList}
        isLoading={isChatLoading}
      />
    </div>
  );
}
