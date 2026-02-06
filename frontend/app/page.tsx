"use client";

import dynamic from 'next/dynamic';
import { Sparkles } from 'lucide-react';

const LegionInterface = dynamic(() => import('@/components/LegionInterface'), {
  ssr: false,
  loading: () => (
    <div className="w-screen h-screen bg-surface-0 flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="relative">
          <div className="absolute inset-0 rounded-2xl bg-indigo-500/20 blur-xl animate-glow-pulse" />
          <div className="relative w-14 h-14 rounded-2xl bg-gradient-to-br from-indigo-500 via-violet-500 to-fuchsia-500 flex items-center justify-center shadow-glow-md">
            <Sparkles className="w-6 h-6 text-white" />
          </div>
        </div>
        <div className="text-center">
          <h1 className="text-sm font-semibold text-slate-200">Brain Trust</h1>
          <p className="text-xs text-slate-500 mt-0.5">Loading interface...</p>
        </div>
      </div>
    </div>
  ),
});

export default function Home() {
  return <LegionInterface />;
}
