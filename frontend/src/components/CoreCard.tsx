import React from "react";
import { Compass } from "lucide-react";

const CoreCard = React.memo(function CoreCard() {
    return (
        <div className="glass-panel glass-panel-hover p-2.5">
            <div className="flex items-center gap-3">
                <div className="relative h-9 w-9">
                    <div className="absolute inset-0 rounded-lg bg-[var(--gradient-ring)] opacity-70 blur-[6px]" />
                    <div className="relative grid h-full w-full place-items-center rounded-lg bg-background/60 backdrop-blur">
                        <Compass className="h-4.5 w-4.5 text-[var(--cyan)]" strokeWidth={1.8} />
                    </div>
                </div>
                <div className="flex flex-col">
                    <span className="text-[12px] font-bold tracking-[0.16em] text-foreground">CAPTAIN CORE</span>
                    <span className="text-[9px] tracking-widest text-muted-foreground">v1.2.0 PRO</span>
                </div>
            </div>
            <div className="mt-2 flex items-center gap-2 text-[10px] text-[var(--emerald)]">
                <span className="relative flex h-1.5 w-1.5">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[var(--emerald)] opacity-60" />
                    <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-[var(--emerald)]" />
                </span>
                All Systems Operational
            </div>
        </div>
    );
});

export default CoreCard;
