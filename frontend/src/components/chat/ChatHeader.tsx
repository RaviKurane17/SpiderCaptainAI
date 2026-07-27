import React from 'react';
import { Activity, Cpu, Wifi, Database, Settings, MoreVertical } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ChatHeaderProps {
    isConnected: boolean;
    latency: number;
    modelName: string;
    workspaceName: string;
}

export const ChatHeader: React.FC<ChatHeaderProps> = ({ isConnected, latency, modelName, workspaceName }) => {
    return (
        <div className="h-14 border-b border-white/5 flex items-center justify-between px-6 shrink-0 bg-black/10 backdrop-blur-md">
            <div className="flex items-center gap-4">
                <div className="flex items-center gap-3">
                    <div className="h-8 w-8 rounded-full bg-[var(--cyan)]/20 flex items-center justify-center border border-[var(--cyan)]/30 shadow-[0_0_15px_rgba(0,255,255,0.1)] relative">
                        <Activity className="h-4 w-4 text-[var(--cyan)]" />
                        {isConnected && (
                            <div className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 bg-emerald-500 rounded-full border border-black" />
                        )}
                    </div>
                    <div className="flex flex-col">
                        <span className="text-sm font-bold text-white tracking-wide">CAPTAIN AI</span>
                        <div className="flex items-center gap-2">
                            <span className={cn(
                                "text-[9px] font-mono tracking-widest uppercase flex items-center gap-1",
                                isConnected ? "text-[var(--cyan)]" : "text-rose-400"
                            )}>
                                {isConnected ? "System Online" : "System Offline"}
                            </span>
                        </div>
                    </div>
                </div>

                <div className="h-4 w-px bg-white/10 mx-2" />

                <div className="flex items-center gap-4 text-[10px] font-mono text-muted-foreground uppercase tracking-wider">
                    <div className="flex items-center gap-1.5" title="Active Model">
                        <Cpu className="w-3.5 h-3.5" />
                        {modelName}
                    </div>
                    <div className="flex items-center gap-1.5" title="Workspace">
                        <Database className="w-3.5 h-3.5" />
                        {workspaceName}
                    </div>
                    <div className="flex items-center gap-1.5" title="Latency">
                        <Wifi className="w-3.5 h-3.5" />
                        {latency}ms
                    </div>
                </div>
            </div>

            <div className="flex items-center gap-2">
                <button className="p-2 text-muted-foreground hover:text-white hover:bg-white/5 transition rounded-md">
                    <Settings className="h-4 w-4" />
                </button>
                <button className="p-2 text-muted-foreground hover:text-white hover:bg-white/5 transition rounded-md">
                    <MoreVertical className="h-4 w-4" />
                </button>
            </div>
        </div>
    );
};
