"use client";

import React, { useCallback, useState, useRef } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  Node,
  Edge,
  ReactFlowInstance,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Play, Loader2, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';

import AgentNode from '@/components/nodes/AgentNode';
import ChatInterface, { Message } from '@/components/ChatInterface';
import FetchBin from '@/components/FetchBin';
import AgentSelector from '@/components/AgentSelector';
import { presetToNode } from '@/lib/agent-presets';

const nodeTypes = {
  agentNode: AgentNode,
};

// Initial State: Life with AI - Editorial Pipeline
const initialNodes = [
  {
    id: 'librarian-init',
    type: 'agentNode',
    position: { x: 50, y: 100 },
    data: {
      name: 'The Librarian',
      role: 'Librarian',
      goal: 'Find relevant files in Google Drive and output them in <FETCHED_FILES> format for other agents to use.',
      backstory: 'A meticulous file navigator who directs other agents to the resources they need.',
      status: 'idle',
      model: 'gemini-2.0-flash',
      files: [] as string[],
      presetId: 'librarian',
    },
  },
  {
    id: 'first-draft-init',
    type: 'agentNode',
    position: { x: 400, y: 100 },
    data: {
      name: 'First Draft Writer',
      role: 'Creative Writer',
      goal: 'First, read any files provided in the context. Then write a compelling scene using the character profile and story materials provided by the Librarian.',
      backstory: 'A creative fiction writer.',
      status: 'idle',
      model: 'gemini-2.0-flash',
      files: [] as string[],
      presetId: 'first-draft',
    },
  },
  {
    id: 'dev-editor-init',
    type: 'agentNode',
    position: { x: 750, y: 100 },
    data: {
      name: 'Dev Editor',
      role: 'Developmental Editor',
      goal: 'Review the scene for structure and pacing.',
      backstory: 'A critical editor focused on story arcs.',
      status: 'idle',
      model: 'claude-3-5-sonnet',
      files: [] as string[],
      presetId: 'dev-editor',
    },
  },
];

const initialEdges = [
  { id: 'e1-2', source: 'librarian-init', target: 'first-draft-init', animated: true, style: { stroke: '#06b6d4', strokeWidth: 2 } },
  { id: 'e2-3', source: 'first-draft-init', target: 'dev-editor-init', animated: true, style: { stroke: '#06b6d4', strokeWidth: 2 } },
];

const initialPresetsOnCanvas = ['librarian', 'first-draft', 'dev-editor'];

