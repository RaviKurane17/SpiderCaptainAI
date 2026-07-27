import React, { useState, useEffect } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Brain, Save, X } from "lucide-react";
import { MemoryRecord } from "./MemoryList";

interface MemoryDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    initialData?: MemoryRecord | null;
    onSave: (data: Partial<MemoryRecord>) => void;
}

const CATEGORIES = [
    "Personal", "Education", "Projects", "Coding", "Programming", 
    "Career", "Goals", "Preferences", "Communication", "Workspace", 
    "Automation", "Tasks", "Files", "Folders", "Schedules", 
    "Devices", "Accounts", "Bookmarks", "Research", "Custom"
];

export const MemoryDialog: React.FC<MemoryDialogProps> = ({ open, onOpenChange, initialData, onSave }) => {
    const [title, setTitle] = useState("");
    const [summary, setSummary] = useState("");
    const [category, setCategory] = useState("Personal");
    const [tags, setTags] = useState("");
    const [privacy, setPrivacy] = useState("Normal");
    const [priority, setPriority] = useState("Normal");

    // Populate data when editing
    useEffect(() => {
        if (open && initialData) {
            setTitle(initialData.title || "");
            setSummary(initialData.summary || "");
            setCategory(initialData.category || "Personal");
            setTags(initialData.tags || "");
            setPrivacy(initialData.privacy || "Normal");
            setPriority(initialData.priority || "Normal");
        } else if (open && !initialData) {
            // Reset for new memory
            setTitle("");
            setSummary("");
            setCategory("Personal");
            setTags("");
            setPrivacy("Normal");
            setPriority("Normal");
        }
    }, [open, initialData]);

    const handleSave = () => {
        if (!title.trim() || !summary.trim()) return;
        
        onSave({
            ...(initialData ? { id: initialData.id } : {}),
            title,
            summary,
            category,
            tags,
            privacy,
            priority,
            source: initialData ? initialData.source : "Manual",
            layer: "Long-Term"
        });
        onOpenChange(false);
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[500px] bg-black/95 border border-[var(--cyan)]/20 text-white backdrop-blur-2xl shadow-[0_0_50px_rgba(0,255,255,0.05)]">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2 text-[var(--cyan)]">
                        <Brain className="w-5 h-5" />
                        {initialData ? "Edit Memory" : "Add Memory"}
                    </DialogTitle>
                    <DialogDescription className="text-muted-foreground text-xs">
                        Teach CAPTAIN AI a new fact, preference, or concept.
                    </DialogDescription>
                </DialogHeader>

                <div className="grid gap-4 py-4">
                    <div className="grid gap-2">
                        <Label htmlFor="title" className="text-xs text-muted-foreground uppercase font-mono tracking-wider">Title</Label>
                        <Input 
                            id="title" 
                            placeholder="e.g. My Workspace Path" 
                            value={title} 
                            onChange={e => setTitle(e.target.value)} 
                            className="bg-white/5 border-white/10 text-white focus:border-[var(--cyan)]/50"
                        />
                    </div>

                    <div className="grid gap-2">
                        <Label htmlFor="summary" className="text-xs text-muted-foreground uppercase font-mono tracking-wider">Content / Summary</Label>
                        <Textarea 
                            id="summary" 
                            placeholder="e.g. My primary workspace is located at D:\Projects" 
                            value={summary} 
                            onChange={e => setSummary(e.target.value)} 
                            className="bg-white/5 border-white/10 text-white focus:border-[var(--cyan)]/50 min-h-[100px] resize-none"
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="grid gap-2">
                            <Label className="text-xs text-muted-foreground uppercase font-mono tracking-wider">Category</Label>
                            <Select value={category} onValueChange={setCategory}>
                                <SelectTrigger className="bg-white/5 border-white/10 text-white focus:ring-[var(--cyan)]/50">
                                    <SelectValue placeholder="Select Category" />
                                </SelectTrigger>
                                <SelectContent className="bg-black border-white/10 max-h-[200px]">
                                    {CATEGORIES.map(cat => (
                                        <SelectItem key={cat} value={cat} className="text-white focus:bg-white/10 focus:text-white cursor-pointer">
                                            {cat}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        
                        <div className="grid gap-2">
                            <Label className="text-xs text-muted-foreground uppercase font-mono tracking-wider">Privacy</Label>
                            <Select value={privacy} onValueChange={setPrivacy}>
                                <SelectTrigger className="bg-white/5 border-white/10 text-white focus:ring-[var(--cyan)]/50">
                                    <SelectValue placeholder="Privacy Level" />
                                </SelectTrigger>
                                <SelectContent className="bg-black border-white/10">
                                    <SelectItem value="Normal" className="text-white focus:bg-white/10 cursor-pointer">Normal</SelectItem>
                                    <SelectItem value="Private" className="text-amber-400 focus:bg-white/10 cursor-pointer">Private</SelectItem>
                                    <SelectItem value="Sensitive" className="text-rose-400 focus:bg-white/10 cursor-pointer">Sensitive</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4">
                        <div className="grid gap-2">
                            <Label htmlFor="tags" className="text-xs text-muted-foreground uppercase font-mono tracking-wider">Tags (Comma Separated)</Label>
                            <Input 
                                id="tags" 
                                placeholder="e.g. Code, UI, Config" 
                                value={tags} 
                                onChange={e => setTags(e.target.value)} 
                                className="bg-white/5 border-white/10 text-white focus:border-[var(--cyan)]/50 text-xs"
                            />
                        </div>
                        
                        <div className="grid gap-2">
                            <Label className="text-xs text-muted-foreground uppercase font-mono tracking-wider">Priority</Label>
                            <Select value={priority} onValueChange={setPriority}>
                                <SelectTrigger className="bg-white/5 border-white/10 text-white focus:ring-[var(--cyan)]/50">
                                    <SelectValue placeholder="Priority" />
                                </SelectTrigger>
                                <SelectContent className="bg-black border-white/10">
                                    <SelectItem value="Low" className="text-white focus:bg-white/10 cursor-pointer">Low</SelectItem>
                                    <SelectItem value="Normal" className="text-[var(--cyan)] focus:bg-white/10 cursor-pointer">Normal</SelectItem>
                                    <SelectItem value="High" className="text-purple-400 focus:bg-white/10 cursor-pointer">High</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                </div>

                <DialogFooter className="gap-2 sm:justify-between">
                    <Button variant="ghost" className="text-muted-foreground hover:text-white hover:bg-white/10" onClick={() => onOpenChange(false)}>
                        <X className="w-4 h-4 mr-2" /> Cancel
                    </Button>
                    <Button 
                        disabled={!title.trim() || !summary.trim()} 
                        className="bg-[var(--cyan)]/20 text-[var(--cyan)] hover:bg-[var(--cyan)]/30 border border-[var(--cyan)]/50" 
                        onClick={handleSave}
                    >
                        <Save className="w-4 h-4 mr-2" /> Save Memory
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
};
