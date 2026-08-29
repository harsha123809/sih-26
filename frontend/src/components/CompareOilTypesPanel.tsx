import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Detection } from "../types/api";

// Reference VV/VH ratio bands (dB), consistent with the scenario profiles the
// simulated inference wrapper draws from — the "fingerprint" ranges used to
// tell crude and HFO apart in Channel 2 of the model's input tensor.
const REFERENCE_BANDS = [
  { name: "Crude Oil (typ.)", low: 2.5, high: 4.0, color: "#F2A93B" },
  { name: "Heavy Fuel Oil (typ.)", low: 6.0, high: 8.5, color: "#E24E42" },
];

export function CompareOilTypesPanel({ detection, onClose }: { detection: Detection; onClose: () => void }) {
  const data = [
    ...REFERENCE_BANDS.map((b) => ({ label: b.name, low: b.low, band: b.high - b.low, color: b.color, isCurrent: false })),
    {
      label: "This Detection",
      low: Math.max(detection.vv_vh_ratio_db - 0.1, 0),
      band: 0.2,
      color: "#34D3C4",
      isCurrent: true,
    },
  ];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
    >
      <div className="w-[560px] rounded-card border border-border bg-panel p-4 shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="mb-1 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-text-primary">Compare Oil Types — VV/VH Fingerprint</h2>
          <button onClick={onClose} className="text-text-secondary hover:text-text-primary" aria-label="Close">
            ✕
          </button>
        </div>
        <p className="mb-4 text-xs2 text-text-secondary">
          VV/VH ratio (computed in linear power, then log-scaled) is the primary oil-type fingerprint: higher
          viscosity HFO dampens the cross-polarised return more strongly than low-viscosity crude, producing a
          higher ratio.
        </p>

        {!detection.has_polarimetry ? (
          <div className="rounded-card border border-amber/30 bg-amber/10 px-3 py-3 text-xs2 text-amber">
            VH channel unavailable for this scene — oil type is UNRESOLVED. Fabricating a VV/VH ratio without
            real cross-polarisation data would be a guess, not a measurement, so none is shown.
          </div>
        ) : (
          <div className="h-52 w-full">
            <ResponsiveContainer>
              <BarChart data={data} layout="vertical" margin={{ left: 8, right: 24 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#232D3B" horizontal={false} />
                <XAxis
                  type="number"
                  domain={[0, 10]}
                  tick={{ fill: "#8A97A8", fontSize: 11 }}
                  stroke="#232D3B"
                  label={{ value: "VV/VH ratio (dB)", position: "insideBottom", offset: -4, fill: "#8A97A8", fontSize: 11 }}
                />
                <YAxis type="category" dataKey="label" tick={{ fill: "#E4E9F0", fontSize: 11 }} stroke="#232D3B" width={120} />
                <Tooltip
                  contentStyle={{ background: "#18202C", border: "1px solid #232D3B", borderRadius: 6, fontSize: 12 }}
                  formatter={(_value, _name, entry) => {
                    const p = entry.payload as (typeof data)[number];
                    return [`${p.low.toFixed(1)}–${(p.low + p.band).toFixed(1)} dB`, "Range"];
                  }}
                />
                <Bar dataKey="low" stackId="a" fill="transparent" />
                <Bar dataKey="band" stackId="a" radius={[3, 3, 3, 3]}>
                  {data.map((d, i) => (
                    <Cell key={i} fill={d.color} fillOpacity={d.isCurrent ? 1 : 0.55} />
                  ))}
                </Bar>
                <ReferenceLine x={detection.vv_vh_ratio_db} stroke="#34D3C4" strokeDasharray="4 4" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        <div className="mt-3 flex items-center justify-between rounded-card border border-border bg-elevated px-3 py-2 text-xs2">
          <span className="text-text-secondary">Measured VV/VH ratio</span>
          <span className="mono-num text-teal">{detection.vv_vh_ratio_db.toFixed(2)} dB</span>
        </div>
      </div>
    </div>
  );
}