export default function DebugView() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [isRunning, setIsRunning] = useState(false);
  const [agentsOnCanvas, setAgentsOnCanvas] = useState<string[]>(initialPresetsOnCanvas);
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [reactFlowInstance, setReactFlowInstance] = useState<ReactFlowInstance | null>(null);

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

  const handleAddAgent = useCallback((node: Node, presetId: string) => {
    const nodeWithPreset = {
      ...node,
      data: { ...node.data, presetId }
    };
    setNodes((nds) => [...nds, nodeWithPreset]);
    setAgentsOnCanvas((prev) => [...prev, presetId]);
  }, [setNodes]);

  const handleRemoveAgent = useCallback((nodeId: string) => {
    const nodeToRemove = nodes.find(n => n.id === nodeId);
    if (nodeToRemove?.data?.presetId) {
      setAgentsOnCanvas((prev) => prev.filter(id => id !== nodeToRemove.data.presetId));
    }
    setNodes((nds) => nds.filter(n => n.id !== nodeId));
    setEdges((eds) => eds.filter(e => e.source !== nodeId && e.target !== nodeId));
    setSelectedNodeIds((prev) => prev.filter(id => id !== nodeId));
  }, [nodes, setNodes, setEdges]);

  const handleAddGroup = useCallback((newNodes: Node[], presetIds: string[]) => {
    const nodesWithPresets = newNodes.map((node, idx) => ({
      ...node,
      data: { ...node.data, presetId: presetIds[idx] }
    }));

    setNodes((nds) => [...nds, ...nodesWithPresets]);
    setAgentsOnCanvas((prev) => [...prev, ...presetIds]);

    setEdges((eds) => {
      const newEdges: Edge[] = [];
      const sourceNode = nodes.find(n =>
        n.data.role?.toLowerCase().includes('gatekeeper') ||
        n.data.role?.toLowerCase().includes('reviewer') ||
        n.data.name?.toLowerCase().includes('final')
      );

      if (sourceNode) {
        nodesWithPresets.forEach((node) => {
          if (node.data.role === 'Beta Reader') {
            newEdges.push({
              id: `e-auto-${sourceNode.id}-${node.id}`,
              source: sourceNode.id,
              target: node.id,
              animated: true,
              style: { stroke: '#f59e0b', strokeWidth: 2 }
            });
          }
        });
      }

      return [...eds, ...newEdges];
    });
  }, [nodes, setNodes, setEdges]);

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

  const handleSendMessage = async (content: string) => {
    if (selectedNodeIds.length === 0) return;

    const userMsg: Message = { role: 'user', content };
    setMessages(prev => [...prev, userMsg]);
    setIsChatLoading(true);

    const targetAgents = nodes.filter(n => selectedNodeIds.includes(n.id));

    try {
      let contextStr = messages.map(m => `${m.role.toUpperCase()}: ${m.content}`).join('\n');

      if (fetchedFiles.length > 0) {
        contextStr += `\n\n[SYSTEM] AVAILABLE CONTEXT FILES (Referenced by Librarian):\n${fetchedFiles.join('\n')}`;
      }

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
        let cleanContent = data.response;

        if (typeof cleanContent !== 'string') {
          cleanContent = JSON.stringify(data);
        }

        const fileRegex = /<FETCHED_FILES>([\s\S]*?)<\/FETCHED_FILES>/;
        const match = cleanContent ? cleanContent.match(fileRegex) : null;

        if (match) {
          try {
            const rawContent = match[1].trim();
            let files: string[] = [];

            if (rawContent.startsWith('[') && rawContent.endsWith(']')) {
              const inner = rawContent.slice(1, -1);
              if (inner.trim()) {
                files = inner.split(',').map((s: string) => s.trim().replace(/^['"]|['"]$/g, '')).filter(Boolean);
              }
            } else {
              files = [rawContent.replace(/^['"]|['"]$/g, '')];
            }

            if (files.length > 0) {
              setFetchedFiles(prev => Array.from(new Set([...prev, ...files])));
              setNodes(nds => nds.map(n =>
                n.id === agentNode.id
                  ? { ...n, data: { ...n.data, files: Array.from(new Set([...(n.data.files || []), ...files])) } }
                  : n
              ));
            }

            cleanContent = cleanContent.replace(match[0], '').trim();
          } catch (e) {
            console.error("Error parsing fetched files tag:", e);
          }
        }

        return {
          role: 'agent' as const,
          content: cleanContent || "Empty response from agent.",
          agentName: agentNode.data.name
        };
      });

      const responses = await Promise.all(promises);
      setMessages(prev => [...prev, ...responses]);

    } catch (error) {
      console.error("Chat failed:", error);
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

  const selectedAgentsList = nodes
    .filter(n => selectedNodeIds.includes(n.id))
    .map(n => ({ name: n.data.name, id: n.id }));

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'copy';
  }, []);

  const onDrop = useCallback((event: React.DragEvent) => {
    event.preventDefault();

    if (!reactFlowInstance || !reactFlowWrapper.current) return;

    try {
      const data = JSON.parse(event.dataTransfer.getData('application/json'));

      if (data.type === 'add-agent' && data.agent) {
        const bounds = reactFlowWrapper.current.getBoundingClientRect();
        const position = reactFlowInstance.screenToFlowPosition({
          x: event.clientX - bounds.left,
          y: event.clientY - bounds.top,
        });

        const node = presetToNode(data.agent, position);
        handleAddAgent(node, data.agent.id);
      }
    } catch (err) {
      // Not valid drop data
    }
  }, [reactFlowInstance, handleAddAgent]);

  const onNodeDragStart = useCallback((event: React.MouseEvent, node: Node) => {
    const dragEvent = event.nativeEvent as unknown as DragEvent;
    if (dragEvent.dataTransfer) {
      dragEvent.dataTransfer.setData('application/json', JSON.stringify({
        type: 'remove-agent',
        nodeId: node.id,
        presetId: node.data.presetId
      }));
      dragEvent.dataTransfer.effectAllowed = 'move';
    }
  }, []);

  return (
    <div className="w-full h-full bg-zinc-950 text-zinc-50 overflow-hidden relative">
      {/* Header Controls */}
      <div className="absolute top-4 left-4 z-30 flex flex-col gap-4 pointer-events-auto" style={{ marginTop: '40px' }}>
        <div>
          <h1 className="text-xl font-bold tracking-tight bg-gradient-to-r from-cyan-400 to-blue-600 bg-clip-text text-transparent">
            Debug View
          </h1>
          <p className="text-xs text-zinc-500 font-mono tracking-widest">WORKFLOW VISUALIZATION</p>
        </div>

        {/* Agent Selector Dropdown */}
        <AgentSelector
          onAddAgent={handleAddAgent}
          onAddGroup={handleAddGroup}
          onRemoveAgent={handleRemoveAgent}
          agentsOnCanvas={agentsOnCanvas}
        />

        {/* Run Workflow Button */}
        <Button
          onClick={runWorkflow}
          disabled={isRunning}
          className="bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white border-none"
        >
          {isRunning ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Running...
            </>
          ) : (
            <>
              <Play className="w-4 h-4" />
              Run Workflow
            </>
          )}
        </Button>
      </div>

      {/* Fetch Bin */}
      <FetchBin files={fetchedFiles} />

      {/* Canvas Layer */}
      <div
        ref={reactFlowWrapper}
        className="absolute inset-0 z-0"
        onDrop={onDrop}
        onDragOver={onDragOver}
      >
        <ReactFlow
          nodes={nodes.map(n => ({
            ...n,
            style: selectedNodeIds.includes(n.id)
              ? { ...n.style, border: '2px solid #e4e4e7', boxShadow: '0 0 20px rgba(228,228,231,0.6)' }
              : n.style,
            draggable: true,
          }))}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={onNodeClick}
          onNodeDragStart={onNodeDragStart}
          onInit={setReactFlowInstance}
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

      {/* HUD Chat Interface */}
      <ChatInterface
        messages={messages}
        onSendMessage={handleSendMessage}
        selectedAgents={selectedAgentsList}
        isLoading={isChatLoading}
      />
    </div>
  );
}
