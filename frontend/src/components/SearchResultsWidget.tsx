import React, { useState, useEffect, useRef, useMemo } from "react";
import { Folder, File as FileIcon, HardDrive, Info, ChevronDown } from "lucide-react";

interface SearchResult {
    name: string;
    path: string;
    is_dir: boolean;
    confidence_score?: number;
    match_type?: string;
    size?: string;
    modified?: string;
    item_count?: number;
}

interface SearchResultsWidgetProps {
    query: string;
    results: SearchResult[];
    onOpen: (path: string) => void;
    ws: WebSocket | null;
}

const HighlightedText = ({ text, highlight }: { text: string; highlight: string }) => {
    if (!highlight || !highlight.trim()) return <span>{text}</span>;
    const regex = new RegExp(`(${highlight})`, "gi");
    const parts = text.split(regex);
    return (
        <span className="truncate">
            {parts.map((part, i) =>
                regex.test(part) ? (
                    <mark key={i} className="bg-yellow-500/30 text-yellow-200 bg-transparent">
                        {part}
                    </mark>
                ) : (
                    <span key={i}>{part}</span>
                )
            )}
        </span>
    );
};

export const SearchResultsWidget = React.memo(function SearchResultsWidget({ query, results, onOpen, ws }: SearchResultsWidgetProps) {
    const [expanded, setExpanded] = useState(results.length <= 5);
    const [displayCount, setDisplayCount] = useState(expanded ? Math.min(25, results.length) : Math.min(5, results.length));
    const [selectedIndex, setSelectedIndex] = useState(-1);
    const containerRef = useRef<HTMLDivElement>(null);
    const listRef = useRef<HTMLDivElement>(null);
    
    // Auto-focus container when results change
    useEffect(() => {
        if (containerRef.current) {
            containerRef.current.focus();
        }
    }, [results]);

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (!expanded && e.key === 'ArrowDown' && selectedIndex === displayCount - 1) {
            // allow expansion
        }
        
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            setSelectedIndex(prev => Math.min(prev + 1, displayCount - 1));
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            setSelectedIndex(prev => Math.max(prev - 1, 0));
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (selectedIndex >= 0 && selectedIndex < displayCount) {
                onOpen(results[selectedIndex].path);
            } else if (!expanded && results.length > 5 && selectedIndex === displayCount) {
                expandList();
            }
        } else if (e.key === 'Escape') {
            setSelectedIndex(-1);
            if (containerRef.current) containerRef.current.blur();
        }
    };
    
    const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
        if (!expanded) return;
        const target = e.target as HTMLDivElement;
        const bottom = target.scrollHeight - target.scrollTop <= target.clientHeight + 100;
        if (bottom && displayCount < results.length) {
            setDisplayCount(prev => Math.min(prev + 25, results.length));
        }
    };
    
    const expandList = () => {
        setExpanded(true);
        setDisplayCount(Math.min(25, results.length));
        if (containerRef.current) containerRef.current.focus();
    };

    // Metadata lazy loading
    const [metadata, setMetadata] = useState<Record<string, any>>({});
    
    useEffect(() => {
        if (!ws || ws.readyState !== WebSocket.OPEN) return;
        
        const pathsToFetch = results.slice(0, displayCount)
            .filter(r => !metadata[r.path])
            .map(r => r.path);
            
        if (pathsToFetch.length > 0) {
            ws.send(JSON.stringify({
                type: "get_file_info_batch",
                paths: pathsToFetch
            }));
        }
    }, [displayCount, results, ws, metadata]);
    
    useEffect(() => {
        if (!ws) return;
        const handleMessage = (e: MessageEvent) => {
            try {
                const data = JSON.parse(e.data);
                if (data.type === "file_info_batch_data") {
                    setMetadata(prev => {
                        const next = { ...prev };
                        data.metadata.forEach((m: any) => {
                            next[m.path] = m;
                        });
                        return next;
                    });
                }
            } catch (e) {}
        };
        ws.addEventListener("message", handleMessage);
        return () => ws.removeEventListener("message", handleMessage);
    }, [ws]);

    return (
        <div 
            ref={containerRef}
            tabIndex={0}
            onKeyDown={handleKeyDown}
            className="w-full rounded-md border border-white/10 bg-black/40 flex flex-col focus:outline-none focus:ring-1 focus:ring-[var(--cyan)] transition-shadow group/widget"
        >
            <div 
                ref={listRef}
                onScroll={handleScroll}
                className="max-h-[300px] overflow-y-auto custom-scrollbar"
            >
                {results.slice(0, displayCount).map((item, idx) => {
                    const meta = metadata[item.path];
                    const isSelected = selectedIndex === idx;
                    
                    return (
                        <button
                            key={idx}
                            onMouseEnter={() => setSelectedIndex(idx)}
                            onClick={() => onOpen(item.path)}
                            className={`group relative flex w-full items-center gap-3 border-b border-white/5 px-3 py-2 text-left transition-colors last:border-0 ${isSelected ? "bg-white/10" : "hover:bg-white/5"}`}
                        >
                            <div className="grid h-8 w-8 shrink-0 place-items-center rounded bg-white/5">
                                {item.is_dir ? (
                                    <Folder className="h-4 w-4 text-[var(--cyan)]" fill="currentColor" fillOpacity={0.2} />
                                ) : (
                                    <FileIcon className="h-4 w-4 text-muted-foreground" />
                                )}
                            </div>
                            <div className="flex flex-col overflow-hidden flex-1">
                                <div className="flex items-center gap-2">
                                    <span className="truncate text-sm font-medium text-white">
                                        <HighlightedText text={item.name} highlight={query} />
                                    </span>
                                    {item.match_type && (
                                        <span className="text-[9px] px-1.5 py-0.5 rounded-sm bg-white/10 text-white/50 border border-white/5 font-mono">
                                            {item.match_type} {item.confidence_score !== undefined ? `${item.confidence_score}%` : ''}
                                        </span>
                                    )}
                                </div>
                                <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
                                    <HardDrive className="h-3 w-3 shrink-0" />
                                    <span className="truncate">{item.path}</span>
                                </div>
                            </div>
                            
                            {meta && (
                                <div className="absolute right-full mr-2 top-0 opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50 bg-black/90 backdrop-blur-xl border border-white/10 p-3 rounded-lg shadow-2xl flex flex-col gap-1 w-max max-w-[300px]">
                                    <div className="text-xs font-bold text-white truncate">{item.name}</div>
                                    <div className="text-[10px] text-muted-foreground break-all">{item.path}</div>
                                    <div className="h-px w-full bg-white/10 my-1" />
                                    <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[10px]">
                                        <span className="text-white/40">Type</span><span className="text-white text-right">{meta.type}</span>
                                        <span className="text-white/40">Size</span><span className="text-white text-right">{meta.size}</span>
                                        <span className="text-white/40">Modified</span><span className="text-white text-right">{meta.modified}</span>
                                        {meta.type === "Folder" && <><span className="text-white/40">Items</span><span className="text-white text-right">{meta.item_count}</span></>}
                                    </div>
                                </div>
                            )}
                        </button>
                    );
                })}
                
                {!expanded && results.length > 5 && (
                    <button 
                        onMouseEnter={() => setSelectedIndex(displayCount)}
                        onClick={expandList}
                        className={`flex w-full items-center justify-center gap-2 py-2 text-[11px] font-medium transition-colors border-t border-white/5 ${selectedIndex === displayCount ? 'bg-white/10 text-[var(--cyan)]' : 'text-muted-foreground hover:text-[var(--cyan)] hover:bg-white/5'}`}
                    >
                        Show all {results.length} results <ChevronDown className="h-3 w-3" />
                    </button>
                )}
                
                {expanded && displayCount < results.length && (
                    <div className="py-2 text-center text-[10px] text-muted-foreground border-t border-white/5">
                        Scroll to load more ({displayCount} of {results.length})
                    </div>
                )}
            </div>
        </div>
    );
});
