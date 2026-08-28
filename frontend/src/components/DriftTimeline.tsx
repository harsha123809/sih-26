import { useEffect, useRef, useState } from "react";
import type { DriftConeFrame } from "../types/api";
import { ActionButton } from "./States";

export function DriftTimeline({
  frames,
  activeIndex,
  onChange,
}: {
  frames: DriftConeFrame[];
  activeIndex: number;
  onChange: (i: number) => void;
}) {
  const [playing, setPlaying] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const reducedMotion = useRef(
    typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches
  );

  useEffect(() => {
    if (!playing) {
      if (timerRef.current) clearInterval(timerRef.current);
      return;
    }
    if (reducedMotion.current) {
      onChange(frames.length - 1);
      setPlaying(false);
      return;
    }
    timerRef.current = setInterval(() => {
      onChange(activeIndex >= frames.length - 1 ? 0 : activeIndex + 1);
    }, 700);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing, activeIndex, frames.length]);

  const frame = frames[Math.min(activeIndex, frames.length - 1)];

  return (
    <div className="pointer-events-auto absolute bottom-4 left-1/2 z-10 w-[520px] -translate-x-1/2 rounded-card border border-border bg-panel/95 px-4 py-3 shadow-2xl backdrop-blur">
      <div className="mb-2 flex items-center justify-between">
        <span className="label-caps">Drift Cone Playback</span>
        <span className="mono-num text-xs2 text-teal">
          T-{frame.hours_back}h · spread {frame.particle_spread_m.toLocaleString()} m
        </span>
      </div>
      <div className="flex items-center gap-3">
        <ActionButton onClick={() => setPlaying((p) => !p)} variant={playing ? "primary" : "default"}>
          {playing ? "❚❚" : "►"}
        </ActionButton>
        <input
          type="range"
          min={0}
          max={frames.length - 1}
          value={activeIndex}
          onChange={(e) => {
            setPlaying(false);
            onChange(Number(e.target.value));
          }}
          className="w-full accent-teal"
          aria-label="Drift cone timeline"
        />
      </div>
      <div className="mt-1 flex justify-between text-[10px] text-text-secondary">
        <span>Now</span>
        <span>T-{frames[frames.length - 1]?.hours_back}h (origin estimate)</span>
      </div>
    </div>
  );
}
