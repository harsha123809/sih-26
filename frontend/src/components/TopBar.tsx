import type { Scene } from "../types/api";
import { ActionButton } from "./States";

export function TopBar({
  scenes,
  selectedSceneId,
  onSelectScene,
  onRunAnalysis,
  analysing,
  physicsGateOn,
  onTogglePhysicsGate,
  onOpenBacktrack,
  backtrackDisabled,
  onRunAttribution,
  attributionDisabled,
  attributing,
  onDetectSpoofing,
  spoofingDisabled,
  detectingSpoofing,
  onExport,
  exportDisabled,
  onSimulateLowWind,
  simulateDisabled,
  onCompareOilTypes,
  compareDisabled,
}: {
  scenes: Scene[];
  selectedSceneId: string | null;
  onSelectScene: (id: string) => void;
  onRunAnalysis: () => void;
  analysing: boolean;
  physicsGateOn: boolean;
  onTogglePhysicsGate: () => void;
  onOpenBacktrack: () => void;
  backtrackDisabled: boolean;
  onRunAttribution: () => void;
  attributionDisabled: boolean;
  attributing: boolean;
  onDetectSpoofing: () => void;
  spoofingDisabled: boolean;
  detectingSpoofing: boolean;
  onExport: (format: "json" | "pdf") => void;
  exportDisabled: boolean;
  onSimulateLowWind: () => void;
  simulateDisabled: boolean;
  onCompareOilTypes: () => void;
  compareDisabled: boolean;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-border bg-panel px-4 py-2.5">
      <select
        value={selectedSceneId ?? ""}
        onChange={(e) => onSelectScene(e.target.value)}
        className="max-w-[280px] rounded-input border border-border bg-elevated px-2 py-1.5 text-xs2 text-text-primary focus-visible:outline-none"
        aria-label="Select scene"
      >
        <option value="" disabled>
          Select a scene…
        </option>
        {scenes.map((s) => (
          <option key={s.id} value={s.id}>
            {s.name}
          </option>
        ))}
      </select>

      <div className="mx-1 h-5 w-px bg-border" />

      <ActionButton
        variant="primary"
        onClick={onRunAnalysis}
        disabled={!selectedSceneId || analysing}
        title={!selectedSceneId ? "Select a scene first" : "Run the classification model on this scene"}
      >
        {analysing ? "Analysing…" : "Run Analysis"}
      </ActionButton>

      <ActionButton
        active={physicsGateOn}
        onClick={onTogglePhysicsGate}
        disabled={!selectedSceneId}
        title="Toggle the physics-gate reliability filter"
      >
        {physicsGateOn ? "✓ Physics Gate" : "Physics Gate Off"}
      </ActionButton>

      <ActionButton
        onClick={onOpenBacktrack}
        disabled={backtrackDisabled}
        title={backtrackDisabled ? "Run analysis first" : "Back-track the slick to its likely origin"}
      >
        Back-track Drift
      </ActionButton>

      <ActionButton
        onClick={onRunAttribution}
        disabled={attributionDisabled}
        title={attributionDisabled ? "Run analysis first" : "Score candidate vessels"}
      >
        {attributing ? "Scoring…" : "Run Attribution"}
      </ActionButton>

      <ActionButton
        onClick={onDetectSpoofing}
        disabled={spoofingDisabled}
        title={spoofingDisabled ? "Run analysis first" : "Cross-reference radar targets against AIS"}
      >
        {detectingSpoofing ? "Scanning…" : "Detect Spoofing"}
      </ActionButton>

      <ActionButton
        onClick={onCompareOilTypes}
        disabled={compareDisabled}
        title={compareDisabled ? "Run analysis first" : "Compare VV/VH signatures"}
      >
        Compare Oil Types
      </ActionButton>

      <div className="mx-1 h-5 w-px bg-border" />

      <ActionButton
        onClick={onSimulateLowWind}
        disabled={simulateDisabled}
        title={simulateDisabled ? "Select a scene first" : "Demo: force wind to 1.0 m/s and confirm the gate suppresses the detection"}
      >
        Simulate Low Wind Scenario
      </ActionButton>

      <div className="ml-auto flex gap-2">
        <ActionButton onClick={() => onExport("json")} disabled={exportDisabled} title="Download JSON + GeoJSON evidence bundle">
          Export Evidence
        </ActionButton>
      </div>
    </div>
  );
}
