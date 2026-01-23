"use client";

import React, { useEffect, useState, useRef } from 'react';
import { Terminal as TerminalIcon, XCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function Terminal() {
    const [logs, setLogs] = useState<string[]>([]);
    const [isOpen, setIsOpen] = useState(true);
    const scrollRef = useRef<HTMLDivElement>(null);
    const ws = useRef<WebSocket | null>(null);

    useEffect(() => {
        // Connect to WS
        const clientId = Date.now();
        const socket = new WebSocket(`ws://127.0.0.1:8000/ws/${clientId}`);

        socket.onopen = () => {
            setLogs(prev => [...prev, "> SYSTEM LINK ESTABLISHED...", "> WAITING FOR AGENT STREAM..."]);
        };

        socket.onmessage = (event) => {
            // Append content
            // CrewAI output might be partial. 
            // For simplicity, we treat each message as a line or chunk.
            setLogs(prev => [...prev, event.data]);
        };

        socket.onclose = () => {
            setLogs(prev => [...prev, "> SYSTEM LINK TERMINATED."]);
        };

        ws.current = socket;

        return () => {
            socket.close();
        };
    }, []);

    // Auto-scroll
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [logs]);

    if (!isOpen) return (
        <Button
            variant="outline"
            size="icon"
            className="fixed bottom-4 right-4 bg-black border-cyan-800 text-cyan-500 z-50 hover:bg-cyan-900/20"
            onClick={() => setIsOpen(true)}
        >
            <TerminalIcon className="h-4 w-4" />
        </Button>
    );

    return (
        <div className="fixed bottom-4 right-4 w-96 h-64 bg-black/90 backdrop-blur border border-cyan-800 rounded-lg shadow-2xl z-50 flex flex-col overflow-hidden font-mono text-xs">
            <div className="flex items-center justify-between px-3 py-2 bg-zinc-900/50 border-b border-cyan-900/50">
                <div className="flex items-center gap-2 text-cyan-500">
                    <TerminalIcon className="h-3 w-3" />
                    <span className="tracking-widest uppercase">Agent Matrix</span>
                </div>
                <button onClick={() => setIsOpen(false)} className="text-zinc-500 hover:text-cyan-500 transition-colors">
                    <XCircle className="h-3 w-3" />
                </button>
            </div>

            <div
                ref={scrollRef}
                className="flex-1 p-3 overflow-y-auto space-y-1 text-cyan-400/80"
            >
                {logs.map((log, i) => (
                    <div key={i} className="break-words whitespace-pre-wrap animate-in fade-in duration-300">
                        {log}
                    </div>
                ))}
            </div>
        </div>
    );
}
