import React, { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Bot, Loader2, CheckCircle2, Play } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils'; // Shadcn utility

// Visual States: "Diamond Age" Aesthetic
// idle: Low opacity, minimal pulse
// thinking: High contrast border, rapid pulse, 'scanning' animation
// done: Green glow, solid border

type AgentStatus = 'idle' | 'thinking' | 'done' | 'error';

interface AgentData {
    name: string;
    role: string;
    status: AgentStatus;
    currentTool?: string;
    model: string;
}

const AgentNode = ({ data, selected }: NodeProps<AgentData>) => {
    return (
        <div className={cn(
            "relative group transition-all duration-300",
            selected && "scale-105"
        )}>
            {/* Sci-Fi Glow Effect Backdrop */}
            <div className={cn(
                "absolute -inset-0.5 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-500 opacity-20 blur transition duration-500",
                data.status === 'thinking' && "opacity-75 blur-md animate-pulse",
                data.status === 'done' && "from-green-500 to-emerald-500 opacity-50",
                data.status === 'error' && "from-red-600 to-orange-600 opacity-75"
            )} />

            <Card className="relative w-64 border-zinc-800 bg-zinc-950/90 text-zinc-100 backdrop-blur-xl">
                {/* Input Handle (Top) */}
                <Handle
                    type="target"
                    position={Position.Top}
                    className="!bg-cyan-500 !w-3 !h-3 !border-none"
                />

                <CardHeader className="pb-2 pt-3 px-4 flex flex-row items-center justify-between space-y-0">
                    <div className="flex items-center gap-2">
                        <div className={cn(
                            "p-1.5 rounded-md bg-zinc-900 border border-zinc-700",
                            data.status === 'thinking' && "border-cyan-500 text-cyan-400"
                        )}>
                            <Bot className="w-5 h-5" />
                        </div>
                        <div>
                            <CardTitle className="text-sm font-bold font-mono tracking-tight uppercase text-zinc-100">
                                {data.name}
                            </CardTitle>
                            <p className="text-[10px] text-zinc-400 font-mono uppercase truncate max-w-[120px]">
                                {data.role}
                            </p>
                        </div>
                    </div>

                    {/* Status Indicator */}
                    <div className="">
                        {data.status === 'thinking' && (
                            <Loader2 className="w-4 h-4 text-cyan-400 animate-spin" />
                        )}
                        {data.status === 'done' && (
                            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        )}
                        {data.status === 'idle' && (
                            <div className="w-2 h-2 rounded-full bg-zinc-700" />
                        )}
                    </div>
                </CardHeader>

                <CardContent className="px-4 pb-3">
                    {/* Active Tool Display (The "Cyberpunk HUD" detail) */}
                    {data.status === 'thinking' && data.currentTool && (
                        <div className="mt-2 text-xs font-mono">
                            <span className="text-zinc-500 mr-2">{'>'} EXECUTING:</span>
                            <span className="text-cyan-400 animate-pulse">
                                {data.currentTool}
                            </span>
                        </div>
                    )}

                    {/* Model Badge */}
                    <div className="mt-3 flex justify-between items-center opacity-60">
                        <Badge variant="outline" className="text-[10px] h-5 border-zinc-700">
                            {data.model}
                        </Badge>
                        <Play className={cn(
                            "w-3 h-3 text-zinc-600",
                            data.status === 'thinking' && "text-cyan-500 fill-cyan-500"
                        )} />
                    </div>
                </CardContent>

                {/* Output Handle (Bottom) */}
                <Handle
                    type="source"
                    position={Position.Bottom}
                    className="!bg-cyan-500 !w-3 !h-3 !border-none"
                />
            </Card>
        </div>
    );
};

export default memo(AgentNode);
