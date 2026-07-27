import React, { useMemo } from "react";
import { Sparkles, Mic, Database, ListChecks, ChevronRight } from "lucide-react";
import PanelHeader from "./PanelHeader";

interface AiStatusProps {
    aiState: string;
    isMuted: boolean;
    tasks?: any[];
}

const AiStatus = React.memo(function AiStatus({ aiState, isMuted, tasks }: AiStatusProps) {
    const voice = useMemo(() => {
        if (isMuted) return { val: "Muted", color: "text-[var(--rose)]", pulse: false };
        if (aiState === "SPEAKING") return { val: "Speaking", color: "text-[var(--emerald)]", pulse: true };
        if (aiState === "THINKING") return { val: "Thinking", color: "text-[var(--amber)]", pulse: true };
        return { val: "Listening", color: "text-[var(--cyan)]", pulse: true };
    }, [aiState, isMuted]);

    const todayCount = tasks ? tasks.filter(t => t.when === "Today").length : 0;

    const items = useMemo(
        () => [
            { icon: Sparkles, label: "Model", val: "Gemini 2.5 Pro", color: "text-[var(--violet)]" },
            { icon: Mic, label: "Voice Status", val: voice.val, color: voice.color, pulse: voice.pulse },
            { icon: Database, label: "Memory", val: "Connected", color: "text-[var(--cyan)]", dot: "emerald" },
            { icon: ListChecks, label: "Today's Tasks", val: todayCount.toString(), color: "text-[var(--cyan)]", chevron: true },
        ],
        [voice, todayCount]
    );

    return (
        <div className="glass-panel glass-panel-hover p-3">
            <PanelHeader title="AI STATUS" />
            <div className="mt-3 flex flex-col divide-y divide-white/5">
                {items.map((it, i) => (
                    <div key={i} className="flex items-center justify-between py-1">
                        <div className="flex items-center gap-3">
                            <it.icon className={`h-4 w-4 ${it.color}`} strokeWidth={1.8} />
                            <span className="text-sm text-muted-foreground">{it.label}</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <span className="text-sm font-medium text-foreground">{it.val}</span>
                            {it.pulse && (
                                <div className="flex items-end gap-[2px]">
                                    {[0.4, 0.9, 0.6].map((h, k) => (
                                        <span
                                            key={k}
                                            className="w-[2px] rounded-full bg-[var(--cyan)]"
                                            style={{
                                                height: `${h * 12}px`,
                                                animation: `wave 0.9s ease-in-out ${k * 0.15}s infinite alternate`,
                                            }}
                                        />
                                    ))}
                                </div>
                            )}
                            {it.dot === "emerald" && (
                                <span className="h-1.5 w-1.5 rounded-full bg-[var(--emerald)] shadow-[0_0_8px_var(--emerald)]" />
                            )}
                            {it.chevron && <ChevronRight className="h-4 w-4 text-[var(--cyan)]" strokeWidth={2} />}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
});

export default AiStatus;
