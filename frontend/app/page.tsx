"use client";

import dynamic from 'next/dynamic';
import { Loader2 } from 'lucide-react';

const LegionInterface = dynamic(() => import('@/components/LegionInterface'), {
  ssr: false,
  loading: () => (
    <div className="w-screen h-screen bg-zinc-950 flex items-center justify-center">
      <Loader2 className="w-10 h-10 animate-spin text-emerald-400" />
    </div>
  ),
});

const DebugView = dynamic(() => import('@/components/DebugView'), {
  ssr: false,
});

export default function Home() {
  return <LegionInterface DebugView={DebugView} />;
}
