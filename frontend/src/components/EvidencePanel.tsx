import { useState } from "react";
import type { AttributionCandidate, Detection, Incident, Scene } from "../types/api";
import { OilClassBadge, ReliabilityBadge, VesselStatusBadge } from "./Badges";
import { ActionButton, EmptyState, SectionLabel } from "./States";
import { fmtArea, fmtDist, OIL_COLORS, OIL_LABELS } from "../lib/theme";

const STAGES = ["Detection", "Classification", "Reliability", "Back-track", "Candidates"] as const;

export function EvidencePanel({
  scene,
  detection,
  incident,
  onClose,
  onInvestigate,
  onMarkStatus,
  onExport,
}: {
  scene: Scene;
  detection: Detection;
  incident: Incident;
  onClose: () => void;
  onInvestigate: (mmsi: string) => void;
  onMarkStatus: (status: "CONFIRMED" | "FALSE_POSITIVE") => void;
  onExport: (format: "json" | "pdf") => void;
}) {
  const [openStage, setOpenStage] = useState<number>(0);

  const included = incident.candidates.filter((c) => !c.excluded);
  const excluded = incident.candidates.filter((c) => c.excluded);

  return (
    <aside className="flex w-[420px] flex-shrink-0 animate-[slide-in_0.2s_ease-out] flex-col border-l border-border bg-panel">
      <style>{`@keyframes slide-in { from { transform: translateX(16px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }`}</style>

      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div>
          <div className="label-caps">Chain of Evidence</div>
          <div className="mono-num text-xs2 text-text-secondary">{incident.id}</div>
        </div>
        <button onClick={onClose} className="text-text-secondary hover:text-text-primary" aria-label="Close evidence panel">
          ✕
        </button>
      </div>

      <div className="flex gap-2 border-b border-border px-4 py-3">
        <ActionButton
          variant={incident.status === "CONFIRMED" ? "danger" : "default"}
          onClick={() => onMarkStatus("CONFIRMED")}
        >
          Mark Confirmed
        </ActionButton>
        <ActionButton
          variant={incident.status === "FALSE_POSITIVE" ? "primary" : "default"}
          onClick={() => onMarkStatus("FALSE_POSITIVE")}
        >
          Mark False Positive
        </ActionButton>
      </div>

      <div className="scrollbar-thin flex-1 overflow-y-auto">
        {/* 1. Detection */}
        <Stage index={0} title={STAGES[0]} open={openStage === 0} onToggle={setOpenStage}>
          <Row label="Scene">{scene.name}</Row>
          <Row label="Acquired">{new Date(scene.acquisition_time).toUTCString()}</Row>
          <Row label="Slick Area">{fmtArea(detection.area_m2)}</Row>
          <Row label="Centroid">
            <span className="mono-num">
              {detection.centroid[1].toFixed(4)}, {detection.centroid[0].toFixed(4)}
            </span>
          </Row>
          <div className="mt-2 aspect-video w-full rounded-input border border-border bg-elevated/60 bg-[repeating-linear-gradient(45deg,rgba(255,255,255,0.02)_0px,rgba(255,255,255,0.02)_2px,transparent_2px,transparent_10px)] flex items-center justify-center text-xs2 text-text-secondary">
            SAR thumbnail unavailable — simulation mode
          </div>
        </Stage>

        {/* 2. Classification */}
        <Stage index={1} title={STAGES[1]} open={openStage === 1} onToggle={setOpenStage}>
          <div className="mb-2 flex items-center justify-between">
            <span className="label-caps">Predicted class</span>
            <OilClassBadge oilClass={detection.predicted_class} />
          </div>
          {!detection.has_polarimetry && (
            <div className="mb-2 rounded-input border border-amber/30 bg-amber/10 px-2 py-1.5 text-xs2 text-amber">
              VH channel unavailable — oil type reported as UNRESOLVED rather than guessed.
            </div>
          )}
          <div className="flex flex-col gap-1.5">
            {Object.entries(detection.class_probabilities).map(([cls, p]) => (
              <div key={cls} className="flex items-center gap-2">
                <span className="w-24 flex-shrink-0 text-xs2 text-text-secondary">{OIL_LABELS[cls as keyof typeof OIL_LABELS]}</span>
                <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-elevated">
                  <div
                    className="h-full rounded-full"
                    style={{ width: `${p * 100}%`, backgroundColor: OIL_COLORS[cls as keyof typeof OIL_COLORS] }}
                  />
                </div>
                <span className="mono-num w-10 text-right text-xs2">{(p * 100).toFixed(0)}%</span>
              </div>
            ))}
          </div>
          <Row label="VV/VH ratio">
            <span className="mono-num">{detection.has_polarimetry ? `${detection.vv_vh_ratio_db.toFixed(2)} dB` : "—"}</span>
          </Row>
        </Stage>

        {/* 3. Reliability */}
        <Stage index={2} title={STAGES[2]} open={openStage === 2} onToggle={setOpenStage}>
          <div className="mb-2 flex items-center justify-between">
            <span className="label-caps">Verdict</span>
            <ReliabilityBadge verdict={detection.reliability.verdict} />
          </div>
          <Row label="Wind speed">
            <span className="mono-num">{scene.environment.wind_speed_ms.toFixed(1)} m/s</span>
          </Row>
          <Row label="Incidence angle">
            <span className="mono-num">{scene.environment.incidence_angle_deg.toFixed(1)}°</span>
          </Row>
          <Row label="Precipitation">
            <span className="mono-num">{scene.environment.precipitation_mm_hr.toFixed(1)} mm/hr</span>
          </Row>
          {detection.reliability.possible_rain_artefact && (
            <div className="my-2 rounded-input border border-amber/30 bg-amber/10 px-2 py-1.5 text-xs2 text-amber">
              Possible rain artefact flagged.
            </div>
          )}
          <div className="mt-2 rounded-input border border-border bg-elevated px-2.5 py-2 text-xs2 leading-relaxed text-text-secondary">
            {detection.reliability.reason}
          </div>
        </Stage>

        {/* 4. Back-track */}
        <Stage index={3} title={STAGES[3]} open={openStage === 3} onToggle={setOpenStage}>
          {incident.backtrack ? (
            <>
              <Row label="Hours traced">{incident.backtrack.hours_traced}h</Row>
              <Row label="Particles">{incident.backtrack.particle_count.toLocaleString()}</Row>
              <Row label="Origin estimate">
                <span className="mono-num">
                  {incident.backtrack.origin_estimate[1].toFixed(4)}, {incident.backtrack.origin_estimate[0].toFixed(4)}
                </span>
              </Row>
              <Row label="Final spread">
                {fmtDist(incident.backtrack.frames[incident.backtrack.frames.length - 1]?.particle_spread_m ?? 0)}
              </Row>
            </>
          ) : (
            <EmptyState icon="↺" title="Not yet run" hint="Use “Back-track Drift” in the toolbar to trace the slick to its origin." />
          )}
        </Stage>

        {/* 5. Candidates */}
        <Stage index={4} title={STAGES[4]} open={openStage === 4} onToggle={setOpenStage}>
          {incident.candidates.length === 0 ? (
            <EmptyState
              icon="⛴"
              title="No attribution computed yet"
              hint="Use “Run Attribution” in the toolbar. If the vessel is fully dark, no AIS-tracked candidate may exist — that absence is itself a finding."
            />
          ) : (
            <>
              <div className="flex flex-col gap-2">
                {included.map((c) => (
                  <CandidateCard key={c.vessel.mmsi} candidate={c} onInvestigate={() => onInvestigate(c.vessel.mmsi)} />
                ))}
              </div>
              {excluded.length > 0 && (
                <details className="mt-3 rounded-card border border-border bg-elevated/50">
                  <summary className="cursor-pointer select-none px-2.5 py-2 text-xs2 font-medium text-text-secondary">
                    Ruled Out ({excluded.length})
                  </summary>
                  <div className="flex flex-col gap-2 px-2.5 pb-2.5">
                    {excluded.map((c) => (
                      <CandidateCard key={c.vessel.mmsi} candidate={c} onInvestigate={() => onInvestigate(c.vessel.mmsi)} muted />
                    ))}
                  </div>
                </details>
              )}
            </>
          )}
          {incident.truth_gap_results.length > 0 && (
            <div className="mt-3">
              <SectionLabel>Truth Gap</SectionLabel>
              <div className="flex flex-col gap-1.5">
                {incident.truth_gap_results.map((tg, i) => (
                  <div key={i} className="flex items-center justify-between rounded-input border border-border bg-elevated px-2.5 py-1.5">
                    <span className="text-xs2 text-text-secondary">{tg.vessel_profile?.name ?? "Unidentified hull"}</span>
                    <div className="flex items-center gap-2">
                      {tg.deception_index_m > 0 && <span className="mono-num text-xs2 text-violet">{fmtDist(tg.deception_index_m)}</span>}
                      <VesselStatusBadge status={tg.status} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Stage>
      </div>

      <div className="flex gap-2 border-t border-border px-4 py-3">
        <ActionButton onClick={() => onExport("json")}>Export JSON/GeoJSON</ActionButton>
        <ActionButton onClick={() => onExport("pdf")}>Export PDF</ActionButton>
      </div>
    </aside>
  );
}

function Stage({
  index,
  title,
  open,
  onToggle,
  children,
}: {
  index: number;
  title: string;
  open: boolean;
  onToggle: (i: number) => void;
  children: React.ReactNode;
}) {
  return (
    <div className="border-b border-border">
      <button
        onClick={() => onToggle(open ? -1 : index)}
        className="flex w-full items-center gap-2.5 px-4 py-3 text-left focus-visible:outline-none"
        aria-expanded={open}
      >
        <span
          className={`flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full border text-[10px] font-semibold ${
            open ? "border-teal bg-teal/15 text-teal" : "border-border text-text-secondary"
          }`}
        >
          {index + 1}
        </span>
        <span className={`flex-1 text-sm font-medium ${open ? "text-text-primary" : "text-text-secondary"}`}>{title}</span>
        <span className={`text-text-secondary transition-transform duration-150 ${open ? "rotate-90" : ""}`}>›</span>
      </button>
      {open && <div className="px-4 pb-4 pl-[46px]">{children}</div>}
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="mb-1.5 flex items-center justify-between text-xs2">
      <span className="text-text-secondary">{label}</span>
      <span className="text-text-primary">{children}</span>
    </div>
  );
}

function CandidateCard({
  candidate,
  onInvestigate,
  muted,
}: {
  candidate: AttributionCandidate;
  onInvestigate: () => void;
  muted?: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className={`rounded-card border px-2.5 py-2 ${muted ? "border-border bg-bg/40 opacity-70" : "border-border bg-elevated"}`}>
      <div className="mb-1 flex items-center justify-between">
        <span className="text-sm font-medium text-text-primary">{candidate.vessel.name}</span>
        <span className="mono-num text-sm font-semibold text-teal">{candidate.score.toFixed(2)}</span>
      </div>
      <div className="mb-2 flex items-center justify-between text-xs2 text-text-secondary">
        <span className="mono-num">MMSI {candidate.vessel.mmsi}</span>
        <span>{candidate.vessel.vessel_type}</span>
      </div>
      <div className="mb-2 flex gap-2">
        <ActionButton onClick={onInvestigate}>Investigate</ActionButton>
        <ActionButton onClick={() => setExpanded((e) => !e)}>{expanded ? "Hide detail" : "Show detail"}</ActionButton>
      </div>
      {expanded && (
        <div className="flex flex-col gap-1">
          <ScoreBar label="Spatiotemporal" value={candidate.spatiotemporal_overlap} />
          <ScoreBar label="Cargo compat." value={candidate.cargo_compatibility} />
          <ScoreBar label="Deception idx." value={candidate.normalised_deception_index} />
          <ScoreBar label="Behavioural" value={candidate.behavioural_anomaly} />
          <ul className="mt-1.5 flex flex-col gap-1 border-t border-border pt-1.5">
            {candidate.reasoning.map((r, i) => (
              <li key={i} className="text-xs2 leading-relaxed text-text-secondary">
                • {r}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function ScoreBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-24 flex-shrink-0 text-[10px] text-text-secondary">{label}</span>
      <div className="h-1 flex-1 overflow-hidden rounded-full bg-bg">
        <div className="h-full rounded-full bg-teal" style={{ width: `${value * 100}%` }} />
      </div>
      <span className="mono-num w-8 text-right text-[10px] text-text-secondary">{value.toFixed(2)}</span>
    </div>
  );
}
