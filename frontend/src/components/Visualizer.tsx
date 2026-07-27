import React, { useEffect, useRef, useMemo } from "react";
import { cn } from "@/lib/utils";

interface OrbProps {
    aiState: string;
}

const Orb3DCanvas = React.memo(function Orb3DCanvas({ aiState }: OrbProps) {
    const canvasRef = useRef<HTMLCanvasElement>(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const maybeCtx = canvas.getContext("2d");
        if (!maybeCtx) return;
        // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
        const ctx = maybeCtx;

        let animationFrameId: number;
        let width = canvas.offsetWidth;
        let height = canvas.offsetHeight;
        canvas.width = width;
        canvas.height = height;

        const resizeObserver = new ResizeObserver((entries) => {
            for (const entry of entries) {
                width = entry.contentRect.width;
                height = entry.contentRect.height;
                canvas.width = width;
                canvas.height = height;
            }
        });
        resizeObserver.observe(canvas);

        const numParticles = 750;
        const sphereRadius = 80;
        const focalLength = 210;

        const particles: { phi: number; theta: number; speedOffset: number }[] = [];
        for (let i = 0; i < numParticles; i++) {
            const phi = Math.acos(1 - (2 * i) / numParticles);
            const theta = Math.sqrt(numParticles * Math.PI) * phi;
            particles.push({ phi, theta, speedOffset: Math.random() * Math.PI * 2 });
        }

        const numAmbient = 60;
        const ambientParticles: { x: number; y: number; vx: number; vy: number; alpha: number; r: number }[] = [];
        for (let i = 0; i < numAmbient; i++) {
            const isLeft = Math.random() > 0.5;
            ambientParticles.push({
                x: isLeft ? Math.random() * (width * 0.35) : width * 0.65 + Math.random() * (width * 0.35),
                y: Math.random() * height,
                vx: (Math.random() - 0.5) * 0.16,
                vy: (Math.random() - 0.5) * 0.16,
                alpha: Math.random() * 0.35 + 0.1,
                r: Math.random() * 0.7 + 0.3,
            });
        }

        const projectedPoints: { x: number; y: number; z: number; colorStr: string; alpha: number }[] = [];

        // Pause rendering entirely while the window is hidden/minimized —
        // there's no reason to spend CPU/GPU on a 750-particle canvas
        // animation nobody can see, and it frees up cycles for the
        // real-time audio pipeline running alongside it.
        let isVisible = document.visibilityState === "visible";
        const handleVisibility = () => {
            isVisible = document.visibilityState === "visible";
            if (isVisible) {
                animationFrameId = requestAnimationFrame(animate);
            }
        };
        document.addEventListener("visibilitychange", handleVisibility);

        function animate(timestamp: number) {
            if (!isVisible) return;   // don't schedule the next frame while hidden
            ctx.clearRect(0, 0, width, height);
            const centerX = width / 2;
            const centerY = height / 2 - 12;

            const glowGrad = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, sphereRadius * 1.5);
            glowGrad.addColorStop(0, "rgba(6, 240, 255, 0.18)");
            glowGrad.addColorStop(0.5, "rgba(139, 92, 246, 0.04)");
            glowGrad.addColorStop(1, "rgba(0, 0, 0, 0)");
            ctx.fillStyle = glowGrad;
            ctx.beginPath();
            ctx.arc(centerX, centerY, sphereRadius * 1.5, 0, Math.PI * 2);
            ctx.fill();

            let waveAmp = 14, waveFreq = 3.0, rotSpeed = 0.00035, speedMultiplier = 1.0;
            if (aiState === "SPEAKING") { waveAmp = 22; waveFreq = 4.0; rotSpeed = 0.00065; speedMultiplier = 2.2; }
            else if (aiState === "THINKING") { waveAmp = 8; waveFreq = 2.0; rotSpeed = 0.00015; speedMultiplier = 1.5; }
            else if (aiState === "MUTED") { waveAmp = 2.0; waveFreq = 1.0; rotSpeed = 0.00005; speedMultiplier = 0.2; }

            const time = timestamp * 0.0015 * speedMultiplier;
            projectedPoints.length = 0;

            particles.forEach((p) => {
                const wave1 = Math.sin(p.theta * waveFreq + time * 1.6) * Math.cos(p.phi * (waveFreq + 0.5) - time * 1.1);
                const wave2 = Math.cos(p.speedOffset + time * 2.0) * (waveAmp / 30);
                const radiusMod = sphereRadius + (wave1 + wave2) * waveAmp;

                const x = radiusMod * Math.sin(p.phi) * Math.cos(p.theta);
                const y = radiusMod * Math.sin(p.phi) * Math.sin(p.theta);
                const z = radiusMod * Math.cos(p.phi);

                const rotY = timestamp * rotSpeed;
                const rotX = timestamp * (rotSpeed * 0.4);

                const cosY = Math.cos(rotY + p.speedOffset * 0.005);
                const sinY = Math.sin(rotY + p.speedOffset * 0.005);
                const x1 = x * cosY - z * sinY;
                const z1 = z * cosY + x * sinY;

                const cosX = Math.cos(rotX);
                const sinX = Math.sin(rotX);
                const y2 = y * cosX - z1 * sinX;
                const z2 = z1 * cosX + y * sinX;

                const scale = focalLength / (focalLength + z2);
                const canvasX = centerX + x1 * scale;
                const canvasY = centerY + y2 * scale;

                const ratio = Math.max(0, Math.min(1, (x1 + sphereRadius * 1.1) / (sphereRadius * 2.2)));
                let red, green, blue;
                if (ratio < 0.5) {
                    const t = ratio * 2;
                    red = Math.floor(6 + t * 133); green = Math.floor(240 + t * (92 - 240)); blue = Math.floor(255 + t * (246 - 255));
                } else {
                    const t = (ratio - 0.5) * 2;
                    red = Math.floor(139 + t * 97); green = Math.floor(92 + t * (72 - 92)); blue = Math.floor(246 + t * (153 - 246));
                }

                const alpha = Math.max(0.18, (z2 + sphereRadius * 1.5) / (sphereRadius * 3));
                const colorStr = `rgba(${red}, ${green}, ${blue}, ${alpha})`;
                const pSize = Math.max(0.55, (z2 + sphereRadius * 1.5) / (sphereRadius * 2.5)) * 0.85;

                ctx.beginPath();
                ctx.arc(canvasX, canvasY, pSize, 0, Math.PI * 2);
                ctx.fillStyle = colorStr;
                ctx.fill();

                projectedPoints.push({ x: canvasX, y: canvasY, z: z2, colorStr: `rgba(${red}, ${green}, ${blue}, ${alpha * 0.045})`, alpha });
            });

            ctx.lineWidth = 0.4;
            for (let i = 0; i < projectedPoints.length; i += 8) {
                for (let j = i + 1; j < projectedPoints.length; j += 12) {
                    const pt1 = projectedPoints[i];
                    const pt2 = projectedPoints[j];
                    const dx = pt1.x - pt2.x;
                    const dy = pt1.y - pt2.y;
                    if (dx * dx + dy * dy < 1024) {
                        ctx.strokeStyle = pt1.colorStr;
                        ctx.beginPath();
                        ctx.moveTo(pt1.x, pt1.y);
                        ctx.lineTo(pt2.x, pt2.y);
                        ctx.stroke();
                    }
                }
            }

            ambientParticles.forEach((ap) => {
                ap.x += ap.vx;
                ap.y += ap.vy;
                if (ap.x < 0) ap.x = width * 0.35;
                if (ap.x > width) ap.x = width * 0.65;
                if (ap.y < 0 || ap.y > height) ap.vy *= -1;
                const sideRatio = ap.x / width;
                ctx.beginPath();
                ctx.arc(ap.x, ap.y, ap.r, 0, Math.PI * 2);
                ctx.fillStyle = `rgba(${Math.floor(6 + sideRatio * 162)}, ${Math.floor(182 - sideRatio * 97)}, ${Math.floor(212 + sideRatio * 35)}, ${ap.alpha})`;
                ctx.fill();
            });

            animationFrameId = requestAnimationFrame(animate);
        }

        animationFrameId = requestAnimationFrame(animate);
        return () => {
            cancelAnimationFrame(animationFrameId);
            resizeObserver.disconnect();
            document.removeEventListener("visibilitychange", handleVisibility);
        };
    }, [aiState]);

    return <canvas ref={canvasRef} className="absolute inset-0 h-full w-full pointer-events-none" />;
});

