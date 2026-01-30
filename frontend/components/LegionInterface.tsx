"use client";

import React, { useState, useCallback } from 'react';
import dynamic from 'next/dynamic';
import { MessageSquare, Activity, Settings, Loader2, Zap } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import ExecutionTraceView, { ExecutionTrace, StepTrace } from './ExecutionTraceView';

// Dynamic import with SSR disabled to prevent hydration issues with timestamps
const WillowChat = dynamic(() => import('./WillowChat'), {
  ssr: false,
  loading: () => (
    <div className="flex-1 flex items-center justify-center bg-zinc-950">
      <Loader2 className="w-8 h-8 animate-spin text-emerald-400" />
    </div>
  ),
});

type ViewMode = 'chat' | 'trace' | 'settings';

// Active agent type
interface ActiveAgent {
  id: string;
  name: string;
  role: string;
  abbrev: string;
  status: 'idle' | 'working' | 'done';
}

// Agent abbreviation helper
function getAgentAbbrev(role: string, name: string): string {
  const roleMap: Record<string, string> = {
    'Executive Conductor': 'W',
    'Librarian': 'Li',
    'Writer': 'Wr',
    'Creative Writer': 'Wr',
    'Developmental Editor': 'DE',
    'Line Editor': 'LE',
    'Copy Editor': 'CE',
    'Editor': 'Ed',
    'Beta Reader': 'BR',
    'Developer': 'Dv',
    'Artist': 'Ar',
    'Analyst': 'An',
  };

  // Check role first
  if (roleMap[role]) return roleMap[role];

  // Fall back to first letters of name
  const words = name.split(' ');
  if (words.length >= 2) {
    return words[0][0] + words[1][0];
  }
  return name.substring(0, 2);
}

