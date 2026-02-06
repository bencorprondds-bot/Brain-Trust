import React, { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Bot, Loader2, CheckCircle2, TriangleAlert, GripVertical, Sparkles } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

type AgentStatus = 'idle' | 'thinking' | 'done' | 'error';

interface AgentData {
    name: string;
    role: string;
    status: AgentStatus;
    currentTool?: string;
    model: string;
    files?: string[];
    presetId?: string;
}

const AgentNode = ({ data, selected, id }: NodeProps<AgentData>) => {
    const handleDragStart = (e: React.DragEvent) => {
        e.dataTransfer.setData('application/json', JSON.stringify({
            type: 'remove-agent',
            nodeId: id,
            presetId: data.presetId
        }));
        e.dataTransfer.effectAllowed = 'move';
    };

    const glowConfig = {
        idle: 'from-indigo-500/10 to-violet-500/10 opacity-0 group-hover:opacity-30',
        thinking: 'from-indigo-500 to-violet-500 opacity-30 blur-md animate-glow-pulse',
        done: 'from-emerald-500 to-teal-500 opacity-25',
        error: 'from-red-500 to-orange-500 opacity-30',
    };

    const borderConfig = {
        idle: 'border-slate-800/60',
        thinking: 'border-indigo-500/40 animate-border-glow',
        done: 'border-emerald-500/30',
        error: 'border-red-500/30',
    };

    return (
        <div className={cn(
            'relative group transition-all duration-300',
            selected && 'scale-[1.03]'
        )}>
            {/* Glow Backdrop */}
            <div className={cn(
                'absolute -inset-1 rounded-2xl bg-gradient-to-r transition-all duration-500 blur-sm',
                glowConfig[data.status],
            )} />

            <Card className={cn(
                'relative w-64 bg-surface-1/95 backdrop-blur-xl text-slate-100 rounded-xl border shadow-elevation-2',
                borderConfig[data.status],
            )}>
                {/* Input Handle */}
                <Handle
                    type="target"
                    position={Position.Top}
                    className="!bg-indigo-500 !w-2.5 !h-2.5 !border-2 !border-surface-0"
                />

                <CardHeader className="pb-2 pt-3 px-4 flex flex-row items-center justify-between space-y-0">
                    {/* Drag handle */}
                    <div
                        draggable
                        onDragStart={handleDragStart}
                        className={cn(
                            'absolute -left-1 top-1/2 -translate-y-1/2 p-1 rounded-l-lg',
                            'opacity-0 group-hover:opacity-100 transition-opacity cursor-grab active:cursor-grabbing',
                            'bg-surface-3 hover:bg-red-500/10 hover:text-red-400 border-r border-slate-800/40',
                            'flex items-center justify-center'
                        )}
                        title="Drag to remove"
                    >
                        <GripVertical className="w-3 h-3" />
                    </div>

                    <div className="flex items-center gap-2.5">
                        <div className={cn(
                            'p-1.5 rounded-lg border transition-colors',
                            data.status === 'thinking'
                                ? 'bg-indigo-500/10 border-indigo-500/30 text-indigo-400'
                                : 'bg-surface-2 border-slate-800/40 text-slate-400',
                        )}>
                            <Bot className="w-4 h-4" />
                        </div>
                        <div>
                            <CardTitle className="text-sm font-semibold tracking-tight text-slate-100">
                                {data.name}
                            </CardTitle>
                            <p className="text-[10px] text-slate-500 truncate max-w-[120px]">
                                {data.role}
                            </p>
                        </div>
                    </div>

                    {/* Status */}
                    <div>
                        {data.status === 'thinking' && (
                            <Loader2 className="w-4 h-4 text-indigo-400 animate-spin" />
                        )}
                        {data.status === 'done' && (
                            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        )}
                        {data.status === 'error' && (
                            <TriangleAlert className="w-4 h-4 text-red-400" />
                        )}
                        {data.status === 'idle' && (
                            <div className="w-2 h-2 rounded-full bg-slate-700" />
                        )}
                    </div>
                </CardHeader>

                <CardContent className="px-4 pb-3">
                    {data.status === 'thinking' && data.currentTool && (
                        <div className="mt-2 flex items-center gap-2 text-xs">
                            <span className="text-slate-500 font-mono">{'>'}</span>
                            <span className="text-indigo-400 font-mono truncate animate-pulse">
                                {data.currentTool}
                            </span>
                        </div>
                    )}

                    <div className="mt-3 flex justify-between items-center">
                        {(!data.model || data.model === 'auto') ? (
                            <Badge variant="outline" className="text-[10px] h-5 border-indigo-500/30 text-indigo-400 gap-1">
                                <Sparkles className="w-2.5 h-2.5" />
                                Auto
                            </Badge>
                        ) : (
                            <Badge variant="outline" className="text-[10px] h-5 border-slate-700 text-slate-400">
                                {data.model}
                            </Badge>
                        )}
                    </div>
                </CardContent>

                {/* Output Handle */}
                <Handle
                    type="source"
                    position={Position.Bottom}
                    className="!bg-indigo-500 !w-2.5 !h-2.5 !border-2 !border-surface-0"
                />

                {/* File Context */}
                {data.files && data.files.length > 0 && (
                    <div className="absolute bottom-full mb-3 left-1/2 -translate-x-1/2 flex flex-col items-center gap-1 w-max max-w-[220px] pointer-events-none">
                        <span className="text-[9px] text-indigo-400/60 font-mono uppercase tracking-widest mb-0.5">Context</span>
                        {data.files.map((f, i) => (
                            <div key={i} className="bg-surface-2/90 backdrop-blur border border-indigo-500/20 px-2.5 py-1 rounded-lg text-[10px] font-medium text-indigo-200 shadow-elevation-1 truncate max-w-full">
                                {f.split(/[/\\]/).pop()}
                            </div>
                        ))}
                    </div>
                )}
            </Card>
        </div>
    );
};

export default memo(AgentNode);
