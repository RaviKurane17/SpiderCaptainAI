import { useState, useEffect, useCallback } from "react";

export interface Command {
    id: number;
    title: string;
    cmd: string;
    desc: string;
    category: string;
    icon: string;
    color: string;
    is_pinned: boolean;
    created_at: number;
}

export interface CommandHistory {
    id: number;
    cmd: string;
    status: string;
    latency: number;
    executed_at: number;
}

export function useCommands(wsRef: React.MutableRefObject<WebSocket | null>) {
    const [commands, setCommands] = useState<Command[]>([]);
    const [history, setHistory] = useState<CommandHistory[]>([]);

    useEffect(() => {
        const ws = wsRef.current;
        if (!ws) return;

        const handleMessage = (e: MessageEvent) => {
            try {
                const msg = JSON.parse(e.data);
                if (msg.type === "commands_data") {
                    setCommands(msg.data);
                } else if (msg.type === "command_history_data") {
                    setHistory(msg.data);
                }
            } catch (err) {
                console.error("Failed to parse message in useCommands", err);
            }
        };

        ws.addEventListener("message", handleMessage);
        
        // Fetch initial data
        if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: "get_commands" }));
            ws.send(JSON.stringify({ type: "get_command_history" }));
        }

        return () => {
            ws.removeEventListener("message", handleMessage);
        };
    }, [wsRef]);

    const togglePin = useCallback((id: number, currentPinned: boolean) => {
        if (!wsRef.current) return;
        const newPinned = !currentPinned;
        
        // Optimistic UI update
        setCommands(prev => prev.map(c => c.id === id ? { ...c, is_pinned: newPinned } : c));
        
        wsRef.current.send(JSON.stringify({
            type: "toggle_pin_command",
            id: id,
            is_pinned: newPinned
        }));
    }, [wsRef]);

    const refreshHistory = useCallback(() => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: "get_command_history" }));
        }
    }, [wsRef]);

    return { commands, history, togglePin, refreshHistory };
}
