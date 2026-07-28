import React, { useEffect, useState } from "react";
import { Activity, X, Database, Search, HardDrive } from "lucide-react";

export interface DiagnosticsData {
    query: string;
    memory_mb: number;
    threads: number;
    cancelled: boolean;
}

interface DeveloperDiagnosticsProps {
    data: DiagnosticsData | null;
    onClose: () => void;
}

export function DeveloperDiagnostics({ data, onClose }: DeveloperDiagnosticsProps) {
    if (!data) return null;

    return (
        <div className="fixed bottom-24 right-8 w-80 bg-[#1A1E24]/90 backdrop-blur-xl border border-white/10 rounded-lg shadow-2xl p-4 z-50 overflow-hidden font-mono text-xs">
            {/* Top gradient accent */}
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-[var(--cyan)] to-[var(--magenta)] opacity-50" />
            
            <div className="flex items-center justify-between border-b border-white/10 pb-2 mb-3">
                <div className="flex items-center gap-2 text-[var(--cyan)]">
                    <Activity size={14} className="animate-pulse" />
                    <span className="font-bold tracking-widest text-[10px] uppercase">Engine Diagnostics</span>
                </div>
                <button onClick={onClose} className="text-white/40 hover:text-white">
                    <X size={14} />
                </button>
            </div>

            <div className="flex flex-col gap-3">
                <div className="flex justify-between items-center">
                    <span className="text-white/50 flex items-center gap-1.5"><Search size={12}/> Query:</span>
                    <span className="text-white truncate max-w-[120px]">{data.query || "None"}</span>
                </div>
                <div className="flex justify-between items-center">
                    <span className="text-white/50 flex items-center gap-1.5"><HardDrive size={12}/> Memory:</span>
                    <span className={data.memory_mb > 150 ? "text-red-400" : "text-green-400"}>
                        {data.memory_mb} MB
                    </span>
                </div>
                <div className="flex justify-between items-center">
                    <span className="text-white/50 flex items-center gap-1.5"><Database size={12}/> Threads:</span>
                    <span className="text-white">{data.threads}</span>
                </div>
                <div className="flex justify-between items-center mt-1 pt-2 border-t border-white/5">
                    <span className="text-white/50">Status:</span>
                    {data.cancelled ? (
                        <span className="text-red-400 font-semibold uppercase text-[10px]">Cancelled</span>
                    ) : (
                        <span className="text-[var(--cyan)] font-semibold uppercase text-[10px] animate-pulse">Running</span>
                    )}
                </div>
            </div>
        </div>
    );
}
