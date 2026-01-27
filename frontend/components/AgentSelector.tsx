'use client';

import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown, Users, User, Bot, Layers, Check } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  AgentPreset,
  AgentGroup,
  allAgents,
  agentGroups,
  coreAgents,
  editorialAgents,
  betaReaderAgents,
  utilityAgents,
  getAgentsFromGroup,
  presetToNode,
} from '@/lib/agent-presets';

interface AgentSelectorProps {
  onAddAgent: (node: ReturnType<typeof presetToNode>) => void;
  onAddGroup: (nodes: ReturnType<typeof presetToNode>[]) => void;
  className?: string;
}

export default function AgentSelector({ onAddAgent, onAddGroup, className }: AgentSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<'agents' | 'groups'>('agents');
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleAddAgent = (agent: AgentPreset) => {
    // Calculate position - stagger based on existing nodes would be ideal
    // For now, use a semi-random offset
    const position = {
      x: 100 + Math.random() * 200,
      y: 100 + Math.random() * 200,
    };
    onAddAgent(presetToNode(agent, position));
    setIsOpen(false);
  };

  const handleAddGroup = (group: AgentGroup) => {
    const agents = getAgentsFromGroup(group.id);
    const nodes = agents.map((agent, index) => {
      // Arrange in a grid pattern
      const cols = 4;
      const row = Math.floor(index / cols);
      const col = index % cols;
      const position = {
        x: 100 + col * 300,
        y: 300 + row * 200,
      };
      return presetToNode(agent, position);
    });
    onAddGroup(nodes);
    setIsOpen(false);
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'core':
        return <Bot className="w-3.5 h-3.5" />;
      case 'editorial':
        return <Layers className="w-3.5 h-3.5" />;
      case 'beta-reader':
        return <User className="w-3.5 h-3.5" />;
      default:
        return <Bot className="w-3.5 h-3.5" />;
    }
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'core':
        return 'text-cyan-400 bg-cyan-950/50 border-cyan-500/30';
      case 'editorial':
        return 'text-purple-400 bg-purple-950/50 border-purple-500/30';
      case 'beta-reader':
        return 'text-amber-400 bg-amber-950/50 border-amber-500/30';
      default:
        return 'text-zinc-400 bg-zinc-800 border-zinc-700';
    }
  };

  return (
    <div ref={dropdownRef} className={cn('relative', className)}>
      {/* Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'flex items-center gap-2 px-3 py-2 rounded-lg',
          'bg-zinc-900 border border-zinc-800 hover:border-zinc-700',
          'text-sm font-medium text-zinc-300 hover:text-zinc-100',
          'transition-all duration-200',
          isOpen && 'border-cyan-500/50 ring-1 ring-cyan-500/20'
        )}
      >
        <Users className="w-4 h-4 text-cyan-400" />
        <span>Add Agents</span>
        <ChevronDown className={cn('w-4 h-4 transition-transform', isOpen && 'rotate-180')} />
      </button>

      {/* Dropdown Panel */}
      {isOpen && (
        <div className="absolute top-full left-0 mt-2 w-80 z-50 animate-in fade-in slide-in-from-top-2 duration-200">
          <div className="bg-zinc-950 border border-zinc-800 rounded-lg shadow-xl overflow-hidden">
            {/* Tabs */}
            <div className="flex border-b border-zinc-800">
              <button
                onClick={() => setActiveTab('agents')}
                className={cn(
                  'flex-1 px-4 py-2.5 text-xs font-medium uppercase tracking-wider',
                  'transition-colors',
                  activeTab === 'agents'
                    ? 'bg-zinc-900 text-cyan-400 border-b-2 border-cyan-400'
                    : 'text-zinc-500 hover:text-zinc-300'
                )}
              >
                Individual Agents
              </button>
              <button
                onClick={() => setActiveTab('groups')}
                className={cn(
                  'flex-1 px-4 py-2.5 text-xs font-medium uppercase tracking-wider',
                  'transition-colors',
                  activeTab === 'groups'
                    ? 'bg-zinc-900 text-cyan-400 border-b-2 border-cyan-400'
                    : 'text-zinc-500 hover:text-zinc-300'
                )}
              >
                Agent Groups
              </button>
            </div>

            {/* Content */}
            <div className="max-h-96 overflow-y-auto">
              {activeTab === 'agents' ? (
                <div className="p-2 space-y-3">
                  {/* Core Agents */}
                  <AgentCategory
                    title="Core"
                    agents={coreAgents}
                    onSelect={handleAddAgent}
                    getCategoryIcon={getCategoryIcon}
                    getCategoryColor={getCategoryColor}
                  />

                  {/* Editorial Agents */}
                  <AgentCategory
                    title="Editorial Pipeline"
                    agents={editorialAgents}
                    onSelect={handleAddAgent}
                    getCategoryIcon={getCategoryIcon}
                    getCategoryColor={getCategoryColor}
                  />

                  {/* Beta Readers */}
                  <AgentCategory
                    title="Beta Readers"
                    agents={betaReaderAgents}
                    onSelect={handleAddAgent}
                    getCategoryIcon={getCategoryIcon}
                    getCategoryColor={getCategoryColor}
                  />

                  {/* Utility Agents */}
                  <AgentCategory
                    title="Utility"
                    agents={utilityAgents}
                    onSelect={handleAddAgent}
                    getCategoryIcon={getCategoryIcon}
                    getCategoryColor={getCategoryColor}
                  />
                </div>
              ) : (
                <div className="p-2 space-y-2">
                  {agentGroups.map((group) => (
                    <button
                      key={group.id}
                      onClick={() => handleAddGroup(group)}
                      className={cn(
                        'w-full flex items-start gap-3 p-3 rounded-lg',
                        'bg-zinc-900/50 border border-zinc-800',
                        'hover:bg-zinc-800/80 hover:border-zinc-700',
                        'transition-all duration-150 text-left',
                        group.id === 'beta-readers-all' && 'border-amber-500/30 hover:border-amber-500/50'
                      )}
                    >
                      <div
                        className={cn(
                          'p-2 rounded-md',
                          group.id === 'beta-readers-all'
                            ? 'bg-amber-950/50 text-amber-400'
                            : group.id === 'editorial-team'
                            ? 'bg-purple-950/50 text-purple-400'
                            : 'bg-cyan-950/50 text-cyan-400'
                        )}
                      >
                        <Users className="w-4 h-4" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-zinc-200 text-sm">{group.name}</div>
                        <div className="text-xs text-zinc-500 mt-0.5">{group.description}</div>
                        <div className="text-[10px] text-zinc-600 mt-1 font-mono">
                          {group.agentIds.length} agents
                        </div>
                      </div>
                    </button>
                  ))}

                  {/* Special highlight for Beta Readers group */}
                  <div className="mt-3 p-3 bg-amber-950/20 border border-amber-500/20 rounded-lg">
                    <div className="flex items-center gap-2 text-amber-400 text-xs font-medium">
                      <Check className="w-3.5 h-3.5" />
                      <span>Beta Readers run in parallel after Final Review</span>
                    </div>
                    <p className="text-[10px] text-zinc-500 mt-1">
                      Select "All Beta Readers" to add the complete reader panel. They'll provide
                      diverse feedback simultaneously.
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Sub-component for agent category sections
function AgentCategory({
  title,
  agents,
  onSelect,
  getCategoryIcon,
  getCategoryColor,
}: {
  title: string;
  agents: AgentPreset[];
  onSelect: (agent: AgentPreset) => void;
  getCategoryIcon: (category: string) => React.ReactNode;
  getCategoryColor: (category: string) => string;
}) {
  if (agents.length === 0) return null;

  return (
    <div>
      <div className="text-[10px] font-medium text-zinc-500 uppercase tracking-wider px-2 mb-1.5">
        {title}
      </div>
      <div className="space-y-1">
        {agents.map((agent) => (
          <button
            key={agent.id}
            onClick={() => onSelect(agent)}
            className={cn(
              'w-full flex items-center gap-2.5 px-2.5 py-2 rounded-md',
              'hover:bg-zinc-800/70 transition-colors text-left group'
            )}
          >
            <div className={cn('p-1.5 rounded border', getCategoryColor(agent.category))}>
              {getCategoryIcon(agent.category)}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm text-zinc-200 truncate group-hover:text-zinc-50">
                {agent.name}
              </div>
              <div className="text-[10px] text-zinc-500 truncate">{agent.role}</div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
