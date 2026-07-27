import React, { useCallback } from "react";
import { X, CalendarDays, BellRing, Check, Pencil } from "lucide-react";
import { cn } from "@/lib/utils";

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

/* ---- Add Reminder Modal ---- */
interface AddModalProps {
    title: string;
    desc: string;
    date: string;
    time: string;
    reminder: boolean;
    onTitleChange: (v: string) => void;
    onDescChange: (v: string) => void;
    onDateChange: (v: string) => void;
    onTimeChange: (v: string) => void;
    onReminderToggle: () => void;
    onConfirm: () => void;
    onClose: () => void;
}

export const AddReminderModal = React.memo(function AddReminderModal({
    title, desc, date, time, reminder,
    onTitleChange, onDescChange, onDateChange, onTimeChange,
    onReminderToggle, onConfirm, onClose,
}: AddModalProps) {
    return (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-md select-none animate-fade-in p-4">
            <div className="glass-panel w-full max-w-sm p-6 border border-white/10 flex flex-col gap-4 shadow-2xl relative">
                <div className="flex items-center justify-between border-b border-white/5 pb-2">
                    <h3 className="text-xs font-black tracking-[0.2em] uppercase text-gradient-cyber">
                        {title !== undefined && desc !== undefined ? "Save Reminder" : "Add New Reminder"}
                    </h3>
                    <button onClick={onClose} className="text-muted-foreground hover:text-rose-400 no-drag p-1 rounded hover:bg-white/5 cursor-pointer">
                        <X className="h-4 w-4" />
                    </button>
                </div>
                <div className="flex flex-col gap-3.5">
                    <div className="flex flex-col gap-1.5">
                        <label className="text-[10px] uppercase font-bold tracking-[0.2em] text-muted-foreground">Task Title</label>
                        <input type="text" value={title} onChange={(e) => onTitleChange(e.target.value)}
                            placeholder="e.g. DBMS Lecture"
                            className="bg-black/40 border border-white/10 text-xs text-foreground p-2 rounded focus:outline-none focus:border-[var(--cyan)] transition animate-none" />
                    </div>
                    <div className="flex flex-col gap-1.5">
                        <label className="text-[10px] uppercase font-bold tracking-[0.2em] text-muted-foreground">Description</label>
                        <input type="text" value={desc} onChange={(e) => onDescChange(e.target.value)}
                            placeholder="e.g. Work on Spring Boot"
                            className="bg-black/40 border border-white/10 text-xs text-foreground p-2 rounded focus:outline-none focus:border-[var(--cyan)] transition animate-none" />
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                        <div className="flex flex-col gap-1.5">
                            <label className="text-[10px] uppercase font-bold tracking-[0.2em] text-muted-foreground">Date</label>
                            <input type="date" value={date} onChange={(e) => onDateChange(e.target.value)}
                                className="bg-black/40 border border-white/10 text-xs text-foreground p-2 rounded focus:outline-none focus:border-[var(--cyan)] cursor-pointer transition animate-none" />
                        </div>
                        <div className="flex flex-col gap-1.5">
                            <label className="text-[10px] uppercase font-bold tracking-[0.2em] text-muted-foreground">Time</label>
                            <input type="time" value={time} onChange={(e) => onTimeChange(e.target.value)}
                                className="bg-black/40 border border-white/10 text-xs text-foreground p-2 rounded focus:outline-none focus:border-[var(--cyan)] cursor-pointer transition animate-none" />
                        </div>
                    </div>
                    <div className="flex items-center gap-2.5 mt-1 cursor-pointer" onClick={onReminderToggle}>
                        <div className={cn("h-4 w-4 border rounded flex items-center justify-center transition-colors", reminder ? "bg-[var(--cyan)] border-[var(--cyan)]" : "border-white/20")}>
                            {reminder && <Check className="h-3 w-3 text-black" strokeWidth={3} />}
                        </div>
                        <span className="text-[11px] font-medium text-muted-foreground select-none">Remind me 15m before start</span>
                    </div>
                </div>
                <div className="flex gap-2 justify-end mt-2">
                    <button onClick={onClose}
                        className="px-4 py-2 rounded text-[11px] font-bold uppercase border border-white/10 text-muted-foreground hover:bg-white/5 cursor-pointer transition">
                        Cancel
                    </button>
                    <button onClick={onConfirm}
                        className="px-4 py-2 rounded text-[11px] font-bold uppercase bg-gradient-to-r from-[var(--cyan)] to-[var(--violet)] text-primary-foreground shadow-[0_0_15px_oklch(0.75_0.22_225/0.3)] hover:scale-[1.02] cursor-pointer transition">
                        Save Task
                    </button>
                </div>
            </div>
        </div>
    );
});

