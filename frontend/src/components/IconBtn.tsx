import React from "react";

const IconBtn = React.memo(function IconBtn({
    children,
    ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement>) {
    return (
        <button
            {...props}
            className="grid h-10 w-10 place-items-center rounded-lg border border-white/5 text-muted-foreground transition-all duration-300 hover:scale-105 hover:border-[oklch(0.75_0.22_225/0.5)] hover:text-[var(--cyan)] hover:shadow-[0_0_20px_oklch(0.75_0.22_225/0.35)] cursor-pointer"
        >
            {children}
        </button>
    );
});

export default IconBtn;
