import { useState, useEffect, useCallback } from "react";

export interface FileItem {
    name: string;
    path: string;
    is_dir: boolean;
    size: number;
    ext: string;
    modified: number;
    created?: number;
}

export interface WorkspaceProject {
    id: number;
    name: string;
    path: string;
    status: string;
    created_at: number;
    last_accessed: number;
}

export interface DevInfo {
    is_git: boolean;
    branch: string;
    status: string;
    language: string;
}

export interface DriveInfo {
    device: string;
    mountpoint: string;
    fstype: string;
    total: number;
    used: number;
    free: number;
    percent: number;
}

export function useFiles(wsRef: React.MutableRefObject<WebSocket | null>) {
    const [currentPath, setCurrentPath] = useState<string>("");
    const [files, setFiles] = useState<FileItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchResults, setSearchResults] = useState<FileItem[]>([]);
    const [isSearching, setIsSearching] = useState(false);
    const [previewData, setPreviewData] = useState<any>(null);

    // Workspace Management
    const [workspaceProjects, setWorkspaceProjects] = useState<WorkspaceProject[]>([]);
    const [workspacePinned, setWorkspacePinned] = useState<any[]>([]);
    const [workspaceRoot, setWorkspaceRoot] = useState<string>("");

    // System Info
    const [drives, setDrives] = useState<DriveInfo[]>([]);
    const [specialFolders, setSpecialFolders] = useState<Record<string, string>>({});
    const [recycleBin, setRecycleBin] = useState<any>(null);

    // Dev Tools
    const [devInfo, setDevInfo] = useState<DevInfo | null>(null);

    useEffect(() => {
        const ws = wsRef.current;
        if (!ws) return;

        const handleMessage = (e: MessageEvent) => {
            try {
                const data = JSON.parse(e.data);
                if (data.type === "files_data") {
                    setFiles(data.files);
                    setCurrentPath(data.path);
                    setLoading(false);
                } else if (data.type === "file_op_result") {
                    // Refresh current directory after an operation
                    if (data.result?.success) {
                        refreshCurrentDir();
                    }
                } else if (data.type === "file_search_results") {
                    setSearchResults(data.files);
                    setIsSearching(false);
                } else if (data.type === "file_preview_data") {
                    setPreviewData(data.preview);
                } else if (data.type === "workspace_state_data") {
                    setWorkspaceProjects(data.data.projects);
                    setWorkspacePinned(data.data.pinned);
                    setWorkspaceRoot(data.data.root);
                } else if (data.type === "project_action_result") {
                    if (data.result?.success) {
                        refreshWorkspace();
                    }
                } else if (data.type === "system_info_data") {
                    setDrives(data.drives);
                    setSpecialFolders(data.special_folders);
                    setRecycleBin(data.recycle_bin);
                } else if (data.type === "dev_info_data") {
                    if (data.path === currentPath) {
                        setDevInfo(data.info);
                    }
                } else if (data.type === "recycle_bin_result") {
                    if (data.result?.success) {
                        refreshSystemInfo();
                    }
                }
            } catch (err) {
                console.error("Failed to parse file message", err);
            }
        };

        ws.addEventListener("message", handleMessage);

        // Initial load
        if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: "get_files" }));
            ws.send(JSON.stringify({ type: "get_workspace_state" }));
            ws.send(JSON.stringify({ type: "get_system_info" }));
        }

        return () => ws.removeEventListener("message", handleMessage);
    }, [wsRef]);

    const navigateTo = useCallback((path: string) => {
        if (!wsRef.current) return;
        setLoading(true);
        wsRef.current.send(JSON.stringify({ type: "get_files", path }));
        wsRef.current.send(JSON.stringify({ type: "get_dev_info", path }));
    }, [wsRef]);

    const navigateUp = useCallback(() => {
        if (!currentPath) return;
        // Basic path up calculation
        const parts = currentPath.replace(/\\/g, '/').split('/');
        parts.pop();
        if (parts.length > 0) {
            navigateTo(parts.join('/'));
        }
    }, [currentPath, navigateTo]);

    const refreshCurrentDir = useCallback(() => {
        navigateTo(currentPath);
    }, [currentPath, navigateTo]);

    const fileOperation = useCallback((operation: string, source: string, dest?: string) => {
        if (!wsRef.current) return;
        wsRef.current.send(JSON.stringify({
            type: "file_operation",
            operation,
            source,
            dest
        }));
    }, [wsRef]);

    const searchFiles = useCallback((query: string) => {
        if (!wsRef.current) return;
        if (!query.trim()) {
            setSearchResults([]);
            return;
        }
        setIsSearching(true);
        wsRef.current.send(JSON.stringify({
            type: "search_files",
            query,
            path: currentPath
        }));
    }, [currentPath, wsRef]);

    const requestPreview = useCallback((path: string) => {
        if (!wsRef.current) return;
        setPreviewData(null); // Reset preview
        wsRef.current.send(JSON.stringify({ type: "get_file_preview", path }));
    }, [wsRef]);

    const refreshWorkspace = useCallback(() => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: "get_workspace_state" }));
        }
    }, [wsRef]);

    const refreshSystemInfo = useCallback(() => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: "get_system_info" }));
        }
    }, [wsRef]);

    const emptyRecycleBin = useCallback(() => {
        if (!wsRef.current) return;
        wsRef.current.send(JSON.stringify({ type: "empty_recycle_bin" }));
    }, [wsRef]);

    const createProject = useCallback((name: string) => {
        if (!wsRef.current) return;
        wsRef.current.send(JSON.stringify({ type: "create_project", name }));
    }, [wsRef]);

    const archiveProject = useCallback((name: string) => {
        if (!wsRef.current) return;
        wsRef.current.send(JSON.stringify({ type: "archive_project", name }));
    }, [wsRef]);

    const executeDevCommand = useCallback((command: string, path: string) => {
        if (!wsRef.current) return;
        wsRef.current.send(JSON.stringify({ type: "execute_dev_command", command, path }));
    }, [wsRef]);

    return {
        currentPath,
        files,
        loading,
        searchResults,
        isSearching,
        previewData,
        workspaceProjects,
        workspacePinned,
        workspaceRoot,
        devInfo,
        drives,
        specialFolders,
        recycleBin,
        navigateTo,
        navigateUp,
        refreshCurrentDir,
        fileOperation,
        searchFiles,
        requestPreview,
        setPreviewData,
        refreshWorkspace,
        refreshSystemInfo,
        emptyRecycleBin,
        createProject,
        archiveProject,
        executeDevCommand
    };
}
