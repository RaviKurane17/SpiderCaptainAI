import React from 'react';
import { Plus, Search, Pin, PinOff, Trash2, MessageSquare, Folder, Hash } from 'lucide-react';
import { ChatSession } from '../../hooks/useChat';
import { cn } from '@/lib/utils';
import {
    ContextMenu,
    ContextMenuContent,
    ContextMenuItem,
    ContextMenuSeparator,
    ContextMenuTrigger,
} from "@/components/ui/context-menu";

interface ChatSidebarProps {
    sessions: ChatSession[];
    activeSessionId: string | null;
    searchQuery: string;
    setSearchQuery: (v: string) => void;
    onNewChat: () => void;
    onLoadSession: (id: string) => void;
    onTogglePin: (id: string, isPinned: boolean) => void;
    onDeleteSession: (id: string) => void;
}

export const ChatSidebar: React.FC<ChatSidebarProps> = ({
    sessions, activeSessionId, searchQuery, setSearchQuery,
    onNewChat, onLoadSession, onTogglePin, onDeleteSession
}) => {
    const displaySessions = sessions.filter(s => s.title.toLowerCase().includes(searchQuery.toLowerCase()));

    // For production-ready UI, we might group them by "Today", "Previous 7 Days", etc.
    const pinned = displaySessions.filter(s => s.is_pinned);
    const unpinned = displaySessions.filter(s => !s.is_pinned);

    return (
        <div className="w-64 glass-panel flex flex-col p-0 overflow-hidden select-none">
            <div className="p-3 border-b border-white/5 flex flex-col gap-3">
                <button 
                    onClick={onNewChat}
                    className="w-full flex items-center justify-center gap-2 bg-[var(--cyan)]/10 hover:bg-[var(--cyan)]/20 text-[var(--cyan)] border border-[var(--cyan)]/30 text-xs font-semibold py-2.5 rounded-md transition-colors"
                >
                    <Plus className="h-4 w-4" /> New Chat <span className="ml-auto text-[9px] font-mono text-[var(--cyan)]/60">Ctrl+N</span>
                </button>
                <div className="relative">
                    <Search className="absolute left-2.5 top-2 h-4 w-4 text-muted-foreground" />
                    <input 
                        id="chat-search-input"
                        type="text"
                        placeholder="Search History..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full h-8 bg-black/20 border border-white/10 rounded-md pl-9 pr-3 text-xs text-foreground focus:outline-none focus:border-white/20 transition-all placeholder:text-muted-foreground"
                    />
                </div>
            </div>

            {/* Smart Filters placeholder */}
            <div className="px-3 py-2 border-b border-white/5 flex gap-2 overflow-x-auto custom-scrollbar">
                <div className="px-2 py-1 rounded bg-white/10 text-[9px] font-mono uppercase text-white whitespace-nowrap cursor-pointer hover:bg-white/20 transition">All</div>
                <div className="px-2 py-1 rounded bg-black/40 text-[9px] font-mono uppercase text-muted-foreground whitespace-nowrap cursor-pointer hover:text-white transition">Today</div>
                <div className="px-2 py-1 rounded bg-black/40 text-[9px] font-mono uppercase text-muted-foreground whitespace-nowrap cursor-pointer hover:text-white transition">Coding</div>
            </div>
            
            <div className="flex-1 overflow-y-auto p-2 flex flex-col gap-1 custom-scrollbar">
                {pinned.length > 0 && (
                    <div className="mb-2">
                        <div className="text-[9px] font-mono uppercase text-muted-foreground px-3 py-1 tracking-widest">Pinned</div>
                        {pinned.map(s => <SessionItem key={s.id} s={s} isActive={activeSessionId === s.id} onLoad={onLoadSession} onPin={onTogglePin} onDelete={onDeleteSession} />)}
                    </div>
                )}
                
                {unpinned.length > 0 && (
                    <div className="mb-2">
                        <div className="text-[9px] font-mono uppercase text-muted-foreground px-3 py-1 tracking-widest">Recent</div>
                        {unpinned.map(s => <SessionItem key={s.id} s={s} isActive={activeSessionId === s.id} onLoad={onLoadSession} onPin={onTogglePin} onDelete={onDeleteSession} />)}
                    </div>
                )}
            </div>
        </div>
    );
};

const SessionItem = ({ s, isActive, onLoad, onPin, onDelete }: { s: ChatSession, isActive: boolean, onLoad: (id: string) => void, onPin: (id: string, p: boolean) => void, onDelete: (id: string) => void }) => {
    return (
        <ContextMenu>
            <ContextMenuTrigger>
                <button 
                    onClick={() => onLoad(s.id)}
                    className={cn(
                        "w-full text-left px-3 py-2 rounded-md transition-all flex items-start gap-2 group",
                        isActive 
                            ? "bg-white/10 shadow-[inset_0_0_10px_rgba(255,255,255,0.05)] border border-white/10" 
                            : "border border-transparent hover:bg-white/5 hover:border-white/5"
                    )}
                >
                    {s.is_pinned ? (
                        <Pin className="h-3.5 w-3.5 text-[var(--cyan)] shrink-0 mt-0.5" />
                    ) : (
                        <MessageSquare className={cn("h-3.5 w-3.5 shrink-0 mt-0.5", isActive ? "text-white" : "text-muted-foreground")} />
                    )}
                    <div className="flex flex-col flex-1 min-w-0">
                        <span className={cn("text-[12px] truncate", isActive ? "text-white font-medium" : "text-muted-foreground")}>
                            {s.title}
                        </span>
                        <div className="flex items-center gap-2 mt-0.5">
                            <span className="text-[9px] text-muted-foreground/60 font-mono">
                                {new Date(s.updated_at * 1000).toLocaleDateString()}
                            </span>
                            {s.tags && <span className="text-[8px] bg-white/5 text-white/50 px-1 rounded uppercase tracking-wider">{s.tags.split(',')[0]}</span>}
                        </div>
                    </div>
                </button>
            </ContextMenuTrigger>
            <ContextMenuContent className="bg-black/90 backdrop-blur-xl border-white/10 text-foreground w-48">
                <ContextMenuItem onClick={() => onPin(s.id, !s.is_pinned)} className="text-xs cursor-pointer hover:bg-white/10">
                    {s.is_pinned ? <><PinOff className="mr-2 h-4 w-4"/> Unpin Chat</> : <><Pin className="mr-2 h-4 w-4"/> Pin Chat</>}
                </ContextMenuItem>
                <ContextMenuItem className="text-xs cursor-pointer hover:bg-white/10">
                    <Folder className="mr-2 h-4 w-4"/> Move to Collection
                </ContextMenuItem>
                <ContextMenuItem className="text-xs cursor-pointer hover:bg-white/10">
                    <Hash className="mr-2 h-4 w-4"/> Add Tag
                </ContextMenuItem>
                <ContextMenuSeparator className="bg-white/10" />
                <ContextMenuItem onClick={() => onDelete(s.id)} className="text-xs text-rose-400 focus:text-rose-300 cursor-pointer hover:bg-rose-500/20">
                    <Trash2 className="mr-2 h-4 w-4" /> Delete Chat
                </ContextMenuItem>
            </ContextMenuContent>
        </ContextMenu>
    );
};