// Agent avatar component
function AgentAvatar({ agent, isSelected, onClick }: {
  agent: ActiveAgent;
  isSelected?: boolean;
  onClick?: () => void;
}) {
  const statusColors = {
    idle: 'bg-zinc-700 text-zinc-400',
    working: 'bg-cyan-600 text-white animate-pulse',
    done: 'bg-emerald-600 text-white',
  };

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            onClick={onClick}
            className={`
              w-9 h-9 rounded-lg flex items-center justify-center
              text-xs font-bold transition-all duration-200
              ${statusColors[agent.status]}
              ${isSelected ? 'ring-2 ring-emerald-400' : ''}
              ${onClick ? 'hover:scale-110 cursor-pointer' : 'cursor-default'}
            `}
          >
            {agent.abbrev}
          </button>
        </TooltipTrigger>
        <TooltipContent side="right" className="bg-zinc-800 border-zinc-700">
          <div className="text-sm font-medium">{agent.name}</div>
          <div className="text-xs text-zinc-400">{agent.role}</div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

export default function LegionInterface() {
  const [viewMode, setViewMode] = useState<ViewMode>('chat');
  const [devMode, setDevMode] = useState(false);

  // Execution history state
  const [executions, setExecutions] = useState<ExecutionTrace[]>([]);

  // Active agents state (agents currently in the conversation)
  const [activeAgents, setActiveAgents] = useState<ActiveAgent[]>([
    { id: 'willow', name: 'Willow', role: 'Executive Conductor', abbrev: 'W', status: 'idle' }
  ]);

  // Selected agent for direct chat (null = Willow)
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);

  // Callback when execution starts/updates/completes
  const handleExecutionUpdate = useCallback((execution: ExecutionTrace) => {
    setExecutions(prev => {
      const existing = prev.findIndex(e => e.id === execution.id);
      if (existing >= 0) {
        const updated = [...prev];
        updated[existing] = execution;
        return updated;
      }
      return [...prev, execution];
    });

    // Update active agents based on execution steps
    const newAgents: ActiveAgent[] = [
      { id: 'willow', name: 'Willow', role: 'Executive Conductor', abbrev: 'W', status: 'idle' }
    ];

    execution.steps.forEach(step => {
      const existingAgent = newAgents.find(a => a.role === step.agent_role);
      if (!existingAgent) {
        newAgents.push({
          id: `agent-${step.agent_role.toLowerCase().replace(/\s+/g, '-')}`,
          name: step.agent_role,
          role: step.agent_role,
          abbrev: getAgentAbbrev(step.agent_role, step.agent_role),
          status: step.status === 'running' ? 'working' : step.status === 'completed' ? 'done' : 'idle',
        });
      } else if (step.status === 'running') {
        existingAgent.status = 'working';
      } else if (step.status === 'completed' && existingAgent.status !== 'working') {
        existingAgent.status = 'done';
      }
    });

    // Update Willow's status
    if (execution.status === 'running') {
      newAgents[0].status = 'working';
    } else if (execution.status === 'completed') {
      newAgents[0].status = 'done';
    }

    setActiveAgents(newAgents);
  }, []);

  // Reset agent statuses after completion
  const handleExecutionComplete = useCallback(() => {
    setActiveAgents(prev => prev.map(a => ({ ...a, status: 'idle' as const })));
  }, []);

  return (
    <div className="w-screen h-screen bg-zinc-950 text-zinc-50 overflow-hidden flex">
      {/* Sidebar */}
      <div className="w-16 bg-zinc-900 border-r border-zinc-800 flex flex-col items-center py-4">
        {/* Logo */}
        <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-emerald-500 to-cyan-500 flex items-center justify-center font-bold text-lg mb-4">
          L
        </div>

        {/* Navigation Tabs */}
        <div className="flex flex-col gap-2 mb-4">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant={viewMode === 'chat' ? 'default' : 'ghost'}
                  size="icon"
                  onClick={() => setViewMode('chat')}
                  className={viewMode === 'chat' ? 'bg-emerald-600' : 'text-zinc-400 hover:text-zinc-100'}
                >
                  <MessageSquare className="w-5 h-5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="right">Chat with Willow</TooltipContent>
            </Tooltip>
          </TooltipProvider>

          {devMode && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant={viewMode === 'trace' ? 'default' : 'ghost'}
                    size="icon"
                    onClick={() => setViewMode('trace')}
                    className={viewMode === 'trace' ? 'bg-cyan-600' : 'text-zinc-400 hover:text-zinc-100'}
                  >
                    <Activity className="w-5 h-5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="right">Execution Trace</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </div>

        {/* Divider */}
        <div className="w-8 h-px bg-zinc-700 my-2" />

        {/* Active Agents Section */}
        <div className="flex-1 flex flex-col gap-2 items-center overflow-y-auto py-2">
          {activeAgents.map(agent => (
            <AgentAvatar
              key={agent.id}
              agent={agent}
              isSelected={selectedAgentId === agent.id}
              onClick={() => {
                if (agent.id === 'willow') {
                  setSelectedAgentId(null);
                } else {
                  setSelectedAgentId(agent.id === selectedAgentId ? null : agent.id);
                }
              }}
            />
          ))}
        </div>

        {/* Bottom: Quick Actions & Settings */}
        <div className="flex flex-col gap-2 mt-4">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="text-zinc-400 hover:text-zinc-100"
                  title="Quick Actions"
                >
                  <Zap className="w-5 h-5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="right">Quick Actions (coming soon)</TooltipContent>
            </Tooltip>
          </TooltipProvider>

          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant={devMode ? 'default' : 'ghost'}
                  size="icon"
                  onClick={() => setDevMode(!devMode)}
                  className={devMode ? 'bg-amber-600' : 'text-zinc-400 hover:text-zinc-100'}
                  title="Developer Mode"
                >
                  <Settings className="w-5 h-5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="right">
                {devMode ? 'Developer Mode: ON' : 'Developer Mode: OFF'}
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col relative">
        {/* Chat View - Always mounted, visibility controlled */}
        <div className={`absolute inset-0 ${viewMode === 'chat' ? 'z-10' : 'z-0 pointer-events-none opacity-0'}`}>
          <WillowChat
            onExecutionUpdate={handleExecutionUpdate}
            onExecutionComplete={handleExecutionComplete}
            selectedAgentId={selectedAgentId}
            showDevToggle={!devMode}
            onToggleDevMode={() => setDevMode(true)}
          />
        </div>

        {/* Trace View */}
        {devMode && (
          <div className={`absolute inset-0 ${viewMode === 'trace' ? 'z-10' : 'z-0 pointer-events-none opacity-0'}`}>
            <ExecutionTraceView
              executions={executions}
              onBack={() => setViewMode('chat')}
            />
          </div>
        )}
      </div>
    </div>
  );
}
