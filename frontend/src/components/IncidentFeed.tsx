import { useMemo, useState } from "react";
import { OilClassBadge, ReliabilityBadge } from "./Badges";
import { EmptyState } from "./States";
import { fmtDist } from "../lib/theme";
import type { IncidentSummary } from "../lib/types-local";

type SortKey = "time" | "confidence" | "deception";

export function IncidentFeed({
  incidents,
  selectedId,
  onSelect,
  collapsed,
  onToggleCollapsed,
}: {
  incidents: IncidentSummary[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  collapsed: boolean;
  onToggleCollapsed: () => void;
}) {
  const [sortKey, setSortKey] = useState<SortKey>("time");

  const sorted = useMemo(() => {
    const copy = [...incidents];
    if (sortKey === "confidence") copy.sort((a, b) => b.confidence - a.confidence);
    else if (sortKey === "deception") copy.sort((a, b) => (b.deceptionIndexM ?? -1) - (a.deceptionIndexM ?? -1));
    else copy.sort((a, b) => b.createdAt.localeCompare(a.createdAt));
    return copy;
  }, [incidents, sortKey]);

  if (collapsed) {
    return (
      <div className="flex w-8 flex-shrink-0 flex-col items-center border-r border-border bg-panel py-3">
        <button
          onClick={onToggleCollapsed}
          className="rounded-input p-1 text-text-secondary hover:bg-elevated hover:text-text-primary"
          title="Expand incident feed"
          aria-label="Expand incident feed"
        >
          »
        </button>
      </div>
    );
  }

  return (
    <div className="flex w-80 flex-shrink-0 flex-col border-r border-border bg-panel">
      <div className="flex items-center justify-between border-b border-border px-3 py-2.5">
        <span className="label-caps">Incident Feed</span>
        <div className="flex items-center gap-1">
          <select
            value={sortKey}
            onChange={(e) => setSortKey(e.target.value as SortKey)}
            className="rounded-input border border-border bg-elevated px-1.5 py-1 text-xs2 text-text-secondary focus-visible:outline-none"
            aria-label="Sort incidents by"
          >
            <option value="time">Newest</option>
            <option value="confidence">Confidence</option>
            <option value="deception">Deception Index</option>
          </select>
          <button
            onClick={onToggleCollapsed}
            className="rounded-input p-1 text-text-secondary hover:bg-elevated hover:text-text-primary"
            title="Collapse incident feed"
            aria-label="Collapse incident feed"
          >
            «
          </button>
        </div>
      </div>
      <div className="scrollbar-thin flex-1 overflow-y-auto p-2">
        {sorted.length === 0 ? (
          <EmptyState icon="◌" title="No incidents yet" hint="Select a scene and run analysis to create one." />
        ) : (
          <ul className="flex flex-col gap-1.5">
            {sorted.map((inc) => (
              <li key={inc.incidentId}>
                <button
                  onClick={() => onSelect(inc.incidentId)}
                  className={`w-full rounded-card border px-2.5 py-2 text-left transition-colors duration-150 ${
                    inc.incidentId === selectedId
                      ? "border-teal/50 bg-teal/10"
                      : "border-border bg-elevated hover:border-teal/30"
                  }`}
                >
                  <div className="mb-1 flex items-center justify-between gap-2">
                    <span className="truncate text-sm font-medium text-text-primary">{inc.sceneName}</span>
                    <StatusPill status={inc.status} />
                  </div>
                  <div className="mb-1.5 flex flex-wrap items-center gap-1">
                    <OilClassBadge oilClass={inc.predictedClass} />
                    <ReliabilityBadge verdict={inc.verdict} />
                  </div>
                  <div className="flex items-center justify-between text-xs2 text-text-secondary">
                    <span className="mono-num">{(inc.confidence * 100).toFixed(0)}% conf.</span>
                    {inc.deceptionIndexM != null && (
                      <span className="mono-num text-violet">DI {fmtDist(inc.deceptionIndexM)}</span>
                    )}
                  </div>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function StatusPill({ status }: { status: "OPEN" | "CONFIRMED" | "FALSE_POSITIVE" }) {
  const map = {
    OPEN: { label: "Open", cls: "text-text-secondary border-border" },
    CONFIRMED: { label: "Confirmed", cls: "text-hfo-red border-hfo-red/40 bg-hfo-red/10" },
    FALSE_POSITIVE: { label: "False Positive", cls: "text-text-secondary border-border bg-elevated" },
  } as const;
  const m = map[status];
  return <span className={`flex-shrink-0 rounded-input border px-1.5 py-0.5 text-[10px] ${m.cls}`}>{m.label}</span>;
}
