import { useEffect, useRef, useState, useCallback } from "react";
import { Bot, User, Compass } from "lucide-react";

export interface LogRow {
    id: number;          // stable unique id — use as React key
    who: string;
    icon: React.ElementType;
    color: string;
    text: string;
    time: string;
    done?: boolean;
}

export interface Metrics {
    cpu: number;
    ram: number;
    gpu: number;
    disk: number;
    uptime: string;
    processes: string;
    threads: string;
    network: string;
}

const DEFAULT_METRICS: Metrics = {
    cpu: 35, ram: 64, gpu: 0, disk: 58,
    uptime: "0h 0m 0s", processes: "0", threads: "0", network: "↓ 0 KB/s   ↑ 0 KB/s",
};

const WS_URL   = "ws://127.0.0.1:8765";
const MAX_LOGS = 25;

let _logIdCounter = 1;
function nextId() { return _logIdCounter++; }

export function useWebSocket() {
    const [isConnected,  setIsConnected]  = useState(false);
    const [isMuted,      setIsMuted]      = useState(false);
    const [isVolumeMuted,setIsVolumeMuted]= useState(false);
    const [aiState,      setAiState]      = useState("LISTENING");
    const [metrics,      setMetrics]      = useState<Metrics>(DEFAULT_METRICS);
    const [latency,      setLatency]      = useState<number>(0);
    const [navigatePage, setNavigatePage] = useState<string | null>(null);
    const [remindersData,setRemindersData]= useState<any[] | null>(null);
    const [logs,         setLogs]         = useState<LogRow[]>([]);
    const [lastMessage,  setLastMessage]  = useState<any>(null);
    const [setupComplete, setSetupComplete] = useState<boolean | null>(null);
    const wsRef = useRef<WebSocket | null>(null);

    // When the frontend sends a command, we lock state to THINKING until
    // the backend explicitly transitions to SPEAKING or back to LISTENING.
    // This prevents the WS reconnect handshake from flashing LISTENING
    // while Gemini is still processing the request.
    const awaitingResponseRef = useRef(false);
    // Safety-net: if no state transition arrives within this many ms after a
    // command is sent (backend crash / timeout / silent completion), auto-reset
    // back to LISTENING so the UI never stays stuck on THINKING.
    const thinkingTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const THINKING_TIMEOUT_MS = 30_000; // 30 s

    // Dedup guard: track the last log entry to prevent identical messages
    // arriving within 500 ms (e.g. frontend optimistic + backend echo).
    const lastLogRef = useRef<{ who: string; text: string; ts: number }>({
        who: "", text: "", ts: 0,
    });

    const appendLog = useCallback((row: Omit<LogRow, "id">) => {
        const now = Date.now();
        const last = lastLogRef.current;
        // Drop if same who+text within 500 ms
        if (
            last.who === row.who &&
            last.text === row.text &&
            now - last.ts < 500
        ) {
            return;
        }
        lastLogRef.current = { who: row.who, text: row.text, ts: now };
        setLogs((prev) => [...prev, { ...row, id: nextId() }].slice(-MAX_LOGS));
    }, []);

    useEffect(() => {
        const now = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        setLogs([{
            id: nextId(), who: "SYSTEM", icon: Compass,
            color: "text-muted-foreground",
            text: "Captain AI Dashboard loaded.", time: now,
        }]);

        let socket: WebSocket;
        let reconnectTimer: ReturnType<typeof setTimeout>;

        function connect() {
            socket = new WebSocket(WS_URL);
            wsRef.current = socket;

            socket.onopen = () => {
                setIsConnected(true);
                // Immediately ask for settings to determine setup state
                socket.send(JSON.stringify({ type: 'get_all_settings' }));
                
                // Ping interval
                const pingInterval = setInterval(() => {
                    if (socket.readyState === WebSocket.OPEN) {
                        socket.send(JSON.stringify({ type: "ping", timestamp: Date.now() }));
                    }
                }, 2000);
                
                // Attach interval to socket object for cleanup
                (socket as any)._pingInterval = pingInterval;
            };

            socket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data as string);
                    setLastMessage(data);
                    const type = data.type;

                    if (type === "metrics") {
                        setMetrics({
                            cpu: data.cpu,       ram: data.ram,
                            gpu: data.gpu,       disk: data.disk,
                            uptime: data.uptime, processes: data.processes,
                            threads: data.threads, network: data.network,
                        });
                    } else if (type === "state") {
                        const newState: string = data.state;
                        // If we're waiting for a response (THINKING), only allow
                        // transitions to SPEAKING (Gemini started talking) or
                        // LISTENING (turn completed cleanly). Block spurious
                        // LISTENING from WS reconnect handshake.
                        if (awaitingResponseRef.current) {
                            if (newState === "SPEAKING" || newState === "LISTENING") {
                                awaitingResponseRef.current = false;
                                // Clear the safety-net timeout — backend responded in time
                                if (thinkingTimeoutRef.current !== null) {
                                    clearTimeout(thinkingTimeoutRef.current);
                                    thinkingTimeoutRef.current = null;
                                }
                                setAiState(newState);
                            }
                            // ignore any other state while awaiting (e.g. reconnect LISTENING flash)
                        } else {
                            setAiState(newState);
                        }
                    } else if (type === "muted") {
                        setIsMuted(data.muted);
                    } else if (type === "volume_muted") {
                        setIsVolumeMuted(data.muted);
                    } else if (type === "log") {
                        const entry = data.log;
                        if (!entry) return;
                        const who: string = entry.who;
                        appendLog({
                            who,
                            icon:  who === "YOU" ? User : who === "CAPTAIN" ? Bot : Compass,
                            color: who === "YOU"
                                ? "text-[var(--cyan)]"
                                : who === "CAPTAIN"
                                ? "text-[var(--violet)]"
                                : "text-muted-foreground",
                            text: entry.text,
                            time: entry.time,
                            done: who === "CAPTAIN" && (entry.text as string).includes("Done"),
                        });
                    } else if (type === "all_settings_data") {
                        if (data.settings && data.settings.setup_complete !== undefined) {
                            setSetupComplete(data.settings.setup_complete);
                        } else {
                            setSetupComplete(true); // Fallback if missing
                        }
                    } else if (type === "pong") {
                        const rtt = Date.now() - (data.timestamp || Date.now());
                        setLatency(Math.max(1, Math.round(rtt)));
                    } else if (type === "navigate") {
                        if (data.page) {
                            setNavigatePage(data.page);
                        }
                    } else if (type === "reminders_data") {
                        setRemindersData(data.data);
                    }
                } catch {
                    // malformed packet — ignore
                }
            };

            socket.onclose = () => {
                setIsConnected(false);
                setLatency(0);
                if ((socket as any)._pingInterval) {
                    clearInterval((socket as any)._pingInterval);
                }
                reconnectTimer = setTimeout(connect, 3000);
            };

            socket.onerror = () => socket.close();
        }

        connect();
        return () => {
            if (socket && (socket as any)._pingInterval) {
                clearInterval((socket as any)._pingInterval);
            }
            socket?.close();
            clearTimeout(reconnectTimer);
            if (thinkingTimeoutRef.current !== null) {
                clearTimeout(thinkingTimeoutRef.current);
            }
        };
    }, [appendLog]);

    const sendCommand = useCallback((payload: object) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify(payload));
        }
    }, []);

    const handleSendCommand = useCallback(
        (text: string) => {
            if (!text.trim()) return;
            sendCommand({ type: "command", text });

            // Add the "YOU" row immediately (optimistic) — backend will NOT echo it back.
            const now = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
            appendLog({
                who: "YOU", icon: User, color: "text-[var(--cyan)]",
                text, time: now,
            });

            // Lock state to THINKING — block any spurious LISTENING from
            // WS reconnect handshake until we get SPEAKING or LISTENING
            // from the actual Gemini response.
            awaitingResponseRef.current = true;
            setAiState("THINKING");

            // Safety-net: if the backend never sends a state transition, reset
            // back to LISTENING after the timeout so the UI doesn't stay frozen.
            if (thinkingTimeoutRef.current !== null) {
                clearTimeout(thinkingTimeoutRef.current);
            }
            thinkingTimeoutRef.current = setTimeout(() => {
                if (awaitingResponseRef.current) {
                    awaitingResponseRef.current = false;
                    thinkingTimeoutRef.current = null;
                    setAiState("LISTENING");
                }
            }, THINKING_TIMEOUT_MS);
        },
        [sendCommand, appendLog]
    );

    const handleMicToggle = useCallback(() => {
        sendCommand({ type: "mic_toggle" });
        setIsMuted((prev) => !prev);
    }, [sendCommand]);

    const handleVolumeToggle = useCallback(() => {
        setIsVolumeMuted((prev) => !prev);
        sendCommand({ type: "volume_toggle" });
    }, [sendCommand]);

    const handleBrightnessToggle = useCallback(() => {
        sendCommand({ type: "brightness_toggle" });
    }, [sendCommand]);

    const handlePowerClick = useCallback(() => {
        setTimeout(() => sendCommand({ type: "power_click" }), 5000);
    }, [sendCommand]);

    return {
        isConnected, isMuted, isVolumeMuted, aiState, metrics, latency, navigatePage, remindersData, logs, lastMessage, setupComplete,
        wsRef, sendCommand, setNavigatePage,
        // expose appendLog as setLogs replacement for useReminders
        setLogs: useCallback(
            (updater: (prev: LogRow[]) => LogRow[]) => setLogs(updater),
            []
        ),
        handleSendCommand, handleMicToggle, handleVolumeToggle,
        handleBrightnessToggle, handlePowerClick,
    };
}
