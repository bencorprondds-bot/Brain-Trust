"use client";

import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Send,
  Loader2,
  CheckCircle,
  XCircle,
  Settings,
  Sparkles,
  Clock,
  ArrowRight,
  User,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ExecutionTrace, StepTrace } from './ExecutionTraceView';
import { cn } from '@/lib/utils';

interface PlanStep {
  id: string;
  order: number;
  description: string;
  agent_role: string;
  status: string;
}

interface Plan {
  id: string;
  intent_summary: string;
  project: string;
  steps: PlanStep[];
  status: string;
}

interface WillowMessage {
  role: 'user' | 'willow' | 'system';
  content: string;
  timestamp: Date;
  plan?: Plan;
  needs_input?: boolean;
  input_options?: string[];
  execution_result?: {
    status: string;
    final_output?: string;
    step_results?: Array<{
      step_id: string;
      result: string;
      output?: string;
      error?: string;
      duration_seconds?: number;
      tools_called?: string[];
    }>;
    total_duration_seconds?: number;
  };
  agentAttribution?: string;
}

interface WillowChatProps {
  onExecutionUpdate?: (execution: ExecutionTrace) => void;
  onExecutionComplete?: () => void;
  selectedAgentId?: string | null;
  showDevToggle?: boolean;
  onToggleDevMode?: () => void;
}

function getAgentBadge(role: string): string {
  const roleMap: Record<string, string> = {
    'Librarian': 'Li', 'Writer': 'Wr', 'Creative Writer': 'Wr',
    'Developmental Editor': 'DE', 'Line Editor': 'LE', 'Copy Editor': 'CE',
    'Editor': 'Ed', 'Beta Reader': 'BR', 'Developer': 'Dv',
  };
  return roleMap[role] || role.substring(0, 2);
}

