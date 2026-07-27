import React from 'react';
import { Settings, Wrench, Activity, AlertTriangle, CheckCircle, Package, ArrowUpRight } from 'lucide-react';

interface ToolsStats {
    total_tools: number;
    enabled_tools: number;
    disabled_tools: number;
    running_tools: number;
    available_updates: number;
    tool_health: string;
    last_executed: string;
    permission_warnings: number;
    errors: number;
    execution_statistics: string;
}

interface ToolsDashboardProps {
    stats: ToolsStats | null;
}

export const ToolsDashboard: React.FC<ToolsDashboardProps> = ({ stats }) => {
    if (!stats) {
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

    const metrics = [
        { label: "Total Tools", value: stats.total_tools, icon: Package, color: "border-l-blue-500" },
        { label: "Enabled", value: stats.enabled_tools, icon: CheckCircle, color: "border-l-emerald-500" },
        { label: "Disabled", value: stats.disabled_tools, icon: Settings, color: "border-l-slate-500" },
        { label: "Running", value: stats.running_tools, icon: Activity, color: "border-l-purple-500" },
        { label: "Updates", value: stats.available_updates, icon: ArrowUpRight, color: "border-l-amber-500" },
        
        { label: "Health", value: stats.tool_health, icon: Activity, color: stats.tool_health === 'Optimal' ? "border-l-emerald-500" : "border-l-rose-500" },
        { label: "Last Executed", value: stats.last_executed, icon: Wrench, color: "border-l-[var(--cyan)]" },
        { label: "Warnings", value: stats.permission_warnings, icon: AlertTriangle, color: "border-l-amber-500" },
        { label: "Errors", value: stats.errors, icon: AlertTriangle, color: "border-l-rose-500" },
        { label: "Stats", value: stats.execution_statistics, icon: Activity, color: "border-l-blue-500" },
    ];

    return (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3 mb-6">
            {metrics.map((m, i) => (
                <div key={i} className={`bg-black/40 border border-white/5 p-3 flex flex-col justify-between hover:bg-white/5 transition-all border-l-2 ${m.color} rounded-lg shadow-sm`}>
                    <div className="flex items-center gap-2 text-muted-foreground mb-1">
                        <m.icon className="w-3 h-3" />
                        <span className="text-[10px] font-mono uppercase tracking-wider truncate">{m.label}</span>
                    </div>
                    <div className="text-xl font-bold text-white truncate">
                        {m.value}
                    </div>
                </div>
            ))}
        </div>
    );
};
