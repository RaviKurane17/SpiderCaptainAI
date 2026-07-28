import React from "react";
import { Loader2, CheckCircle2, Zap } from "lucide-react";

interface StartupBannerProps {
    state: string;
}

const STATE_LABELS: Record<string, { label: string; done: boolean }> = {
    STARTING:           { label: "Starting Captain AI...",           done: false },
    CORE_INITIALIZING:  { label: "Initializing core systems...",     done: false },
    CORE_READY:         { label: "Core ready — I'm online!",         done: true  },
    BACKGROUND_LOADING: { label: "Loading background services...",   done: false },
    FULLY_READY:        { label: "Fully ready",                      done: true  },
};

export function StartupBanner({ state }: StartupBannerProps) {
    const info = STATE_LABELS[state];

    // Don't show banner once fully ready
    if (!info || state === "FULLY_READY") return null;

    const isDone = info.done;

    return (
        <div className={`
            fixed top-4 left-1/2 -translate-x-1/2 z-[9998]
            flex items-center gap-2.5 px-4 py-2.5 rounded-full
            border backdrop-blur-xl text-xs font-semibold tracking-widest uppercase
            transition-all duration-500 shadow-2xl
            ${isDone
                ? "bg-[var(--cyan)]/10 border-[var(--cyan)]/40 text-[var(--cyan)] shadow-[0_0_20px_var(--cyan)/30]"
                : "bg-white/5 border-white/10 text-white/60"
            }
        `}>
            {isDone
                ? <CheckCircle2 size={14} className="text-[var(--cyan)]" />
                : <Loader2 size={14} className="animate-spin text-white/40" />
            }
            <span>{info.label}</span>
            {isDone && <Zap size={12} className="text-[var(--cyan)] animate-pulse" />}
        </div>
    );
}
