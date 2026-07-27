import React, { useMemo } from "react";
import { Clock, Activity, MonitorCog, Network } from "lucide-react";
import PanelHeader from "./PanelHeader";

interface Metrics {
    cpu: number;
    ram: number;
    gpu: number;
    disk: number;
    uptime: string;
    processes: string;
    threads: string;
    network: string;
}

interface DonutProps {
    label: string;
    val: number;
    color: string;
}

const Donut = React.memo(function Donut({ label, val, color }: DonutProps) {
    const c = 2 * Math.PI * 28;
    return (
        <div className="flex flex-col items-center">
            <div className="relative h-14 w-14">
                <svg viewBox="0 0 64 64" className="h-full w-full -rotate-90">
                    <circle cx="32" cy="32" r="28" stroke="oklch(1 0 0 / 0.06)" strokeWidth="5" fill="none" />
                    <circle
                        cx="32" cy="32" r="28"
                        stroke={color} strokeWidth="5" fill="none"
                        strokeLinecap="round"
                        strokeDasharray={c}
                        strokeDashoffset={c - (c * val) / 100}
                        style={{ filter: `drop-shadow(0 0 6px ${color})`, transition: "stroke-dashoffset 800ms ease" }}
                    />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className="text-[8px] font-semibold tracking-[0.1em] text-muted-foreground">{label}</span>
                    <span className="text-[11px] font-bold" style={{ color }}>{val}%</span>
                </div>
            </div>
        </div>
    );
});

interface SystemOverviewProps {
    metrics: Metrics;
}

const SystemOverview = React.memo(function SystemOverview({ metrics }: SystemOverviewProps) {
    const dataMetrics = useMemo(() => [
        { label: "CPU",  val: metrics.cpu,  color: "oklch(0.75 0.22 225)" },
        { label: "RAM",  val: metrics.ram,  color: "oklch(0.78 0.19 160)" },
        { label: "GPU",  val: metrics.gpu,  color: "oklch(0.65 0.24 300)" },
        { label: "DISK", val: metrics.disk, color: "oklch(0.78 0.16 60)" },
    ], [metrics.cpu, metrics.ram, metrics.gpu, metrics.disk]);

    const rows = useMemo(() => [
        { icon: Clock,      label: "Uptime",    val: metrics.uptime },
        { icon: Activity,   label: "Processes", val: metrics.processes },
        { icon: MonitorCog, label: "Threads",   val: metrics.threads },
        { icon: Network,    label: "Network",   val: metrics.network, tabular: true },
    ], [metrics.uptime, metrics.processes, metrics.threads, metrics.network]);

    return (
        <div className="glass-panel glass-panel-hover p-2.5">
            <PanelHeader title="SYSTEM OVERVIEW" />
            <div className="mt-2 grid grid-cols-4 gap-2">
                {dataMetrics.map((m) => (
                    <Donut key={m.label} label={m.label} val={m.val} color={m.color} />
                ))}
            </div>
            <div className="mt-2 flex flex-col divide-y divide-white/5">
                {rows.map((r, i) => (
                    <div key={i} className="flex items-center justify-between py-0.5">
                        <div className="flex items-center gap-2.5 text-muted-foreground">
                            <r.icon className="h-3.5 w-3.5" strokeWidth={1.6} />
                            <span className="text-[13px]">{r.label}</span>
                        </div>
                        <span className={`text-[13px] text-foreground ${r.tabular ? "tabular-nums" : ""}`}>{r.val}</span>
                    </div>
                ))}
            </div>
        </div>
    );
});

export default SystemOverview;
