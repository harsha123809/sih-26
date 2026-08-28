import type { OilClass, ReliabilityVerdict, VesselMatchStatus } from "../types/api";

export const OIL_COLORS: Record<OilClass, string> = {
  open_water: "#2A3444",
  crude_oil: "#F2A93B",
  heavy_fuel_oil: "#E24E42",
  look_alike: "#6B7DA8",
  ship: "#34D3C4",
  land: "#3A4456",
  unresolved: "#8A97A8",
};

export const OIL_LABELS: Record<OilClass, string> = {
  open_water: "Open Water",
  crude_oil: "Crude Oil",
  heavy_fuel_oil: "Heavy Fuel Oil",
  look_alike: "Look-alike",
  ship: "Ship",
  land: "Land",
  unresolved: "Unresolved (No Polarimetry)",
};

export const VERDICT_META: Record<
  ReliabilityVerdict,
  { label: string; tone: "danger" | "warn" | "ok" }
> = {
  UNRELIABLE_LOW_WIND: { label: "Unreliable — Low Wind", tone: "danger" },
  DEGRADED_LOW: { label: "Degraded — Low Wind", tone: "warn" },
  OPTIMAL: { label: "Optimal", tone: "ok" },
  DEGRADED_HIGH: { label: "Degraded — High Wind", tone: "warn" },
  UNRELIABLE_HIGH_WIND: { label: "Unreliable — High Wind", tone: "danger" },
};

export const VESSEL_STATUS_META: Record<
  VesselMatchStatus,
  { label: string; color: string }
> = {
  MATCHED: { label: "Matched", color: "#34D3C4" },
  DARK_SHIP: { label: "Dark Ship", color: "#C04FD4" },
  SPOOFING_SUSPECTED: { label: "Spoofing Suspected", color: "#C04FD4" },
};

export function toneClasses(tone: "danger" | "warn" | "ok"): string {
  switch (tone) {
    case "ok":
      return "bg-teal/10 text-teal border-teal/30";
    case "warn":
      return "bg-amber/10 text-amber border-amber/30";
    case "danger":
      return "bg-hfo-red/10 text-hfo-red border-hfo-red/30";
  }
}

export function fmtPct(v: number): string {
  return `${(v * 100).toFixed(0)}%`;
}

export function fmtArea(m2: number): string {
  if (m2 >= 1_000_000) return `${(m2 / 1_000_000).toFixed(2)} km²`;
  return `${m2.toFixed(0)} m²`;
}

export function fmtDist(m: number): string {
  if (m >= 1000) return `${(m / 1000).toFixed(1)} km`;
  return `${m.toFixed(0)} m`;
}
