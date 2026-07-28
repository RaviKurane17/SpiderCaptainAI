import React from "react";
import { Minus, Square, X, Box } from "lucide-react";

const TitleBar = React.memo(function TitleBar() {
    const handleControl = (action: string) => {
        const api = (window as any).pywebview?.api;
        if (api) {
            if (action === "minimize") api.minimize();
            else if (action === "maximize") api.maximize();
            else if (action === "close") api.close();
            else if (action === "orb_mode") api.orb_mode();
        } else {
            if (action === "close") window.close();
        }
    };

    return (
        <div className="glass-panel flex h-14 items-center justify-between px-3 pywebview-drag-region select-none">
            <div 
                onClick={() => handleControl("orb_mode")}
                className="flex h-9 w-9 items-center justify-center rounded-md bg-gradient-to-br from-[oklch(0.75_0.22_225)] to-[oklch(0.55_0.24_285)] shadow-[0_0_20px_oklch(0.75_0.22_225/0.5)] cursor-pointer hover:scale-105 hover:brightness-110 transition-all duration-300 no-drag"
                title="Switch to Orb Mode"
            >
                <Box className="h-4.5 w-4.5 text-primary-foreground" strokeWidth={2} />
            </div>
            <div className="flex gap-1">
                <button
                    onClick={() => handleControl("minimize")}
                    className="grid h-7 w-7 place-items-center rounded-md text-muted-foreground transition hover:bg-white/5 hover:text-foreground no-drag"
                    title="Minimize"
                >
                    <Minus className="h-3.5 w-3.5" strokeWidth={1.8} />
                </button>
                <button
                    onClick={() => handleControl("maximize")}
                    className="grid h-7 w-7 place-items-center rounded-md text-muted-foreground transition hover:bg-white/5 hover:text-foreground no-drag"
                    title="Maximize / Restore"
                >
                    <Square className="h-3.5 w-3.5" strokeWidth={1.8} />
                </button>
                <button
                    onClick={() => handleControl("close")}
                    className="grid h-7 w-7 place-items-center rounded-md text-muted-foreground transition hover:bg-white/5 hover:text-rose-500 no-drag"
                    title="Close"
                >
                    <X className="h-3.5 w-3.5" strokeWidth={1.8} />
                </button>
            </div>
        </div>
    );
});

export default TitleBar;