/* ---- View All Modal ---- */
interface ViewAllModalProps {
    tasks: Task[];
    onToggleReminder: (id: number) => void;
    onDeleteTask: (id: number) => void;
    onEditTask: (task: Task) => void;
    onClose: () => void;
}

export const ViewAllModal = React.memo(function ViewAllModal({
    tasks, onToggleReminder, onDeleteTask, onEditTask, onClose,
}: ViewAllModalProps) {
    return (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-md select-none animate-fade-in p-4">
            <div className="glass-panel w-full max-w-md p-6 border border-white/10 flex flex-col gap-4 max-h-[80vh] shadow-2xl relative">
                <div className="flex items-center justify-between border-b border-white/5 pb-2">
                    <h3 className="text-xs font-black tracking-[0.2em] uppercase text-gradient-cyber">Active Reminders</h3>
                    <button onClick={onClose} className="text-muted-foreground hover:text-rose-400 no-drag p-1 rounded hover:bg-white/5 cursor-pointer">
                        <X className="h-4 w-4" />
                    </button>
                </div>
                <div className="flex-1 overflow-y-auto flex flex-col gap-2.5 pr-1 mt-2">
                    {tasks.length === 0 ? (
                        <div className="text-center text-xs text-muted-foreground font-mono py-12">No active reminders scheduled.</div>
                    ) : (
                        tasks.map((t) => (
                            <div key={t.id} className="glass-panel p-3.5 flex items-center gap-3.5 border border-white/5 bg-white/[0.01] hover:bg-white/[0.03] transition duration-300">
                                <div className={`grid h-9 w-9 place-items-center rounded bg-white/5 ${t.color || "text-[var(--cyan)]"}`}>
                                    <CalendarDays className="h-4 w-4" />
                                </div>
                                <div className="flex flex-col flex-1 leading-tight">
                                    <span className="text-xs font-bold text-foreground">{t.title}</span>
                                    <span className="text-[10px] text-muted-foreground mt-0.5">{t.desc}</span>
                                    <span className="text-[9px] text-[var(--cyan)] font-semibold font-mono tracking-wider mt-1.5 uppercase">
                                        {t.when} at {t.time}
                                    </span>
                                </div>
                                <div className="flex items-center gap-1">
                                    <button onClick={() => onToggleReminder(t.id)} className="p-1.5 rounded hover:bg-white/5 cursor-pointer" title="Toggle Alert Notification">
                                        <BellRing className={cn("h-4 w-4 transition", t.reminderActive ? "text-[var(--cyan)] animate-glow-pulse" : "text-muted-foreground hover:text-foreground")} />
                                    </button>
                                    <button onClick={() => onEditTask(t)} className="p-1.5 rounded hover:bg-white/5 text-muted-foreground hover:text-[var(--cyan)] cursor-pointer" title="Edit Reminder">
                                        <Pencil className="h-4 w-4" />
                                    </button>
                                    <button onClick={() => onDeleteTask(t.id)} className="p-1.5 rounded hover:bg-white/5 text-muted-foreground hover:text-rose-500 cursor-pointer" title="Delete Reminder">
                                        <X className="h-4 w-4" />
                                    </button>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
});
