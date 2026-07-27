import React, { useState, useEffect } from 'react';
import { ToolsDashboard } from '../tools/ToolsDashboard';
import { ToolsSearch } from '../tools/ToolsSearch';
import { ToolsList, ToolRecord } from '../tools/ToolsList';
import { useWebSocket } from '../../hooks/useWebSocket';

export const ToolsPanel: React.FC = () => {
    const ws = useWebSocket();
    
    const [stats, setStats] = useState(null);
    const [tools, setTools] = useState<ToolRecord[]>([]);
    
    const [query, setQuery] = useState("");
    const [category, setCategory] = useState("ALL");
    const [status, setStatus] = useState("ALL");
    const [offset, setOffset] = useState(0);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        // Initial load
        ws.sendCommand({ type: "get_tools_stats" });
        ws.sendCommand({ type: "search_tools", query: "", category: "ALL", status: "ALL", limit: 50, offset: 0 });
    }, [ws]);

    useEffect(() => {
        if (!ws.lastMessage) return;
        
        if (ws.lastMessage.type === "tools_stats_data") {
            setStats(ws.lastMessage.stats);
        } else if (ws.lastMessage.type === "tools_search_results") {
            if (ws.lastMessage.offset === 0) {
                setTools(ws.lastMessage.results);
            } else {
                setTools(prev => [...prev, ...ws.lastMessage.results]);
            }
            setLoading(false);
        } else if (ws.lastMessage.type === "tool_action_result") {
            // Refresh stats and list after action
            ws.sendCommand({ type: "get_tools_stats" });
            ws.sendCommand({ type: "search_tools", query, category, status, limit: 50, offset: 0 });
        }
    }, [ws.lastMessage]);

    const handleSearch = (newQuery: string, newCategory: string, newStatus: string) => {
        setQuery(newQuery);
        setCategory(newCategory);
        setStatus(newStatus);
        setOffset(0);
        setLoading(true);
        ws.sendCommand({ 
            type: "search_tools", 
            query: newQuery, 
            category: newCategory, 
            status: newStatus,
            limit: 50, 
            offset: 0 
        });
    };

    const handleToolAction = (toolId: string, action: string, data?: any) => {
        if (action === "set_permission") {
            ws.sendCommand({ type: "update_tool_permission", tool_id: toolId, permission: data });
        } else {
            console.log(`Action ${action} on tool ${toolId} - UI placeholder`);
            // Other actions can be wired to backend as needed
        }
    };

    return (
        <main className="flex h-full min-h-0 flex-col overflow-hidden bg-transparent">
            <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
                <ToolsDashboard stats={stats} />
                
                <ToolsSearch onSearch={handleSearch} />
                
                <div className="h-[600px] mt-4 relative">
                    {loading && tools.length === 0 ? (
                        <div className="absolute inset-0 flex items-center justify-center bg-black/20 backdrop-blur-sm z-10 rounded-xl">
                            <div className="w-8 h-8 border-4 border-[var(--cyan)]/20 border-t-[var(--cyan)] rounded-full animate-spin" />
                        </div>
                    ) : (
                        <ToolsList 
                            tools={tools} 
                            onAction={handleToolAction}
                        />
                    )}
                </div>
            </div>
        </main>
    );
};
