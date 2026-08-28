import { useState } from "react";
import { ActionButton } from "./States";

export function BacktrackModal({
  onClose,
  onRun,
  running,
}: {
  onClose: () => void;
  onRun: (hours: number, particleCount: number) => void;
  running: boolean;
}) {
  const [hours, setHours] = useState(72);
  const [particleCount, setParticleCount] = useState(5000);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="backtrack-modal-title"
    >
      <div
        className="w-[380px] rounded-card border border-border bg-panel p-4 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="backtrack-modal-title" className="mb-1 text-sm font-semibold text-text-primary">
          Back-track Drift
        </h2>
        <p className="mb-4 text-xs2 text-text-secondary">
          Seed particles inside the slick and integrate backwards in time (RK4) against ocean current +
          windage to estimate the release origin. The cone widens going backwards — that is uncertainty,
          not noise.
        </p>

        <label className="mb-3 block">
          <span className="label-caps mb-1.5 block">Trace Window</span>
          <div className="flex gap-1.5">
            {[12, 24, 48, 72].map((h) => (
              <button
                key={h}
                onClick={() => setHours(h)}
                className={`flex-1 rounded-input border py-1.5 text-xs2 font-medium transition-colors ${
                  hours === h
                    ? "border-teal/50 bg-teal/15 text-teal"
                    : "border-border bg-elevated text-text-secondary hover:text-text-primary"
                }`}
              >
                {h}h
              </button>
            ))}
          </div>
        </label>

        <label className="mb-4 block">
          <span className="label-caps mb-1.5 block">
            Particle Count: <span className="mono-num text-text-primary">{particleCount.toLocaleString()}</span>
          </span>
          <input
            type="range"
            min={500}
            max={5000}
            step={500}
            value={particleCount}
            onChange={(e) => setParticleCount(Number(e.target.value))}
            className="w-full accent-teal"
          />
        </label>

        <div className="flex justify-end gap-2">
          <ActionButton onClick={onClose} disabled={running}>
            Cancel
          </ActionButton>
          <ActionButton variant="primary" onClick={() => onRun(hours, particleCount)} disabled={running}>
            {running ? "Running…" : "Run Back-track"}
          </ActionButton>
        </div>
      </div>
    </div>
  );
}