function TypingIndicator() {
  return (
    <div className="flex items-center gap-3 px-4">
      <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500/20 to-violet-500/20 border border-indigo-500/30 flex items-center justify-center shrink-0">
        <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
      </div>
      <div className="bg-surface-2 rounded-2xl rounded-bl-md px-4 py-3 border border-slate-800/40">
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-indigo-400 animate-typing-dot-1" />
          <div className="w-2 h-2 rounded-full bg-indigo-400 animate-typing-dot-2" />
          <div className="w-2 h-2 rounded-full bg-indigo-400 animate-typing-dot-3" />
        </div>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex-1 flex items-center justify-center px-6">
      <div className="max-w-md text-center">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500/20 via-violet-500/15 to-fuchsia-500/10 border border-indigo-500/20 flex items-center justify-center mx-auto mb-6">
          <Sparkles className="w-7 h-7 text-indigo-400" />
        </div>
        <h2 className="text-xl font-semibold text-slate-100 mb-2">
          Welcome to Brain Trust
        </h2>
        <p className="text-sm text-slate-400 leading-relaxed mb-8">
          Tell Willow what you&apos;d like to accomplish and she&apos;ll assemble the right team to make it happen.
        </p>
        <div className="grid grid-cols-1 gap-2">
          {[
            'Write a story about Maya and Pip',
            'Search for Chapter 3 drafts',
            'Run the editorial pipeline',
          ].map((example) => (
            <div
              key={example}
              className="text-left px-4 py-3 rounded-xl bg-surface-2/50 border border-slate-800/40 text-sm text-slate-400 hover:text-slate-200 hover:border-slate-700/60 hover:bg-surface-2 transition-all cursor-default group"
            >
              <span className="text-slate-500 group-hover:text-indigo-400 transition-colors mr-2">&rarr;</span>
              {example}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function WillowChat({
  onExecutionUpdate,
  onExecutionComplete,
  selectedAgentId,
  showDevToggle = true,
  onToggleDevMode
}: WillowChatProps) {
  const [messages, setMessages] = useState<WillowMessage[]>([]);
  const [input, setInput] = useState('');
  const [isInitialized, setIsInitialized] = useState(false);

  useEffect(() => {
    if (!isInitialized) {
      setMessages([{
        role: 'willow',
        content: "Hello! I'm Willow, the Executive Conductor of the Legion. Tell me what you'd like to accomplish, and I'll assemble the right team to make it happen.",
        timestamp: new Date(),
      }]);
      setIsInitialized(true);
    }
  }, [isInitialized]);

  const [isLoading, setIsLoading] = useState(false);
  const [currentPlan, setCurrentPlan] = useState<Plan | null>(null);
  const [currentExecutionId, setCurrentExecutionId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const createExecutionTrace = useCallback((plan: Plan, status: 'running' | 'completed' | 'failed', result?: WillowMessage['execution_result']): ExecutionTrace => {
    const steps: StepTrace[] = plan.steps.map((step, idx) => {
      const stepResult = result?.step_results?.find(r => r.step_id === step.id);
      return {
        id: step.id,
        order: step.order || idx + 1,
        agent_role: step.agent_role,
        description: step.description,
        status: stepResult
          ? (stepResult.result === 'success' ? 'completed' : stepResult.result === 'blocked' ? 'blocked' : 'failed')
          : (status === 'running' ? (idx === 0 ? 'running' : 'pending') : 'pending'),
        duration_seconds: stepResult?.duration_seconds,
        output: stepResult?.output,
        error: stepResult?.error,
        tools_called: stepResult?.tools_called,
      };
    });
    return {
      id: plan.id,
      timestamp: new Date(),
      intent: plan.intent_summary,
      status,
      duration_seconds: result?.total_duration_seconds,
      steps,
      final_output: result?.final_output,
    };
  }, []);

  const sendMessage = async (content: string) => {
    if (!content.trim() || isLoading) return;

    const userMessage: WillowMessage = { role: 'user', content, timestamp: new Date() };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 120000);

    try {
      const response = await fetch('http://localhost:8000/api/v2/intent', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': process.env.NEXT_PUBLIC_BRAIN_TRUST_API_KEY || '',
        },
        body: JSON.stringify({ message: content, auto_execute: false }),
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      if (!response.ok) throw new Error(`Server error: ${response.status}`);

      const data = await response.json();
      const willowMessage: WillowMessage = {
        role: 'willow',
        content: data.message,
        timestamp: new Date(),
        plan: data.plan,
        needs_input: data.needs_input,
        input_options: data.input_options,
        execution_result: data.execution_result,
      };
      setMessages(prev => [...prev, willowMessage]);

      if (data.plan) {
        setCurrentPlan(data.plan);
        setCurrentExecutionId(data.plan.id);
      }
      if (data.execution_result) {
        setCurrentPlan(null);
        onExecutionComplete?.();
      }
    } catch (error) {
      let errorMsg = 'Failed to connect to server';
      if (error instanceof Error) {
        errorMsg = error.name === 'AbortError'
          ? 'Request timed out after 2 minutes. The LLM may be overloaded - try again.'
          : error.message;
      }
      setMessages(prev => [...prev, {
        role: 'system',
        content: `Error: ${errorMsg}. Is the backend running?`,
        timestamp: new Date(),
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleApprove = async (action: 'approve' | 'cancel' | 'modify') => {
    if (!currentPlan) return;
    setIsLoading(true);

    if (action === 'approve' && onExecutionUpdate) {
      onExecutionUpdate(createExecutionTrace(currentPlan, 'running'));
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 180000);

    try {
      const response = await fetch('http://localhost:8000/api/v2/intent/approve', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': process.env.NEXT_PUBLIC_BRAIN_TRUST_API_KEY || '',
        },
        body: JSON.stringify({ plan_id: currentPlan.id, action }),
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      const data = await response.json();

      setMessages(prev => [...prev, {
        role: 'willow',
        content: data.message,
        timestamp: new Date(),
        execution_result: data.execution_result,
      }]);

      if (data.execution_result && onExecutionUpdate && currentPlan) {
        const status = data.execution_result.status === 'completed' ? 'completed' : 'failed';
        onExecutionUpdate(createExecutionTrace(currentPlan, status, data.execution_result));
      }
      if (action === 'approve' || action === 'cancel') {
        setCurrentPlan(null);
        setCurrentExecutionId(null);
        onExecutionComplete?.();
      }
    } catch (error) {
      let errorMsg = 'Action failed';
      if (error instanceof Error) {
        errorMsg = error.name === 'AbortError'
          ? 'Execution timed out after 3 minutes. The task may still be running on the backend.'
          : error.message;
      }
      setMessages(prev => [...prev, { role: 'system', content: `Error: ${errorMsg}`, timestamp: new Date() }]);
      if (onExecutionUpdate && currentPlan) {
        onExecutionUpdate(createExecutionTrace(currentPlan, 'failed'));
      }
    } finally {
      setIsLoading(false);
    }
  };

  const showEmptyState = messages.length <= 1 && !isLoading;

  return (
    <div className="flex flex-col h-full bg-surface-0">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800/60 bg-surface-1/30 backdrop-blur-sm shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500/20 to-violet-500/20 border border-indigo-500/30 flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-indigo-400" />
          </div>
          <div>
            <h1 className="text-sm font-semibold text-slate-100">Willow</h1>
            <p className="text-[11px] text-slate-500">Executive Conductor</p>
          </div>
        </div>
        <div className="flex gap-2">
          {showDevToggle && onToggleDevMode && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onToggleDevMode}
              className="text-slate-400 hover:text-slate-200 text-xs h-8"
            >
              <Settings className="w-3.5 h-3.5 mr-1.5" />
              Dev
            </Button>
          )}
        </div>
      </div>

      {/* Messages */}
      {showEmptyState ? (
        <EmptyState />
      ) : (
        <div className="flex-1 overflow-y-auto px-4 py-5 space-y-5">
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={cn(
                'animate-fade-up flex gap-3',
                msg.role === 'user' ? 'flex-row-reverse' : 'flex-row',
              )}
            >
              {/* Avatar */}
              {msg.role !== 'user' && (
                <div className={cn(
                  'w-8 h-8 rounded-xl flex items-center justify-center shrink-0 mt-0.5',
                  msg.role === 'willow'
                    ? 'bg-gradient-to-br from-indigo-500/20 to-violet-500/20 border border-indigo-500/30'
                    : 'bg-red-500/10 border border-red-500/30',
                )}>
                  {msg.role === 'willow' ? (
                    <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                  ) : (
                    <XCircle className="w-3.5 h-3.5 text-red-400" />
                  )}
                </div>
              )}
              {msg.role === 'user' && (
                <div className="w-8 h-8 rounded-xl bg-slate-700/50 border border-slate-600/30 flex items-center justify-center shrink-0 mt-0.5">
                  <User className="w-3.5 h-3.5 text-slate-300" />
                </div>
              )}

              {/* Message Content */}
              <div className={cn('max-w-[75%] min-w-0')}>
                {msg.role === 'willow' && (
                  <div className="flex items-center gap-2 mb-1.5 px-1">
                    <span className="text-xs font-medium text-slate-400">Willow</span>
                    {msg.agentAttribution && (
                      <Badge variant="outline" className="text-[10px] h-4 border-slate-700 text-slate-500">
                        via {getAgentBadge(msg.agentAttribution)}
                      </Badge>
                    )}
                  </div>
                )}

                <div className={cn(
                  'rounded-2xl px-4 py-3 text-sm leading-relaxed',
                  msg.role === 'user'
                    ? 'bg-indigo-600/20 text-slate-100 border border-indigo-500/20 rounded-br-md'
                    : msg.role === 'system'
                    ? 'bg-red-500/10 text-red-200 border border-red-500/20 rounded-bl-md'
                    : 'bg-surface-2 text-slate-200 border border-slate-800/40 rounded-bl-md',
                )}>
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                </div>

                {/* Plan Display */}
                {msg.plan && (
                  <div className="mt-3 bg-surface-2/80 border border-slate-800/40 rounded-xl overflow-hidden">
                    <div className="px-4 py-3 border-b border-slate-800/40">
                      <div className="flex items-center gap-2 mb-1">
                        <div className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
                        <span className="text-xs font-medium text-slate-300 uppercase tracking-wide">Proposed Plan</span>
                      </div>
                      <p className="text-sm text-slate-200 font-medium">{msg.plan.intent_summary}</p>
                    </div>
                    <div className="px-4 py-3 space-y-2.5">
                      {msg.plan.steps.map((step, stepIdx) => (
                        <div key={step.id} className="flex items-start gap-3">
                          <div className="w-6 h-6 rounded-lg bg-surface-3 flex items-center justify-center shrink-0 mt-0.5">
                            <span className="text-[10px] font-bold text-slate-400">{stepIdx + 1}</span>
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2">
                              <Badge variant="outline" className="text-[10px] h-4 font-mono border-slate-700 text-slate-400">
                                {getAgentBadge(step.agent_role)}
                              </Badge>
                              <span className="text-[10px] text-slate-500">{step.agent_role}</span>
                            </div>
                            <p className="text-sm text-slate-300 mt-0.5">{step.description}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Execution Result */}
                {msg.execution_result && (
                  <div className={cn(
                    'mt-3 rounded-xl border overflow-hidden',
                    msg.execution_result.status === 'completed'
                      ? 'bg-emerald-500/5 border-emerald-500/20'
                      : 'bg-red-500/5 border-red-500/20',
                  )}>
                    <div className="px-4 py-3 flex items-center gap-3">
                      {msg.execution_result.status === 'completed' ? (
                        <div className="w-7 h-7 rounded-lg bg-emerald-500/15 flex items-center justify-center">
                          <CheckCircle className="w-4 h-4 text-emerald-400" />
                        </div>
                      ) : (
                        <div className="w-7 h-7 rounded-lg bg-red-500/15 flex items-center justify-center">
                          <XCircle className="w-4 h-4 text-red-400" />
                        </div>
                      )}
                      <div className="flex-1 min-w-0">
                        <span className={cn(
                          'text-sm font-medium',
                          msg.execution_result.status === 'completed' ? 'text-emerald-300' : 'text-red-300',
                        )}>
                          {msg.execution_result.status === 'completed' ? 'Completed' : 'Failed'}
                        </span>
                      </div>
                      {msg.execution_result.total_duration_seconds && (
                        <div className="flex items-center gap-1 text-xs text-slate-500">
                          <Clock className="w-3 h-3" />
                          <span>{msg.execution_result.total_duration_seconds.toFixed(1)}s</span>
                        </div>
                      )}
                    </div>
                    {msg.execution_result.final_output && (
                      <div className="px-4 pb-3">
                        <div className="bg-surface-1/80 rounded-lg p-3 text-sm text-slate-300 max-h-40 overflow-auto">
                          <pre className="whitespace-pre-wrap font-sans">
                            {msg.execution_result.final_output.slice(0, 500)}
                            {msg.execution_result.final_output.length > 500 && '...'}
                          </pre>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                <span className="text-[10px] text-slate-600 mt-1.5 block px-1" suppressHydrationWarning>
                  {msg.timestamp?.toLocaleTimeString() ?? ''}
                </span>
              </div>
            </div>
          ))}

          {isLoading && <TypingIndicator />}
          <div ref={messagesEndRef} />
        </div>
      )}

      {/* Plan Actions */}
      {currentPlan && !isLoading && (
        <div className="px-4 py-3 border-t border-slate-800/60 bg-surface-1/30 backdrop-blur-sm shrink-0">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-2 min-w-0">
              <div className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse shrink-0" />
              <span className="text-sm text-slate-300 truncate">{currentPlan.intent_summary}</span>
            </div>
            <div className="flex gap-2 shrink-0">
              <Button
                size="sm"
                variant="ghost"
                onClick={() => handleApprove('cancel')}
                className="text-slate-400 hover:text-slate-200 h-8 text-xs"
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={() => handleApprove('approve')}
                className="bg-indigo-600 hover:bg-indigo-500 text-white h-8 text-xs shadow-glow-sm"
              >
                <ArrowRight className="w-3.5 h-3.5 mr-1" />
                Execute
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Input */}
      <div className="px-4 py-4 border-t border-slate-800/60 bg-surface-1/20 shrink-0">
        <div className="flex gap-3 items-end">
          <div className="flex-1 relative">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  sendMessage(input);
                }
              }}
              placeholder={selectedAgentId ? 'Chat with selected agent...' : 'Tell Willow what you want to accomplish...'}
              rows={1}
              className={cn(
                'w-full rounded-xl bg-surface-2 border border-slate-800/60 text-sm text-slate-100',
                'placeholder-slate-500 px-4 py-3 resize-none',
                'focus:outline-none focus:border-indigo-500/40 focus:ring-1 focus:ring-indigo-500/20',
                'transition-all duration-200',
                'disabled:opacity-50',
              )}
              disabled={isLoading}
            />
          </div>
          <Button
            onClick={() => sendMessage(input)}
            disabled={isLoading || !input.trim()}
            size="icon"
            className={cn(
              'h-11 w-11 rounded-xl shrink-0 transition-all duration-200',
              input.trim() && !isLoading
                ? 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-glow-sm'
                : 'bg-surface-3 text-slate-500',
            )}
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </Button>
        </div>
        <p className="text-[11px] text-slate-600 mt-2 px-1">
          Press Enter to send &middot; Shift+Enter for new line
        </p>
      </div>
    </div>
  );
}
