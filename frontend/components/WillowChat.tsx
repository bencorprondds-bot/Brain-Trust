"use client";

import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader2, CheckCircle, XCircle, ChevronRight, Settings, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

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
  };
}

interface WillowChatProps {
  onToggleDebug?: () => void;
  showDebugToggle?: boolean;
}

export default function WillowChat({ onToggleDebug, showDebugToggle }: WillowChatProps) {
  const [messages, setMessages] = useState<WillowMessage[]>([]);
  const [input, setInput] = useState('');
  const [isInitialized, setIsInitialized] = useState(false);

  // Initialize welcome message on client only to avoid hydration mismatch
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
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async (content: string) => {
    if (!content.trim() || isLoading) return;

    // Add user message
    const userMessage: WillowMessage = {
      role: 'user',
      content,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/v2/intent', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': process.env.NEXT_PUBLIC_BRAIN_TRUST_API_KEY || '',
        },
        body: JSON.stringify({
          message: content,
          auto_execute: false,
        }),
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const data = await response.json();

      // Add Willow's response
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
      }

      if (data.execution_result) {
        setCurrentPlan(null);
      }

    } catch (error) {
      setMessages(prev => [...prev, {
        role: 'system',
        content: `Error: ${error instanceof Error ? error.message : 'Failed to connect to server'}. Is the backend running?`,
        timestamp: new Date(),
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleApprove = async (action: 'approve' | 'cancel' | 'modify') => {
    if (!currentPlan) return;

    setIsLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/v2/intent/approve', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': process.env.NEXT_PUBLIC_BRAIN_TRUST_API_KEY || '',
        },
        body: JSON.stringify({
          plan_id: currentPlan.id,
          action,
        }),
      });

      const data = await response.json();

      const willowMessage: WillowMessage = {
        role: 'willow',
        content: data.message,
        timestamp: new Date(),
        execution_result: data.execution_result,
      };
      setMessages(prev => [...prev, willowMessage]);

      if (action === 'approve' || action === 'cancel') {
        setCurrentPlan(null);
      }

    } catch (error) {
      setMessages(prev => [...prev, {
        role: 'system',
        content: `Error: ${error instanceof Error ? error.message : 'Action failed'}`,
        timestamp: new Date(),
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  return (
    <div className="flex flex-col h-full bg-zinc-950">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-zinc-800">
        <div>
          <h1 className="text-xl font-bold bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
            Willow
          </h1>
          <p className="text-xs text-zinc-500">Executive Conductor • Legion v3</p>
        </div>
        <div className="flex gap-2">
          {showDebugToggle && (
            <Button
              variant="outline"
              size="sm"
              onClick={onToggleDebug}
              className="text-zinc-400 border-zinc-700 hover:bg-zinc-800"
            >
              <Settings className="w-4 h-4 mr-1" />
              Debug View
            </Button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] ${
              msg.role === 'user'
                ? 'bg-cyan-900/50 text-cyan-50'
                : msg.role === 'system'
                ? 'bg-red-900/30 text-red-200'
                : 'bg-zinc-800/50 text-zinc-100'
            } rounded-lg p-3`}>
              {msg.role === 'willow' && (
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-emerald-400 text-sm font-medium">Willow</span>
                </div>
              )}
              <p className="whitespace-pre-wrap">{msg.content}</p>

              {/* Plan Display */}
              {msg.plan && (
                <Card className="mt-3 bg-zinc-900/50 border-zinc-700 p-3">
                  <h4 className="text-sm font-medium text-zinc-300 mb-2">
                    Proposed Plan: {msg.plan.intent_summary}
                  </h4>
                  <div className="space-y-2">
                    {msg.plan.steps.map((step, stepIdx) => (
                      <div key={step.id} className="flex items-center gap-2 text-sm">
                        <span className="text-zinc-500">{stepIdx + 1}.</span>
                        <Badge variant="outline" className="text-xs">
                          {step.agent_role}
                        </Badge>
                        <span className="text-zinc-400">{step.description}</span>
                      </div>
                    ))}
                  </div>
                </Card>
              )}

              {/* Execution Result */}
              {msg.execution_result && (
                <Card className={`mt-3 p-3 border ${
                  msg.execution_result.status === 'completed'
                    ? 'bg-emerald-900/20 border-emerald-700'
                    : 'bg-red-900/20 border-red-700'
                }`}>
                  <div className="flex items-center gap-2 mb-2">
                    {msg.execution_result.status === 'completed' ? (
                      <CheckCircle className="w-4 h-4 text-emerald-400" />
                    ) : (
                      <XCircle className="w-4 h-4 text-red-400" />
                    )}
                    <span className="text-sm font-medium">
                      {msg.execution_result.status === 'completed' ? 'Completed' : 'Issue'}
                    </span>
                  </div>
                  {msg.execution_result.final_output && (
                    <p className="text-sm text-zinc-300 whitespace-pre-wrap">
                      {msg.execution_result.final_output.slice(0, 500)}
                      {msg.execution_result.final_output.length > 500 && '...'}
                    </p>
                  )}
                </Card>
              )}

              <span className="text-xs text-zinc-500 mt-2 block" suppressHydrationWarning>
                {msg.timestamp?.toLocaleTimeString() ?? ''}
              </span>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-zinc-800/50 rounded-lg p-3 flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin text-emerald-400" />
              <span className="text-zinc-400">Willow is thinking...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Plan Actions */}
      {currentPlan && !isLoading && (
        <div className="p-3 border-t border-zinc-800 bg-zinc-900/50">
          <div className="flex items-center justify-between">
            <span className="text-sm text-zinc-400">
              Plan ready: {currentPlan.intent_summary}
            </span>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleApprove('cancel')}
                className="text-zinc-400 border-zinc-700"
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={() => handleApprove('approve')}
                className="bg-emerald-600 hover:bg-emerald-500 text-white"
              >
                <ChevronRight className="w-4 h-4 mr-1" />
                Begin
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Input */}
      <div className="p-4 border-t border-zinc-800">
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Tell Willow what you want to accomplish..."
            className="flex-1 bg-zinc-900 border-zinc-700 text-zinc-100 placeholder-zinc-500"
            disabled={isLoading}
          />
          <Button
            onClick={() => sendMessage(input)}
            disabled={isLoading || !input.trim()}
            className="bg-gradient-to-r from-emerald-600 to-cyan-600 hover:from-emerald-500 hover:to-cyan-500"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </Button>
        </div>
        <p className="text-xs text-zinc-600 mt-2">
          Press Enter to send • Examples: "Write a story about Maya and Pip" • "Find Chapter 3"
        </p>
      </div>
    </div>
  );
}
