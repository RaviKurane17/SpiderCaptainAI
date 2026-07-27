import React, { useState } from 'react';
import { Brain, Check, X, ShieldAlert } from 'lucide-react';
import { useWebSocket } from '../../hooks/useWebSocket';

interface MemorySuggestionProps {
    data: {
        title: string;
        summary: string;
        category: string;
    };
}

export const MemorySuggestionCard: React.FC<MemorySuggestionProps> = ({ data }) => {
    const ws = useWebSocket();
    const [status, setStatus] = useState<'pending' | 'saved' | 'rejected'>('pending');

    const handleSave = () => {
        // We will generate a unique ID and send to the server to add
        ws.sendCommand({
            type: "add_memory_direct",
            title: data.title,
            summary: data.summary,
            category: data.category,
            source: "AI Suggested"
        });
        setStatus('saved');
    };

    const handleReject = () => {
        setStatus('rejected');
    };

    if (status === 'saved') {
        return (
            <div className="w-full max-w-sm p-3 rounded-lg border border-emerald-500/30 bg-emerald-500/10 backdrop-blur-md flex items-center gap-3">
                <Check className="w-4 h-4 text-emerald-400" />
                <span className="text-xs text-emerald-400 font-medium tracking-wide">Memory Saved</span>
            </div>
        );
    }

    if (status === 'rejected') {
        return (
            <div className="w-full max-w-sm p-3 rounded-lg border border-white/5 bg-black/20 backdrop-blur-md flex items-center gap-3">
                <X className="w-4 h-4 text-muted-foreground" />
                <span className="text-xs text-muted-foreground font-medium tracking-wide">Memory Ignored</span>
            </div>
        );
    }

    return (
        <div className="w-full max-w-sm rounded-lg border border-[var(--cyan)]/30 bg-black/40 backdrop-blur-md overflow-hidden shadow-xl mb-4 transition-all duration-300 group">
            <div className="p-4 flex flex-col gap-3">
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full border border-[var(--cyan)]/50 bg-[var(--cyan)]/20 text-[var(--cyan)] flex items-center justify-center shrink-0 shadow-[0_0_10px_rgba(0,255,255,0.2)]">
                        <Brain className="w-4 h-4" />
                    </div>
                    <div className="flex flex-col">
                        <span className="text-sm font-semibold text-white tracking-wide">Memory Suggestion</span>
                        <span className="text-[10px] text-muted-foreground uppercase font-mono tracking-wider">
                            I noticed an important fact
                        </span>
                    </div>
                </div>

                <div className="pl-11 pr-2">
                    <h5 className="text-xs font-bold text-white mb-1">{data.title}</h5>
                    <p className="text-xs text-muted-foreground mb-3 leading-relaxed">
                        "{data.summary}"
                    </p>
                    <div className="flex items-center gap-2">
                        <span className="text-[9px] font-mono uppercase tracking-widest px-2 py-0.5 rounded-full border bg-white/5 border-white/10 text-white/70">
                            {data.category}
                        </span>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-2 border-t border-white/10 divide-x divide-white/10">
                <button 
                    onClick={handleReject}
                    className="p-3 text-xs font-medium text-muted-foreground hover:bg-rose-500/20 hover:text-rose-400 transition-colors flex items-center justify-center gap-2"
                >
                    <ShieldAlert className="w-3.5 h-3.5" /> Not Now
                </button>
                <button 
                    onClick={handleSave}
                    className="p-3 text-xs font-medium text-[var(--cyan)] hover:bg-[var(--cyan)]/20 transition-colors flex items-center justify-center gap-2"
                >
                    <Check className="w-3.5 h-3.5" /> Remember This
                </button>
            </div>
        </div>
    );
};
