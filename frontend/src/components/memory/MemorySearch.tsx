import React, { useState, useEffect } from 'react';
import { Search, SlidersHorizontal } from 'lucide-react';

interface MemorySearchProps {
    onSearch: (query: string, category: string, privacy: string) => void;
}

export const MemorySearch: React.FC<MemorySearchProps> = ({ onSearch }) => {
    const [localQuery, setLocalQuery] = useState("");
    const [showFilters, setShowFilters] = useState(false);
    const [selectedCategory, setSelectedCategory] = useState("ALL");
    const [selectedPrivacy, setSelectedPrivacy] = useState("ALL");

    const CATEGORIES = ["ALL", "Personal", "Education", "Projects", "Coding", "Goals", "Preferences", "Tasks", "System Settings"];
    const PRIVACIES = ["ALL", "Normal", "Private", "Sensitive"];

    // Debounce the search query by 300ms so we don't spam the DB as the user types
    useEffect(() => {
        const timer = setTimeout(() => {
            onSearch(localQuery, selectedCategory, selectedPrivacy);
        }, 300);
        return () => clearTimeout(timer);
    }, [localQuery, selectedCategory, selectedPrivacy, onSearch]);

    return (
        <div className="flex flex-col mb-6 gap-3">
            <div className="flex gap-3">
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                    <input 
                        type="text"
                        placeholder="Search memories by keyword or semantic meaning..."
                        value={localQuery}
                        onChange={(e) => setLocalQuery(e.target.value)}
                        className="w-full h-12 bg-black/40 border border-white/10 rounded-xl pl-11 pr-4 text-sm text-foreground focus:outline-none focus:border-[var(--cyan)]/50 focus:ring-1 focus:ring-[var(--cyan)]/50 transition-all placeholder:text-muted-foreground shadow-inner"
                    />
                </div>
                
                <button 
                    onClick={() => setShowFilters(!showFilters)}
                    className={`h-12 px-4 border rounded-xl flex items-center gap-2 transition-colors text-sm font-medium ${
                        showFilters ? 'bg-[var(--cyan)]/20 border-[var(--cyan)]/50 text-[var(--cyan)]' : 'bg-white/5 hover:bg-white/10 border-white/10 text-white'
                    }`}
                >
                    <SlidersHorizontal className="h-4 w-4" />
                    Filters
                </button>
            </div>

            {showFilters && (
                <div className="p-4 rounded-xl border border-white/10 bg-black/40 backdrop-blur-md flex gap-8 animate-in slide-in-from-top-2">
                    <div className="flex flex-col gap-2">
                        <span className="text-[10px] text-muted-foreground uppercase font-mono tracking-widest font-semibold">Category</span>
                        <div className="flex flex-wrap gap-2">
                            {CATEGORIES.map(cat => (
                                <button
                                    key={cat}
                                    onClick={() => setSelectedCategory(cat)}
                                    className={`px-3 py-1 rounded-full text-xs font-medium transition-colors border ${
                                        selectedCategory === cat 
                                            ? 'bg-purple-500/20 text-purple-400 border-purple-500/50' 
                                            : 'bg-white/5 text-muted-foreground border-white/10 hover:bg-white/10'
                                    }`}
                                >
                                    {cat}
                                </button>
                            ))}
                        </div>
                    </div>
                    
                    <div className="w-px bg-white/10 shrink-0" />

                    <div className="flex flex-col gap-2">
                        <span className="text-[10px] text-muted-foreground uppercase font-mono tracking-widest font-semibold">Privacy</span>
                        <div className="flex flex-wrap gap-2">
                            {PRIVACIES.map(priv => (
                                <button
                                    key={priv}
                                    onClick={() => setSelectedPrivacy(priv)}
                                    className={`px-3 py-1 rounded-full text-xs font-medium transition-colors border ${
                                        selectedPrivacy === priv 
                                            ? 'bg-rose-500/20 text-rose-400 border-rose-500/50' 
                                            : 'bg-white/5 text-muted-foreground border-white/10 hover:bg-white/10'
                                    }`}
                                >
                                    {priv}
                                </button>
                            ))}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};
