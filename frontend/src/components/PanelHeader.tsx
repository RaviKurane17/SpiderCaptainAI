import React from "react";
import { MoreHorizontal } from "lucide-react";

interface PanelHeaderProps {
    title: string;
    trailing?: React.ReactNode;
}

const PanelHeader = React.memo(function PanelHeader({ title, trailing }: PanelHeaderProps) {
    return (
        <div className="flex items-center justify-between">
            <h2 className="text-[13px] font-bold tracking-[0.24em] text-foreground">{title}</h2>
            {trailing ?? <MoreHorizontal className="h-4 w-4 text-muted-foreground" strokeWidth={1.8} />}
        </div>
    );
});

export default PanelHeader;
