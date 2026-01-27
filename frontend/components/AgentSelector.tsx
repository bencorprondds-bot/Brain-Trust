'use client';

import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown, Users, User, Bot, Layers, Check, Trash2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  AgentPreset,
  AgentGroup,
  agentGroups,
  coreAgents,
  editorialAgents,
  betaReaderAgents,
  utilityAgents,
  getAgentsFromGroup,
  presetToNode,
  getAgentById,
} from '@/lib/agent-presets';

interface AgentSelectorProps {
  onAddAgent: (node: ReturnType<typeof presetToNode>, presetId: string) => void;
  onAddGroup: (nodes: ReturnType<typeof presetToNode>[], presetIds: string[]) => void;
  onRemoveAgent: (nodeId: string) => void;
  agentsOnCanvas: string[]; // Array of preset IDs currently on canvas
  className?: string;
}

export default function AgentSelector({
  onAddAgent,
  onAddGroup,
  onRemoveAgent,
  agentsOnCanvas,
  className
}: AgentSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<'agents' | 'groups'>('agents');
  const [isDragOver, setIsDragOver] = useState(false);
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

  // Filter out agents already on canvas
  const filterAvailableAgents = (agents: AgentPreset[]) => {
    return agents.filter(agent => !agentsOnCanvas.includes(agent.id));
  };

  const handleDragStart = (e: React.DragEvent, agent: AgentPreset) => {
    e.dataTransfer.setData('application/json', JSON.stringify({
      type: 'add-agent',
      agent: agent
    }));
    e.dataTransfer.effectAllowed = 'copy';
  };

  const handleAddAgent = (agent: AgentPreset) => {
    const position = {
      x: 100 + Math.random() * 200,
      y: 100 + Math.random() * 200,
    };
    onAddAgent(presetToNode(agent, position), agent.id);
    setIsOpen(false);
  };

  const handleAddGroup = (group: AgentGroup) => {
    // Only add agents not already on canvas
    const availableAgentIds = group.agentIds.filter(id => !agentsOnCanvas.includes(id));
    const agents = availableAgentIds.map(id => getAgentById(id)).filter((a): a is AgentPreset => a !== undefined);

    if (agents.length === 0) {
      setIsOpen(false);
      return;
    }

    const nodes = agents.map((agent, index) => {
      const cols = 4;
      const row = Math.floor(index / cols);
      const col = index % cols;
      const position = {
        x: 100 + col * 300,
        y: 300 + row * 200,
      };
      return presetToNode(agent, position);
    });
    onAddGroup(nodes, availableAgentIds);
    setIsOpen(false);
  };

  // Handle drop from canvas (removing agent)
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);

    try {
      const data = JSON.parse(e.dataTransfer.getData('application/json'));
      if (data.type === 'remove-agent' && data.nodeId) {
        onRemoveAgent(data.nodeId);
      }
    } catch (err) {
      // Not valid JSON or wrong data type
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    // Check if it's a remove operation
    try {
      const types = e.dataTransfer.types;
      if (types.includes('application/json')) {
        e.dataTransfer.dropEffect = 'move';
        setIsDragOver(true);
      }
    } catch (err) {
      // Ignore
    }
  };

  const handleDragLeave = (e: React.DragEvent) => {
    // Only set false if we're leaving the entire dropdown area
    if (!dropdownRef.current?.contains(e.relatedTarget as Node)) {
      setIsDragOver(false);
    }
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

  const availableCoreAgents = filterAvailableAgents(coreAgents);
  const availableEditorialAgents = filterAvailableAgents(editorialAgents);
  const availableBetaReaders = filterAvailableAgents(betaReaderAgents);
  const availableUtilityAgents = filterAvailableAgents(utilityAgents);
  const totalAvailable = availableCoreAgents.length + availableEditorialAgents.length +
                         availableBetaReaders.length + availableUtilityAgents.length;

  return (
    <div
      ref={dropdownRef}
      className={cn('relative', className)}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
    >
      {/* Trigger Button - also acts as drop zone */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'flex items-center gap-2 px-3 py-2 rounded-lg',
          'bg-zinc-900 border border-zinc-800 hover:border-zinc-700',
          'text-sm font-medium text-zinc-300 hover:text-zinc-100',
          'transition-all duration-200',
          isOpen && 'border-cyan-500/50 ring-1 ring-cyan-500/20',
          isDragOver && 'border-red-500 ring-2 ring-red-500/30 bg-red-950/30'
        )}
      >
        {isDragOver ? (
          <>
            <Trash2 className="w-4 h-4 text-red-400" />
            <span className="text-red-400">Drop to Remove</span>
          </>
        ) : (
          <>
            <Users className="w-4 h-4 text-cyan-400" />
            <span>Add Agents</span>
            {totalAvailable > 0 && (
              <span className="text-[10px] bg-zinc-800 px-1.5 py-0.5 rounded text-zinc-400">
                {totalAvailable}
              </span>
            )}
            <ChevronDown className={cn('w-4 h-4 transition-transform', isOpen && 'rotate-180')} />
          </>
        )}
      </button>

      {/* Drop Zone Overlay when dragging */}
      {isDragOver && !isOpen && (
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute -inset-2 border-2 border-dashed border-red-500 rounded-xl animate-pulse" />
        </div>
      )}

      {/* Dropdown Panel */}
      {isOpen && (
        <div className="absolute top-full left-0 mt-2 w-80 z-50 animate-in fade-in slide-in-from-top-2 duration-200">
          <div className={cn(
            "bg-zinc-950 border border-zinc-800 rounded-lg shadow-xl overflow-hidden",
            isDragOver && "border-red-500 ring-2 ring-red-500/30"
          )}>
            {/* Drop zone indicator when open and dragging */}
            {isDragOver && (
              <div className="p-3 bg-red-950/50 border-b border-red-500/30 flex items-center gap-2">
                <Trash2 className="w-4 h-4 text-red-400" />
                <span className="text-sm text-red-400">Drop here to remove agent</span>
              </div>
            )}

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
                  {/* Drag hint */}
                  <div className="px-2 py-1.5 text-[10px] text-zinc-500 bg-zinc-900/50 rounded border border-zinc-800">
                    <span className="text-cyan-400">Tip:</span> Drag agents to canvas, or drag canvas agents here to remove
                  </div>

                  {/* Core Agents */}
                  <AgentCategory
                    title="Core"
                    agents={availableCoreAgents}
                    onSelect={handleAddAgent}
                    onDragStart={handleDragStart}
                    getCategoryIcon={getCategoryIcon}
                    getCategoryColor={getCategoryColor}
                  />

                  {/* Editorial Agents */}
                  <AgentCategory
                    title="Editorial Pipeline"
                    agents={availableEditorialAgents}
                    onSelect={handleAddAgent}
                    onDragStart={handleDragStart}
                    getCategoryIcon={getCategoryIcon}
                    getCategoryColor={getCategoryColor}
                  />

                  {/* Beta Readers */}
                  <AgentCategory
                    title="Beta Readers"
                    agents={availableBetaReaders}
                    onSelect={handleAddAgent}
                    onDragStart={handleDragStart}
                    getCategoryIcon={getCategoryIcon}
                    getCategoryColor={getCategoryColor}
                  />

                  {/* Utility Agents */}
                  <AgentCategory
                    title="Utility"
                    agents={availableUtilityAgents}
                    onSelect={handleAddAgent}
                    onDragStart={handleDragStart}
                    getCategoryIcon={getCategoryIcon}
                    getCategoryColor={getCategoryColor}
                  />

                  {totalAvailable === 0 && (
                    <div className="p-4 text-center text-zinc-500 text-sm">
                      All agents are on the canvas
                    </div>
                  )}
                </div>
              ) : (
                <div className="p-2 space-y-2">
                  {agentGroups.map((group) => {
                    const availableCount = group.agentIds.filter(id => !agentsOnCanvas.includes(id)).length;
                    const allOnCanvas = availableCount === 0;

                    return (
                      <button
                        key={group.id}
                        onClick={() => handleAddGroup(group)}
                        disabled={allOnCanvas}
                        className={cn(
                          'w-full flex items-start gap-3 p-3 rounded-lg',
                          'bg-zinc-900/50 border border-zinc-800',
                          'transition-all duration-150 text-left',
                          allOnCanvas
                            ? 'opacity-50 cursor-not-allowed'
                            : 'hover:bg-zinc-800/80 hover:border-zinc-700',
                          group.id === 'beta-readers-all' && !allOnCanvas && 'border-amber-500/30 hover:border-amber-500/50'
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
                            {allOnCanvas ? 'All on canvas' : `${availableCount}/${group.agentIds.length} available`}
                          </div>
                        </div>
                      </button>
                    );
                  })}

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
  onDragStart,
  getCategoryIcon,
  getCategoryColor,
}: {
  title: string;
  agents: AgentPreset[];
  onSelect: (agent: AgentPreset) => void;
  onDragStart: (e: React.DragEvent, agent: AgentPreset) => void;
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
          <div
            key={agent.id}
            draggable
            onDragStart={(e) => onDragStart(e, agent)}
            onClick={() => onSelect(agent)}
            className={cn(
              'w-full flex items-center gap-2.5 px-2.5 py-2 rounded-md',
              'hover:bg-zinc-800/70 transition-colors text-left group cursor-grab active:cursor-grabbing'
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
            <div className="opacity-0 group-hover:opacity-100 transition-opacity">
              <div className="text-[10px] text-zinc-600 bg-zinc-800 px-1.5 py-0.5 rounded">
                drag
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
