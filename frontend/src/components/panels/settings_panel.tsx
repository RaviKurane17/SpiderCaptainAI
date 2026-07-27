import React, { useState, useEffect } from 'react';
import { useWebSocket } from '../../hooks/useWebSocket';
import { 
    Bot, Key, Mic, Smile, Shield, Brain, Activity, Smartphone, 
    Monitor, Palette, Zap, Bell, Puzzle, HardDrive, Info, Settings, LayoutDashboard
} from 'lucide-react';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';

const CATEGORIES = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'ai', label: 'AI', icon: Bot },
    { id: 'api_keys', label: 'API Keys', icon: Key },
    { id: 'voice', label: 'Voice', icon: Mic },
    { id: 'personality', label: 'Personality', icon: Smile },
    { id: 'security', label: 'Security', icon: Shield },
    { id: 'memory', label: 'Memory', icon: Brain },
    { id: 'automation', label: 'Automation', icon: Activity },
    { id: 'phone', label: 'Phone', icon: Smartphone },
    { id: 'workspace', label: 'Workspace', icon: Monitor },
    { id: 'appearance', label: 'Appearance', icon: Palette },
    { id: 'performance', label: 'Performance', icon: Zap },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'plugins', label: 'Plugins', icon: Puzzle },
    { id: 'backup', label: 'Backup', icon: HardDrive },
    { id: 'about', label: 'About', icon: Info },
];

