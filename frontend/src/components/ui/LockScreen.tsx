import React, { useState, useEffect } from "react";
import { Shield, KeyRound, ArrowRight } from "lucide-react";

interface LockScreenProps {
    onUnlock: () => void;
    wsRef: React.MutableRefObject<WebSocket | null>;
    lockType: string;
}

export function LockScreen({ onUnlock, wsRef, lockType }: LockScreenProps) {
    const [pin, setPin] = useState("");
    const [error, setError] = useState(false);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        const handleMessage = (e: MessageEvent) => {
            try {
                const data = JSON.parse(e.data);
                if (data.type === "lock_verified") {
                    setLoading(false);
                    if (data.success) {
                        onUnlock();
                    } else {
                        setError(true);
                        setPin("");
                    }
                }
            } catch (err) {}
        };

        const ws = wsRef.current;
        if (ws) {
            ws.addEventListener("message", handleMessage);
        }
        return () => {
            if (ws) {
                ws.removeEventListener("message", handleMessage);
            }
        };
    }, [wsRef, onUnlock]);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!pin) return;
        setLoading(true);
        setError(false);
        wsRef.current?.send(JSON.stringify({
            type: "verify_lock",
            pin: pin
        }));
    };

    return (
        <div className="fixed inset-0 z-[10000] flex flex-col items-center justify-center bg-black/90 backdrop-blur-xl animate-fade-in select-none">
            <div className="absolute inset-0 bg-[url('/grid.svg')] bg-center [mask-image:linear-gradient(180deg,white,rgba(255,255,255,0))] opacity-20" />
            
            <div className="relative z-10 flex flex-col items-center max-w-sm w-full p-8 glass-panel rounded-2xl border border-white/10 shadow-2xl">
                <div className="h-16 w-16 bg-white/5 rounded-full flex items-center justify-center mb-6 border border-white/10 shadow-[0_0_15px_rgba(255,255,255,0.05)]">
                    <Shield className="h-8 w-8 text-[var(--cyan)]" />
                </div>
                
                <h1 className="text-2xl font-bold text-white mb-2 tracking-wide">SYSTEM LOCKED</h1>
                <p className="text-sm text-muted-foreground mb-8 text-center">
                    Please enter your {lockType} to access Captain AI.
                </p>

                <form onSubmit={handleSubmit} className="w-full flex flex-col gap-4">
                    <div className="relative">
                        <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                        <input
                            type={lockType === "PIN" ? "password" : "password"}
                            inputMode={lockType === "PIN" ? "numeric" : "text"}
                            value={pin}
                            onChange={(e) => {
                                setPin(e.target.value);
                                setError(false);
                            }}
                            disabled={loading}
                            placeholder={`Enter ${lockType}...`}
                            className={`w-full h-12 bg-black/40 border ${error ? 'border-red-500' : 'border-white/10'} rounded-lg pl-10 pr-12 text-white focus:outline-none focus:border-[var(--cyan)] transition-colors`}
                            autoFocus
                        />
                        <button 
                            type="submit"
                            disabled={!pin || loading}
                            className="absolute right-2 top-1/2 -translate-y-1/2 h-8 w-8 bg-white/10 hover:bg-[var(--cyan)] rounded flex items-center justify-center transition-colors disabled:opacity-50"
                        >
                            <ArrowRight className="h-4 w-4 text-white" />
                        </button>
                    </div>
                    {error && (
                        <p className="text-xs text-red-400 text-center animate-shake">
                            Incorrect {lockType}. Please try again.
                        </p>
                    )}
                </form>
            </div>
        </div>
    );
}
