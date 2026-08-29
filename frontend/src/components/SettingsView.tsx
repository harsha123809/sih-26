import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { LoadingState, SectionLabel } from "./States";

export function SettingsView() {
  const [config, setConfig] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    api.configThresholds().then(setConfig).catch(() => setConfig({}));
  }, []);

  if (!config) return <div className="p-6"><LoadingState label="Loading configuration…" /></div>;

  return (
    <div className="scrollbar-thin h-full overflow-y-auto p-6">
      <SectionLabel>Physics-Gate &amp; Attribution Thresholds</SectionLabel>
      <p className="mb-4 max-w-[70ch] text-sm text-text-secondary">
        These live in <code className="mono-num text-text-primary">backend/app/config/thresholds.py</code>,
        outside the model and scoring code, so an operator can retune reliability behaviour without touching
        logic. Read-only here.
      </p>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {Object.entries(config).map(([section, values]) => (
          <div key={section} className="rounded-card border border-border bg-panel p-4">
            <h3 className="mb-2 text-xs2 font-semibold uppercase tracking-[0.08em] text-teal">
              {section.replace(/_/g, " ")}
            </h3>
            <div className="flex flex-col gap-1">
              {typeof values === "object" && values !== null ? (
                Object.entries(values as Record<string, unknown>).map(([k, v]) => (
                  <div key={k} className="flex justify-between text-xs2">
                    <span className="text-text-secondary">{k.replace(/_/g, " ")}</span>
                    <span className="mono-num text-text-primary">{String(v)}</span>
                  </div>
                ))
              ) : (
                <span className="mono-num text-text-primary">{String(values)}</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
