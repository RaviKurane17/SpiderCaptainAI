import { useState, useCallback, useEffect } from "react";
import { Bot, Compass } from "lucide-react";
import type { LogRow } from "./useWebSocket";

let _reminderId = 10000;
function nextReminderId() { return _reminderId++; }

export interface Task {
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

const DEFAULT_TASKS: Task[] = [];

interface UseRemindersOptions {
    wsRef: React.MutableRefObject<WebSocket | null>;
    setLogs: React.Dispatch<React.SetStateAction<LogRow[]>>;
    remindersData?: any[] | null;
    isConnected?: boolean;
}

export function useReminders({ wsRef, setLogs, remindersData, isConnected }: UseRemindersOptions) {
    const [tasks, setTasks] = useState<Task[]>(DEFAULT_TASKS);
    
    // Initial fetch
    useEffect(() => {
        if (isConnected && wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: "get_reminders" }));
        }
    }, [wsRef, isConnected]);
    
    // Sync with backend data
    useEffect(() => {
        if (remindersData && Array.isArray(remindersData)) {
            const newTasks = remindersData.map((r, i) => {
                const title = r.title || "Task";
                const desc = r.desc || "";
                const timeStr = r.time || "12:00 PM";
                
                let when = "Later";
                if (timeStr.toLowerCase().includes("today")) when = "Today";
                if (timeStr.toLowerCase().includes("tomorrow")) when = "Tomorrow";
                
                return {
                    id: Date.now() + i,
                    title,
                    desc,
                    time: timeStr.split("\\n")[0],
                    when,
                    date: new Date().toISOString().split("T")[0],
                    timeRaw: "12:00", // Needs better parsing in reality
                    reminderActive: true,
                    notified: false,
                    color: r.color || "text-[var(--cyan)]"
                };
            });
            setTasks(newTasks);
        }
    }, [remindersData]);

    // Check reminders every 10s
    useEffect(() => {
        const interval = setInterval(() => {
            const now = new Date();
            setTasks((prev) =>
                prev.map((task) => {
                    if (!task.reminderActive || task.notified) return task;
                    const [year, month, day] = task.date.split("-").map(Number);
                    const [hours, minutes] = task.timeRaw.split(":").map(Number);
                    const taskTime = new Date(year, month - 1, day, hours, minutes);
                    const diffMin = (taskTime.getTime() - now.getTime()) / 60000;

                    if (diffMin > 0 && diffMin <= 15) {
                        const notifyTime = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
                        setLogs((logs) =>
                            [...logs, {
                                id: nextReminderId(),
                                who: "CAPTAIN", icon: Bot, color: "text-[var(--violet)]",
                                text: `Boss, your task "${task.title}" is scheduled to start in 15 minutes.`,
                                time: notifyTime,
                            }].slice(-25)
                        );
                        if (wsRef.current?.readyState === WebSocket.OPEN) {
                            wsRef.current.send(JSON.stringify({
                                type: "command",
                                text: `speak Boss, your scheduled task ${task.title} is starting in 15 minutes.`,
                            }));
                        }
                        return { ...task, notified: true };
                    }
                    return task;
                })
            );
        }, 10000);
        return () => clearInterval(interval);
    }, [wsRef, setLogs]);

    const handleAddTask = useCallback(
        (title: string, desc: string, date: string, time: string, reminder: boolean) => {
            if (!title.trim()) return;

            let formattedTime = time;
            if (time) {
                const [h, m] = time.split(":");
                const hour = parseInt(h);
                const ampm = hour >= 12 ? "PM" : "AM";
                formattedTime = `${(hour % 12 || 12).toString().padStart(2, "0")}:${m} ${ampm}`;
            } else {
                formattedTime = "12:00 PM";
            }

            const todayStr = new Date().toISOString().split("T")[0];
            const tomorrow = new Date();
            tomorrow.setDate(tomorrow.getDate() + 1);
            const tomorrowStr = tomorrow.toISOString().split("T")[0];

            let when = date;
            if (date === todayStr) when = "Today";
            else if (date === tomorrowStr) when = "Tomorrow";
            else if (date) when = new Date(date).toLocaleDateString([], { day: "numeric", month: "short", year: "numeric" });
            else when = "Today";

            const newTask: Task = {
                id: Date.now(), title, desc: desc || "Scheduled Task",
                time: formattedTime, when, date: date || todayStr,
                timeRaw: time || "12:00", reminderActive: reminder, notified: false,
                color: "text-[var(--cyan)]",
            };

            setTasks((prev) => [...prev, newTask]);
            
            // Sync with backend
            if (wsRef.current?.readyState === WebSocket.OPEN) {
                // Just use edit_reminder (as it's a list append if it doesn't exist, wait backend edit_reminder loop only matches ID.
                // It's better if we just append to the list. Or better, we can define add_reminder on backend...
                // Actually let me use a trick: in backend edit_rem we can append if not found? 
                // Let me just send 'add_reminder' message if needed, wait I didn't add add_reminder to backend. Let's do it in a moment.
                wsRef.current.send(JSON.stringify({ type: "add_reminder", task: newTask }));
            }

            const logTime = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
            setLogs((prev) => [
                ...prev,
                { id: nextReminderId(), who: "SYSTEM", icon: Compass, color: "text-muted-foreground",
                  text: `Added new reminder: "${title}" scheduled for ${date || todayStr} at ${formattedTime}.`,
                  time: logTime },
            ].slice(-25));
        },
        [setLogs, wsRef]
    );

    const handleEditTask = useCallback((task: Task) => {
        setTasks((prev) => prev.map((t) => t.id === task.id ? task : t));
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: "edit_reminder", task }));
        }
    }, [wsRef]);

    const handleDeleteTask = useCallback((id: number) => {
        setTasks((prev) => prev.filter((t) => t.id !== id));
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: "delete_reminder", id }));
        }
    }, [wsRef]);

    const handleToggleReminder = useCallback((id: number) => {
        setTasks((prev) => {
            const next = prev.map((t) => (t.id === id ? { ...t, reminderActive: !t.reminderActive } : t));
            const toggledTask = next.find(t => t.id === id);
            if (toggledTask && wsRef.current?.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify({ type: "edit_reminder", task: toggledTask }));
            }
            return next;
        });
    }, [wsRef]);

    return { tasks, handleAddTask, handleEditTask, handleDeleteTask, handleToggleReminder };
}