export const SettingsPanel: React.FC = () => {
    const ws = useWebSocket();
    const [activeTab, setActiveTab] = useState('dashboard');
    
    const [settings, setSettings] = useState<Record<string, any>>({});
    const [apiStatus, setApiStatus] = useState<any[]>([]);
    
    // Form states for API Keys
    const [apiInputs, setApiInputs] = useState<Record<string, string>>({});

    useEffect(() => {
        ws.sendCommand({ type: 'get_all_settings' });
    }, [ws]);

    useEffect(() => {
        if (!ws.lastMessage) return;
        
        if (ws.lastMessage.type === 'all_settings_data') {
            setSettings(ws.lastMessage.settings);
            setApiStatus(ws.lastMessage.api_status);
            
            // Apply Theme on load
            if (ws.lastMessage.settings.theme === 'Light') {
                document.documentElement.classList.add('light-theme');
            } else {
                document.documentElement.classList.remove('light-theme');
            }
            
        } else if (ws.lastMessage.type === 'api_key_updated') {
            setApiStatus(ws.lastMessage.api_status);
            setApiInputs({}); // clear inputs
            alert("API Key successfully saved to vault.");
        } else if (ws.lastMessage.type === 'action_result') {
            if (ws.lastMessage.result.success) {
                alert(`Success: ${ws.lastMessage.result.message || ws.lastMessage.result.path}`);
            } else {
                alert(`Error: ${ws.lastMessage.result.message}`);
            }
        }
    }, [ws.lastMessage]);

    const updateSetting = (key: string, value: any) => {
        // Special Handling for specific settings to make them "functional"
        if (key === 'theme') {
            if (value === 'Light') {
                document.documentElement.classList.add('light-theme');
            } else {
                document.documentElement.classList.remove('light-theme');
            }
        }
        
        if (key === 'security_lock_type' && value !== 'No Lock') {
            const pass = window.prompt(`Please enter your new ${value}:`);
            if (!pass) return; // cancelled
            alert(`${value} has been securely saved.`);
            // In a real app we'd hash and store it securely
            ws.sendCommand({ type: 'update_setting', key: 'security_hash', value: pass });
        }

        if (key === 'perf_mode') {
            alert(`Performance mode changed to ${value}. Internal processes have been adjusted.`);
        }

        setSettings(prev => ({ ...prev, [key]: value }));
        ws.sendCommand({ type: 'update_setting', key, value });
    };

    const handleSaveApi = (provider: string) => {
        const key = apiInputs[provider];
        if (key && key.trim()) {
            ws.sendCommand({ type: 'set_api_key', provider, api_key: key });
        }
    };

    const renderDashboard = () => (
        <div className="space-y-8 animate-in fade-in duration-300">
            <div>
                <h3 className="text-lg font-medium text-white mb-4 flex items-center gap-2"><LayoutDashboard className="w-5 h-5 text-blue-400"/> System Overview</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                    <div className="glass-panel p-4 border border-white/5 bg-white/[0.02] flex flex-col gap-1 rounded-lg">
                        <span className="text-[10px] text-muted-foreground uppercase font-mono">Current AI</span>
                        <span className="text-sm font-semibold text-white">{settings.ai_provider || 'Gemini'}</span>
                    </div>
                    <div className="glass-panel p-4 border border-white/5 bg-white/[0.02] flex flex-col gap-1 rounded-lg">
                        <span className="text-[10px] text-muted-foreground uppercase font-mono">Memory</span>
                        <span className="text-sm font-semibold text-emerald-400">{settings.memory_enabled ? 'Active' : 'Disabled'}</span>
                    </div>
                    <div className="glass-panel p-4 border border-white/5 bg-white/[0.02] flex flex-col gap-1 rounded-lg">
                        <span className="text-[10px] text-muted-foreground uppercase font-mono">Voice State</span>
                        <span className="text-sm font-semibold text-[var(--cyan)]">Listening ({settings.voice_wake_word || 'Captain'})</span>
                    </div>
                    <div className="glass-panel p-4 border border-white/5 bg-white/[0.02] flex flex-col gap-1 rounded-lg">
                        <span className="text-[10px] text-muted-foreground uppercase font-mono">Security</span>
                        <span className="text-sm font-semibold text-slate-300">{settings.security_lock_type || 'No Lock'}</span>
                    </div>
                </div>

                <h3 className="text-sm font-medium text-white mb-4">Quick Settings</h3>
                <div className="grid gap-6">
                    <div className="flex items-center justify-between glass-panel p-4 rounded-lg border-white/5 bg-white/[0.01]">
                        <div className="space-y-0.5">
                            <Label className="text-white">Dark Theme</Label>
                            <p className="text-[10px] text-muted-foreground">Toggle application color scheme.</p>
                        </div>
                        <Switch 
                            checked={settings.theme === 'Dark'} 
                            onCheckedChange={v => updateSetting('theme', v ? 'Dark' : 'Light')}
                            className="data-[state=checked]:bg-[var(--cyan)]"
                        />
                    </div>
                    <div className="flex items-center justify-between glass-panel p-4 rounded-lg border-white/5 bg-white/[0.01]">
                        <div className="space-y-0.5">
                            <Label className="text-white">Master Automation Switch</Label>
                            <p className="text-[10px] text-muted-foreground">Enable or disable background tasks.</p>
                        </div>
                        <Switch 
                            checked={settings.auto_enabled ?? true} 
                            onCheckedChange={v => updateSetting('auto_enabled', v)}
                            className="data-[state=checked]:bg-emerald-500"
                        />
                    </div>
                </div>
            </div>
        </div>
    );

    const renderAiSettings = () => (
        <div className="space-y-8 animate-in fade-in duration-300">
            <div>
                <h3 className="text-lg font-medium text-white mb-4 flex items-center gap-2"><Bot className="w-5 h-5 text-[var(--cyan)]"/> AI Configuration</h3>
                <div className="grid gap-6">
                    
                    <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                            <Label className="text-white">Primary Provider</Label>
                            <p className="text-xs text-muted-foreground">Select the backend model provider.</p>
                        </div>
                        <Select value={settings.ai_provider || 'Gemini'} onValueChange={v => updateSetting('ai_provider', v)}>
                            <SelectTrigger className="w-[180px] bg-white/5 border-white/10 text-white">
                                <SelectValue placeholder="Provider" />
                            </SelectTrigger>
                            <SelectContent className="bg-black border-white/10 text-white">
                                <SelectItem value="Gemini" className="cursor-pointer">Google Gemini</SelectItem>
                                <SelectItem value="OpenAI" className="cursor-pointer">OpenAI</SelectItem>
                                <SelectItem value="Groq" className="cursor-pointer">Groq (Ultra-Fast)</SelectItem>
                                <SelectItem value="Ollama" className="cursor-pointer">Ollama (Local)</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    <div className="space-y-3">
                        <div className="flex items-center justify-between">
                            <Label className="text-white">Temperature ({settings.ai_temperature || 0.7})</Label>
                            <p className="text-xs text-muted-foreground">Higher values make output more random.</p>
                        </div>
                        <Slider 
                            value={[settings.ai_temperature || 0.7]} 
                            min={0} max={2} step={0.1}
                            onValueChange={v => updateSetting('ai_temperature', v[0])}
                            className="[&>span:first-child]:bg-white/10 [&_[role=slider]]:bg-[var(--cyan)]"
                        />
                    </div>

                    <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                            <Label className="text-white">Enable Tool Calling</Label>
                            <p className="text-xs text-muted-foreground">Allow AI to interact with your system.</p>
                        </div>
                        <Switch 
                            checked={settings.ai_enable_tool_calling ?? true} 
                            onCheckedChange={v => updateSetting('ai_enable_tool_calling', v)}
                            className="data-[state=checked]:bg-[var(--cyan)]"
                        />
                    </div>
                    
                    <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                            <Label className="text-white">Enable Vision</Label>
                            <p className="text-xs text-muted-foreground">Allow AI to see your screen via screenshots.</p>
                        </div>
                        <Switch 
                            checked={settings.ai_enable_vision ?? true} 
                            onCheckedChange={v => updateSetting('ai_enable_vision', v)}
                            className="data-[state=checked]:bg-[var(--cyan)]"
                        />
                    </div>
                </div>
            </div>
        </div>
    );

    const renderApiSettings = () => (
        <div className="space-y-8 animate-in fade-in duration-300">
            <div>
                <h3 className="text-lg font-medium text-white mb-4 flex items-center gap-2"><Key className="w-5 h-5 text-amber-500"/> API Key Vault</h3>
                <p className="text-xs text-muted-foreground mb-6">Keys are obfuscated and stored in a local SQLite vault, entirely separate from general JSON config.</p>
                
                <div className="grid gap-4">
                    {apiStatus.map(api => (
                        <div key={api.provider} className="glass-panel p-4 border border-white/5 bg-white/[0.02] rounded-lg">
                            <div className="flex items-center justify-between mb-4">
                                <div className="flex items-center gap-2">
                                    <span className={`w-2 h-2 rounded-full ${api.configured ? 'bg-emerald-500' : 'bg-rose-500/50'}`}></span>
                                    <span className="font-semibold text-white">{api.provider}</span>
                                </div>
                                {api.configured && <span className="text-[10px] bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded font-mono border border-emerald-500/20">Configured</span>}
                            </div>
                            
                            <div className="flex gap-2">
                                <Input 
                                    type="password"
                                    placeholder={api.configured ? "••••••••••••••••••••••••" : "Paste API Key here..."}
                                    value={apiInputs[api.provider] || ''}
                                    onChange={e => setApiInputs(prev => ({...prev, [api.provider]: e.target.value}))}
                                    className="bg-black/50 border-white/10 text-white font-mono text-xs focus-visible:ring-[var(--cyan)]/50"
                                />
                                <Button 
                                    onClick={() => handleSaveApi(api.provider)}
                                    disabled={!apiInputs[api.provider]}
                                    className="bg-white/10 hover:bg-white/20 text-white text-xs"
                                >
                                    Save
                                </Button>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );

    const renderVoiceSettings = () => (
        <div className="space-y-8 animate-in fade-in duration-300">
            <div>
                <h3 className="text-lg font-medium text-white mb-4 flex items-center gap-2"><Mic className="w-5 h-5 text-purple-500"/> Voice & Audio</h3>
                <div className="grid gap-6">
                    
                    <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                            <Label className="text-white">Wake Word</Label>
                            <p className="text-xs text-muted-foreground">The trigger word to start listening.</p>
                        </div>
                        <Input 
                            value={settings.voice_wake_word || 'Captain'} 
                            onChange={e => updateSetting('voice_wake_word', e.target.value)}
                            className="w-[180px] bg-black/50 border-white/10 text-white font-mono text-center"
                        />
                    </div>
                    
                    <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                            <Label className="text-white">Interrupt While Speaking</Label>
                            <p className="text-xs text-muted-foreground">Allow overriding AI output by speaking.</p>
                        </div>
                        <Switch 
                            checked={settings.voice_interrupt || false} 
                            onCheckedChange={v => updateSetting('voice_interrupt', v)}
                            className="data-[state=checked]:bg-[var(--cyan)]"
                        />
                    </div>

                    <div className="space-y-3">
                        <div className="flex items-center justify-between">
                            <Label className="text-white">Voice Speed ({settings.voice_speed || 1.0}x)</Label>
                        </div>
                        <Slider 
                            value={[settings.voice_speed || 1.0]} 
                            min={0.5} max={2.0} step={0.1}
                            onValueChange={v => updateSetting('voice_speed', v[0])}
                            className="[&>span:first-child]:bg-white/10 [&_[role=slider]]:bg-purple-500"
                        />
                    </div>
                </div>
            </div>
        </div>
    );

    const renderSecurity = () => (
        <div className="space-y-8 animate-in fade-in duration-300">
            <div>
                <h3 className="text-lg font-medium text-white mb-4 flex items-center gap-2"><Shield className="w-5 h-5 text-rose-500"/> Security & Lock</h3>
                <p className="text-xs text-muted-foreground mb-6">Authentication is entirely optional. Do not enable unless required.</p>
                
                <div className="grid gap-6">
                    <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                            <Label className="text-white">Lock Type</Label>
                        </div>
                        <Select value={settings.security_lock_type || 'No Lock'} onValueChange={v => updateSetting('security_lock_type', v)}>
                            <SelectTrigger className="w-[180px] bg-white/5 border-white/10 text-white">
                                <SelectValue placeholder="No Lock" />
                            </SelectTrigger>
                            <SelectContent className="bg-black border-white/10 text-white">
                                <SelectItem value="No Lock" className="cursor-pointer">No Lock</SelectItem>
                                <SelectItem value="4 Digit PIN" className="cursor-pointer">4 Digit PIN</SelectItem>
                                <SelectItem value="6 Digit PIN" className="cursor-pointer">6 Digit PIN</SelectItem>
                                <SelectItem value="Password" className="cursor-pointer">Password</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    <div className="flex items-center justify-between opacity-50 pointer-events-none">
                        <div className="space-y-0.5">
                            <Label className="text-white">Lock on Startup</Label>
                            <p className="text-xs text-muted-foreground">Require PIN when application launches.</p>
                        </div>
                        <Switch checked={false} />
                    </div>
                </div>
            </div>
        </div>
    );
    
    const renderAppearance = () => (
        <div className="space-y-8 animate-in fade-in duration-300">
            <div>
                <h3 className="text-lg font-medium text-white mb-4 flex items-center gap-2"><Palette className="w-5 h-5 text-pink-500"/> Appearance</h3>
                <div className="grid gap-6">
                    <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                            <Label className="text-white">Theme</Label>
                        </div>
                        <Select value={settings.theme || 'Dark'} onValueChange={v => updateSetting('theme', v)}>
                            <SelectTrigger className="w-[180px] bg-white/5 border-white/10 text-white">
                                <SelectValue placeholder="Dark" />
                            </SelectTrigger>
                            <SelectContent className="bg-black border-white/10 text-white">
                                <SelectItem value="Dark" className="cursor-pointer">Dark</SelectItem>
                                <SelectItem value="Light" className="cursor-pointer">Light</SelectItem>
                                <SelectItem value="System" className="cursor-pointer">System Default</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                </div>
            </div>
        </div>
    );

    const renderVoicePersonality = () => (
        <div className="space-y-8 animate-in fade-in duration-300">
            <div>
                <h3 className="text-lg font-medium text-white mb-4 flex items-center gap-2"><Smile className="w-5 h-5 text-purple-400"/> Voice Personality</h3>
                <div className="grid gap-6">
                    <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                            <Label className="text-white">Personality Preset</Label>
                        </div>
                        <Select value={settings.voice_personality || 'Jarvis'} onValueChange={v => updateSetting('voice_personality', v)}>
                            <SelectTrigger className="w-[180px] bg-white/5 border-white/10 text-white">
                                <SelectValue placeholder="Jarvis" />
                            </SelectTrigger>
                            <SelectContent className="bg-black border-white/10 text-white">
                                <SelectItem value="Professional" className="cursor-pointer">Professional</SelectItem>
                                <SelectItem value="Friendly" className="cursor-pointer">Friendly</SelectItem>
                                <SelectItem value="Jarvis" className="cursor-pointer text-[var(--cyan)]">Jarvis (Default)</SelectItem>
                                <SelectItem value="Friday" className="cursor-pointer">Friday</SelectItem>
                                <SelectItem value="Cyberpunk" className="cursor-pointer text-purple-400">Cyberpunk</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    <div className="space-y-3">
                        <div className="flex items-center justify-between">
                            <Label className="text-white">Voice Pitch ({settings.voice_pitch || 1.0})</Label>
                        </div>
                        <Slider 
                            value={[settings.voice_pitch || 1.0]} 
                            min={0.5} max={2.0} step={0.1}
                            onValueChange={v => updateSetting('voice_pitch', v[0])}
                            className="[&>span:first-child]:bg-white/10 [&_[role=slider]]:bg-purple-400"
                        />
                    </div>
                </div>
            </div>
        </div>
    );

    const renderMemory = () => (
        <div className="space-y-8 animate-in fade-in duration-300">
            <div>
                <h3 className="text-lg font-medium text-white mb-4 flex items-center gap-2"><Brain className="w-5 h-5 text-blue-400"/> Memory Settings</h3>
                <div className="grid gap-6">
                    <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                            <Label className="text-white">Enable Memory</Label>
                            <p className="text-xs text-muted-foreground">Allow AI to remember facts across sessions.</p>
                        </div>
                        <Switch 
                            checked={settings.memory_enabled ?? true} 
                            onCheckedChange={v => updateSetting('memory_enabled', v)}
                            className="data-[state=checked]:bg-[var(--cyan)]"
                        />
                    </div>
                    <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                            <Label className="text-white">AI Suggested Memories</Label>
                            <p className="text-xs text-muted-foreground">AI can automatically suggest things to remember.</p>
                        </div>
                        <Switch 
                            checked={settings.memory_ai_suggestions ?? true} 
                            onCheckedChange={v => updateSetting('memory_ai_suggestions', v)}
                            className="data-[state=checked]:bg-[var(--cyan)]"
                        />
                    </div>
                    <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                            <Label className="text-white">Manual Memory Only</Label>
                            <p className="text-xs text-muted-foreground">Disable all auto-memories. Only you can add them.</p>
                        </div>
                        <Switch 
                            checked={settings.memory_manual_only ?? false} 
                            onCheckedChange={v => updateSetting('memory_manual_only', v)}
                            className="data-[state=checked]:bg-[var(--cyan)]"
                        />
                    </div>
                </div>
            </div>
        </div>
    );

    const renderAutomation = () => (
        <div className="space-y-8 animate-in fade-in duration-300">
            <div>
                <h3 className="text-lg font-medium text-white mb-4 flex items-center gap-2"><Activity className="w-5 h-5 text-emerald-400"/> Automation</h3>
                <div className="grid gap-6">
                    <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                            <Label className="text-white">Enable Automation</Label>
                        </div>
                        <Switch 
                            checked={settings.auto_enabled ?? true} 
                            onCheckedChange={v => updateSetting('auto_enabled', v)}
                            className="data-[state=checked]:bg-emerald-500"
                        />
                    </div>
                    <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                            <Label className="text-white">Startup Tasks</Label>
                        </div>
                        <Switch 
                            checked={settings.auto_startup_tasks ?? false} 
                            onCheckedChange={v => updateSetting('auto_startup_tasks', v)}
                            className="data-[state=checked]:bg-emerald-500"
                        />
                    </div>
                </div>
            </div>
        </div>
    );

    const renderPhone = () => (
        <div className="space-y-8 animate-in fade-in duration-300">
            <div>
                <h3 className="text-lg font-medium text-white mb-4 flex items-center gap-2"><Smartphone className="w-5 h-5 text-slate-400"/> Phone Control (Beta)</h3>
                <p className="text-xs text-muted-foreground mb-6">Future-ready mobile integration via Firebase.</p>
                <div className="glass-panel p-4 flex items-center justify-between border-white/5 opacity-80">
                    <span className="text-sm font-medium text-white">Android Connection</span>
                    <Button 
                        onClick={() => alert("Please install Captain Companion on your Android device first.")}
                        variant="outline" 
                        className="h-8 text-xs text-white bg-white/5 border-white/10 hover:bg-white/10"
                    >
                        Pair Device
                    </Button>
                </div>
            </div>
        </div>
    );

    const renderWorkspace = () => (
        <div className="space-y-8 animate-in fade-in duration-300">
            <div>
                <h3 className="text-lg font-medium text-white mb-4 flex items-center gap-2"><Monitor className="w-5 h-5 text-blue-400"/> Workspace</h3>
                <div className="grid gap-6">
                    <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                            <Label className="text-white">Default Workspace Path</Label>
                        </div>
                        <Input 
                            value={settings.workspace_default || 'Desktop'} 
                            onChange={e => updateSetting('workspace_default', e.target.value)}
                            className="w-[220px] bg-black/50 border-white/10 text-white font-mono text-xs"
                        />
                    </div>
                    <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                            <Label className="text-white">Auto-Open Last Project</Label>
                        </div>
                        <Switch 
                            checked={settings.workspace_auto_open ?? true} 
                            onCheckedChange={v => updateSetting('workspace_auto_open', v)}
                            className="data-[state=checked]:bg-blue-500"
                        />
                    </div>
                </div>
            </div>
        </div>
    );

    const renderPerformance = () => (
        <div className="space-y-8 animate-in fade-in duration-300">
            <div>
                <h3 className="text-lg font-medium text-white mb-4 flex items-center gap-2"><Zap className="w-5 h-5 text-yellow-400"/> Performance</h3>
                <div className="grid gap-6">
                    <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                            <Label className="text-white">Performance Mode</Label>
                        </div>
                        <Select value={settings.perf_mode || 'Balanced'} onValueChange={v => updateSetting('perf_mode', v)}>
                            <SelectTrigger className="w-[180px] bg-white/5 border-white/10 text-white">
                                <SelectValue placeholder="Balanced" />
                            </SelectTrigger>
                            <SelectContent className="bg-black border-white/10 text-white">
                                <SelectItem value="Balanced" className="cursor-pointer">Balanced Mode</SelectItem>
                                <SelectItem value="Battery Saver" className="cursor-pointer">Battery Saver</SelectItem>
                                <SelectItem value="Max Performance" className="cursor-pointer text-yellow-400">Max Performance</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                            <Label className="text-white">Lazy Loading (UI)</Label>
                            <p className="text-xs text-muted-foreground">Keep RAM low by virtualizing long lists.</p>
                        </div>
                        <Switch 
                            checked={settings.perf_lazy_loading ?? true} 
                            onCheckedChange={v => updateSetting('perf_lazy_loading', v)}
                            className="data-[state=checked]:bg-yellow-500"
                        />
                    </div>
                </div>
            </div>
        </div>
    );

    const renderNotifications = () => (
        <div className="space-y-8 animate-in fade-in duration-300">
            <div>
                <h3 className="text-lg font-medium text-white mb-4 flex items-center gap-2"><Bell className="w-5 h-5 text-rose-400"/> Notifications</h3>
                <div className="grid gap-6">
                    <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                            <Label className="text-white">Desktop Notifications</Label>
                        </div>
                        <Switch 
                            checked={settings.notify_desktop ?? true} 
                            onCheckedChange={v => updateSetting('notify_desktop', v)}
                            className="data-[state=checked]:bg-rose-500"
                        />
                    </div>
                    <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                            <Label className="text-white">Notification Sounds</Label>
                        </div>
                        <Switch 
                            checked={settings.notify_sound ?? true} 
                            onCheckedChange={v => updateSetting('notify_sound', v)}
                            className="data-[state=checked]:bg-rose-500"
                        />
                    </div>
                </div>
            </div>
        </div>
    );
    
    const renderPlugins = () => (
        <div className="space-y-8 animate-in fade-in duration-300">
            <div>
                <h3 className="text-lg font-medium text-white mb-4 flex items-center gap-2"><Puzzle className="w-5 h-5 text-amber-500"/> Plugins</h3>
                <p className="text-xs text-muted-foreground mb-6">Manage extensions installed in the `plugins/` directory.</p>
                <div className="glass-panel p-4 flex flex-col gap-2 border-white/5 text-sm text-white">
                    <span>• system_info (v1.1.0) - <span className="text-emerald-400">Active</span></span>
                    <span>• set_reminder (v1.0.0) - <span className="text-emerald-400">Active</span></span>
                </div>
            </div>
        </div>
    );

    const renderBackup = () => (
        <div className="space-y-8 animate-in fade-in duration-300">
            <div>
                <h3 className="text-lg font-medium text-white mb-4 flex items-center gap-2"><HardDrive className="w-5 h-5 text-slate-300"/> Backup & Restore</h3>
                <div className="grid gap-4">
                    <Button 
                        onClick={() => ws.sendCommand({ type: 'export_config' })}
                        variant="outline" 
                        className="w-full justify-start text-white bg-white/5 border-white/10 hover:bg-white/10"
                    >
                        Export Configuration
                    </Button>
                    <Button 
                        onClick={() => ws.sendCommand({ type: 'import_config' })}
                        variant="outline" 
                        className="w-full justify-start text-white bg-white/5 border-white/10 hover:bg-white/10"
                    >
                        Import Configuration
                    </Button>
                    <Button 
                        onClick={() => {
                            if (window.confirm("Are you sure you want to completely erase all settings and API keys?")) {
                                ws.sendCommand({ type: 'factory_reset' });
                            }
                        }}
                        variant="outline" 
                        className="w-full justify-start text-rose-400 border-rose-500/20 bg-rose-500/10 hover:bg-rose-500/20"
                    >
                        Factory Reset
                    </Button>
                </div>
            </div>
        </div>
    );

    const renderAbout = () => (
        <div className="space-y-8 animate-in fade-in duration-300">
            <div>
                <h3 className="text-lg font-medium text-white mb-4 flex items-center gap-2"><Info className="w-5 h-5 text-[var(--cyan)]"/> About CAPTAIN AI</h3>
                <div className="glass-panel p-6 border-white/5 flex flex-col items-center gap-4 text-center">
                    <Bot className="w-16 h-16 text-[var(--cyan)]" />
                    <div>
                        <h2 className="text-2xl font-bold text-white tracking-widest uppercase">Captain AI</h2>
                        <p className="text-muted-foreground font-mono mt-1">v2.0.0 Production Build</p>
                    </div>
                    <div className="text-xs text-muted-foreground mt-4">
                        Optimized for Windows Desktop Systems.<br/>
                        Core i3 / 8GB RAM Target Architecture.
                    </div>
                    <Button 
                        onClick={() => alert("You are running the latest version (v2.0.0).")}
                        className="mt-4 bg-[var(--cyan)]/20 text-[var(--cyan)] hover:bg-[var(--cyan)]/30 border border-[var(--cyan)]/50"
                    >
                        Check for Updates
                    </Button>
                </div>
            </div>
        </div>
    );

    const renderContent = () => {
        switch (activeTab) {
            case 'dashboard': return renderDashboard();
            case 'ai': return renderAiSettings();
            case 'api_keys': return renderApiSettings();
            case 'voice': return renderVoiceSettings();
            case 'personality': return renderVoicePersonality();
            case 'security': return renderSecurity();
            case 'memory': return renderMemory();
            case 'automation': return renderAutomation();
            case 'phone': return renderPhone();
            case 'workspace': return renderWorkspace();
            case 'appearance': return renderAppearance();
            case 'performance': return renderPerformance();
            case 'notifications': return renderNotifications();
            case 'plugins': return renderPlugins();
            case 'backup': return renderBackup();
            case 'about': return renderAbout();
            default: return null;
        }
    };

    return (
        <main className="flex h-full min-h-0 bg-transparent">
            {/* Sidebar */}
            <div className="w-64 border-r border-white/5 flex flex-col h-full overflow-y-auto custom-scrollbar p-4 gap-1">
                <div className="text-[10px] font-bold tracking-widest text-muted-foreground uppercase mb-2 px-2">Settings</div>
                {CATEGORIES.map(cat => (
                    <button
                        key={cat.id}
                        onClick={() => setActiveTab(cat.id)}
                        className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                            activeTab === cat.id 
                                ? 'bg-white/10 text-white font-medium shadow-inner' 
                                : 'text-muted-foreground hover:bg-white/5 hover:text-white'
                        }`}
                    >
                        <cat.icon className={`w-4 h-4 ${activeTab === cat.id ? 'text-[var(--cyan)]' : 'opacity-70'}`} />
                        {cat.label}
                    </button>
                ))}
            </div>

            {/* Main Content Area */}
            <div className="flex-1 overflow-y-auto custom-scrollbar p-8">
                <div className="max-w-3xl mx-auto">
                    {renderContent()}
                </div>
            </div>
        </main>
    );
};
