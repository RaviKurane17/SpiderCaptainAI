import React, { useState, useEffect } from "react";
import { 
    Folder, FolderOpen, Code2, Image as ImageIcon, FileText, 
    Search, ArrowUp, RefreshCw, LayoutGrid, List, FileArchive,
    Trash2, Edit, Copy, FilePlus, Sparkles, MoveRight, 
    GitBranch, TerminalSquare, PlusCircle, Archive,
    HardDrive, Home, Monitor, FileSpreadsheet, Download, Image, Video, Music
} from "lucide-react";
import { useFiles, FileItem, DriveInfo } from "../../hooks/useFiles";
import { cn } from "@/lib/utils";

// Assuming Shadcn standard exports
import {
    ContextMenu,
    ContextMenuContent,
    ContextMenuItem,
    ContextMenuSeparator,
    ContextMenuTrigger,
} from "@/components/ui/context-menu";

interface FilesPanelProps {
    wsRef: React.MutableRefObject<WebSocket | null>;
}

export const FilesPanel: React.FC<FilesPanelProps> = React.memo(({ wsRef }) => {
    const { 
        currentPath, files, loading, searchResults, isSearching, 
        workspaceProjects, devInfo, drives, specialFolders, recycleBin,
        navigateTo, navigateUp, refreshCurrentDir, fileOperation, searchFiles,
        requestPreview, previewData, setPreviewData,
        createProject, archiveProject, executeDevCommand,
        emptyRecycleBin
    } = useFiles(wsRef);

    const [viewMode, setViewMode] = useState<"grid" | "list">("list");
    const [searchQuery, setSearchQuery] = useState("");
    const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set());

    useEffect(() => {
        const timer = setTimeout(() => {
            searchFiles(searchQuery);
        }, 500);
        return () => clearTimeout(timer);
    }, [searchQuery, searchFiles]);

    const getFileIcon = (ext: string, is_dir: boolean) => {
        if (is_dir) return <Folder className="h-5 w-5 text-[var(--cyan)]" fill="currentColor" fillOpacity={0.2} />;
        if (['.zip', '.rar', '.7z', '.tar', '.gz'].includes(ext)) return <FileArchive className="h-5 w-5 text-amber-500" />;
        if (['.py', '.js', '.ts', '.tsx', '.json', '.html', '.css'].includes(ext)) return <Code2 className="h-5 w-5 text-[var(--cyan)]" />;
        if (['.png', '.jpg', '.jpeg', '.webp', '.gif', '.ico'].includes(ext)) return <ImageIcon className="h-5 w-5 text-rose-400" />;
        return <FileText className="h-5 w-5 text-muted-foreground" />;
    };

    const formatBytes = (bytes: number) => {
        if (bytes === undefined || bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    };

    const handleItemDoubleClick = (item: FileItem) => {
        if (item.is_dir) {
            navigateTo(item.path);
        } else {
            requestPreview(item.path);
        }
    };

    const toggleSelection = (e: React.MouseEvent, path: string) => {
        e.stopPropagation();
        const newSel = new Set(selectedFiles);
        if (e.ctrlKey || e.metaKey) {
            if (newSel.has(path)) newSel.delete(path);
            else newSel.add(path);
        } else {
            newSel.clear();
            newSel.add(path);
        }
        setSelectedFiles(newSel);
    };

    const displayFiles = searchQuery.trim() !== "" ? searchResults : files;

    const QuickAccessItem = ({ icon: Icon, label, path, colorClass = "text-muted-foreground" }: any) => (
        <button 
            onClick={() => navigateTo(path)} 
            className={cn(
                "w-full text-left px-3 py-1.5 text-[11px] rounded transition-all flex items-center gap-2",
                currentPath === path 
                    ? "bg-white/10 text-white font-medium" 
                    : "text-muted-foreground hover:bg-white/5 hover:text-white/80"
            )}
        >
            <Icon className={cn("h-3.5 w-3.5", currentPath === path ? "text-white" : colorClass)} /> 
            {label}
        </button>
    );

    return (
        <main className="flex min-h-0 h-full flex-col gap-3">
            {/* Top Toolbar */}
            <div className="glass-panel flex h-14 items-center px-4 justify-between">
                <div className="flex items-center gap-3">
                    <button onClick={navigateUp} className="p-1.5 hover:bg-white/10 rounded-md transition" title="Go Up">
                        <ArrowUp className="h-4 w-4 text-muted-foreground" />
                    </button>
                    <button onClick={refreshCurrentDir} className="p-1.5 hover:bg-white/10 rounded-md transition" title="Refresh">
                        <RefreshCw className={cn("h-4 w-4 text-muted-foreground", loading && "animate-spin")} />
                    </button>
                    <div className="flex items-center gap-2 ml-2 bg-black/20 border border-white/5 px-3 py-1.5 rounded-md min-w-[300px] overflow-hidden">
                        <FolderOpen className="h-3.5 w-3.5 text-[var(--cyan)] shrink-0" />
                        <span className="text-[11px] font-mono text-muted-foreground truncate" title={currentPath}>{currentPath || "Loading path..."}</span>
                    </div>
                </div>

                <div className="flex items-center gap-4">
                    <div className="relative w-64">
                        <Search className="absolute left-2.5 top-2 h-4 w-4 text-muted-foreground" />
                        <input 
                            type="text"
                            placeholder="System-wide Search..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full h-8 bg-black/20 border border-white/10 rounded-md pl-9 pr-3 text-xs text-foreground focus:outline-none focus:border-white/20 transition-all"
                        />
                        {isSearching && <RefreshCw className="absolute right-2.5 top-2 h-4 w-4 text-muted-foreground animate-spin" />}
                    </div>
                    <div className="flex items-center gap-1 bg-black/20 border border-white/5 rounded-md p-0.5">
                        <button onClick={() => setViewMode("list")} className={cn("p-1.5 rounded", viewMode === "list" ? "bg-white/10 text-white" : "text-muted-foreground")}>
                            <List className="h-4 w-4" />
                        </button>
                        <button onClick={() => setViewMode("grid")} className={cn("p-1.5 rounded", viewMode === "grid" ? "bg-white/10 text-white" : "text-muted-foreground")}>
                            <LayoutGrid className="h-4 w-4" />
                        </button>
                    </div>
                </div>
            </div>

            {/* Main Content Area */}
            <div className="flex flex-1 min-h-0 gap-3">
                
                {/* Sidebar Explorer */}
                <div className="w-56 glass-panel flex flex-col p-0 overflow-hidden select-none">
                    <div className="flex-1 overflow-y-auto p-2 flex flex-col gap-4">
                        
                        {/* Quick Access */}
                        <div className="flex flex-col gap-1">
                            <h3 className="text-[10px] font-bold tracking-widest text-muted-foreground/70 mb-1 px-2">QUICK ACCESS</h3>
                            {specialFolders?.Home && <QuickAccessItem icon={Home} label="Home" path={specialFolders.Home} />}
                            {specialFolders?.Desktop && <QuickAccessItem icon={Monitor} label="Desktop" path={specialFolders.Desktop} colorClass="text-blue-400" />}
                            {specialFolders?.Documents && <QuickAccessItem icon={FileSpreadsheet} label="Documents" path={specialFolders.Documents} colorClass="text-emerald-400" />}
                            {specialFolders?.Downloads && <QuickAccessItem icon={Download} label="Downloads" path={specialFolders.Downloads} colorClass="text-amber-400" />}
                            {specialFolders?.Pictures && <QuickAccessItem icon={Image} label="Pictures" path={specialFolders.Pictures} colorClass="text-rose-400" />}
                            {specialFolders?.Videos && <QuickAccessItem icon={Video} label="Videos" path={specialFolders.Videos} colorClass="text-purple-400" />}
                        </div>

                        {/* This PC (Drives) */}
                        <div className="flex flex-col gap-1">
                            <h3 className="text-[10px] font-bold tracking-widest text-muted-foreground/70 mb-1 px-2">THIS PC</h3>
                            {drives?.map((drive: DriveInfo, i) => (
                                <button 
                                    key={i}
                                    onClick={() => navigateTo(drive.mountpoint)}
                                    className={cn(
                                        "w-full text-left px-3 py-2 rounded transition-all flex flex-col gap-1.5 hover:bg-white/5",
                                        currentPath.startsWith(drive.mountpoint) ? "bg-white/5 border border-white/10" : "border border-transparent"
                                    )}
                                >
                                    <div className="flex items-center gap-2">
                                        <HardDrive className={cn("h-3.5 w-3.5", currentPath.startsWith(drive.mountpoint) ? "text-[var(--cyan)]" : "text-muted-foreground")} />
                                        <span className="text-[11px] font-semibold text-foreground">Local Disk ({drive.device})</span>
                                    </div>
                                    <div className="w-full h-1 bg-black/40 rounded-full overflow-hidden">
                                        <div className={cn("h-full", drive.percent > 90 ? "bg-rose-500" : "bg-[var(--cyan)]")} style={{ width: `${drive.percent}%` }}></div>
                                    </div>
                                    <span className="text-[9px] text-muted-foreground">{formatBytes(drive.free)} free of {formatBytes(drive.total)}</span>
                                </button>
                            ))}
                        </div>

                        {/* Workspace Hub */}
                        <div className="flex flex-col gap-1 mt-auto pt-4 border-t border-white/5">
                            <h3 className="text-[10px] font-bold tracking-widest text-muted-foreground/70 mb-1 px-2 flex justify-between items-center">
                                WORKSPACE <PlusCircle className="h-3 w-3 cursor-pointer hover:text-white" onClick={() => {
                                    const name = prompt("Enter project name:");
                                    if (name) createProject(name);
                                }}/>
                            </h3>
                            {workspaceProjects.filter(p => p.status === 'active').map(p => (
                                <ContextMenu key={p.id}>
                                    <ContextMenuTrigger>
                                        <button 
                                            onClick={() => navigateTo(p.path)} 
                                            className={cn(
                                                "w-full text-left px-3 py-1.5 text-[11px] rounded transition-all flex items-center gap-2",
                                                currentPath.includes(p.name) 
                                                    ? "bg-white/10 text-white font-medium" 
                                                    : "text-muted-foreground hover:bg-white/5 hover:text-white/80"
                                            )}
                                        >
                                            <Folder className={cn("h-3 w-3", currentPath.includes(p.name) && "text-[var(--cyan)]")} /> 
                                            {p.name}
                                        </button>
                                    </ContextMenuTrigger>
                                    <ContextMenuContent className="bg-black/90 backdrop-blur-xl border-white/10 text-foreground">
                                        <ContextMenuItem onClick={() => executeDevCommand('vscode', p.path)} className="text-xs cursor-pointer"><Code2 className="mr-2 h-4 w-4 text-[var(--cyan)]"/> Open in VS Code</ContextMenuItem>
                                        <ContextMenuItem onClick={() => executeDevCommand('terminal', p.path)} className="text-xs cursor-pointer"><TerminalSquare className="mr-2 h-4 w-4"/> Open Terminal</ContextMenuItem>
                                    </ContextMenuContent>
                                </ContextMenu>
                            ))}
                        </div>

                    </div>
                    
                    {/* Recycle Bin Status */}
                    {recycleBin && recycleBin.success && (
                        <div className="p-3 bg-[var(--rose)]/10 border-t border-[var(--rose)]/20 flex flex-col gap-2">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2 text-[11px] text-foreground">
                                    <Trash2 className="h-3.5 w-3.5 text-rose-400" />
                                    <span>Recycle Bin</span>
                                </div>
                                <button onClick={emptyRecycleBin} className="text-[10px] bg-rose-500/20 hover:bg-rose-500/40 text-rose-300 px-2 py-0.5 rounded transition">Empty</button>
                            </div>
                            <span className="text-[9px] text-muted-foreground">{recycleBin.count} items ({formatBytes(recycleBin.size)})</span>
                        </div>
                    )}

                    {/* Developer Info Panel */}
                    {devInfo && devInfo.is_git && (
                        <div className="p-3 bg-white/5 border-t border-white/10 flex flex-col gap-2">
                            <h3 className="text-[10px] font-bold tracking-widest text-muted-foreground mb-1">DEV ENVIRONMENT</h3>
                            <div className="flex items-center gap-2 text-[11px] text-foreground">
                                <GitBranch className="h-3.5 w-3.5 text-blue-400" />
                                <span className="truncate">{devInfo.branch}</span>
                                {devInfo.status === 'Dirty' && <span className="w-2 h-2 rounded-full bg-amber-400 ml-auto" title="Uncommitted changes"></span>}
                            </div>
                            <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                                <Code2 className="h-3.5 w-3.5 text-muted-foreground" />
                                <span>{devInfo.language}</span>
                            </div>
                        </div>
                    )}
                </div>

                {/* File Explorer View */}
                <div className="flex-1 glass-panel p-2 overflow-y-auto" onClick={() => setSelectedFiles(new Set())}>
                    {loading && displayFiles.length === 0 ? (
                        <div className="h-full flex items-center justify-center">
                            <span className="animate-pulse text-xs tracking-widest text-muted-foreground">SCANNING DIRECTORY...</span>
                        </div>
                    ) : displayFiles.length === 0 ? (
                        <div className="h-full flex flex-col items-center justify-center opacity-50 text-muted-foreground">
                            <FolderOpen className="h-10 w-10 mb-3" />
                            <span className="text-sm">This folder is empty</span>
                        </div>
                    ) : (
                        <div className={cn(
                            "p-2",
                            viewMode === "grid" ? "grid grid-cols-3 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 gap-3" : "flex flex-col gap-1"
                        )}>
                            {displayFiles.map((f, i) => {
                                const isSelected = selectedFiles.has(f.path);
                                return (
                                    <ContextMenu key={i}>
                                        <ContextMenuTrigger>
                                            <div 
                                                onClick={(e) => toggleSelection(e, f.path)}
                                                onDoubleClick={() => handleItemDoubleClick(f)}
                                                className={cn(
                                                    "group cursor-pointer select-none rounded-md transition-all border",
                                                    isSelected ? "bg-white/10 border-white/20" : "border-transparent hover:bg-white/5 hover:border-white/10",
                                                    viewMode === "grid" 
                                                        ? "flex flex-col items-center justify-center gap-2 p-4 text-center" 
                                                        : "flex items-center gap-3 px-3 py-2"
                                                )}
                                            >
                                                {getFileIcon(f.ext, f.is_dir)}
                                                
                                                {viewMode === "list" ? (
                                                    <>
                                                        <span className="text-[12px] text-foreground font-medium flex-1 truncate">{f.name}</span>
                                                        <span className="text-[11px] font-mono text-muted-foreground w-20 text-right">{f.is_dir ? '--' : formatBytes(f.size)}</span>
                                                        <span className="text-[11px] font-mono text-muted-foreground w-32 text-right truncate">
                                                            {new Date(f.modified * 1000).toLocaleDateString()}
                                                        </span>
                                                    </>
                                                ) : (
                                                    <span className="text-[11px] text-foreground font-medium truncate w-full px-1">{f.name}</span>
                                                )}
                                            </div>
                                        </ContextMenuTrigger>
                                        <ContextMenuContent className="w-56 bg-black/90 backdrop-blur-xl border-white/10 text-foreground">
                                            <ContextMenuItem onClick={() => handleItemDoubleClick(f)} className="text-xs cursor-pointer"><FolderOpen className="mr-2 h-4 w-4" /> Open</ContextMenuItem>
                                            {f.is_dir && (
                                                <>
                                                    <ContextMenuItem onClick={() => executeDevCommand('vscode', f.path)} className="text-xs cursor-pointer"><Code2 className="mr-2 h-4 w-4 text-[var(--cyan)]"/> Open in VS Code</ContextMenuItem>
                                                    <ContextMenuItem onClick={() => executeDevCommand('terminal', f.path)} className="text-xs cursor-pointer"><TerminalSquare className="mr-2 h-4 w-4"/> Open Terminal Here</ContextMenuItem>
                                                </>
                                            )}
                                            {!f.is_dir && <ContextMenuItem className="text-xs cursor-pointer text-[var(--cyan)]"><Sparkles className="mr-2 h-4 w-4" /> AI Summary</ContextMenuItem>}
                                            <ContextMenuSeparator className="bg-white/10" />
                                            <ContextMenuItem className="text-xs cursor-pointer"><Copy className="mr-2 h-4 w-4" /> Copy</ContextMenuItem>
                                            <ContextMenuItem className="text-xs cursor-pointer"><MoveRight className="mr-2 h-4 w-4" /> Move</ContextMenuItem>
                                            <ContextMenuItem onClick={() => {
                                                const newName = prompt("Enter new name:", f.name);
                                                if (newName && newName !== f.name) fileOperation("rename", f.path, newName);
                                            }} className="text-xs cursor-pointer"><Edit className="mr-2 h-4 w-4" /> Rename</ContextMenuItem>
                                            <ContextMenuSeparator className="bg-white/10" />
                                            <ContextMenuItem onClick={() => {
                                                if (confirm(`Move to Recycle Bin?`)) fileOperation("delete", f.path);
                                            }} className="text-xs focus:bg-[var(--rose)]/20 text-rose-400 focus:text-rose-300 cursor-pointer"><Trash2 className="mr-2 h-4 w-4" /> Delete</ContextMenuItem>
                                        </ContextMenuContent>
                                    </ContextMenu>
                                );
                            })}
                        </div>
                    )}
                </div>
            </div>

            {/* Simple File Preview Overlay */}
            {previewData && (
                <div className="absolute inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-10 animate-fade-in">
                    <div className="glass-panel flex flex-col w-full max-w-4xl max-h-full overflow-hidden shadow-2xl relative">
                        <div className="h-12 border-b border-white/10 flex items-center justify-between px-4 bg-white/5">
                            <span className="font-mono text-xs text-foreground font-bold">File Preview</span>
                            <button onClick={() => setPreviewData(null)} className="text-muted-foreground hover:text-white transition">✕</button>
                        </div>
                        <div className="flex-1 overflow-auto p-4 flex items-center justify-center bg-black/40">
                            {previewData.type === 'image' ? (
                                /* eslint-disable-next-line @next/next/no-img-element */
                                <img src={`file://${previewData.path}`} alt="Preview" className="max-w-full max-h-[70vh] object-contain rounded" />
                            ) : previewData.type === 'text' ? (
                                <pre className="text-[11px] font-mono text-[oklch(0.75_0.22_225)] w-full whitespace-pre-wrap">
                                    {previewData.content}
                                </pre>
                            ) : (
                                <span className="text-sm text-muted-foreground">Preview not available</span>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </main>
    );
});

FilesPanel.displayName = "FilesPanel";
