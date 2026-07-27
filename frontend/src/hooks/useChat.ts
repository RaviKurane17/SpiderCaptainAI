import { useState, useEffect, useCallback, useRef } from 'react';

export interface ChatSession {
    id: string;
    title: string;
    is_pinned: boolean;
    created_at: number;
    updated_at: number;
}

export interface ChatMessage {
    id?: number;
    role: "user" | "ai" | "system" | "error" | "tool_execution" | "memory_suggestion";
    content: string; // If role is tool_execution or memory_suggestion, this is JSON stringified data
    tokens?: number;
    latency?: number;
    timestamp: number;
}

export function useChat(wsRef: React.MutableRefObject<WebSocket | null>) {
    const [sessions, setSessions] = useState<ChatSession[]>([]);
    const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [isGenerating, setIsGenerating] = useState(false);

    // Initial fetch
    useEffect(() => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: "get_chat_sessions" }));
        }

        const handleMessage = (e: MessageEvent) => {
            try {
                const data = JSON.parse(e.data);
                
                if (data.type === "chat_sessions_data") {
                    setSessions(data.sessions);
                    // If no active session, pick the most recent one or wait for create
                    if (!activeSessionId && data.sessions.length > 0) {
                        loadSession(data.sessions[0].id);
                    }
                } else if (data.type === "chat_messages_data") {
                    if (data.session_id === activeSessionId) {
                        setMessages(data.messages);
                    }
                } else if (data.type === "chat_action_result") {
                    // refresh sessions
                    if (wsRef.current) wsRef.current.send(JSON.stringify({ type: "get_chat_sessions" }));
                } else if (data.type === "new_chat_message") {
                    // This is pushed live from the server
                    if (data.session_id === activeSessionId) {
                        setMessages(prev => [...prev, data.message]);
                        if (data.message.role === "ai") {
                            setIsGenerating(false);
                        }
                    }
                } else if (data.type === "tool_execution") {
                    if (data.session_id === activeSessionId) {
                        setMessages(prev => {
                            const newMsgs = [...prev];
                            // Find existing tool execution block for this tool if it's currently running
                            const existingIdx = newMsgs.findIndex(m => 
                                m.role === "tool_execution" && 
                                JSON.parse(m.content).tool_name === data.tool_name &&
                                JSON.parse(m.content).status === "running"
                            );
                            
                            const toolData = {
                                tool_name: data.tool_name,
                                status: data.status,
                                duration: data.duration,
                                error: data.error
                            };

                            if (existingIdx >= 0) {
                                newMsgs[existingIdx].content = JSON.stringify(toolData);
                            } else {
                                newMsgs.push({
                                    role: "tool_execution",
                                    content: JSON.stringify(toolData),
                                    timestamp: Date.now() / 1000
                                });
                            }
                            return newMsgs;
                        });
                    }
                } else if (data.type === "memory_suggestion") {
                    if (activeSessionId) {
                        setMessages(prev => [...prev, {
                            role: "memory_suggestion",
                            content: JSON.stringify({
                                title: data.title,
                                summary: data.summary,
                                category: data.category
                            }),
                            timestamp: Date.now() / 1000
                        }]);
                    }
                }
            } catch (err) {}
        };

        if (wsRef.current) {
            wsRef.current.addEventListener("message", handleMessage);
        }
        return () => wsRef.current?.removeEventListener("message", handleMessage);
    }, [wsRef, activeSessionId]);

    const loadSession = useCallback((sessionId: string) => {
        setActiveSessionId(sessionId);
        setMessages([]); // clear current
        if (wsRef.current) {
            wsRef.current.send(JSON.stringify({ type: "get_chat_messages", session_id: sessionId }));
        }
    }, [wsRef]);

    const createNewSession = useCallback(() => {
        const newId = "chat_" + Date.now();
        if (wsRef.current) {
            wsRef.current.send(JSON.stringify({ type: "create_chat_session", session_id: newId, title: "New Conversation" }));
            loadSession(newId);
        }
    }, [wsRef, loadSession]);

    const sendMessage = useCallback((text: string) => {
        if (!wsRef.current || !activeSessionId || !text.trim()) return;
        setIsGenerating(true);
        wsRef.current.send(JSON.stringify({
            type: "send_chat_message",
            session_id: activeSessionId,
            text: text
        }));
        
        // Optimistically add user message (server will also broadcast it but this feels faster)
        setMessages(prev => [...prev, {
            role: "user",
            content: text,
            timestamp: Date.now() / 1000
        }]);
    }, [wsRef, activeSessionId]);

    const togglePin = useCallback((sessionId: string, isPinned: boolean) => {
        if (wsRef.current) {
            wsRef.current.send(JSON.stringify({
                type: "toggle_pin_session",
                session_id: sessionId,
                is_pinned: isPinned
            }));
        }
    }, [wsRef]);

    const deleteSession = useCallback((sessionId: string) => {
        if (wsRef.current) {
            wsRef.current.send(JSON.stringify({
                type: "delete_chat_session",
                session_id: sessionId
            }));
            if (activeSessionId === sessionId) {
                setActiveSessionId(null);
                setMessages([]);
            }
        }
    }, [wsRef, activeSessionId]);

    return {
        sessions,
        activeSessionId,
        messages,
        isGenerating,
        loadSession,
        createNewSession,
        sendMessage,
        togglePin,
        deleteSession
    };
}
