import React, { useState, useMemo, useEffect, useCallback } from "react";
import { 
    MonitorCog, BellRing, Camera, ShieldAlert, CloudRain, HelpCircle, 
    Terminal, Database, Search, Pin, PinOff, Clock, LayoutGrid, CheckCircle2, XCircle, Play, Loader2
} from "lucide-react";
import { useCommands, Command, CommandHistory } from "../../hooks/useCommands";
import { cn } from "@/lib/utils";

const ICON_MAP: Record<string, React.ElementType> = {
    MonitorCog, BellRing, Camera, ShieldAlert, CloudRain, HelpCircle, Terminal, Database
};

interface CommandsPanelProps {
    onSend: (text: string) => void;
    wsRef: React.MutableRefObject<WebSocket | null>;
}

export const CommandsPanel: React.FC<CommandsPanelProps> = React.memo(({ onSend, wsRef }) => {
    const { commands, history, togglePin, refreshHistory } = useCommands(wsRef);
    const [searchQuery, setSearchQuery] = useState("");
    const [activeCategory, setActiveCategory] = useState("All");
    const [executingId, setExecutingId] = useState<number | null>(null);

    // Re-fetch history when panel is active
    useEffect(() => {
        refreshHistory();
        const interval = setInterval(refreshHistory, 5000); // Poll for latest logs
        return () => clearInterval(interval);
    }, [refreshHistory]);

    const categories = useMemo(() => {
        const cats = new Set(commands.map(c => c.category));
        return ["All", "Pinned", ...Array.from(cats)].sort();
    }, [commands]);

    const filteredCommands = useMemo(() => {
        let filtered = commands;
        
        if (activeCategory === "Pinned") {
            filtered = filtered.filter(c => c.is_pinned);
        } else if (activeCategory !== "All") {
            filtered = filtered.filter(c => c.category === activeCategory);
        }

        if (searchQuery.trim() !== "") {
            const lowerQ = searchQuery.toLowerCase();
            filtered = filtered.filter(c => 
                c.title.toLowerCase().includes(lowerQ) || 
                c.cmd.toLowerCase().includes(lowerQ)
            );
        }
        
        return filtered;
    }, [commands, activeCategory, searchQuery]);

    const handleExecute = useCallback((id: number, cmd: string) => {
        if (executingId !== null) return;
        setExecutingId(id);
        onSend(cmd);
        
        // Visual feedback delay
        setTimeout(() => setExecutingId(null), 800);
        // Refresh history
        setTimeout(refreshHistory, 2000);
    }, [executingId, onSend, refreshHistory]);

    return (
        <main className="flex min-h-0 h-full flex-col gap-3">
            <div className="glass-panel flex h-14 items-center px-4 justify-between">
                <span className="text-[14px] font-bold tracking-[0.14em] text-foreground flex items-center gap-2">
                    <Terminal className="h-4 w-4" /> COMMANDS CENTER
                </span>
                <div className="relative w-64">
                    <Search className="absolute left-2.5 top-2 h-4 w-4 text-muted-foreground" />
                    <input 
                        type="text"
                        placeholder="Search commands..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full h-8 bg-black/20 border border-white/10 rounded-md pl-9 pr-3 text-xs text-foreground focus:outline-none focus:border-white/20 transition-all"
                    />
                </div>
            </div>
            
            <div className="flex flex-1 min-h-0 gap-3">
                {/* Categories Sidebar */}
                <div className="w-48 glass-panel flex flex-col p-3 gap-1 overflow-y-auto">
                    <h3 className="text-[10px] font-bold tracking-widest text-muted-foreground mb-2 px-2">CATEGORIES</h3>
                    {categories.map(cat => (
                        <button
                            key={cat}
                            onClick={() => setActiveCategory(cat)}
                            className={cn(
                                "text-left px-3 py-2 text-xs rounded-md transition-all flex items-center gap-2",
                                activeCategory === cat 
                                    ? "bg-white/10 text-white font-medium shadow-[inset_0_0_10px_rgba(255,255,255,0.05)]" 
                                    : "text-muted-foreground hover:bg-white/5 hover:text-white/80"
                            )}
                        >
                            {cat === "Pinned" ? <Pin className="h-3 w-3" /> : <LayoutGrid className="h-3 w-3" />}
                            {cat}
                        </button>
                    ))}
                </div>

                {/* Commands Grid */}
                <div className="flex-1 glass-panel p-4 overflow-y-auto flex flex-col">
                    {filteredCommands.length === 0 ? (
                        <div className="m-auto flex flex-col items-center justify-center text-muted-foreground opacity-50">
                            <Search className="h-8 w-8 mb-2" />
                            <p className="text-sm">No commands found.</p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 auto-rows-max">
                            {filteredCommands.map((c) => {
                                const IconComp = ICON_MAP[c.icon] || Terminal;
                                return (
                                    <div 
                                        key={c.id} 
                                        className="group relative glass-panel glass-panel-hover p-4 flex flex-col gap-3 hover:border-[oklch(0.75_0.22_225/0.4)] transition duration-300"
                                    >
                                        <div className="flex items-start justify-between">
                                            <div className="flex items-center gap-3">
                                                <div className={cn("grid h-8 w-8 place-items-center rounded bg-white/5", c.color)}>
                                                    <IconComp className="h-4.5 w-4.5" />
                                                </div>
                                                <div className="flex flex-col">
                                                    <span className="font-semibold text-[13px] text-foreground">{c.title}</span>
                                                    <span className="text-[10px] text-muted-foreground uppercase tracking-wider">{c.category}</span>
                                                </div>
                                            </div>
                                            <button 
                                                onClick={(e) => { e.stopPropagation(); togglePin(c.id, c.is_pinned); }}
                                                className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 hover:bg-white/10 rounded-md"
                                                title={c.is_pinned ? "Unpin command" : "Pin command"}
                                            >
                                                {c.is_pinned ? <PinOff className="h-3.5 w-3.5 text-amber-400" /> : <Pin className="h-3.5 w-3.5 text-muted-foreground" />}
                                            </button>
                                        </div>
                                        <p className="text-[11px] text-muted-foreground line-clamp-2 min-h-[32px]">{c.desc}</p>
                                        <div className="flex items-center justify-between mt-auto pt-2">
                                            <span className="text-[9px] font-mono text-[oklch(0.75_0.22_225/0.85)] bg-white/5 px-2 py-1 rounded truncate max-w-[70%]">
                                                &gt; {c.cmd}
                                            </span>
                                            <button 
                                                onClick={() => handleExecute(c.id, c.cmd)}
                                                disabled={executingId === c.id}
                                                className={cn(
                                                    "flex items-center gap-1.5 text-[10px] px-2.5 py-1 rounded-md transition-all",
                                                    executingId === c.id 
                                                        ? "bg-emerald-500/20 text-emerald-400" 
                                                        : "bg-white/10 hover:bg-white/20 text-white active:scale-95"
                                                )}
                                            >
                                                {executingId === c.id ? (
                                                    <><Loader2 className="h-3 w-3 animate-spin" /> Sent</>
                                                ) : (
                                                    <><Play className="h-3 w-3" /> Execute</>
                                                )}
                                            </button>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>

                {/* Execution History / Logs */}
                <div className="w-72 glass-panel flex flex-col p-0 overflow-hidden">
                    <div className="h-10 border-b border-white/5 flex items-center px-4 bg-white/5">
                        <span className="text-[11px] font-bold tracking-widest text-foreground flex items-center gap-2">
                            <Clock className="h-3.5 w-3.5 text-[oklch(0.75_0.22_225)]" /> 
                            EXECUTION LOG
                        </span>
                    </div>
                    <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-2">
                        {history.length === 0 ? (
                            <div className="m-auto text-center text-xs text-muted-foreground/50 py-10">No recent executions.</div>
                        ) : (
                            history.map((log) => (
                                <div key={log.id} className="bg-black/20 border border-white/5 rounded-md p-2.5 flex flex-col gap-1.5">
                                    <div className="flex items-center justify-between">
                                        <span className="text-[10px] font-mono text-white/90 truncate max-w-[75%]" title={log.cmd}>{log.cmd}</span>
                                        {log.status === "Success" ? (
                                            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
                                        ) : (
                                            <XCircle className="h-3.5 w-3.5 text-rose-400 shrink-0" />
                                        )}
                                    </div>
                                    <div className="flex items-center justify-between text-[9px] text-muted-foreground mt-1">
                                        <span>{new Date(log.executed_at * 1000).toLocaleTimeString()}</span>
                                        <span>{log.latency.toFixed(2)}s</span>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </div>
        </main>
    );
});

CommandsPanel.displayName = "CommandsPanel";
