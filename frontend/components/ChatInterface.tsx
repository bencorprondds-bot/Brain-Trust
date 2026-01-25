import React, { useState, useRef, useEffect } from 'react';
import { Send, User, Bot, Sparkles, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';

export interface Message {
    role: 'user' | 'agent' | 'system';
    content: string;
    agentName?: string;
}

interface ChatInterfaceProps {
    messages: Message[];
    onSendMessage: (content: string) => void;
    selectedAgents: { name: string; id: string }[];
    isLoading: boolean;
}

export default function ChatInterface({ messages, onSendMessage, selectedAgents, isLoading }: ChatInterfaceProps) {
    const [input, setInput] = useState('');
    const scrollRef = useRef<HTMLDivElement>(null);
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);

    // Auto-resize textarea
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto'; // Reset
            textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`; // Grow up to ~8 lines
        }
    }, [input]);

    const handleSend = () => {
        if (!input.trim()) return;

        // Validation: Agent Selection
        if (selectedAgents.length === 0) {
            alert("Please select at least one agent node to chat with!");
            return;
        }

        onSendMessage(input);
        setInput('');
        if (textareaRef.current) textareaRef.current.style.height = 'auto';
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="absolute inset-0 z-20 pointer-events-none flex flex-col justify-between">

            {/* TOP PANEL - History (Reduced Height: 35vh) */}
            <div className="self-end w-full max-w-[500px] h-[35vh] max-h-[600px] mr-6 mt-4 pointer-events-auto flex flex-col transition-all duration-300 ease-in-out">
                {/* Card Container for History */}
                <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar bg-zinc-950/80 backdrop-blur-md rounded-2xl border border-zinc-800/50 shadow-2xl" ref={scrollRef}>

                    {messages.length === 0 && selectedAgents.length > 0 && (
                        <div className="text-zinc-500 italic text-sm mt-4 text-center">
                            Ready to chat with {selectedAgents.map(a => a.name).join(', ')}...
                        </div>
                    )}

                    {messages.length === 0 && selectedAgents.length === 0 && (
                        <div className="text-zinc-600 italic text-xs mt-10 text-center">
                            Chat history will appear here...
                        </div>
                    )}

                    {messages.map((msg, idx) => (
                        <div key={idx} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                            {msg.role !== 'system' && (
                                <div className={`flex items-center gap-2 mb-1 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                                    {msg.role === 'user' ? <User size={12} className="text-zinc-400" /> : <Bot size={12} className={selectedAgents.length > 1 ? "text-indigo-400" : "text-cyan-400"} />}
                                    <span className="text-[10px] text-zinc-500 font-mono uppercase tracking-wider">{msg.role === 'user' ? 'YOU' : msg.agentName}</span>
                                </div>
                            )}

                            {msg.role === 'system' ? (
                                <div className="flex items-center gap-2 p-2 px-4 rounded-lg bg-red-900/20 border border-red-500/20 text-red-300 text-xs text-left">
                                    <AlertCircle size={12} />
                                    {msg.content}
                                </div>
                            ) : (
                                <div className={`p-3 rounded-xl text-sm max-w-[90%] whitespace-pre-wrap shadow-sm leading-relaxed ${msg.role === 'user'
                                        ? 'bg-indigo-600 text-white rounded-tr-none'
                                        : 'bg-zinc-800 text-zinc-200 rounded-tl-none border border-zinc-700'
                                    }`}>
                                    {msg.content}
                                </div>
                            )}
                        </div>
                    ))}

                    {isLoading && (
                        <div className="flex items-center gap-2 text-xs text-zinc-500 p-2 animate-pulse">
                            <Sparkles size={14} className="text-cyan-400" />
                            <span className="font-mono">AGENTS THINKING...</span>
                        </div>
                    )}
                </div>
            </div>

            {/* BOTTOM PANEL - Input */}
            <div className="w-full bg-zinc-950/80 backdrop-blur-md border-t border-zinc-800 pointer-events-auto p-4 pb-6 shadow-[0_-10px_40px_rgba(0,0,0,0.5)]">
                <div className="max-w-4xl mx-auto flex flex-col gap-2">

                    {/* Context Indicator */}
                    <div className="flex items-center gap-2 text-xs text-zinc-500 mb-1 px-1">
                        {selectedAgents.length > 0 ? (
                            <>
                                <span className="text-zinc-400">Broadcasting to:</span>
                                <div className="flex flex-wrap gap-2">
                                    {selectedAgents.map(a => (
                                        <span key={a.id} className="bg-zinc-800 text-zinc-300 px-2 py-0.5 rounded border border-zinc-700 font-mono text-[10px] flex items-center gap-1">
                                            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse"></span>
                                            {a.name}
                                        </span>
                                    ))}
                                </div>
                            </>
                        ) : (
                            <span className="text-amber-500/80 italic flex items-center gap-1">
                                <AlertCircle size={10} />
                                Select an agent node above to enable transmission...
                            </span>
                        )}
                    </div>

                    <div className="flex gap-3 items-end">
                        <textarea
                            ref={textareaRef}
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder={selectedAgents.length > 0 ? `Message ${selectedAgents.length} active agents...` : "Select an agent to start chatting..."}
                            disabled={isLoading}
                            rows={1}
                            className={`flex-1 bg-zinc-900 border rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 resize-none min-h-[50px] max-h-[200px] text-zinc-200 shadow-inner custom-scrollbar transition-all
                    ${selectedAgents.length === 0 ? 'border-zinc-700 placeholder:text-zinc-600 focus:border-zinc-600' : 'border-zinc-700 focus:border-indigo-500/50 placeholder:text-zinc-600'}`}
                            style={{ scrollbarWidth: 'thin' }}
                        />
                        <Button
                            onClick={handleSend}
                            disabled={isLoading || !input.trim()}
                            className={`h-[50px] w-[50px] rounded-xl shadow-lg flex items-center justify-center shrink-0 transition-all
                    ${selectedAgents.length === 0
                                    ? 'bg-zinc-800 text-zinc-600 hover:bg-zinc-800 shadow-none clickable'
                                    : 'bg-indigo-600 hover:bg-indigo-500 shadow-indigo-500/20 text-white'}`}
                        >
                            <Send size={20} />
                        </Button>
                    </div>
                    <div className="text-[10px] text-zinc-600 text-center font-mono pt-1">
                        SHIFT + ENTER for new line
                    </div>
                </div>
            </div>

            <style>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 8px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background-color: rgba(255, 255, 255, 0.1);
          border-radius: 4px;
        }
      `}</style>
        </div>
    );
}
