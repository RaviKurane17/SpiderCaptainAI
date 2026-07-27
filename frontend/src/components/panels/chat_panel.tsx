import React, { useState, useRef, useEffect } from "react";
import { 
    MessageSquare, Pin, PinOff, Plus, Search, Trash2, 
    MoreVertical, Send, Mic, Image as ImageIcon, Paperclip, 
    StopCircle, Activity, Clock
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { useChat, ChatSession, ChatMessage } from "../../hooks/useChat";
import { useKeyboardShortcuts } from "../../hooks/useShortcuts";
import { ToolExecutionCard, ToolExecutionData } from "../chat/ToolExecutionCard";
import { EmptyState } from "../chat/EmptyState";
import { ChatHeader } from "../chat/ChatHeader";
import { ChatComposer } from "../chat/ChatComposer";
import { ChatSidebar } from "../chat/ChatSidebar";
import { MemorySuggestionCard } from "../chat/MemorySuggestionCard";
import { cn } from "@/lib/utils";

// Assuming Shadcn exports
import {
    ContextMenu,
    ContextMenuContent,
    ContextMenuItem,
    ContextMenuSeparator,
    ContextMenuTrigger,
} from "@/components/ui/context-menu";

interface ChatPanelProps {
    wsRef: React.MutableRefObject<WebSocket | null>;
}

export const ChatPanel: React.FC<ChatPanelProps> = React.memo(({ wsRef }) => {
    const { 
        sessions, activeSessionId, messages, isGenerating,
        loadSession, createNewSession, sendMessage, togglePin, deleteSession
    } = useChat(wsRef);

    const [input, setInput] = useState("");
    const [searchQuery, setSearchQuery] = useState("");
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Auto scroll to bottom on new messages
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    // Keyboard shortcuts
    useKeyboardShortcuts({
        onNewChat: createNewSession,
        onSearchChat: () => {
            // Focus internal search bar
            const searchInput = document.getElementById("chat-search-input");
            if (searchInput) searchInput.focus();
        },
        onStopGeneration: () => {
            // TODO: implement hard stop if generating
        },
        onClearChat: () => {
            if (activeSessionId) deleteSession(activeSessionId);
        }
    });

    const handleSend = () => {
        if (!input.trim() || isGenerating) return;
        sendMessage(input);
        setInput("");
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const displaySessions = sessions.filter(s => s.title.toLowerCase().includes(searchQuery.toLowerCase()));
    return (
        <main className="flex min-h-0 h-full flex-col gap-3">
            <div className="flex flex-1 min-h-0 gap-3">
                
                {/* Sidebar: Chat History */}
                <ChatSidebar 
                    sessions={sessions}
                    activeSessionId={activeSessionId}
                    searchQuery={searchQuery}
                    setSearchQuery={setSearchQuery}
                    onNewChat={createNewSession}
                    onLoadSession={loadSession}
                    onTogglePin={togglePin}
                    onDeleteSession={deleteSession}
                />

                {/* Main Chat Interface */}
                <div className="flex-1 glass-panel flex flex-col overflow-hidden relative">
                    {/* Header */}
                    <ChatHeader 
                        isConnected={wsRef.current?.readyState === WebSocket.OPEN}
                        latency={42} // TODO: hook up to real latency state
                        modelName="Gemini 2.5 Flash"
                        workspaceName="Captain_AI_UI"
                    />

                    {/* Message Feed */}
                    <div className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-10 flex flex-col gap-6 custom-scrollbar">
                        {messages.length === 0 ? (
                            <EmptyState onActionClick={(prompt) => {
                                setInput(prompt);
                                // Optional: automatically send, or just populate the input
                            }} />
                        ) : (
                            messages.map((m, i) => {
                                if (m.role === "tool_execution") {
                                    return (
                                        <div key={i} className="flex w-full justify-start">
                                            <ToolExecutionCard data={JSON.parse(m.content) as ToolExecutionData} />
                                        </div>
                                    );
                                }
                                
                                if (m.role === "memory_suggestion") {
                                    const parsed = JSON.parse(m.content);
                                    return (
                                        <div key={i} className="flex w-full justify-start">
                                            <MemorySuggestionCard data={parsed} />
                                        </div>
                                    );
                                }
                                
                                return (
                                    <div key={i} className={cn("flex w-full", m.role === "user" ? "justify-end" : "justify-start")}>
                                    <div className={cn(
                                        "max-w-[85%] rounded-2xl p-4 shadow-xl border",
                                        m.role === "user" 
                                            ? "bg-white/10 border-white/10 text-white" 
                                            : m.role === "error"
                                                ? "bg-rose-500/10 border-rose-500/20 text-rose-200"
                                                : "bg-black/40 border-white/5 text-foreground backdrop-blur-md"
                                    )}>
                                        {m.role === "ai" ? (
                                            <div className="prose prose-invert prose-sm max-w-none 
                                                prose-p:leading-relaxed prose-pre:p-0 prose-pre:bg-transparent
                                                prose-code:text-[var(--cyan)] prose-code:bg-white/5 prose-code:px-1 prose-code:py-0.5 prose-code:rounded
                                            ">
                                                <ReactMarkdown
                                                    remarkPlugins={[remarkGfm]}
                                                    components={{
                                                        code({node, inline, className, children, ...props}: any) {
                                                            const match = /language-(\w+)/.exec(className || '')
                                                            return !inline && match ? (
                                                                <div className="rounded-lg overflow-hidden border border-white/10 my-4 shadow-2xl">
                                                                    <div className="bg-black/60 px-4 py-1.5 text-xs font-mono text-muted-foreground border-b border-white/10 flex justify-between items-center">
                                                                        {match[1]}
                                                                    </div>
                                                                    <SyntaxHighlighter
                                                                        {...props}
                                                                        style={vscDarkPlus as any}
                                                                        language={match[1]}
                                                                        PreTag="div"
                                                                        customStyle={{ margin: 0, background: 'rgba(0,0,0,0.4)', padding: '1rem' }}
                                                                    >
                                                                        {String(children).replace(/\n$/, '')}
                                                                    </SyntaxHighlighter>
                                                                </div>
                                                            ) : (
                                                                <code {...props} className={className}>
                                                                    {children}
                                                                </code>
                                                            )
                                                        }
                                                    }}
                                                >
                                                    {m.content}
                                                </ReactMarkdown>
                                            </div>
                                        ) : (
                                            <p className="text-sm whitespace-pre-wrap leading-relaxed">{m.content}</p>
                                        )}

                                        {/* Meta Footer */}
                                        {(m.tokens || m.latency) ? (
                                            <div className="mt-3 pt-2 border-t border-white/5 flex items-center justify-end gap-3 text-[9px] font-mono text-muted-foreground/50">
                                                {m.tokens > 0 && <span>Tokens: {m.tokens}</span>}
                                                {m.latency > 0 && <span className="flex items-center gap-1"><Clock className="h-3 w-3"/> {m.latency.toFixed(2)}s</span>}
                                            </div>
                                        ) : null}
                                    </div>
                                </div>
                            );
                        })
                        )}
                        {isGenerating && (
                            <div className="flex w-full justify-start">
                                <div className="bg-black/40 border border-white/5 rounded-2xl p-4 shadow-xl flex items-center gap-2">
                                    <div className="h-2 w-2 bg-[var(--cyan)] rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                                    <div className="h-2 w-2 bg-[var(--cyan)] rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                                    <div className="h-2 w-2 bg-[var(--cyan)] rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                                    <span className="text-xs text-muted-foreground ml-2 font-mono uppercase tracking-widest animate-pulse">Generating</span>
                                </div>
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                    </div>

                    {/* Composer */}
                    <ChatComposer 
                        input={input}
                        setInput={setInput}
                        isGenerating={isGenerating}
                        onSend={handleSend}
                        onStop={() => {
                            // TODO: implement actual stop logic
                        }}
                    />

                </div>
            </div>
        </main>
    );
});

ChatPanel.displayName = "ChatPanel";
