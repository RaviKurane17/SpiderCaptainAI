import React from 'react';
import { Virtuoso } from 'react-virtuoso';
import { Settings, Shield, Activity, Lock, AlertTriangle, Play, Square, RefreshCw, Eye, MoreVertical } from 'lucide-react';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator } from '@/components/ui/dropdown-menu';

export interface ToolRecord {
    id: string;
    name: string;
    description: string;
    version: string;
    category: string;
    status: string;
    health: string;
    ai_callable: string;
    security_level: string;
    execution_count: number;
    avg_runtime_ms: number;
    last_used: number;
    is_pinned: number;
}

interface ToolsListProps {
    tools: ToolRecord[];
    onAction: (toolId: string, action: string, data?: any) => void;
}

export const ToolsList: React.FC<ToolsListProps> = ({ tools, onAction }) => {
    
    const timeAgo = (ts: number) => {
        if (!ts) return "Never";
        const diff = Math.floor(Date.now() / 1000 - ts);
        if (diff < 60) return "Just now";
        if (diff < 3600) return `${Math.floor(diff/60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff/3600)}h ago`;
        return `${Math.floor(diff/86400)}d ago`;
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'Enabled': return 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20';
            case 'Disabled': return 'text-slate-400 bg-slate-400/10 border-slate-400/20';
            case 'Running': return 'text-[var(--cyan)] bg-[var(--cyan)]/10 border-[var(--cyan)]/20';
            case 'Crashed': return 'text-rose-400 bg-rose-400/10 border-rose-400/20';
            default: return 'text-slate-400 bg-slate-400/10 border-slate-400/20';
        }
    };

    const getSecurityIcon = (level: string) => {
        switch (level) {
            case 'Boss Mode': return <Lock className="w-3 h-3 text-rose-500" />;
            case 'Administrator': return <Shield className="w-3 h-3 text-amber-500" />;
            case 'Developer': return <Settings className="w-3 h-3 text-purple-500" />;
            default: return <Shield className="w-3 h-3 text-emerald-500" />;
        }
    };

    if (tools.length === 0) {
        return (
            <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground">
                <Settings className="w-12 h-12 mb-4 opacity-20" />
                <p>No tools found matching your criteria</p>
            </div>
        );
    }

    return (
        <Virtuoso
            style={{ height: '100%' }}
            data={tools}
            className="virtual-scroll"
            itemContent={(_, t) => (
                <div className="group mb-3 glass-panel p-4 hover:bg-white/5 transition-colors border border-white/5 hover:border-white/10 rounded-xl flex items-center justify-between gap-4 cursor-default">
                    
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                            <span className="font-bold text-base text-foreground truncate">{t.name}</span>
                            <span className="text-[10px] text-muted-foreground bg-white/5 px-2 py-0.5 rounded-full border border-white/10 font-mono">v{t.version}</span>
                            {t.is_pinned === 1 && (
                                <span className="text-[10px] text-amber-400 bg-amber-400/10 px-2 py-0.5 rounded-full border border-amber-400/20 font-mono">Pinned</span>
                            )}
                        </div>
                        <p className="text-sm text-muted-foreground truncate mb-3">{t.description}</p>
                        
                        <div className="flex items-center gap-3 flex-wrap">
                            <span className={`text-[10px] px-2 py-0.5 rounded-full border font-mono tracking-wide ${getStatusColor(t.status)}`}>
                                {t.status}
                            </span>
                            
                            <div className="flex items-center gap-1.5 text-xs text-muted-foreground border border-white/10 bg-black/40 px-2 py-0.5 rounded-md">
                                <span className="w-2 h-2 rounded-full bg-blue-500/50"></span>
                                {t.category}
                            </div>
                            
                            <div className="flex items-center gap-1.5 text-xs text-muted-foreground border border-white/10 bg-black/40 px-2 py-0.5 rounded-md">
                                {getSecurityIcon(t.security_level)}
                                {t.security_level}
                            </div>
                        </div>
                    </div>

                    <div className="flex flex-col items-end gap-3 shrink-0">
                        <div className="flex items-center gap-2">
                            <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                    <button className="text-[10px] border border-white/10 bg-black hover:bg-white/10 text-muted-foreground px-3 py-1 rounded-md transition flex items-center gap-2 font-mono">
                                        AI Status: <span className={t.ai_callable === 'Blocked' ? 'text-rose-400' : 'text-[var(--cyan)]'}>{t.ai_callable}</span>
                                    </button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end" className="bg-black/95 border-white/10 backdrop-blur-xl">
                                    <DropdownMenuItem onSelect={() => onAction(t.id, 'set_permission', 'Allowed')} className="text-emerald-400 cursor-pointer focus:bg-white/10">Allowed (Auto)</DropdownMenuItem>
                                    <DropdownMenuItem onSelect={() => onAction(t.id, 'set_permission', 'Ask Every Time')} className="text-amber-400 cursor-pointer focus:bg-white/10">Ask Every Time</DropdownMenuItem>
                                    <DropdownMenuItem onSelect={() => onAction(t.id, 'set_permission', 'Blocked')} className="text-rose-400 cursor-pointer focus:bg-white/10">Blocked</DropdownMenuItem>
                                </DropdownMenuContent>
                            </DropdownMenu>

                            <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                    <button className="p-1.5 hover:bg-white/10 rounded-md transition text-muted-foreground">
                                        <MoreVertical className="w-4 h-4" />
                                    </button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end" className="bg-black/95 border-white/10 backdrop-blur-xl w-48">
                                    <DropdownMenuItem onSelect={() => onAction(t.id, 'run')} className="text-white cursor-pointer focus:bg-white/10">
                                        <Play className="w-4 h-4 mr-2 text-emerald-400" /> Run Tool
                                    </DropdownMenuItem>
                                    <DropdownMenuItem onSelect={() => onAction(t.id, 'stop')} className="text-white cursor-pointer focus:bg-white/10">
                                        <Square className="w-4 h-4 mr-2 text-rose-400" /> Stop Tool
                                    </DropdownMenuItem>
                                    <DropdownMenuSeparator className="bg-white/10" />
                                    <DropdownMenuItem onSelect={() => onAction(t.id, 'logs')} className="text-white cursor-pointer focus:bg-white/10">
                                        <Eye className="w-4 h-4 mr-2 text-blue-400" /> View Logs
                                    </DropdownMenuItem>
                                    <DropdownMenuItem onSelect={() => onAction(t.id, 'test')} className="text-white cursor-pointer focus:bg-white/10">
                                        <Activity className="w-4 h-4 mr-2 text-[var(--cyan)]" /> Test / Health Check
                                    </DropdownMenuItem>
                                    <DropdownMenuSeparator className="bg-white/10" />
                                    <DropdownMenuItem onSelect={() => onAction(t.id, 'toggle_pin')} className="text-white cursor-pointer focus:bg-white/10">
                                        {t.is_pinned ? "Unpin Tool" : "Pin Tool"}
                                    </DropdownMenuItem>
                                </DropdownMenuContent>
                            </DropdownMenu>
                        </div>

                        <div className="text-[10px] text-muted-foreground flex items-center gap-3 font-mono">
                            <span>Runs: {t.execution_count}</span>
                            <span>Avg: {t.avg_runtime_ms}ms</span>
                            <span>Active: {timeAgo(t.last_used)}</span>
                        </div>
                    </div>
                </div>
            )}
        />
    );
};
