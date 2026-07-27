import React, { useState, useEffect, useRef } from 'react';
import { MemoryDashboard } from '../memory/MemoryDashboard';
import { MemorySearch } from '../memory/MemorySearch';
import { MemoryList, MemoryRecord } from '../memory/MemoryList';
import { MemoryDialog } from '../memory/MemoryDialog';
import { useWebSocket } from '../../hooks/useWebSocket';
import { Plus } from 'lucide-react';

export const MemoryPanel: React.FC = () => {
    const ws = useWebSocket();
    const [stats, setStats] = useState<any>(null);
    const [memories, setMemories] = useState<MemoryRecord[]>([]);
    const [query, setQuery] = useState("");
    const [category, setCategory] = useState("ALL");
    const [offset, setOffset] = useState(0);
    const [loading, setLoading] = useState(false);
    
    const [dialogOpen, setDialogOpen] = useState(false);
    const [editingMemory, setEditingMemory] = useState<MemoryRecord | null>(null);

    // Initial load
    useEffect(() => {
        if (!ws.isConnected) return;
        ws.sendCommand({ type: "get_memory_stats" });
        ws.sendCommand({ type: "search_memories", query: "", category: "ALL", limit: 50, offset: 0 });
    }, [ws.isConnected]);

    // Handle incoming WS messages
    useEffect(() => {
        if (!ws.lastMessage) return;
        const data = ws.lastMessage;
        
        if (data.type === "memory_stats_data") {
            setStats(data.stats);
        } else if (data.type === "memory_search_results") {
            if (data.offset === 0) {
                setMemories(data.results);
            } else {
                setMemories(prev => [...prev, ...data.results]);
            }
            setLoading(false);
        } else if (data.type === "memory_action_result") {
            // Refresh on mutation
            ws.sendCommand({ type: "get_memory_stats" });
            ws.sendCommand({ type: "search_memories", query, category, limit: 50, offset: 0 });
        }
    }, [ws.lastMessage]);

    const handleSearch = (newQuery: string, newCategory: string, newPrivacy: string) => {
        setQuery(newQuery);
        setCategory(newCategory);
        // Note: You can add `privacy: newPrivacy` to state or just send it directly.
        setOffset(0);
        setLoading(true);
        ws.sendCommand({ 
            type: "search_memories", 
            query: newQuery, 
            category: newCategory, 
            privacy: newPrivacy,
            limit: 50, 
            offset: 0 
        });
    };

    const handleDelete = (id: string) => {
        ws.sendCommand({ type: "delete_memory", memory_id: id });
    };

    const handlePin = (id: string) => {
        // Optimistic UI update could go here
        ws.sendCommand({ type: "toggle_pin_memory", memory_id: id });
    };

    const handleEdit = (m: MemoryRecord) => {
        setEditingMemory(m);
        setDialogOpen(true);
    };
    
    const handleAddClick = () => {
        setEditingMemory(null);
        setDialogOpen(true);
    };

    const handleSaveMemory = (data: Partial<MemoryRecord>) => {
        if (data.id) {
            // Editing existing memory
            ws.sendCommand({ type: "edit_memory_direct", ...data });
        } else {
            // Adding new memory
            ws.sendCommand({ type: "add_memory_direct", ...data });
        }
    };

    return (
        <main className="flex h-full min-h-0 flex-col overflow-hidden bg-transparent">
            {/* Top Toolbar */}
            <div className="h-14 border-b border-white/5 flex items-center justify-between px-6 shrink-0 bg-black/10 backdrop-blur-md">
                <div className="flex flex-col">
                    <span className="text-sm font-bold text-white tracking-wide">Memory Manager</span>
                    <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest">Personal Knowledge Base</span>
                </div>
                
                <button 
                    onClick={handleAddClick}
                    className="h-8 px-4 bg-[var(--cyan)]/10 hover:bg-[var(--cyan)]/20 border border-[var(--cyan)]/30 text-[var(--cyan)] text-xs font-semibold rounded-md transition-colors flex items-center gap-2"
                >
                    <Plus className="w-3.5 h-3.5" /> Add Memory
                </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8 custom-scrollbar">
                <div className="max-w-6xl mx-auto flex flex-col h-full">
                    <MemoryDashboard stats={stats} />
                    <MemorySearch onSearch={handleSearch} />
                    
                    {loading && memories.length === 0 ? (
                        <div className="flex-1 glass-panel flex items-center justify-center">
                            <span className="text-muted-foreground text-sm font-mono animate-pulse">Scanning Neural Paths...</span>
                        </div>
                    ) : (
                        <MemoryList 
                            memories={memories} 
                            onDelete={handleDelete}
                            onPin={handlePin}
                            onEdit={handleEdit}
                        />
                    )}
                </div>
            </div>
            
            <MemoryDialog 
                open={dialogOpen}
                onOpenChange={setDialogOpen}
                initialData={editingMemory}
                onSave={handleSaveMemory}
            />
        </main>
    );
};
