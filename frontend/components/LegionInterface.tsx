"use client";

import React, { useState } from 'react';
import dynamic from 'next/dynamic';
import { MessageSquare, Network, Activity, Settings, ChevronLeft, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

// Dynamic import with SSR disabled to prevent hydration issues with timestamps
const WillowChat = dynamic(() => import('./WillowChat'), {
  ssr: false,
  loading: () => (
    <div className="flex-1 flex items-center justify-center bg-zinc-950">
      <Loader2 className="w-8 h-8 animate-spin text-emerald-400" />
    </div>
  ),
});

interface LegionInterfaceProps {
  DebugView?: React.ComponentType;
}

type ViewMode = 'command' | 'debug';

export default function LegionInterface({ DebugView }: LegionInterfaceProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('command');
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <div className="w-screen h-screen bg-zinc-950 text-zinc-50 overflow-hidden flex">
      {/* Sidebar */}
      <div className={`${sidebarOpen ? 'w-16' : 'w-0'} transition-all duration-300 bg-zinc-900 border-r border-zinc-800 flex flex-col items-center py-4 gap-4`}>
        {sidebarOpen && (
          <>
            {/* Logo */}
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-emerald-500 to-cyan-500 flex items-center justify-center font-bold text-lg">
              L
            </div>

            <div className="flex-1" />

            {/* View Toggle Buttons */}
            <Button
              variant={viewMode === 'command' ? 'default' : 'ghost'}
              size="icon"
              onClick={() => setViewMode('command')}
              className={viewMode === 'command' ? 'bg-emerald-600' : 'text-zinc-400 hover:text-zinc-100'}
              title="Command Interface"
            >
              <MessageSquare className="w-5 h-5" />
            </Button>

            <Button
              variant={viewMode === 'debug' ? 'default' : 'ghost'}
              size="icon"
              onClick={() => setViewMode('debug')}
              className={viewMode === 'debug' ? 'bg-cyan-600' : 'text-zinc-400 hover:text-zinc-100'}
              title="Debug View"
            >
              <Network className="w-5 h-5" />
            </Button>

            <div className="flex-1" />

            {/* Bottom Icons */}
            <Button
              variant="ghost"
              size="icon"
              className="text-zinc-400 hover:text-zinc-100"
              title="Activity"
            >
              <Activity className="w-5 h-5" />
            </Button>

            <Button
              variant="ghost"
              size="icon"
              className="text-zinc-400 hover:text-zinc-100"
              title="Settings"
            >
              <Settings className="w-5 h-5" />
            </Button>
          </>
        )}
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {viewMode === 'command' ? (
          <WillowChat
            onToggleDebug={() => setViewMode('debug')}
            showDebugToggle={!!DebugView}
          />
        ) : (
          <div className="flex-1 relative">
            {/* Back to Command Button */}
            <div className="absolute top-4 left-4 z-50">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setViewMode('command')}
                className="bg-zinc-900/80 text-zinc-300 border-zinc-700 hover:bg-zinc-800"
              >
                <ChevronLeft className="w-4 h-4 mr-1" />
                Back to Willow
              </Button>
            </div>

            {/* Debug View Content */}
            {DebugView ? (
              <DebugView />
            ) : (
              <div className="flex items-center justify-center h-full text-zinc-500">
                <div className="text-center">
                  <Network className="w-16 h-16 mx-auto mb-4 opacity-50" />
                  <p>Debug view not configured</p>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
