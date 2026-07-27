import React, { useState } from 'react';
import { useWebSocket } from '../../hooks/useWebSocket';
import { Shield, Key, Sparkles, ChevronRight, CheckCircle2, Lock } from 'lucide-react';

export function SetupWizard() {
    const ws = useWebSocket();
    const [step, setStep] = useState(1);
    
    // Form states
    const [provider, setProvider] = useState('Gemini');
    const [apiKey, setApiKey] = useState('');
    const [securityType, setSecurityType] = useState('No Lock');
    const [pin, setPin] = useState('');

    const handleNext = () => setStep(s => s + 1);
    const handleBack = () => setStep(s => s - 1);

    const handleComplete = () => {
        // Save API Key if entered
        if (apiKey.trim()) {
            ws.sendCommand({ type: 'set_api_key', provider, api_key: apiKey.trim() });
        }
        
        // Save Security Hash if chosen
        if (securityType !== 'No Lock' && pin.trim()) {
            ws.sendCommand({ type: 'update_setting', key: 'security_lock_type', value: securityType });
            ws.sendCommand({ type: 'update_setting', key: 'security_hash', value: pin });
        }

        // Mark setup as complete
        ws.sendCommand({ type: 'update_setting', key: 'setup_complete', value: true });
        
        // Let the root reload or let the websocket state update
        window.location.reload();
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md overflow-hidden">
            {/* Animated Background Orbs */}
            <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-cyan-500/20 rounded-full blur-[120px] pointer-events-none" />
            <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-purple-500/20 rounded-full blur-[120px] pointer-events-none" />

            <div className="glass-panel p-8 md:p-12 w-full max-w-2xl relative z-10 border border-white/10 rounded-2xl shadow-2xl flex flex-col min-h-[500px]">
                
                {/* Header */}
                <div className="flex items-center gap-3 mb-8">
                    <Sparkles className="w-8 h-8 text-cyan-400" />
                    <h1 className="text-2xl font-bold tracking-wider text-white">CAPTAIN AI <span className="text-cyan-400 font-light">INITIALIZATION</span></h1>
                </div>

                {/* Progress Bar */}
                <div className="flex gap-2 mb-12">
                    {[1, 2, 3].map(i => (
                        <div key={i} className={`h-1.5 flex-1 rounded-full transition-all duration-500 ${step >= i ? 'bg-cyan-500 shadow-[0_0_10px_rgba(6,182,212,0.6)]' : 'bg-white/10'}`} />
                    ))}
                </div>

                {/* Content Area */}
                <div className="flex-1">
                    {step === 1 && (
                        <div className="animate-in fade-in slide-in-from-right-8 duration-500">
                            <h2 className="text-3xl font-light text-white mb-4">Welcome aboard.</h2>
                            <p className="text-slate-400 text-lg leading-relaxed mb-8">
                                I am Captain, your advanced AI desktop assistant. Before I can interface with your system, we need to establish secure connections and configure my neural architecture.
                            </p>
                            <p className="text-slate-400 text-lg leading-relaxed">
                                This setup will only take a moment.
                            </p>
                        </div>
                    )}

                    {step === 2 && (
                        <div className="animate-in fade-in slide-in-from-right-8 duration-500">
                            <div className="flex items-center gap-3 mb-6">
                                <Key className="w-6 h-6 text-purple-400" />
                                <h2 className="text-2xl font-medium text-white">Neural Interface Key</h2>
                            </div>
                            <p className="text-slate-400 mb-6">Select your primary AI provider and securely input your API key. This key is encrypted and stored locally in your vault.</p>
                            
                            <div className="space-y-4">
                                <div className="flex flex-col gap-2">
                                    <label className="text-sm text-slate-300 font-medium">AI Provider</label>
                                    <select 
                                        className="bg-black/40 border border-white/10 rounded-lg p-3 text-white focus:outline-none focus:border-cyan-500"
                                        value={provider}
                                        onChange={e => setProvider(e.target.value)}
                                    >
                                        <option value="Gemini">Google Gemini (Recommended)</option>
                                        <option value="OpenAI">OpenAI</option>
                                        <option value="Groq">Groq</option>
                                        <option value="Anthropic">Anthropic Claude</option>
                                        <option value="Ollama">Ollama (Local)</option>
                                    </select>
                                </div>
                                
                                {provider !== 'Ollama' && (
                                    <div className="flex flex-col gap-2">
                                        <label className="text-sm text-slate-300 font-medium">API Key</label>
                                        <input 
                                            type="password"
                                            placeholder="Paste your API key here..."
                                            className="bg-black/40 border border-white/10 rounded-lg p-3 text-white focus:outline-none focus:border-cyan-500 font-mono"
                                            value={apiKey}
                                            onChange={e => setApiKey(e.target.value)}
                                        />
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {step === 3 && (
                        <div className="animate-in fade-in slide-in-from-right-8 duration-500">
                            <div className="flex items-center gap-3 mb-6">
                                <Shield className="w-6 h-6 text-green-400" />
                                <h2 className="text-2xl font-medium text-white">System Security</h2>
                            </div>
                            <p className="text-slate-400 mb-6">Protect your AI configuration and memories with an optional security lock.</p>
                            
                            <div className="space-y-6">
                                <div className="grid grid-cols-2 gap-4">
                                    {['No Lock', '4 Digit PIN'].map(type => (
                                        <button 
                                            key={type}
                                            onClick={() => setSecurityType(type)}
                                            className={`p-4 rounded-xl border transition-all text-left flex flex-col gap-2
                                                ${securityType === type 
                                                    ? 'border-green-500 bg-green-500/10 shadow-[0_0_15px_rgba(34,197,94,0.2)]' 
                                                    : 'border-white/10 bg-white/5 hover:bg-white/10'}`}
                                        >
                                            <div className="flex justify-between items-center w-full">
                                                <span className="text-white font-medium">{type}</span>
                                                {securityType === type && <CheckCircle2 className="w-5 h-5 text-green-500" />}
                                            </div>
                                            <span className="text-xs text-slate-400">
                                                {type === 'No Lock' ? 'Fast access, zero friction.' : 'Standard numeric security pin.'}
                                            </span>
                                        </button>
                                    ))}
                                </div>

                                {securityType !== 'No Lock' && (
                                    <div className="flex flex-col gap-2 animate-in fade-in zoom-in-95 duration-300">
                                        <label className="text-sm text-slate-300 font-medium flex items-center gap-2">
                                            <Lock className="w-4 h-4"/> Enter your PIN
                                        </label>
                                        <input 
                                            type="password"
                                            maxLength={4}
                                            placeholder="••••"
                                            className="bg-black/40 border border-white/10 rounded-lg p-3 text-white text-center tracking-[1em] focus:outline-none focus:border-green-500 font-mono text-xl"
                                            value={pin}
                                            onChange={e => setPin(e.target.value.replace(/[^0-9]/g, ''))}
                                        />
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </div>

                {/* Footer Controls */}
                <div className="flex justify-between items-center mt-8 pt-6 border-t border-white/10">
                    <button 
                        onClick={handleBack}
                        className={`px-6 py-2 rounded-lg text-slate-300 hover:text-white transition-colors ${step === 1 ? 'invisible' : ''}`}
                    >
                        Back
                    </button>
                    
                    {step < 3 ? (
                        <button 
                            onClick={handleNext}
                            disabled={step === 2 && provider !== 'Ollama' && apiKey.length < 10}
                            className="px-6 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-medium flex items-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_0_15px_rgba(6,182,212,0.3)] hover:shadow-[0_0_25px_rgba(6,182,212,0.5)]"
                        >
                            Next <ChevronRight className="w-4 h-4" />
                        </button>
                    ) : (
                        <button 
                            onClick={handleComplete}
                            disabled={securityType !== 'No Lock' && pin.length < 4}
                            className="px-6 py-2 rounded-lg bg-green-600 hover:bg-green-500 text-white font-medium flex items-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_0_15px_rgba(34,197,94,0.3)] hover:shadow-[0_0_25px_rgba(34,197,94,0.5)]"
                        >
                            Complete Setup <CheckCircle2 className="w-4 h-4" />
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}
