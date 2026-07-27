import React from 'react';
import { Database, BrainCircuit, HardDrive, BarChart3, Activity } from 'lucide-react';

interface MemoryStats {
    total_memories: number;
    manual_memories: number;
    ai_suggested_memories: number;
    permanent_memories: number;
    temporary_memories: number;
    project_memories: number;
    conversation_memories: number;
    personal_memories: number;
    recent_memories: number;
    pinned_memories: number;
    favourite_memories: number;
    db_size_bytes: number;
    categories: Record<string, number>;
    last_updated: number;
    last_backup: string;
    search_statistics: string;
    health: string;
}

interface MemoryDashboardProps {
    stats: MemoryStats | null;
}

export const MemoryDashboard: React.FC<MemoryDashboardProps> = ({ stats }) => {
    if (!stats) {
        // Skeleton loader
        return (
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3 mb-6">
                {[...Array(10)].map((_, i) => (
                    <div key={i} className="glass-panel p-3 h-20 animate-pulse flex flex-col justify-between">
                        <div className="h-3 bg-white/10 rounded w-1/3" />
                        <div className="h-6 bg-white/10 rounded w-1/2" />
                    </div>
                ))}
            </div>
        );
    }

    const formatBytes = (bytes: number) => {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };
    
    const timeAgo = (ts: number) => {
        if (!ts) return "Never";
        const diff = Math.floor(Date.now() / 1000 - ts);
        if (diff < 60) return "Just now";
        if (diff < 3600) return `${Math.floor(diff/60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff/3600)}h ago`;
        return `${Math.floor(diff/86400)}d ago`;
    };

    const metrics = [
        { label: "Total Memories", value: stats.total_memories, icon: Database, color: "border-l-[var(--cyan)]" },
        { label: "Manual Memories", value: stats.manual_memories, icon: Activity, color: "border-l-emerald-500" },
        { label: "AI Suggested", value: stats.ai_suggested_memories, icon: BrainCircuit, color: "border-l-purple-500" },
        { label: "Permanent", value: stats.permanent_memories, icon: HardDrive, color: "border-l-amber-500" },
        { label: "Temporary", value: stats.temporary_memories, icon: Database, color: "border-l-rose-500" },
        { label: "Project specific", value: stats.project_memories, icon: Database, color: "border-l-slate-400" },
        { label: "Conversation", value: stats.conversation_memories, icon: Database, color: "border-l-slate-400" },
        { label: "Recent (24h)", value: stats.recent_memories, icon: Database, color: "border-l-slate-400" },
        { label: "Pinned", value: stats.pinned_memories, icon: Database, color: "border-l-slate-400" },
        { label: "Storage Size", value: formatBytes(stats.db_size_bytes), icon: HardDrive, color: "border-l-[var(--cyan)]" },
    ];

    return (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3 mb-6">
            {metrics.map((m, i) => (
                <div key={i} className={`bg-black/40 border border-white/5 p-3 flex flex-col justify-between hover:bg-white/5 transition-all border-l-2 ${m.color} rounded-lg shadow-sm`}>
                    <div className="flex items-center gap-2 text-muted-foreground mb-1">
                        <m.icon className="w-3 h-3" />
                        <span className="text-[10px] font-mono uppercase tracking-wider truncate">{m.label}</span>
                    </div>
                    <div className="text-xl font-bold text-white">
                        {m.value}
                    </div>
                </div>
            ))}
        </div>
    );
};
