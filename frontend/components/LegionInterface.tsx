"use client";

import React, { useState, useCallback } from 'react';
import dynamic from 'next/dynamic';
import {
  MessageSquare,
  Activity,
  Settings,
  Loader2,
  ChevronLeft,
  ChevronRight,
  Wifi,
  Sparkles,
} from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import ExecutionTraceView, { ExecutionTrace, StepTrace } from './ExecutionTraceView';
import { cn } from '@/lib/utils';

const WillowChat = dynamic(() => import('./WillowChat'), {
  ssr: false,
  loading: () => (
    <div className="flex-1 flex items-center justify-center bg-surface-0">
      <div className="flex flex-col items-center gap-3">
        <div className="relative">
          <div className="absolute inset-0 rounded-full bg-indigo-500/20 animate-ping" />
          <Loader2 className="w-8 h-8 animate-spin text-indigo-400 relative" />
        </div>
        <span className="text-sm text-slate-500 font-medium">Loading interface...</span>
      </div>
    </div>
  ),
});

type ViewMode = 'chat' | 'trace';

interface ActiveAgent {
  id: string;
  name: string;
  role: string;
  abbrev: string;
  status: 'idle' | 'working' | 'done';
}

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
  if (roleMap[role]) return roleMap[role];
  const words = name.split(' ');
  if (words.length >= 2) return words[0][0] + words[1][0];
  return name.substring(0, 2);
}

