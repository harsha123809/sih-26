import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { AISPosition, VesselProfile, VesselTruthGapResult } from "../types/api";
import { ActionButton, EmptyState, LoadingState, SectionLabel } from "./States";
import { VesselStatusBadge } from "./Badges";
import { fmtDist } from "../lib/theme";

export function VesselsView({
  onViewOnMap,
}: {
  onViewOnMap: (mmsi: string, track: AISPosition[]) => void;
}) {
  const [vessels, setVessels] = useState<VesselProfile[] | null>(null);
  const [flags, setFlags] = useState<(VesselTruthGapResult & { scene_id: string; scene_name: string })[] | null>(null);
  const [selected, setSelected] = useState<VesselProfile | null>(null);
  const [track, setTrack] = useState<AISPosition[] | null>(null);
  const [loadingTrack, setLoadingTrack] = useState(false);

  useEffect(() => {
    api.listVessels().then(setVessels).catch(() => setVessels([]));
    api.vesselsSpoofing().then(setFlags).catch(() => setFlags([]));
  }, []);

  const selectVessel = async (v: VesselProfile) => {
    setSelected(v);
    setLoadingTrack(true);
    try {
      const res = await api.vesselTrack(v.mmsi);
      setTrack(res.track as AISPosition[]);
    } catch {
      setTrack([]);
    } finally {
      setLoadingTrack(false);
    }
  };

  return (
    <div className="scrollbar-thin flex h-full gap-4 overflow-y-auto p-6">
      <div className="w-full max-w-md flex-shrink-0">
        <SectionLabel>Truth Gap Alerts</SectionLabel>
        {flags === null ? (
          <LoadingState label="Scanning scenes for spoofing / dark ships…" />
        ) : flags.length === 0 ? (
          <EmptyState icon="⚑" title="No flags" />
        ) : (
          <div className="mb-6 flex flex-col gap-2">
            {flags.map((f, i) => (
              <div key={i} className="rounded-card border border-violet/30 bg-violet/5 px-3 py-2.5">
                <div className="mb-1 flex items-center justify-between">
                  <span className="text-sm font-medium text-text-primary">
                    {f.vessel_profile?.name ?? "Unidentified hull"}
                  </span>
                  <VesselStatusBadge status={f.status} />
                </div>
                <div className="flex items-center justify-between text-xs2 text-text-secondary">
                  <span>{f.scene_name}</span>
                  {f.deception_index_m > 0 && <span className="mono-num text-violet">{fmtDist(f.deception_index_m)}</span>}
                </div>
              </div>
            ))}
          </div>
        )}

        <SectionLabel>Vessel Registry</SectionLabel>
        {vessels === null ? (
          <LoadingState label="Loading vessels…" />
        ) : (
          <div className="flex flex-col gap-1.5">
            {vessels.map((v) => (
              <button
                key={v.mmsi}
                onClick={() => selectVessel(v)}
                className={`rounded-card border px-3 py-2 text-left transition-colors ${
                  selected?.mmsi === v.mmsi ? "border-teal/50 bg-teal/10" : "border-border bg-panel hover:border-teal/30"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm text-text-primary">{v.name}</span>
                  <span className="mono-num text-xs2 text-text-secondary">{v.mmsi}</span>
                </div>
                <div className="text-xs2 text-text-secondary">
                  {v.vessel_type} · {v.gross_tonnage.toLocaleString()} GT
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="flex-1">
        <SectionLabel>Vessel Detail</SectionLabel>
        {!selected ? (
          <EmptyState icon="⛴" title="Select a vessel" hint="Choose a vessel from the registry to see its profile and AIS track." />
        ) : (
          <div className="rounded-card border border-border bg-panel p-4">
            <h3 className="mb-3 text-base font-semibold text-text-primary">{selected.name}</h3>
            <div className="mb-4 grid grid-cols-2 gap-x-6 gap-y-1.5 text-xs2">
              <Field label="MMSI" value={selected.mmsi} mono />
              <Field label="Type" value={selected.vessel_type} />
              <Field label="Gross tonnage" value={`${selected.gross_tonnage.toLocaleString()} GT`} />
              <Field label="Length" value={`${selected.length_m} m`} />
              <Field label="Bunker fuel" value={selected.bunker_fuel_type} />
              <Field label="Cargo" value={selected.cargo_type ?? "—"} />
              {selected.cargo_capacity_m3 && (
                <Field label="Cargo capacity" value={`${selected.cargo_capacity_m3.toLocaleString()} m³`} />
              )}
            </div>

            {loadingTrack ? (
              <LoadingState label="Loading AIS track…" />
            ) : track && track.length > 0 ? (
              <>
                <div className="mb-2 flex items-center justify-between">
                  <SectionLabel>AIS Track ({track.length} positions)</SectionLabel>
                  <ActionButton variant="primary" onClick={() => onViewOnMap(selected.mmsi, track)}>
                    View on Map
                  </ActionButton>
                </div>
                <div className="scrollbar-thin max-h-56 overflow-y-auto rounded-input border border-border">
                  <table className="w-full text-xs2">
                    <thead className="sticky top-0 bg-elevated text-text-secondary">
                      <tr>
                        <th className="px-2 py-1.5 text-left font-medium">Time</th>
                        <th className="px-2 py-1.5 text-left font-medium">Lat</th>
                        <th className="px-2 py-1.5 text-left font-medium">Lon</th>
                        <th className="px-2 py-1.5 text-left font-medium">Speed</th>
                      </tr>
                    </thead>
                    <tbody>
                      {track.map((p, i) => (
                        <tr key={i} className="border-t border-border">
                          <td className="mono-num px-2 py-1.5">{new Date(p.timestamp).toUTCString().slice(17, 25)}</td>
                          <td className="mono-num px-2 py-1.5">{p.lat.toFixed(4)}</td>
                          <td className="mono-num px-2 py-1.5">{p.lon.toFixed(4)}</td>
                          <td className="mono-num px-2 py-1.5">{p.speed_knots.toFixed(1)} kn</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            ) : (
              <EmptyState icon="▨" title="No AIS track" hint="This vessel is dark for the analysed window — no transponder data available." />
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function Field({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex justify-between border-b border-border/60 py-1">
      <span className="text-text-secondary">{label}</span>
      <span className={mono ? "mono-num text-text-primary" : "text-text-primary"}>{value}</span>
    </div>
  );
}
