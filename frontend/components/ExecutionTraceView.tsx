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
  ChevronLeft,
  Wrench,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

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

function StepStatusIcon({ status }: { status: StepTrace['status'] }) {
  switch (status) {
    case 'completed':
      return <CheckCircle className="w-4 h-4 text-emerald-400" />;
    case 'failed':
      return <XCircle className="w-4 h-4 text-red-400" />;
    case 'running':
      return <Loader2 className="w-4 h-4 text-indigo-400 animate-spin" />;
    case 'blocked':
      return <AlertCircle className="w-4 h-4 text-amber-400" />;
    default:
      return <Clock className="w-4 h-4 text-slate-600" />;
  }
}

function getAgentAbbrev(role: string): string {
  const abbrevMap: Record<string, string> = {
    'Librarian': 'Li', 'Writer': 'Wr', 'Creative Writer': 'Wr',
    'Editor': 'Ed', 'Developmental Editor': 'DE', 'Line Editor': 'LE',
    'Copy Editor': 'CE', 'Beta Reader': 'BR', 'Developer': 'Dv',
    'Artist': 'Ar', 'Analyst': 'An', 'Executive Conductor': 'W',
  };
  return abbrevMap[role] || role.substring(0, 2);
}

function StepItem({ step, isExpanded, onToggle }: {
  step: StepTrace;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const hasDetails = step.output || step.error || (step.tools_called && step.tools_called.length > 0);

  const statusBorder = {
    pending: 'border-slate-700/50',
    running: 'border-indigo-500/40',
    completed: 'border-emerald-500/40',
    failed: 'border-red-500/40',
    blocked: 'border-amber-500/40',
  }[step.status];

  return (
    <div className={cn('border-l-2 pl-4 py-2.5 ml-3 transition-colors', statusBorder)}>
      <div
        className={cn(
          'flex items-center gap-2.5',
          hasDetails && 'cursor-pointer hover:bg-surface-3/50 -ml-4 pl-4 py-1.5 rounded-lg',
        )}
        onClick={hasDetails ? onToggle : undefined}
      >
        {hasDetails && (
          isExpanded
            ? <ChevronDown className="w-3 h-3 text-slate-500 shrink-0" />
            : <ChevronRight className="w-3 h-3 text-slate-500 shrink-0" />
        )}
        <StepStatusIcon status={step.status} />
        <Badge variant="outline" className="text-[10px] h-5 font-mono border-slate-700 text-slate-400 shrink-0">
          {getAgentAbbrev(step.agent_role)}
        </Badge>
        <span className="text-sm text-slate-300 flex-1 truncate">{step.description}</span>
        {step.duration_seconds !== undefined && (
          <div className="flex items-center gap-1 text-xs text-slate-500 shrink-0">
            <Clock className="w-3 h-3" />
            <span>{step.duration_seconds.toFixed(1)}s</span>
          </div>
        )}
      </div>

      {isExpanded && hasDetails && (
        <div className="mt-2.5 ml-6 space-y-2.5 animate-fade-up">
          {step.tools_called && step.tools_called.length > 0 && (
            <div className="flex items-center gap-1.5 text-xs text-slate-500">
              <Wrench className="w-3 h-3" />
              <span>{step.tools_called.join(', ')}</span>
            </div>
          )}
          {step.output && (
            <div className="bg-surface-1 rounded-lg p-3 text-xs text-slate-400 max-h-40 overflow-auto border border-slate-800/40">
              <pre className="whitespace-pre-wrap font-mono">{step.output.slice(0, 500)}{step.output.length > 500 ? '...' : ''}</pre>
            </div>
          )}
          {step.error && (
            <div className="bg-red-500/5 border border-red-500/20 rounded-lg p-3 text-xs text-red-300">
              {step.error}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ExecutionItem({ execution }: { execution: ExecutionTrace }) {
  const [isExpanded, setIsExpanded] = useState(execution.status === 'running');
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set());

  const toggleStep = (stepId: string) => {
    setExpandedSteps(prev => {
      const next = new Set(prev);
      if (next.has(stepId)) next.delete(stepId);
      else next.add(stepId);
      return next;
    });
  };

  const statusConfig = {
    running: {
      border: 'border-indigo-500/30',
      bg: 'bg-indigo-500/5',
      icon: <Loader2 className="w-4 h-4 text-indigo-400 animate-spin" />,
      label: 'Running',
      labelColor: 'text-indigo-400',
    },
    completed: {
      border: 'border-emerald-500/30',
      bg: 'bg-emerald-500/5',
      icon: <CheckCircle className="w-4 h-4 text-emerald-400" />,
      label: 'Completed',
      labelColor: 'text-emerald-400',
    },
    failed: {
      border: 'border-red-500/30',
      bg: 'bg-red-500/5',
      icon: <XCircle className="w-4 h-4 text-red-400" />,
      label: 'Failed',
      labelColor: 'text-red-400',
    },
  }[execution.status];

  return (
    <div className={cn('rounded-xl border mb-3 overflow-hidden transition-all', statusConfig.border, statusConfig.bg)}>
      <div
        className="px-4 py-3.5 cursor-pointer hover:bg-surface-3/30 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          {isExpanded
            ? <ChevronDown className="w-4 h-4 text-slate-400 shrink-0" />
            : <ChevronRight className="w-4 h-4 text-slate-400 shrink-0" />
          }
          {statusConfig.icon}
          <div className="flex-1 min-w-0">
            <span className="text-sm font-medium text-slate-200 truncate block">{execution.intent}</span>
            <div className="flex items-center gap-2 mt-0.5">
              <span className={cn('text-[10px] font-medium', statusConfig.labelColor)}>{statusConfig.label}</span>
              <span className="text-[10px] text-slate-600">&middot;</span>
              <span className="text-[10px] text-slate-500" suppressHydrationWarning>
                {execution.timestamp.toLocaleTimeString()}
              </span>
              <span className="text-[10px] text-slate-600">&middot;</span>
              <span className="text-[10px] text-slate-500">{execution.steps.length} steps</span>
            </div>
          </div>
          {execution.duration_seconds !== undefined && (
            <div className="flex items-center gap-1 text-xs text-slate-500 shrink-0">
              <Clock className="w-3 h-3" />
              <span>{execution.duration_seconds.toFixed(1)}s</span>
            </div>
          )}
        </div>
      </div>

      {isExpanded && (
        <div className="px-4 pb-4">
          <div className="border-t border-slate-800/40 pt-3 mt-1">
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
            <div className="mt-3 pt-3 border-t border-slate-800/40">
              <div className="text-xs text-slate-500 mb-1.5 font-medium">Final Output</div>
              <div className="bg-surface-1 rounded-lg p-3 text-xs text-slate-400 max-h-32 overflow-auto border border-slate-800/40">
                <pre className="whitespace-pre-wrap font-mono">
                  {execution.final_output.slice(0, 300)}
                  {execution.final_output.length > 300 ? '...' : ''}
                </pre>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ExecutionTraceView({ executions, onBack }: ExecutionTraceViewProps) {
  return (
    <div className="flex flex-col h-full bg-surface-0">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800/60 bg-surface-1/30 backdrop-blur-sm shrink-0">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={onBack}
            className="text-slate-400 hover:text-slate-200 h-8 -ml-2"
          >
            <ChevronLeft className="w-4 h-4 mr-1" />
            Back
          </Button>
          <div>
            <h1 className="text-sm font-semibold text-slate-100">Execution Traces</h1>
            <p className="text-[11px] text-slate-500">Monitor agent activity</p>
          </div>
        </div>
        <Badge variant="outline" className="text-[10px] h-5 border-slate-700 text-slate-400">
          {executions.length} execution{executions.length !== 1 ? 's' : ''}
        </Badge>
      </div>

      {/* Execution List */}
      <div className="flex-1 overflow-y-auto p-4">
        {executions.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-500">
            <div className="w-14 h-14 rounded-2xl bg-surface-2 border border-slate-800/40 flex items-center justify-center mb-4">
              <Clock className="w-6 h-6 text-slate-600" />
            </div>
            <p className="text-sm font-medium text-slate-400">No executions yet</p>
            <p className="text-xs text-slate-600 mt-1">Send a message to Willow to see traces here</p>
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
