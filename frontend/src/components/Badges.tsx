import type { OilClass, ReliabilityVerdict, VesselMatchStatus } from "../types/api";
import { OIL_COLORS, OIL_LABELS, VERDICT_META, VESSEL_STATUS_META, toneClasses } from "../lib/theme";

export function OilClassBadge({ oilClass }: { oilClass: OilClass }) {
  const color = OIL_COLORS[oilClass];
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-input border px-2 py-0.5 text-xs2 font-medium"
      style={{ borderColor: `${color}55`, color, backgroundColor: `${color}18` }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: color }} />
      {OIL_LABELS[oilClass]}
    </span>
  );
}

export function ReliabilityBadge({ verdict }: { verdict: ReliabilityVerdict }) {
  const meta = VERDICT_META[verdict];
  return (
    <span
      className={`inline-flex items-center rounded-input border px-2 py-0.5 text-xs2 font-medium ${toneClasses(meta.tone)}`}
    >
      {meta.label}
    </span>
  );
}

export function VesselStatusBadge({ status }: { status: VesselMatchStatus }) {
  const meta = VESSEL_STATUS_META[status];
  const glow = status !== "MATCHED";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-input border px-2 py-0.5 text-xs2 font-medium ${
        glow ? "animate-pulse" : ""
      }`}
      style={{ borderColor: `${meta.color}55`, color: meta.color, backgroundColor: `${meta.color}18` }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: meta.color }} />
      {meta.label}
    </span>
  );
}

export function ConfidenceReadout({ value, verdict }: { value: number; verdict: ReliabilityVerdict }) {
  const meta = VERDICT_META[verdict];
  return (
    <div className="flex items-baseline gap-2">
      <span className="mono-num text-lg font-semibold">{(value * 100).toFixed(0)}%</span>
      <ReliabilityBadge verdict={verdict} />
    </div>
  );
}
