import { createFileRoute } from "@tanstack/react-router";
import React, { lazy, Suspense, useState, useCallback, useMemo } from "react";
import { cn } from "@/lib/utils";
import { Power, Sun, Volume2, VolumeX, Home, Terminal, Folder, MessageSquare, Layers, Settings, Database } from "lucide-react";

// ── Eagerly loaded (always visible) ─────────────────────────────────────────
import TitleBar      from "../components/TitleBar";
import CoreCard      from "../components/CoreCard";
import IconBtn       from "../components/IconBtn";
import Header        from "../components/Header";
import Visualizer    from "../components/Visualizer";
import ActivityCard  from "../components/ActivityCard";
import Composer      from "../components/Composer";
import AiStatus      from "../components/AiStatus";
import SystemOverview from "../components/SystemOverview";
import CalendarPanel from "../components/CalendarPanel";
import { AddReminderModal, ViewAllModal } from "../components/ReminderModals";
import { SetupWizard } from "../components/ui/SetupWizard";
import { LockScreen } from "../components/ui/LockScreen";
import { DeveloperDiagnostics } from "../components/DeveloperDiagnostics";
import { StartupBanner } from "../components/StartupBanner";

// ── Lazily loaded panels (only when user navigates there) ────────────────────
const ChatPanel     = lazy(() => import("../components/panels/chat_panel").then((m) => ({ default: m.ChatPanel })));
const CommandsPanel = lazy(() => import("../components/panels/commands_panel").then((m) => ({ default: m.CommandsPanel })));
const FilesPanel    = lazy(() => import("../components/panels/files_panel").then((m) => ({ default: m.FilesPanel })));
const MemoryPanel   = lazy(() => import("../components/panels/memory_panel").then((m) => ({ default: m.MemoryPanel })));
const ToolsPanel    = lazy(() => import("../components/panels/tools_panel").then((m) => ({ default: m.ToolsPanel })));
const SettingsPanel = lazy(() => import("../components/panels/settings_panel").then((m) => ({ default: m.SettingsPanel })));

// ── Hooks ────────────────────────────────────────────────────────────────────
import { useWebSocket } from "../hooks/useWebSocket";
import { useReminders } from "../hooks/useReminders";

export const Route = createFileRoute("/")({
    component: CaptainAI,
});

type NavItem = { icon: React.ElementType; label: string; sub: string };

const NAV: NavItem[] = [
    { icon: Home,         label: "HOME",     sub: "Dashboard" },
    { icon: Terminal,     label: "COMMANDS", sub: "Quick Actions" },
    { icon: Folder,       label: "FILES",    sub: "File Explorer" },
    { icon: MessageSquare,label: "CHAT",     sub: "AI Conversation" },
    { icon: Database,     label: "MEMORY",   sub: "Knowledge Base" },
    { icon: Layers,       label: "TOOLS",    sub: "System Tools" },
    { icon: Settings,     label: "SETTINGS", sub: "Preferences" },
];

function PanelFallback() {
    return (
        <div className="flex h-full items-center justify-center text-xs text-muted-foreground tracking-widest animate-pulse">
            LOADING...
        </div>
    );
}

