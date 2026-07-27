import React, { useEffect, useMemo, useState } from "react";
import { cn } from "@/lib/utils";
import { Signal, CloudRain } from "lucide-react";

interface HeaderProps {
    isConnected: boolean;
    latency: number;
}

const Header = React.memo(function Header({ isConnected, latency }: HeaderProps) {
    const [time, setTime] = useState<Date | null>(null);

    useEffect(() => {
        setTime(new Date());
        const timer = setInterval(() => setTime(new Date()), 1000);
        return () => clearInterval(timer);
    }, []);

    const { hm, ampm, dateStr } = useMemo(() => {
        if (!time) return { hm: "--:--", ampm: "AM", dateStr: "---, --- --, ----" };
        const timeStr = time.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: true });
        const parts = timeStr.split(" ");
        return {
            hm: parts[0],
            ampm: parts[1] || "",
            dateStr: time.toLocaleDateString([], { weekday: "short", day: "numeric", month: "short", year: "numeric" }),
        };
    }, [time]);

    return (
        <div className="glass-panel flex h-14 items-center justify-between px-5 w-full select-none animate-fade-in">
            <div
                className={cn(
                    "flex items-center gap-1.5 rounded-full border px-3.5 py-1 shrink-0 transition-colors duration-300",
                    isConnected
                        ? "border-[oklch(0.78_0.19_160/0.4)] bg-[oklch(0.78_0.19_160/0.08)] text-[var(--emerald)]"
                        : "border-[oklch(0.65_0.22_20/0.4)] bg-[oklch(0.65_0.22_20/0.08)] text-[var(--rose)] animate-pulse"
                )}
            >
                <span className="relative flex h-1.5 w-1.5">
                    <span
                        className={cn(
                            "absolute inline-flex h-full w-full animate-ping rounded-full opacity-60",
                            isConnected ? "bg-[var(--emerald)]" : "bg-[var(--rose)]"
                        )}
                    />
                    <span
                        className={cn(
                            "relative inline-flex h-1.5 w-1.5 rounded-full",
                            isConnected ? "bg-[var(--emerald)]" : "bg-[var(--rose)]"
                        )}
                    />
                </span>
                <span className="text-[11px] font-semibold tracking-[0.2em]">
                    {isConnected ? "ONLINE" : "OFFLINE"}
                </span>
            </div>

            <div className="flex flex-col items-center shrink-0 mx-2">
                <h1
                    className="text-[20px] font-black tracking-[0.22em] text-gradient-cyber leading-none"
                    style={{ fontFamily: "var(--font-display)" }}
                >
                    CAPTAIN AI
                </h1>
                <div className="mt-0.5 flex items-center gap-2">
                    <span className="h-px w-6 bg-gradient-to-r from-transparent to-[var(--cyan)]" />
                    <span className="text-[9px] tracking-[0.25em] text-muted-foreground whitespace-nowrap">
                        AI COMMAND INTERFACE
                    </span>
                    <span className="h-px w-6 bg-gradient-to-l from-transparent to-[var(--cyan)]" />
                </div>
            </div>

            <div className="flex items-center gap-4 text-muted-foreground shrink-0">
                <div className="flex items-center gap-2">
                    <Signal className="h-[18px] w-[18px] text-[var(--cyan)]" strokeWidth={1.8} />
                    <span className="text-[13px] font-medium tabular-nums text-foreground">
                        {isConnected ? `${latency}ms` : "--ms"}
                    </span>
                </div>
                <div className="h-5 w-px bg-white/10" />
                <div className="flex items-center gap-2.5">
                    <CloudRain className="h-[22px] w-[22px] text-[var(--cyan)]" strokeWidth={1.6} />
                    <div className="flex flex-col leading-none">
                        <span className="text-[13px] font-bold tabular-nums text-foreground">27°C</span>
                        <span className="text-[9px] text-muted-foreground mt-0.5">Light Rain</span>
                    </div>
                </div>
                <div className="h-5 w-px bg-white/10" />
                <div className="flex flex-col items-end leading-none">
                    <span className="text-[13px] font-bold tabular-nums text-[var(--cyan)]">
                        {hm}
                        <span className="text-[9px] font-medium ml-0.5">{ampm}</span>
                    </span>
                    <span className="text-[9px] text-muted-foreground mt-0.5">{dateStr}</span>
                </div>
            </div>
        </div>
    );
});

export default Header;
