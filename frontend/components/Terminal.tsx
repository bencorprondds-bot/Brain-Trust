"use client";

import React, { useEffect, useState, useRef } from 'react';
import { Terminal as TerminalIcon, X, Minus } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function Terminal() {
    const [logs, setLogs] = useState<string[]>([]);
    const [isOpen, setIsOpen] = useState(true);
    const [isMinimized, setIsMinimized] = useState(false);
    const scrollRef = useRef<HTMLDivElement>(null);
    const ws = useRef<WebSocket | null>(null);

    useEffect(() => {
        const clientId = Date.now();
        const socket = new WebSocket(`ws://127.0.0.1:8000/ws/${clientId}`);

        socket.onopen = () => {
            setLogs(prev => [...prev, '> System link established', '> Waiting for agent stream...']);
        };

        socket.onmessage = (event) => {
            setLogs(prev => [...prev, event.data]);
        };

        socket.onclose = () => {
            setLogs(prev => [...prev, '> System link terminated']);
        };

        ws.current = socket;
        return () => { socket.close(); };
    }, []);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [logs]);

    if (!isOpen) return (
        <button
            className="fixed bottom-4 right-4 w-9 h-9 rounded-xl bg-surface-2 border border-slate-800/60 text-slate-400 hover:text-indigo-400 hover:border-indigo-500/30 z-50 flex items-center justify-center transition-all duration-200 shadow-elevation-2"
            onClick={() => setIsOpen(true)}
        >
            <TerminalIcon className="h-4 w-4" />
        </button>
    );

    return (
        <div className={cn(
            'fixed bottom-4 right-4 w-[420px] bg-surface-1/95 backdrop-blur-xl border border-slate-800/60 rounded-xl shadow-elevation-3 z-50 flex flex-col overflow-hidden font-mono text-xs transition-all duration-300',
            isMinimized ? 'h-10' : 'h-64',
        )}>
            {/* Header */}
            <div className="flex items-center justify-between px-3 py-2.5 bg-surface-2/50 border-b border-slate-800/40 shrink-0">
                <div className="flex items-center gap-2">
                    <TerminalIcon className="h-3.5 w-3.5 text-indigo-400" />
                    <span className="text-xs font-medium text-slate-300 tracking-wide">Agent Stream</span>
                    <span className="text-[10px] text-slate-600">{logs.length} lines</span>
                </div>
                <div className="flex items-center gap-1">
                    <button
                        onClick={() => setIsMinimized(!isMinimized)}
                        className="w-5 h-5 rounded flex items-center justify-center text-slate-500 hover:text-slate-300 hover:bg-surface-3/50 transition-colors"
                    >
                        <Minus className="h-3 w-3" />
                    </button>
                    <button
                        onClick={() => setIsOpen(false)}
                        className="w-5 h-5 rounded flex items-center justify-center text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                    >
                        <X className="h-3 w-3" />
                    </button>
                </div>
            </div>

            {/* Log Output */}
            {!isMinimized && (
                <div
                    ref={scrollRef}
                    className="flex-1 p-3 overflow-y-auto space-y-0.5"
                >
                    {logs.map((log, i) => (
                        <div
                            key={i}
                            className={cn(
                                'break-words whitespace-pre-wrap animate-fade-up py-0.5',
                                log.startsWith('>')
                                    ? 'text-slate-500'
                                    : log.toLowerCase().includes('error')
                                    ? 'text-red-400/80'
                                    : 'text-indigo-300/70',
                            )}
                        >
                            {log}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