function AgentAvatar({ agent, isSelected, onClick }: {
  agent: ActiveAgent;
  isSelected?: boolean;
  onClick?: () => void;
}) {
  const statusStyles = {
    idle: 'bg-slate-800/80 text-slate-400 border-slate-700/50',
    working: 'bg-indigo-600/20 text-indigo-300 border-indigo-500/50 shadow-glow-sm',
    done: 'bg-emerald-600/20 text-emerald-300 border-emerald-500/50',
  };

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            onClick={onClick}
            className={cn(
              'w-9 h-9 rounded-xl flex items-center justify-center',
              'text-xs font-bold border transition-all duration-300',
              statusStyles[agent.status],
              isSelected && 'ring-2 ring-indigo-400/60 ring-offset-1 ring-offset-[hsl(225,15%,6%)]',
              onClick && 'hover:scale-105 cursor-pointer',
              !onClick && 'cursor-default',
              agent.status === 'working' && 'animate-pulse',
            )}
          >
            {agent.abbrev}
          </button>
        </TooltipTrigger>
        <TooltipContent side="right" className="glass border-slate-700/50">
          <div className="text-sm font-medium text-slate-100">{agent.name}</div>
          <div className="text-xs text-slate-400">{agent.role}</div>
          <div className={cn(
            'text-[10px] mt-1 font-medium',
            agent.status === 'idle' && 'text-slate-500',
            agent.status === 'working' && 'text-indigo-400',
            agent.status === 'done' && 'text-emerald-400',
          )}>
            {agent.status === 'idle' ? 'Standing by' : agent.status === 'working' ? 'Active' : 'Complete'}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

export default function LegionInterface() {
  const [viewMode, setViewMode] = useState<ViewMode>('chat');
  const [devMode, setDevMode] = useState(false);
  const [sidebarExpanded, setSidebarExpanded] = useState(false);
  const [executions, setExecutions] = useState<ExecutionTrace[]>([]);
  const [activeAgents, setActiveAgents] = useState<ActiveAgent[]>([
    { id: 'willow', name: 'Willow', role: 'Executive Conductor', abbrev: 'W', status: 'idle' }
  ]);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);

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

    if (execution.status === 'running') newAgents[0].status = 'working';
    else if (execution.status === 'completed') newAgents[0].status = 'done';

    setActiveAgents(newAgents);
  }, []);

  const handleExecutionComplete = useCallback(() => {
    setActiveAgents(prev => prev.map(a => ({ ...a, status: 'idle' as const })));
  }, []);

  const isAnyAgentWorking = activeAgents.some(a => a.status === 'working');

  const navItems = [
    { id: 'chat' as ViewMode, icon: MessageSquare, label: 'Chat' },
    ...(devMode ? [{ id: 'trace' as ViewMode, icon: Activity, label: 'Traces' }] : []),
  ];

  return (
    <div className="w-screen h-screen bg-surface-0 text-slate-50 overflow-hidden flex flex-col">
      {/* ── Top Bar ── */}
      <div className="h-12 flex items-center justify-between px-4 border-b border-slate-800/60 bg-surface-1/80 backdrop-blur-sm shrink-0 z-20">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 via-violet-500 to-fuchsia-500 flex items-center justify-center shadow-glow-sm">
            <Sparkles className="w-3.5 h-3.5 text-white" />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-slate-100">Brain Trust</span>
            <span className="text-[10px] font-mono text-slate-500 bg-slate-800/60 px-1.5 py-0.5 rounded">v2.5</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {isAnyAgentWorking && (
            <div className="flex items-center gap-2 text-xs text-indigo-400 bg-indigo-500/10 px-2.5 py-1 rounded-full border border-indigo-500/20">
              <Loader2 className="w-3 h-3 animate-spin" />
              <span className="font-medium">Processing</span>
            </div>
          )}
          <div className="flex items-center gap-1.5 text-xs text-slate-500">
            <Wifi className="w-3.5 h-3.5 text-emerald-500" />
            <span className="hidden sm:inline">Connected</span>
          </div>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* ── Sidebar ── */}
        <div className={cn(
          'flex flex-col border-r border-slate-800/60 bg-surface-1/50 transition-all duration-300 ease-in-out shrink-0',
          sidebarExpanded ? 'w-52' : 'w-14',
        )}>
          {/* Navigation */}
          <div className="flex flex-col gap-1 p-2 pt-3">
            {navItems.map(item => {
              const isActive = viewMode === item.id;
              return (
                <TooltipProvider key={item.id}>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button
                        onClick={() => setViewMode(item.id)}
                        className={cn(
                          'flex items-center gap-3 rounded-xl transition-all duration-200',
                          sidebarExpanded ? 'px-3 py-2.5' : 'p-2.5 justify-center',
                          isActive
                            ? 'bg-indigo-500/15 text-indigo-300 shadow-glow-sm'
                            : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50',
                        )}
                      >
                        <item.icon className={cn('w-[18px] h-[18px] shrink-0', isActive && 'text-indigo-400')} />
                        {sidebarExpanded && (
                          <span className="text-sm font-medium truncate">{item.label}</span>
                        )}
                      </button>
                    </TooltipTrigger>
                    {!sidebarExpanded && (
                      <TooltipContent side="right" className="glass border-slate-700/50">
                        {item.label}
                      </TooltipContent>
                    )}
                  </Tooltip>
                </TooltipProvider>
              );
            })}
          </div>

          {/* Divider */}
          <div className="mx-3 h-px bg-slate-800/60 my-2" />

          {/* Active Agents */}
          <div className="flex-1 flex flex-col gap-1.5 items-center overflow-y-auto py-2 px-2">
            {sidebarExpanded && (
              <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wider mb-1 self-start px-1">
                Agents
              </span>
            )}
            {activeAgents.map(agent => (
              <div key={agent.id} className={cn('flex items-center gap-2.5', sidebarExpanded ? 'w-full px-1' : '')}>
                <AgentAvatar
                  agent={agent}
                  isSelected={selectedAgentId === agent.id}
                  onClick={() => {
                    if (agent.id === 'willow') setSelectedAgentId(null);
                    else setSelectedAgentId(agent.id === selectedAgentId ? null : agent.id);
                  }}
                />
                {sidebarExpanded && (
                  <div className="min-w-0 flex-1">
                    <div className="text-xs font-medium text-slate-300 truncate">{agent.name}</div>
                    <div className="text-[10px] text-slate-500 truncate">{agent.role}</div>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Bottom Controls */}
          <div className="flex flex-col gap-1 p-2 border-t border-slate-800/60">
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    onClick={() => setDevMode(!devMode)}
                    className={cn(
                      'flex items-center gap-3 rounded-xl transition-all duration-200',
                      sidebarExpanded ? 'px-3 py-2.5' : 'p-2.5 justify-center',
                      devMode
                        ? 'bg-amber-500/15 text-amber-400'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50',
                    )}
                  >
                    <Settings className="w-[18px] h-[18px] shrink-0" />
                    {sidebarExpanded && <span className="text-sm font-medium">Dev Mode</span>}
                  </button>
                </TooltipTrigger>
                {!sidebarExpanded && (
                  <TooltipContent side="right" className="glass border-slate-700/50">
                    {devMode ? 'Dev Mode: ON' : 'Dev Mode: OFF'}
                  </TooltipContent>
                )}
              </Tooltip>
            </TooltipProvider>

            <button
              onClick={() => setSidebarExpanded(!sidebarExpanded)}
              className={cn(
                'flex items-center gap-3 rounded-xl transition-all duration-200 text-slate-500 hover:text-slate-300 hover:bg-slate-800/50',
                sidebarExpanded ? 'px-3 py-2.5' : 'p-2.5 justify-center',
              )}
            >
              {sidebarExpanded ? (
                <>
                  <ChevronLeft className="w-[18px] h-[18px] shrink-0" />
                  <span className="text-sm font-medium">Collapse</span>
                </>
              ) : (
                <ChevronRight className="w-[18px] h-[18px] shrink-0" />
              )}
            </button>
          </div>
        </div>

        {/* ── Main Content ── */}
        <div className="flex-1 flex flex-col relative min-w-0">
          <div className={cn(
            'absolute inset-0 transition-opacity duration-300',
            viewMode === 'chat' ? 'z-10 opacity-100' : 'z-0 pointer-events-none opacity-0'
          )}>
            <WillowChat
              onExecutionUpdate={handleExecutionUpdate}
              onExecutionComplete={handleExecutionComplete}
              selectedAgentId={selectedAgentId}
              showDevToggle={!devMode}
              onToggleDevMode={() => setDevMode(true)}
            />
          </div>

          {devMode && (
            <div className={cn(
              'absolute inset-0 transition-opacity duration-300',
              viewMode === 'trace' ? 'z-10 opacity-100' : 'z-0 pointer-events-none opacity-0'
            )}>
              <ExecutionTraceView
                executions={executions}
                onBack={() => setViewMode('chat')}
              />
            </div>
          )}
        </div>
      </div>

      {/* ── Status Bar ── */}
      <div className="h-7 flex items-center justify-between px-4 border-t border-slate-800/60 bg-surface-1/50 text-[11px] text-slate-500 shrink-0">
        <div className="flex items-center gap-4">
          <span className="font-mono">Legion v3</span>
          <span>{activeAgents.length} agent{activeAgents.length !== 1 ? 's' : ''}</span>
          {executions.length > 0 && (
            <span>{executions.length} execution{executions.length !== 1 ? 's' : ''}</span>
          )}
        </div>
        <div className="flex items-center gap-3">
          {devMode && (
            <span className="text-amber-500/80 font-medium">DEV</span>
          )}
          <span className="font-mono">localhost:8000</span>
        </div>
      </div>
    </div>
  );
}
