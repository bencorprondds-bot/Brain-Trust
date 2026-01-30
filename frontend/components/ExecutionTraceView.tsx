"use client";

import React, { useState } from 'react';
import {
  ChevronDown,
  ChevronRight,
  CheckCircle,
  XCircle,
  Clock,
  Loader2,
  AlertCircle,
  ChevronLeft
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

// Types for execution traces
export interface StepTrace {
  id: string;
  order: number;
  agent_role: string;
  description: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'blocked';
  duration_seconds?: number;
  output?: string;
  error?: string;
  tools_called?: string[];
}

export interface ExecutionTrace {
  id: string;
  timestamp: Date;
  intent: string;
  status: 'running' | 'completed' | 'failed';
  duration_seconds?: number;
  steps: StepTrace[];
  final_output?: string;
}

interface ExecutionTraceViewProps {
  executions: ExecutionTrace[];
  onBack: () => void;
}

// Status icon component
function StepStatusIcon({ status }: { status: StepTrace['status'] }) {
  switch (status) {
    case 'completed':
      return <CheckCircle className="w-4 h-4 text-emerald-400" />;
    case 'failed':
      return <XCircle className="w-4 h-4 text-red-400" />;
    case 'running':
      return <Loader2 className="w-4 h-4 text-cyan-400 animate-spin" />;
    case 'blocked':
      return <AlertCircle className="w-4 h-4 text-amber-400" />;
    default:
      return <Clock className="w-4 h-4 text-zinc-500" />;
  }
}

// Agent abbreviation helper
function getAgentAbbrev(role: string): string {
  const abbrevMap: Record<string, string> = {
    'Librarian': 'Li',
    'Writer': 'Wr',
    'Creative Writer': 'Wr',
    'Editor': 'Ed',
    'Developmental Editor': 'DE',
    'Line Editor': 'LE',
    'Copy Editor': 'CE',
    'Beta Reader': 'BR',
    'Developer': 'Dv',
    'Artist': 'Ar',
    'Analyst': 'An',
    'Executive Conductor': 'W',
  };
  return abbrevMap[role] || role.substring(0, 2);
}

// Single step component
function StepItem({ step, isExpanded, onToggle }: {
  step: StepTrace;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const hasDetails = step.output || step.error || (step.tools_called && step.tools_called.length > 0);

  return (
    <div className="border-l-2 border-zinc-700 pl-4 py-2 ml-2">
      <div
        className={`flex items-center gap-2 ${hasDetails ? 'cursor-pointer hover:bg-zinc-800/50 -ml-4 pl-4 py-1 rounded' : ''}`}
        onClick={hasDetails ? onToggle : undefined}
      >
        {hasDetails && (
          isExpanded
            ? <ChevronDown className="w-3 h-3 text-zinc-500" />
            : <ChevronRight className="w-3 h-3 text-zinc-500" />
        )}
        <StepStatusIcon status={step.status} />
        <Badge variant="outline" className="text-xs font-mono">
          {getAgentAbbrev(step.agent_role)}
        </Badge>
        <span className="text-sm text-zinc-300 flex-1 truncate">
          {step.description}
        </span>
        {step.duration_seconds !== undefined && (
          <span className="text-xs text-zinc-500">
            {step.duration_seconds.toFixed(1)}s
          </span>
        )}
      </div>

      {isExpanded && hasDetails && (
        <div className="mt-2 ml-6 space-y-2">
          {step.tools_called && step.tools_called.length > 0 && (
            <div className="text-xs text-zinc-500">
              Tools: {step.tools_called.join(', ')}
            </div>
          )}
          {step.output && (
            <div className="bg-zinc-900 rounded p-2 text-xs text-zinc-400 max-h-40 overflow-auto">
              <pre className="whitespace-pre-wrap">{step.output.slice(0, 500)}{step.output.length > 500 ? '...' : ''}</pre>
            </div>
          )}
          {step.error && (
            <div className="bg-red-900/20 border border-red-800 rounded p-2 text-xs text-red-300">
              {step.error}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Single execution component
function ExecutionItem({ execution }: { execution: ExecutionTrace }) {
  const [isExpanded, setIsExpanded] = useState(execution.status === 'running');
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set());

  const toggleStep = (stepId: string) => {
    setExpandedSteps(prev => {
      const next = new Set(prev);
      if (next.has(stepId)) {
        next.delete(stepId);
      } else {
        next.add(stepId);
      }
      return next;
    });
  };

  const statusColor = {
    running: 'border-cyan-500 bg-cyan-500/10',
    completed: 'border-emerald-500 bg-emerald-500/10',
    failed: 'border-red-500 bg-red-500/10',
  }[execution.status];

  return (
    <Card className={`bg-zinc-900/50 border ${statusColor} mb-3`}>
      <div
        className="p-3 cursor-pointer hover:bg-zinc-800/30"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2">
          {isExpanded
            ? <ChevronDown className="w-4 h-4 text-zinc-400" />
            : <ChevronRight className="w-4 h-4 text-zinc-400" />
          }
          {execution.status === 'running' && (
            <Loader2 className="w-4 h-4 text-cyan-400 animate-spin" />
          )}
          {execution.status === 'completed' && (
            <CheckCircle className="w-4 h-4 text-emerald-400" />
          )}
          {execution.status === 'failed' && (
            <XCircle className="w-4 h-4 text-red-400" />
          )}
          <span className="text-sm font-medium text-zinc-200 flex-1 truncate">
            {execution.intent}
          </span>
          {execution.duration_seconds !== undefined && (
            <span className="text-xs text-zinc-500">
              {execution.duration_seconds.toFixed(1)}s
            </span>
          )}
        </div>
        <div className="text-xs text-zinc-500 mt-1 ml-6">
          {execution.timestamp.toLocaleTimeString()} · {execution.steps.length} steps
        </div>
      </div>

      {isExpanded && (
        <div className="px-3 pb-3">
          <div className="border-t border-zinc-800 pt-3 mt-1">
            {execution.steps.map((step) => (
              <StepItem
                key={step.id}
                step={step}
                isExpanded={expandedSteps.has(step.id)}
                onToggle={() => toggleStep(step.id)}
              />
            ))}
          </div>

          {execution.final_output && (
            <div className="mt-3 pt-3 border-t border-zinc-800">
              <div className="text-xs text-zinc-500 mb-1">Final Output:</div>
              <div className="bg-zinc-900 rounded p-2 text-xs text-zinc-400 max-h-32 overflow-auto">
                <pre className="whitespace-pre-wrap">
                  {execution.final_output.slice(0, 300)}
                  {execution.final_output.length > 300 ? '...' : ''}
                </pre>
              </div>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

export default function ExecutionTraceView({ executions, onBack }: ExecutionTraceViewProps) {
  return (
    <div className="flex flex-col h-full bg-zinc-950">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-zinc-800">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={onBack}
            className="text-zinc-400 hover:text-zinc-100"
          >
            <ChevronLeft className="w-4 h-4 mr-1" />
            Back
          </Button>
          <div>
            <h1 className="text-lg font-semibold text-zinc-100">Execution Trace</h1>
            <p className="text-xs text-zinc-500">View what Willow and the team are doing</p>
          </div>
        </div>
        <Badge variant="outline" className="text-zinc-400">
          {executions.length} execution{executions.length !== 1 ? 's' : ''}
        </Badge>
      </div>

      {/* Execution List */}
      <div className="flex-1 overflow-y-auto p-4">
        {executions.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-zinc-500">
            <Clock className="w-12 h-12 mb-3 opacity-50" />
            <p>No executions yet</p>
            <p className="text-sm mt-1">Send a message to Willow to see traces here</p>
          </div>
        ) : (
          [...executions].reverse().map((execution) => (
            <ExecutionItem key={execution.id} execution={execution} />
          ))
        )}
      </div>
    </div>
  );
}