function CaptainAI() {
    const [activeTab, setActiveTab] = useState("HOME");
    const [brightness, setBrightness] = useState(100);
    const [isShuttingDown, setIsShuttingDown] = useState(false);
    const [showStartup, setShowStartup] = useState(true);
    
    // Lock screen states
    const [isLocked, setIsLocked] = useState(false);
    const [lockType, setLockType] = useState("");
    
    // Developer Diagnostics Panel
    const [showDiagnostics, setShowDiagnostics] = useState(false);

    React.useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            // Toggle Developer Diagnostics with Ctrl + Shift + D
            if (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === 'd') {
                e.preventDefault();
                setShowDiagnostics((prev) => !prev);
            }
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, []);

    React.useEffect(() => {
        if (showStartup) {
            const audioTimer = setTimeout(() => {
                const audio = new Audio('/startupvoice.wav');
                audio.playbackRate = 0.85;
                audio.play().catch(e => console.log('Audio play failed:', e));
            }, 1000);

            const t = setTimeout(() => {
                setShowStartup(false);
            }, 4000);

            return () => {
                clearTimeout(t);
                clearTimeout(audioTimer);
            };
        }
    }, [showStartup]);

    // Add-reminder modal state
    const [showAddModal, setShowAddModal] = useState(false);
    const [showAllModal, setShowAllModal] = useState(false);
    const [newTaskTitle, setNewTaskTitle] = useState("");
    const [newTaskDesc,  setNewTaskDesc]  = useState("");
    const [newTaskDate,  setNewTaskDate]  = useState("");
    const [newTaskTime,  setNewTaskTime]  = useState("");
    const [newTaskReminder, setNewTaskReminder] = useState(true);
    const [editingTaskId, setEditingTaskId] = useState<number | null>(null);

    const {
        isConnected, isMuted, isVolumeMuted, aiState, metrics, latency, navigatePage, setNavigatePage, remindersData, logs, diagnostics, startupState,
        wsRef, setLogs, setupComplete, initialSettings,
        handleSendCommand, handleMicToggle, handleVolumeToggle,
        handleBrightnessToggle: _brightnessWS, handlePowerClick: _powerWS,
    } = useWebSocket();

    // Check lock state when settings are received
    React.useEffect(() => {
        if (initialSettings) {
            if (initialSettings.security_lock_on_startup && 
                initialSettings.security_lock_type && 
                initialSettings.security_lock_type !== "No Lock") {
                setIsLocked(true);
                setLockType(initialSettings.security_lock_type);
            }
        }
    }, [initialSettings]);

    const { tasks, handleAddTask, handleEditTask, handleDeleteTask, handleToggleReminder } = useReminders({ wsRef, setLogs, remindersData, isConnected });

    React.useEffect(() => {
        if (navigatePage) {
            setActiveTab(navigatePage);
            setNavigatePage(null);
        }
    }, [navigatePage, setNavigatePage]);

    const handleBrightnessToggle = useCallback(() => {
        setBrightness((prev) => (prev === 100 ? 60 : prev === 60 ? 30 : 100));
        _brightnessWS();
    }, [_brightnessWS]);

    const handlePowerClick = useCallback(() => {
        setIsShuttingDown(true);
        _powerWS();
    }, [_powerWS]);

    const handleAddClick    = useCallback(() => {
        setEditingTaskId(null);
        setNewTaskTitle(""); setNewTaskDesc(""); setNewTaskDate(""); setNewTaskTime(""); setNewTaskReminder(true);
        setShowAddModal(true);
    },  []);
    const handleViewAllClick = useCallback(() => setShowAllModal(true), []);
    
    const handleEditTaskClick = useCallback((task: any) => {
        setEditingTaskId(task.id);
        setNewTaskTitle(task.title);
        setNewTaskDesc(task.desc);
        setNewTaskDate(task.date);
        
        let tTime = task.timeRaw || "12:00";
        if (tTime.includes("AM") || tTime.includes("PM")) {
            // try to parse if it's display time
            const [timeStr, modifier] = tTime.split(" ");
            let [hours, minutes] = timeStr.split(":");
            if (hours === "12") hours = "00";
            if (modifier === "PM") hours = (parseInt(hours, 10) + 12).toString();
            tTime = `${hours.padStart(2, "0")}:${minutes}`;
        }
        setNewTaskTime(tTime);
        setNewTaskReminder(task.reminderActive);
        setShowAllModal(false);
        setShowAddModal(true);
    }, []);

    const handleConfirmAdd = useCallback(() => {
        if (editingTaskId !== null) {
            let formattedTime = newTaskTime;
            if (newTaskTime) {
                const [h, m] = newTaskTime.split(":");
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
            
            let when = newTaskDate;
            if (newTaskDate === todayStr) when = "Today";
            else if (newTaskDate === tomorrowStr) when = "Tomorrow";
            else if (newTaskDate) when = new Date(newTaskDate).toLocaleDateString([], { day: "numeric", month: "short", year: "numeric" });
            else when = "Today";

            handleEditTask({
                id: editingTaskId,
                title: newTaskTitle,
                desc: newTaskDesc,
                date: newTaskDate || todayStr,
                time: formattedTime,
                timeRaw: newTaskTime || "12:00",
                when: when,
                reminderActive: newTaskReminder,
                notified: false,
                color: "text-[var(--cyan)]"
            });
        } else {
            handleAddTask(newTaskTitle, newTaskDesc, newTaskDate, newTaskTime, newTaskReminder);
        }
        setShowAddModal(false);
        setNewTaskTitle(""); setNewTaskDesc(""); setNewTaskDate(""); setNewTaskTime(""); setNewTaskReminder(true);
        setEditingTaskId(null);
    }, [handleAddTask, handleEditTask, editingTaskId, newTaskTitle, newTaskDesc, newTaskDate, newTaskTime, newTaskReminder]);

    const isMainTab = activeTab === "HOME" || activeTab === "CHAT";

    const gridClass = useMemo(
        () =>
            `grid h-full w-full gap-3 transition-all duration-300 ${
                isMainTab && activeTab === "HOME"
                    ? "grid-cols-[240px_1fr_320px]"
                    : "grid-cols-[240px_1fr]"
            }`,
        [isMainTab, activeTab]
    );

    if (setupComplete === false) {
        return <SetupWizard />;
    }

    return (
        <div className="relative z-10 h-screen w-screen overflow-hidden p-3 font-sans bg-black">
            {showStartup && (
                <div className="absolute inset-0 z-[9999] flex items-center justify-center bg-black/60 backdrop-blur-sm">
                    <video src="/startvid.mp4" autoPlay playsInline className="w-full h-full object-cover mix-blend-screen opacity-90" />
                </div>
            )}
            
            {isLocked && !showStartup && (
                <LockScreen onUnlock={() => setIsLocked(false)} wsRef={wsRef} lockType={lockType} />
            )}

            <div className={gridClass}>
                {/* ── SIDEBAR ──────────────────────────────────────────── */}
                <aside className="flex min-h-0 flex-col gap-3">
                    <TitleBar />
                    <nav className="glass-panel flex flex-col flex-1 min-h-0 p-2 justify-between">
                        {NAV.map((n) => (
                            <div
                                key={n.label}
                                onClick={() => setActiveTab(n.label)}
                                className={activeTab === n.label ? "nav-item nav-item-active cursor-pointer" : "nav-item cursor-pointer"}
                            >
                                <n.icon className="h-4 w-4" strokeWidth={1.6} />
                                <div className="flex flex-col">
                                    <span className="text-[12px] font-semibold tracking-[0.14em]">{n.label}</span>
                                    <span className="text-[10px] text-muted-foreground">{n.sub}</span>
                                </div>
                            </div>
                        ))}
                    </nav>
                    <div className="mt-auto flex flex-col gap-2">
                        <CoreCard />
                        <div className="glass-panel flex items-center justify-around p-1.5">
                            <IconBtn onClick={handleVolumeToggle}>
                                {isVolumeMuted
                                    ? <VolumeX className="h-4 w-4 text-[var(--rose)]" strokeWidth={1.6} />
                                    : <Volume2 className="h-4 w-4" strokeWidth={1.6} />}
                            </IconBtn>
                            <IconBtn onClick={handleBrightnessToggle}>
                                <Sun className="h-4 w-4" strokeWidth={1.6} />
                            </IconBtn>
                            <IconBtn onClick={handlePowerClick}>
                                <Power className="h-4 w-4" strokeWidth={1.6} />
                            </IconBtn>
                        </div>
                    </div>
                </aside>

                {/* ── CONTENT ──────────────────────────────────────────── */}
                {activeTab === "HOME" && (
                    <>
                        <main className="flex min-h-0 flex-col gap-3 animate-fade-in">
                            <Header isConnected={isConnected} latency={latency} />
                            <section className="glass-panel relative flex min-h-0 flex-1 flex-col items-center gap-3 p-4 overflow-hidden">
                                <div className="relative z-10 flex min-h-0 flex-1 w-full items-center justify-center">
                                    <Visualizer aiState={aiState} />
                                </div>
                                <ActivityCard rows={logs} onCommand={handleSendCommand} />
                                <Composer isMuted={isMuted} onMicToggle={handleMicToggle} onSend={handleSendCommand} />
                            </section>
                        </main>
                        <aside className="flex min-h-0 flex-col gap-3 overflow-hidden h-full animate-fade-in">
                            <AiStatus aiState={aiState} isMuted={isMuted} tasks={tasks} />
                            <SystemOverview metrics={metrics} />
                            <CalendarPanel
                                className="flex-1 min-h-0"
                                tasks={tasks}
                                onAddClick={handleAddClick}
                                onViewAllClick={handleViewAllClick}
                                onToggleReminder={handleToggleReminder}
                            />
                        </aside>
                    </>
                )}

                {activeTab === "CHAT" && (
                    <div className="animate-fade-in h-full min-h-0">
                        <Suspense fallback={<PanelFallback />}>
                            <ChatPanel wsRef={wsRef} />
                        </Suspense>
                    </div>
                )}

                {activeTab === "COMMANDS" && (
                    <div className="animate-fade-in h-full min-h-0">
                        <Suspense fallback={<PanelFallback />}>
                            <CommandsPanel onSend={handleSendCommand} wsRef={wsRef} />
                        </Suspense>
                    </div>
                )}

                {activeTab === "FILES" && (
                    <div className="animate-fade-in h-full min-h-0">
                        <Suspense fallback={<PanelFallback />}>
                            <FilesPanel wsRef={wsRef} />
                        </Suspense>
                    </div>
                )}

                {activeTab === "MEMORY" && (
                    <div className="animate-fade-in h-full min-h-0">
                        <Suspense fallback={<PanelFallback />}>
                            <MemoryPanel wsRef={wsRef} />
                        </Suspense>
                    </div>
                )}

                {activeTab === "TOOLS" && (
                    <div className="animate-fade-in h-full min-h-0">
                        <Suspense fallback={<PanelFallback />}>
                            <ToolsPanel wsRef={wsRef} metrics={metrics} />
                        </Suspense>
                    </div>
                )}

                {activeTab === "SETTINGS" && (
                    <div className="animate-fade-in h-full min-h-0">
                        <Suspense fallback={<PanelFallback />}>
                            <SettingsPanel wsRef={wsRef} />
                        </Suspense>
                    </div>
                )}
            </div>

            {/* ── MODALS ───────────────────────────────────────────────── */}
            {showAddModal && (
                <AddReminderModal
                    title={newTaskTitle} desc={newTaskDesc}
                    date={newTaskDate}   time={newTaskTime}
                    reminder={newTaskReminder}
                    onTitleChange={setNewTaskTitle} onDescChange={setNewTaskDesc}
                    onDateChange={setNewTaskDate}   onTimeChange={setNewTaskTime}
                    onReminderToggle={() => setNewTaskReminder((r) => !r)}
                    onConfirm={handleConfirmAdd}
                    onClose={() => setShowAddModal(false)}
                />
            )}

            {showAllModal && (
                <ViewAllModal
                    tasks={tasks}
                    onToggleReminder={handleToggleReminder}
                    onDeleteTask={handleDeleteTask}
                    onEditTask={handleEditTaskClick}
                    onClose={() => setShowAllModal(false)}
                />
            )}

            {/* ── OVERLAYS ─────────────────────────────────────────────── */}
            <StartupBanner state={startupState} />

            {showDiagnostics && (
                <DeveloperDiagnostics 
                    data={diagnostics} 
                    onClose={() => setShowDiagnostics(false)} 
                />
            )}
            
            {brightness < 100 && (
                <div
                    className="pointer-events-none fixed inset-0 z-[9999] bg-black transition-opacity duration-300"
                    style={{ opacity: brightness === 60 ? 0.35 : 0.65 }}
                />
            )}

            {isShuttingDown && (
                <div className="fixed inset-0 z-[10000] flex flex-col items-center justify-center bg-black/60 backdrop-blur-md animate-fade-in select-none">
                    <video src="/endvid.mp4" autoPlay playsInline className="absolute inset-0 w-full h-full object-cover mix-blend-screen opacity-90 z-0" />
                    <div className="relative z-10 flex flex-col items-center justify-center">
                        <div className="relative flex h-20 w-20 items-center justify-center">
                            <span className="absolute inset-0 animate-ping rounded-full border-2 border-[var(--cyan)]/40" />
                            <Power className="h-8 w-8 text-[var(--cyan)] animate-pulse" />
                        </div>
                        <h2 className="mt-6 text-xl font-bold tracking-wider text-foreground text-center">SHUTTING DOWN</h2>
                        <p className="mt-2 text-sm text-muted-foreground text-center">Captain AI is closing...</p>
                    </div>
                </div>
            )}
        </div>
    );
}
