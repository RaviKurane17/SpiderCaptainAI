import React, { useState } from 'react';
import { Virtuoso } from 'react-virtuoso';
import { 
    Brain, Shield, Lock, EyeOff, CalendarClock, Tag, 
    MoreVertical, Trash2, Edit2, Pin, PinOff, Combine, ArrowUpRight 
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
    ContextMenu,
    ContextMenuContent,
    ContextMenuItem,
    ContextMenuSeparator,
    ContextMenuTrigger,
} from "@/components/ui/context-menu";

export interface MemoryRecord {
    id: string;
    layer: string;
    title: string;
    summary: string;
    category: string;
    tags: string;
    importance_score: number;
    priority: string;
    privacy: string;
    source: string;
    expires_at: number | null;
    pinned?: number;
    created_at: number;
    updated_at: number;
}

interface MemoryListProps {
    memories: MemoryRecord[];
    onDelete: (id: string) => void;
    onPin: (id: string) => void;
    onEdit: (m: MemoryRecord) => void;
}

export const MemoryList: React.FC<MemoryListProps> = ({ memories, onDelete, onPin, onEdit }) => {
    return (
        <div className="flex-1 glass-panel p-2 flex flex-col h-full min-h-[400px]">
            {memories.length === 0 ? (
                <div className="flex-1 flex flex-col items-center justify-center opacity-40">
                    <Brain className="w-12 h-12 mb-4 text-muted-foreground" />
                    <span className="text-sm font-medium tracking-wide">No memories found.</span>
                </div>
            ) : (
                <Virtuoso
                    className="custom-scrollbar"
                    style={{ height: '100%', width: '100%' }}
                    data={memories}
                    itemContent={(index, memory) => (
                        <MemoryCard 
                            key={memory.id} 
                            memory={memory} 
                            onDelete={() => onDelete(memory.id)}
                            onPin={() => onPin(memory.id)}
                            onEdit={() => onEdit(memory)}
                        />
                    )}
                />
            )}
        </div>
    );
};

const MemoryCard = ({ memory, onDelete, onPin, onEdit }: { memory: MemoryRecord, onDelete: () => void, onPin: () => void, onEdit: () => void }) => {
    const isPrivate = memory.privacy === 'Private';
    const isSensitive = memory.privacy === 'Sensitive';
    const isManual = memory.source === 'Manual';
    
    // Color coding based on category
    const categoryColors: Record<string, string> = {
        'Personal': 'bg-blue-500/20 text-blue-400 border-blue-500/30',
        'Coding': 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
        'Projects': 'bg-purple-500/20 text-purple-400 border-purple-500/30',
        'System Settings': 'bg-slate-500/20 text-slate-400 border-slate-500/30',
        'Tasks': 'bg-amber-500/20 text-amber-400 border-amber-500/30'
    };
    
    const catColor = categoryColors[memory.category] || 'bg-white/10 text-white border-white/20';

    return (
        <ContextMenu>
            <ContextMenuTrigger>
                <div className="p-4 mb-2 mx-2 bg-black/40 border border-white/5 rounded-xl hover:bg-white/5 transition-all group flex gap-4 shadow-sm hover:shadow-md cursor-pointer">
                    <div className="flex flex-col items-center gap-2 pt-1">
                        {isSensitive ? <EyeOff className="w-4 h-4 text-rose-400" /> :
                         isPrivate ? <Lock className="w-4 h-4 text-amber-400" /> :
                         <Brain className="w-4 h-4 text-[var(--cyan)]" />}
                         
                        <div className="w-px h-full bg-white/10 group-hover:bg-[var(--cyan)]/30 transition-colors" />
                    </div>
                    
                    <div className="flex-1 flex flex-col min-w-0">
                        <div className="flex items-center justify-between mb-1">
                            <h4 className={cn("text-sm font-semibold truncate", isSensitive ? "text-rose-400/80 italic blur-[2px] group-hover:blur-0 transition-all" : "text-white")}>
                                {memory.title}
                            </h4>
                            <div className="flex items-center gap-2">
                                <span className={cn("text-[9px] font-mono uppercase tracking-widest px-2 py-0.5 rounded-full border", catColor)}>
                                    {memory.category}
                                </span>
                            </div>
                        </div>
                        
                        <p className={cn("text-xs text-muted-foreground line-clamp-2 mb-3", isSensitive && "blur-[3px] group-hover:blur-0 transition-all")}>
                            {memory.summary}
                        </p>
                        
                        <div className="flex items-center gap-4 mt-auto">
                            <div className="flex items-center gap-1.5 text-[10px] font-mono text-muted-foreground uppercase tracking-wider">
                                <CalendarClock className="w-3 h-3" />
                                {new Date(memory.updated_at * 1000).toLocaleDateString()}
                            </div>
                            
                            {memory.tags && (
                                <div className="flex items-center gap-1.5 text-[10px] font-mono text-muted-foreground uppercase tracking-wider">
                                    <Tag className="w-3 h-3" />
                                    <div className="flex gap-1">
                                        {memory.tags.split(',').map((t, i) => (
                                            <span key={i} className="px-1.5 py-0.5 bg-white/5 rounded text-white/70">{t.trim()}</span>
                                        ))}
                                    </div>
                                </div>
                            )}
                            
                            <div className="ml-auto text-[10px] font-mono uppercase tracking-wider flex items-center gap-1">
                                {memory.pinned === 1 && <Pin className="w-3 h-3 text-emerald-400 mr-2" />}
                                {isManual ? <span className="text-emerald-400/80 flex items-center gap-1"><Shield className="w-3 h-3"/> User Defined</span> 
                                          : <span className="text-[var(--cyan)]/80 flex items-center gap-1"><ArrowUpRight className="w-3 h-3"/> AI Extracted</span>}
                            </div>
                        </div>
                    </div>
                </div>
            </ContextMenuTrigger>
            
            <ContextMenuContent className="w-48 bg-black/90 backdrop-blur-xl border-white/10 text-white">
                <ContextMenuItem onClick={onEdit} className="text-xs cursor-pointer hover:bg-white/10">
                    <Edit2 className="mr-2 w-4 h-4" /> Edit Memory
                </ContextMenuItem>
                <ContextMenuItem onClick={onPin} className="text-xs cursor-pointer hover:bg-white/10">
                    {memory.pinned === 1 ? <PinOff className="mr-2 w-4 h-4" /> : <Pin className="mr-2 w-4 h-4" />}
                    {memory.pinned === 1 ? "Unpin Memory" : "Pin to Working Context"}
                </ContextMenuItem>
                <ContextMenuItem className="text-xs cursor-pointer hover:bg-white/10">
                    <Combine className="mr-2 w-4 h-4" /> Merge with...
                </ContextMenuItem>
                <ContextMenuSeparator className="bg-white/10" />
                <ContextMenuItem onClick={onDelete} className="text-xs text-rose-400 hover:bg-rose-500/20 hover:text-rose-300 cursor-pointer">
                    <Trash2 className="mr-2 w-4 h-4" /> Forget Memory
                </ContextMenuItem>
            </ContextMenuContent>
        </ContextMenu>
    );
};
