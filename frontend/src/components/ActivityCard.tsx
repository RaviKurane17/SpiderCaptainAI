import React, { useMemo, useRef, useEffect, useState } from "react";
import { CircleCheck, Folder, File as FileIcon, HardDrive } from "lucide-react";
import type { LogRow } from "../hooks/useWebSocket";
import { SearchResultsWidget } from "./SearchResultsWidget";

interface ActivityCardProps {
    rows: LogRow[];
    onCommand?: (cmd: string) => void;
}

const TABS = ["ACTIVITY", "CONVERSATION", "SYSTEM LOG"] as const;

const ActivityCard = React.memo(function ActivityCard({ rows, onCommand }: ActivityCardProps) {
    const [activeSubTab, setActiveSubTab] = useState<typeof TABS[number]>("ACTIVITY");
    const bottomRef = useRef<HTMLDivElement>(null);

    const filteredRows = useMemo(() => {
        if (activeSubTab === "CONVERSATION") return rows.filter((r) => r.who === "YOU" || r.who === "CAPTAIN");
        if (activeSubTab === "SYSTEM LOG") return rows.filter((r) => r.who === "SYSTEM");
        return rows;
    }, [rows, activeSubTab]);

    // Auto-scroll to latest entry
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [filteredRows.length]);

    return (
        <div className="glass-panel w-full p-2.5 flex flex-col min-h-0 flex-1">
            <div className="flex gap-6 border-b border-white/5 pb-1.5 shrink-0">
                {TABS.map((t) => (
                    <button
                        key={t}
                        onClick={() => setActiveSubTab(t)}
                        className={`text-[11px] font-semibold tracking-[0.24em] transition relative pb-1 ${
                            activeSubTab === t
                                ? "text-[var(--cyan)] [text-shadow:0_0_12px_var(--cyan)]"
                                : "text-muted-foreground hover:text-foreground"
                        }`}
                    >
                        {t}
                        {activeSubTab === t && (
                            <div className="absolute bottom-0 left-0 h-[2px] w-full rounded-full bg-gradient-to-r from-[var(--cyan)] to-transparent" />
                        )}
                    </button>
                ))}
            </div>
            <div className="mt-1 flex-1 min-h-0 overflow-y-auto flex flex-col divide-y divide-white/5 pr-1">
                {filteredRows.map((r) => (
                    <div key={r.id} className="flex flex-col py-1 shrink-0">
                        <div className="flex items-center gap-3">
                            <div className="grid h-7 w-7 place-items-center rounded-lg border border-white/5 bg-white/5">
                                <r.icon className={`h-4 w-4 ${r.color}`} strokeWidth={1.8} />
                            </div>
                            <div className="flex w-24 flex-col leading-tight shrink-0">
                                <span className={`text-[11px] font-bold tracking-[0.2em] ${r.color}`}>{r.who}</span>
                                <span className="text-[10px] text-muted-foreground">{r.time}</span>
                            </div>
                            <span
                                className={`flex-1 text-sm ${
                                    r.who === "CAPTAIN" ? "text-[var(--violet)]" : "text-foreground"
                                }`}
                            >
                                {r.text}
                            </span>
                            {r.done && (
                                <span className="flex items-center gap-1 text-[11px] text-[var(--emerald)] shrink-0">
                                    <CircleCheck className="h-3.5 w-3.5" strokeWidth={2} /> Done
                                </span>
                            )}
                        </div>
                        {r.payload && r.payload.type === "search_results" && r.payload.data && r.payload.data.length > 0 && (
                            <div className="ml-[120px] mt-2 mb-2">
                                <SearchResultsWidget 
                                    query={r.payload.query || ""} 
                                    results={r.payload.data} 
                                    onOpen={(path) => onCommand?.(`open "${path}"`)} 
                                    ws={null} 
                                />
                            </div>
                        )}
                    </div>
                ))}
                <div ref={bottomRef} />
            </div>
        </div>
    );
});

export default ActivityCard;
