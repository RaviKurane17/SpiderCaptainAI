import React, { useRef, useEffect } from 'react';
import { Paperclip, Mic, Send, StopCircle, ImageIcon, FileText } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ChatComposerProps {
    input: string;
    setInput: (v: string) => void;
    isGenerating: boolean;
    onSend: () => void;
    onStop?: () => void;
}

export const ChatComposer: React.FC<ChatComposerProps> = ({ input, setInput, isGenerating, onSend, onStop }) => {
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // Auto-resize textarea
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
            textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
        }
    }, [input]);

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            onSend();
        }
    };

    return (
        <div className="p-4 bg-black/20 border-t border-white/5 backdrop-blur-xl relative">
            <div className="max-w-4xl mx-auto flex flex-col gap-2 relative">
                
                {/* File Dropzone / Attachment Area placeholder */}
                {/* <div className="flex gap-2 mb-2 px-2">... attachments ...</div> */}

                <div className="relative">
                    <textarea
                        ref={textareaRef}
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Ask CAPTAIN AI..."
                        className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3.5 min-h-[56px] max-h-48 resize-none text-sm text-foreground focus:outline-none focus:border-white/20 focus:ring-1 focus:ring-white/20 transition-all placeholder:text-muted-foreground pr-32 custom-scrollbar shadow-inner"
                        rows={1}
                    />
                    
                    {/* Character Counter */}
                    <div className="absolute left-4 -bottom-5 text-[9px] font-mono text-muted-foreground tracking-widest uppercase">
                        {input.length} chars
                    </div>
                    
                    <div className="absolute right-2 top-2 flex items-center gap-1">
                        <button className="p-2 text-muted-foreground hover:text-white transition rounded-md hover:bg-white/10" title="Attach Image">
                            <ImageIcon className="h-4 w-4" />
                        </button>
                        <button className="p-2 text-muted-foreground hover:text-white transition rounded-md hover:bg-white/10" title="Attach PDF/File">
                            <FileText className="h-4 w-4" />
                        </button>
                        <div className="w-px h-4 bg-white/10 mx-1" />
                        <button className="p-2 text-muted-foreground hover:text-white transition rounded-md hover:bg-white/10" title="Voice Input">
                            <Mic className="h-4 w-4" />
                        </button>

                        {isGenerating ? (
                            <button 
                                onClick={onStop}
                                className="p-2 ml-1 bg-rose-500/20 text-rose-400 hover:bg-rose-500/40 hover:text-rose-300 transition rounded-md"
                            >
                                <StopCircle className="h-4 w-4" />
                            </button>
                        ) : (
                            <button 
                                onClick={onSend}
                                disabled={!input.trim()}
                                className="p-2 ml-1 bg-[var(--cyan)]/20 text-[var(--cyan)] hover:bg-[var(--cyan)]/40 hover:text-[oklch(0.85_0.22_225)] transition rounded-md disabled:opacity-30 disabled:hover:bg-[var(--cyan)]/20 disabled:hover:text-[var(--cyan)]"
                            >
                                <Send className="h-4 w-4" />
                            </button>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};
