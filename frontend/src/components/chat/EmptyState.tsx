import React from 'react';
import { Sparkles, Terminal, Code2, FolderSearch, PenTool, Search, Bot } from 'lucide-react';
import { cn } from '@/lib/utils';

interface QuickAction {
    icon: React.ReactNode;
    title: string;
    prompt: string;
    color: string;
}

const quickActions: QuickAction[] = [
    {
        icon: <Code2 className="w-5 h-5" />,
        title: "Start Coding Session",
        prompt: "Let's start a new coding session. I need help building...",
        color: "text-blue-400"
    },
    {
        icon: <FolderSearch className="w-5 h-5" />,
        title: "Analyze Workspace",
        prompt: "Analyze my current workspace and tell me what the architecture looks like.",
        color: "text-emerald-400"
    },
    {
        icon: <PenTool className="w-5 h-5" />,
        title: "Explain Code",
        prompt: "Can you explain how the core event loop works in this project?",
        color: "text-purple-400"
    },
    {
        icon: <Terminal className="w-5 h-5" />,
        title: "Generate SQL",
        prompt: "Help me write a complex SQL query to get...",
        color: "text-amber-400"
    }
];

export const EmptyState: React.FC<{ onActionClick: (prompt: string) => void }> = ({ onActionClick }) => {
    return (
        <div className="h-full flex flex-col items-center justify-center animate-fade-in pb-10">
            <div className="flex flex-col items-center mb-10 text-center">
                <div className="w-16 h-16 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center mb-6 shadow-2xl relative">
                    <div className="absolute inset-0 bg-[var(--cyan)]/20 rounded-2xl blur-xl animate-pulse" />
                    <Bot className="w-8 h-8 text-[var(--cyan)] relative z-10" />
                </div>
                <h2 className="text-2xl font-bold text-white tracking-wide mb-2">How can I help you today?</h2>
                <p className="text-sm text-muted-foreground max-w-md">
                    I am CAPTAIN AI, your advanced desktop assistant. I can write code, analyze local files, execute terminal commands, and manage your system.
                </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full max-w-2xl px-6">
                {quickActions.map((action, idx) => (
                    <button
                        key={idx}
                        onClick={() => onActionClick(action.prompt)}
                        className="flex flex-col items-start p-4 bg-white/5 border border-white/10 rounded-xl hover:bg-white/10 hover:border-white/20 transition-all duration-300 text-left group"
                    >
                        <div className={cn("mb-3 p-2 rounded-lg bg-black/40 border border-white/5", action.color)}>
                            {action.icon}
                        </div>
                        <span className="text-sm font-semibold text-white mb-1 group-hover:text-[var(--cyan)] transition-colors">{action.title}</span>
                        <span className="text-xs text-muted-foreground line-clamp-2">{action.prompt}</span>
                    </button>
                ))}
            </div>
        </div>
    );
};
