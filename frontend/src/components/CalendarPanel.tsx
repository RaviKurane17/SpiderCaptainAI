import React from "react";
import { cn } from "@/lib/utils";
import { CalendarDays, Plus, ChevronRight, BellRing } from "lucide-react";
import PanelHeader from "./PanelHeader";

interface Task {
    id: number;
    title: string;
    desc: string;
    time: string;
    when: string;
    date: string;
    timeRaw: string;
    reminderActive: boolean;
    notified: boolean;
    color: string;
}

interface CalendarPanelProps {
    className?: string;
    tasks: Task[];
    onAddClick: () => void;
    onViewAllClick: () => void;
    onToggleReminder: (id: number) => void;
}

const CalendarPanel = React.memo(function CalendarPanel({
    className,
    tasks,
    onAddClick,
    onViewAllClick,
    onToggleReminder,
}: CalendarPanelProps) {
    const visibleTasks = tasks.slice(0, 3);

    return (
        <div className={cn("glass-panel glass-panel-hover p-3 flex flex-col min-h-0", className)}>
            <PanelHeader
                title="CALENDAR & REMINDERS"
                trailing={
                    <button
                        onClick={onAddClick}
                        className="no-drag p-1 rounded hover:bg-white/5 text-[var(--cyan)] hover:scale-105 transition cursor-pointer"
                        title="Add New Task"
                    >
                        <Plus className="h-4.5 w-4.5" strokeWidth={2.4} />
                    </button>
                }
            />
            <div className="mt-3 flex-1 min-h-0 overflow-y-auto pr-1 flex flex-col gap-2">
                {visibleTasks.length === 0 ? (
                    <span className="text-[11px] text-muted-foreground font-mono py-6 text-center">
                        No active reminders.
                    </span>
                ) : (
                    visibleTasks.map((t) => (
                        <div
                            key={t.id}
                            className="group flex items-center gap-3 rounded-lg border border-transparent p-2 transition hover:border-[oklch(0.75_0.22_225/0.25)] hover:bg-white/[0.02]"
                        >
                            <div
                                className={`grid h-9 w-9 place-items-center rounded-lg border border-white/5 bg-white/5 ${t.color || "text-[var(--cyan)]"}`}
                            >
                                <CalendarDays className="h-4 w-4" strokeWidth={1.8} />
                            </div>
                            <div className="flex flex-1 flex-col leading-tight">
                                <span className="text-[13px] font-semibold text-foreground">{t.title}</span>
                                <span className="text-[11px] text-muted-foreground">{t.desc}</span>
                            </div>
                            <div className="flex flex-col items-end leading-tight">
                                <span className="text-[12px] font-semibold text-foreground tabular-nums">{t.time}</span>
                                <span className="text-[10px] text-muted-foreground">{t.when}</span>
                            </div>
                            <button
                                onClick={() => onToggleReminder(t.id)}
                                className="no-drag p-1 rounded hover:bg-white/5 cursor-pointer shadow-none"
                                title="Toggle Alert Notification"
                            >
                                <BellRing
                                    className={cn(
                                        "h-4 w-4 transition",
                                        t.reminderActive
                                            ? "text-[var(--cyan)] animate-glow-pulse"
                                            : "text-muted-foreground group-hover:text-foreground"
                                    )}
                                    strokeWidth={1.6}
                                />
                            </button>
                        </div>
                    ))
                )}
            </div>
            <button
                onClick={onViewAllClick}
                className="mt-3 shrink-0 flex w-full items-center justify-center gap-2 rounded-lg border border-[oklch(0.75_0.22_225/0.3)] py-1.5 text-[12px] font-semibold tracking-[0.18em] text-[var(--cyan)] transition hover:border-[oklch(0.75_0.22_225/0.6)] hover:bg-[oklch(0.75_0.22_225/0.08)] hover:shadow-[0_0_20px_oklch(0.75_0.22_225/0.3)] cursor-pointer"
            >
                View All Reminders
                <ChevronRight className="h-4 w-4" strokeWidth={2} />
            </button>
        </div>
    );
});

export default CalendarPanel;
