import { useEffect } from 'react';

export function useKeyboardShortcuts(actions: {
    onNewChat?: () => void;
    onSearchChat?: () => void;
    onSearchConversations?: () => void;
    onClearChat?: () => void;
    onStopGeneration?: () => void;
    onExport?: () => void;
}) {
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            // Check for modifier keys
            const isCtrl = e.ctrlKey || e.metaKey;
            
            if (isCtrl && e.key === 'n') {
                e.preventDefault();
                actions.onNewChat?.();
            } else if (isCtrl && e.shiftKey && e.key === 'f') {
                e.preventDefault();
                actions.onSearchConversations?.();
            } else if (isCtrl && !e.shiftKey && e.key === 'f') {
                e.preventDefault();
                actions.onSearchChat?.();
            } else if (isCtrl && e.key === 'l') {
                e.preventDefault();
                actions.onClearChat?.();
            } else if (isCtrl && e.key === 'e') {
                e.preventDefault();
                actions.onExport?.();
            } else if (e.key === 'Escape') {
                actions.onStopGeneration?.();
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [actions]);
}
