import React from 'react';
import { FileText, FolderOpen } from 'lucide-react';

interface FetchBinProps {
    files: string[];
}

export default function FetchBin({ files }: FetchBinProps) {
    if (files.length === 0) return null;

    return (
        <div className="absolute top-[120px] left-4 z-40 w-64 pointer-events-auto">
            <div className="bg-zinc-900/90 backdrop-blur-md border border-cyan-500/30 rounded-lg shadow-[0_0_15px_rgba(6,182,212,0.2)] overflow-hidden transition-all animate-in fade-in slide-in-from-left-4 duration-500">
                {/* Header */}
                <div className="px-3 py-2 bg-gradient-to-r from-cyan-900/50 to-transparent border-b border-cyan-500/20 flex items-center gap-2">
                    <FolderOpen size={14} className="text-cyan-400" />
                    <span className="text-xs font-bold text-cyan-100 uppercase tracking-widest">CONTEXT BIN</span>
                    <span className="ml-auto text-[10px] text-cyan-400 font-mono bg-cyan-950/50 px-1.5 rounded">{files.length}</span>
                </div>

                {/* File List */}
                <div className="max-h-48 overflow-y-auto p-1 text-left">
                    {files.map((file, idx) => (
                        <div key={idx} className="flex items-center gap-2 p-2 hover:bg-zinc-800/50 rounded transition-colors group cursor-default" title={file}>
                            <FileText size={12} className="text-zinc-500 group-hover:text-cyan-300 transition-colors shrink-0" />
                            <span className="text-xs text-zinc-400 group-hover:text-zinc-200 truncate font-mono">
                                {file.split(/[/\\]/).pop()}
                            </span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