interface VisualizerProps {
    aiState: string;
}

const Visualizer = React.memo(function Visualizer({ aiState }: VisualizerProps) {
    const { statusText, pulseColor, textColor } = useMemo(() => {
        if (aiState === "SPEAKING") return { statusText: "Captain is speaking", pulseColor: "bg-[var(--emerald)]/60", textColor: "text-[var(--emerald)]" };
        if (aiState === "THINKING") return { statusText: "Thinking...", pulseColor: "bg-[var(--amber)]/60", textColor: "text-[var(--amber)]" };
        if (aiState === "MUTED") return { statusText: "Microphone Muted", pulseColor: "bg-[var(--rose)]/60", textColor: "text-[var(--rose)]" };
        return { statusText: "I'm listening, Boss", pulseColor: "bg-[var(--cyan)]/60", textColor: "text-[var(--cyan)]" };
    }, [aiState]);

    return (
        <div className="relative flex h-[260px] w-full items-center justify-center select-none overflow-hidden">
            <Orb3DCanvas aiState={aiState} />
            <div className="absolute bottom-2 flex flex-col items-center z-10">
                <p className={cn("text-[13px] font-medium tracking-wider transition-colors duration-300", textColor)}>
                    {statusText}
                </p>
                <div className="mt-1 flex gap-1">
                    {Array.from({ length: 5 }).map((_, i) => (
                        <span
                            key={i}
                            className={cn("h-1 w-1 rounded-full animate-glow-pulse transition-colors duration-300", pulseColor)}
                            style={{ animationDelay: `${i * 0.15}s` }}
                        />
                    ))}
                </div>
            </div>
        </div>
    );
});

export default Visualizer;