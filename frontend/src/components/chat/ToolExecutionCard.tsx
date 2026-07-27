import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Wrench, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface ToolExecutionData {
    tool_name: string;
    status: 'running' | 'success' | 'error';
    duration?: number;
    error?: string;
    logs?: string[];
}

export const ToolExecutionCard: React.FC<{ data: ToolExecutionData }> = ({ data }) => {
    const [expanded, setExpanded] = useState(false);

    const isRunning = data.status === 'running';
    const isSuccess = data.status === 'success';
    const isError = data.status === 'error';

    return (
        <div className="w-full max-w-sm rounded-lg border border-white/10 bg-black/40 backdrop-blur-md overflow-hidden shadow-xl mb-4 transition-all duration-300">
            <div 
                className="flex items-center justify-between p-3 cursor-pointer hover:bg-white/5 transition-colors"
                onClick={() => setExpanded(!expanded)}
            >
                <div className="flex items-center gap-3">
                    <div className={cn(
                        "flex items-center justify-center w-8 h-8 rounded-full border shadow-[0_0_10px_rgba(0,0,0,0.5)]",
                        isRunning ? "border-[var(--cyan)] bg-[var(--cyan)]/20 text-[var(--cyan)]" : 
                        isSuccess ? "border-emerald-500/50 bg-emerald-500/20 text-emerald-400" :
                        "border-rose-500/50 bg-rose-500/20 text-rose-400"
                    )}>
                        {isRunning ? <Loader2 className="w-4 h-4 animate-spin" /> : 
                         isSuccess ? <CheckCircle2 className="w-4 h-4" /> : 
                         <XCircle className="w-4 h-4" />}
                    </div>
                    <div className="flex flex-col">
                        <span className="text-sm font-medium text-white tracking-wide">
                            {data.tool_name}
                        </span>
                        <span className="text-[10px] text-muted-foreground uppercase font-mono tracking-wider">
                            {isRunning ? 'Executing...' : 
                             isSuccess ? `Completed in ${data.duration?.toFixed(2)}s` : 
                             `Failed in ${data.duration?.toFixed(2)}s`}
                        </span>
                    </div>
                </div>
                <button className="text-muted-foreground hover:text-white transition-colors">
                    {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>
            </div>

            {expanded && (
                <div className="px-3 pb-3 pt-1 border-t border-white/5 bg-black/20">
                    <div className="text-xs font-mono text-muted-foreground whitespace-pre-wrap mt-2">
                        {isRunning && "Awaiting tool execution..."}
                        {isError && <span className="text-rose-400">{data.error}</span>}
                        {isSuccess && <span className="text-emerald-400/80">Process finished with exit code 0.</span>}
                        
                        {/* Render logs if any were captured */}
                        {data.logs && data.logs.length > 0 && (
                            <div className="mt-2 border-l-2 border-white/10 pl-2">
                                {data.logs.map((l, i) => (
                                    <div key={i}>{l}</div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};
