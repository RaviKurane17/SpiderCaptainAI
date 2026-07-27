import React, { useState, useRef, useCallback } from "react";
import { cn } from "@/lib/utils";
import { Mic, Paperclip, Zap, Send, X } from "lucide-react";

interface ComposerProps {
    isMuted: boolean;
    onMicToggle: () => void;
    onSend: (text: string, file?: File) => void;
}

const Composer = React.memo(function Composer({ isMuted, onMicToggle, onSend }: ComposerProps) {
    const [inputValue, setInputValue] = useState("");
    const [attachedFile, setAttachedFile] = useState<{ file: File; name: string; size: number } | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) setAttachedFile({ file, name: file.name, size: file.size });
    }, []);

    const handlePaperclipClick = useCallback(() => {
        fileInputRef.current?.click();
    }, []);

    const handleSend = useCallback(() => {
        if (!inputValue.trim() && !attachedFile) return;
        
        onSend(inputValue, attachedFile?.file);
        setInputValue("");
        setAttachedFile(null);
    }, [inputValue, attachedFile, onSend]);

    const handleKeyDown = useCallback(
        (e: React.KeyboardEvent<HTMLInputElement>) => {
            if (e.key === "Enter") handleSend();
        },
        [handleSend]
    );

    return (
        <div className="flex w-full items-center gap-4 shrink-0">
            <input type="file" ref={fileInputRef} onChange={handleFileChange} className="hidden" />
            <button
                onClick={onMicToggle}
                className={cn(
                    "relative grid h-10 w-10 shrink-0 place-items-center rounded-full border transition-all duration-300 hover:scale-105",
                    isMuted
                        ? "border-[oklch(0.65_0.22_20/0.5)] bg-[oklch(0.65_0.22_20/0.08)] text-[var(--rose)] shadow-[0_0_20px_oklch(0.65_0.22_20/0.3)]"
                        : "border-[oklch(0.75_0.22_225/0.5)] bg-[oklch(0.75_0.22_225/0.08)] text-[var(--cyan)] hover:shadow-[0_0_30px_oklch(0.75_0.22_225/0.5)]"
                )}
            >
                {!isMuted && (
                    <span className="absolute inset-0 animate-pulse-ring rounded-full border border-[var(--cyan)]/40" />
                )}
                <Mic className="h-[18px] w-[18px]" strokeWidth={2} />
            </button>

            <div className="relative flex-1">
                {attachedFile && (
                    <div className="absolute -top-10 left-0 flex items-center gap-2 rounded-lg bg-[var(--cyan)]/10 border border-[var(--cyan)]/30 px-3 py-1 text-xs text-[var(--cyan)] animate-fade-in select-none">
                        <Paperclip className="h-3.5 w-3.5" />
                        <span className="font-semibold">
                            {attachedFile.name} ({(attachedFile.size / 1024).toFixed(1)} KB)
                        </span>
                        <button
                            onClick={() => setAttachedFile(null)}
                            className="ml-1 text-[var(--cyan)] hover:text-white cursor-pointer p-0.5 rounded hover:bg-white/5 transition"
                            title="Remove attachment"
                        >
                            <X className="h-3 w-3" />
                        </button>
                    </div>
                )}
                <div className="glass-panel flex items-center gap-3 px-4 py-2">
                    <input
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder={isMuted ? "Microphone muted. Type your command..." : "Ask anything, Captain..."}
                        className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
                    />
                    <button
                        onClick={handlePaperclipClick}
                        className="grid h-8 w-8 place-items-center rounded-lg text-muted-foreground transition hover:bg-white/5 hover:text-[var(--cyan)] cursor-pointer"
                        title="Attach file"
                    >
                        <Paperclip className="h-4 w-4" strokeWidth={1.8} />
                    </button>
                    <button className="grid h-8 w-8 place-items-center rounded-lg text-muted-foreground transition hover:bg-white/5 hover:text-[var(--amber)]">
                        <Zap className="h-4 w-4" strokeWidth={1.8} />
                    </button>
                    <button
                        onClick={handleSend}
                        className="grid h-8 w-8 place-items-center rounded-full border border-[oklch(0.75_0.22_225/0.5)] text-[var(--cyan)] transition-all hover:scale-105 hover:bg-[oklch(0.75_0.22_225/0.15)] hover:shadow-[0_0_20px_oklch(0.75_0.22_225/0.45)]"
                    >
                        <Send className="h-4 w-4" strokeWidth={2} />
                    </button>
                </div>
            </div>
        </div>
    );
});

export default Composer;
