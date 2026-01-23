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
  Edge,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Play, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import Terminal from '@/components/Terminal';

import AgentNode from '@/components/nodes/AgentNode';

const nodeTypes = {
  agentNode: AgentNode,
};

// Initial State: "Diamond Age" Demo
const initialNodes = [
  {
    id: '1',
    type: 'agentNode',
    position: { x: 250, y: 50 },
    data: {
      name: 'ARIA',
      role: 'Strategic CEO',
      goal: 'Define the high-level strategy for the project',
      backstory: 'An experienced executive AI.',
      status: 'idle',
      model: 'gemini-2.5-pro'
    },
  },
  {
    id: '2',
    type: 'agentNode',
    position: { x: 100, y: 300 },
    data: {
      name: 'VECTOR',
      role: 'Lead Engineer',
      goal: 'Implement the code based on the strategy',
      backstory: 'A senior python engineer.',
      status: 'idle',
      // currentTool: 'git_pull_request', 
      model: 'claude-3.5-sonnet'
    },
  },
  {
    id: '3',
    type: 'agentNode',
    position: { x: 400, y: 300 },
    data: {
      name: 'MARCUS',
      role: 'Creative Lead',
      goal: 'Design the user interface and experience',
      backstory: 'A visionary designer.',
      status: 'idle',
      model: 'gemini-1.5-flash'
    },
  },
];

const initialEdges = [
  { id: 'e1-2', source: '1', target: '2', animated: true, style: { stroke: '#06b6d4', strokeWidth: 2 } }, // Cyan pulse
  { id: 'e1-3', source: '1', target: '3', style: { stroke: '#52525b' } },
];

export default function Home() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [isRunning, setIsRunning] = useState(false);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge({ ...params, animated: true, style: { stroke: '#06b6d4' } }, eds)),
    [setEdges],
  );

  const runWorkflow = async () => {
    setIsRunning(true);
    // Visual Feedback: Set status to 'thinking'
    setNodes((nds) => nds.map((n) => ({
      ...n,
      data: { ...n.data, status: 'thinking' }
    })));

    try {
      const payload = {
        nodes: nodes,
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

      // Update status to 'done' (Simple demo)
      setNodes((nds) => nds.map((n) => ({
        ...n,
        data: { ...n.data, status: 'done' }
      })));

    } catch (error) {
      console.error("Workflow failed:", error);
      setNodes((nds) => nds.map((n) => ({
        ...n,
        data: { ...n.data, status: 'error' }
      })));
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="w-screen h-screen bg-zinc-950 text-zinc-50 overflow-hidden">
      <div className="absolute top-4 left-4 z-10 flex flex-col gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight bg-gradient-to-r from-cyan-400 to-blue-600 bg-clip-text text-transparent">
            BRAIN TRUST v2.0
          </h1>
          <p className="text-xs text-zinc-500 font-mono tracking-widest">VISUAL ORCHESTRATION PLATFORM</p>
        </div>

        <Button
          onClick={runWorkflow}
          disabled={isRunning}
          className="bg-cyan-600 hover:bg-cyan-500 text-white border border-cyan-400/20 shadow-[0_0_20px_rgba(6,182,212,0.3)] transition-all"
        >
          {isRunning ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              EXECUTING CREW...
            </>
          ) : (
            <>
              <Play className="mr-2 h-4 w-4 fill-current" />
              RUN WORKFLOW
            </>
          )}
        </Button>
      </div>

      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
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
  );
}
