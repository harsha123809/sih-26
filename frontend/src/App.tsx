import { useEffect, useMemo, useState } from "react";
import { IconRail, type ViewKey } from "./components/IconRail";
import { IncidentFeed } from "./components/IncidentFeed";
import { MapView } from "./components/MapView";
import { TopBar } from "./components/TopBar";
import { EvidencePanel } from "./components/EvidencePanel";
import { BacktrackModal } from "./components/BacktrackModal";
import { CompareOilTypesPanel } from "./components/CompareOilTypesPanel";
import { DriftTimeline } from "./components/DriftTimeline";
import { ScenesView } from "./components/ScenesView";
import { VesselsView } from "./components/VesselsView";
import { ModelView } from "./components/ModelView";
import { SettingsView } from "./components/SettingsView";
import { api } from "./lib/api";
import type { AISPosition, Detection, Incident, Scene } from "./types/api";
import { buildSummary } from "./lib/types-local";

interface TrackedIncident {
  scene: Scene;
  detection: Detection;
  incident: Incident;
}

export default function App() {
  const [view, setView] = useState<ViewKey>("map");
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [selectedSceneId, setSelectedSceneId] = useState<string | null>(null);

  const [tracked, setTracked] = useState<Record<string, TrackedIncident>>({});
  const [rawByIncident, setRawByIncident] = useState<Record<string, Detection>>({});
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null);

  const [physicsGateOn, setPhysicsGateOn] = useState(true);
  const [feedCollapsed, setFeedCollapsed] = useState(false);
  const [panelOpen, setPanelOpen] = useState(false);

  const [analysing, setAnalysing] = useState(false);
  const [attributing, setAttributing] = useState(false);
  const [detectingSpoofing, setDetectingSpoofing] = useState(false);
  const [showSpoofLinks, setShowSpoofLinks] = useState(false);

  const [backtrackModalOpen, setBacktrackModalOpen] = useState(false);
  const [backtrackRunning, setBacktrackRunning] = useState(false);
  const [activeFrameIndex, setActiveFrameIndex] = useState(0);

  const [compareOpen, setCompareOpen] = useState(false);
  const [focusVessel, setFocusVessel] = useState<{ mmsi: string; track: AISPosition[] } | null>(null);

  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listScenes().then(setScenes).catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    if (!error) return;
    const t = setTimeout(() => setError(null), 6000);
    return () => clearTimeout(t);
  }, [error]);

  const selectedScene = useMemo(() => scenes.find((s) => s.id === selectedSceneId) ?? null, [scenes, selectedSceneId]);
  const selected = selectedIncidentId ? tracked[selectedIncidentId] : null;
  const displayedDetection =
    selected && !physicsGateOn ? rawByIncident[selected.incident.id] ?? selected.detection : selected?.detection ?? null;

  const incidentSummaries = useMemo(
    () => Object.values(tracked).map((t) => buildSummary(t.scene.name, t.detection, t.incident)),
    [tracked]
  );

  function selectIncident(id: string) {
    const t = tracked[id];
    if (!t) return;
    setSelectedIncidentId(id);
    setSelectedSceneId(t.scene.id);
    setPhysicsGateOn(true);
    setShowSpoofLinks(false);
    setActiveFrameIndex(0);
    setFocusVessel(null);
    setPanelOpen(true);
    setView("map");
  }

  function updateIncident(id: string, patch: Partial<Incident>) {
    setTracked((prev) => {
      const existing = prev[id];
      if (!existing) return prev;
      return { ...prev, [id]: { ...existing, incident: { ...existing.incident, ...patch } } };
    });
  }

  async function handleRunAnalysis() {
    if (!selectedSceneId) return;
    setAnalysing(true);
    setError(null);
    try {
      const detection = await api.analyseScene(selectedSceneId, { apply_physics_gate: true });
      const scene = scenes.find((s) => s.id === selectedSceneId)!;
      const incidentId = `inc-${detection.id}`;
      const incident = await api.getIncident(incidentId);
      setTracked((prev) => ({ ...prev, [incidentId]: { scene, detection, incident } }));
      setSelectedIncidentId(incidentId);
      setPhysicsGateOn(true);
      setShowSpoofLinks(false);
      setActiveFrameIndex(0);
      setFocusVessel(null);
      setPanelOpen(true);
    } catch (e) {
      setError(String(e));
    } finally {
      setAnalysing(false);
    }
  }

  async function handleTogglePhysicsGate() {
    if (!selected) {
      setPhysicsGateOn((v) => !v);
      return;
    }
    const next = !physicsGateOn;
    setPhysicsGateOn(next);
    if (!next && !rawByIncident[selected.incident.id]) {
      try {
        const raw = await api.analyseScene(selected.scene.id, { apply_physics_gate: false });
        setRawByIncident((prev) => ({ ...prev, [selected.incident.id]: raw }));
      } catch (e) {
        setError(String(e));
      }
    }
  }

  async function handleBacktrack(hours: number, particleCount: number) {
    if (!selected) return;
    setBacktrackRunning(true);
    setError(null);
    try {
      const result = await api.backtrack(selected.incident.id, hours, particleCount);
      updateIncident(selected.incident.id, { backtrack: result });
      setActiveFrameIndex(0);
      setBacktrackModalOpen(false);
    } catch (e) {
      setError(String(e));
    } finally {
      setBacktrackRunning(false);
    }
  }

  async function handleRunAttribution() {
    if (!selected) return;
    setAttributing(true);
    setError(null);
    try {
      const res = await api.attribution(selected.incident.id);
      updateIncident(selected.incident.id, { candidates: res.candidates, truth_gap_results: res.truth_gap_results });
    } catch (e) {
      setError(String(e));
    } finally {
      setAttributing(false);
    }
  }

  async function handleDetectSpoofing() {
    if (!selected) return;
    setDetectingSpoofing(true);
    setError(null);
    try {
      const results = await api.sceneTruthGap(selected.scene.id);
      updateIncident(selected.incident.id, { truth_gap_results: results });
      setShowSpoofLinks(true);
    } catch (e) {
      setError(String(e));
    } finally {
      setDetectingSpoofing(false);
    }
  }

  async function handleExport(format: "json" | "pdf") {
    if (!selected) return;
    if (format === "pdf") {
      const a = document.createElement("a");
      a.href = api.evidencePdfUrl(selected.incident.id);
      a.download = `${selected.incident.id}-evidence.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      return;
    }
    try {
      const bundle = await api.evidenceJson(selected.incident.id);
      const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${selected.incident.id}-evidence.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(String(e));
    }
  }

  async function handleSimulateLowWind() {
    if (!selectedSceneId) return;
    setAnalysing(true);
    setError(null);
    try {
      const detection = await api.analyseScene(selectedSceneId, { apply_physics_gate: true, force_wind_speed_ms: 1.0 });
      const scene = scenes.find((s) => s.id === selectedSceneId)!;
      const incidentId = `inc-${detection.id}`;
      const incident = await api.getIncident(incidentId);
      setTracked((prev) => ({ ...prev, [incidentId]: { scene, detection, incident } }));
      setSelectedIncidentId(incidentId);
      setPhysicsGateOn(true);
      setShowSpoofLinks(false);
      setActiveFrameIndex(0);
      setFocusVessel(null);
      setPanelOpen(true);
    } catch (e) {
      setError(String(e));
    } finally {
      setAnalysing(false);
    }
  }

  async function handleInvestigate(mmsi: string) {
    try {
      const res = await api.vesselTrack(mmsi);
      setFocusVessel({ mmsi, track: res.track as AISPosition[] });
    } catch (e) {
      setError(String(e));
    }
  }

  async function handleMarkStatus(status: "CONFIRMED" | "FALSE_POSITIVE") {
    if (!selected) return;
    try {
      const next = status === selected.incident.status ? "OPEN" : status;
      const updated = await api.updateIncidentStatus(selected.incident.id, next);
      updateIncident(selected.incident.id, { status: updated.status });
    } catch (e) {
      setError(String(e));
    }
  }

  const backtrackDisabled = !selected;
  const attributionDisabled = !selected;
  const spoofingDisabled = !selected;
  const exportDisabled = !selected;
  const compareDisabled = !displayedDetection;
  const simulateDisabled = !selectedSceneId;

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-bg">
      <IconRail active={view} onChange={setView} />

      {view === "map" && (
        <IncidentFeed
          incidents={incidentSummaries}
          selectedId={selectedIncidentId}
          onSelect={selectIncident}
          collapsed={feedCollapsed}
          onToggleCollapsed={() => setFeedCollapsed((c) => !c)}
        />
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        {view === "map" && (
          <>
            <TopBar
              scenes={scenes}
              selectedSceneId={selectedSceneId}
              onSelectScene={(id) => {
                setSelectedSceneId(id);
                setSelectedIncidentId(null);
                setPanelOpen(false);
                setFocusVessel(null);
                setShowSpoofLinks(false);
              }}
              onRunAnalysis={handleRunAnalysis}
              analysing={analysing}
              physicsGateOn={physicsGateOn}
              onTogglePhysicsGate={handleTogglePhysicsGate}
              onOpenBacktrack={() => setBacktrackModalOpen(true)}
              backtrackDisabled={backtrackDisabled}
              onRunAttribution={handleRunAttribution}
              attributionDisabled={attributionDisabled}
              attributing={attributing}
              onDetectSpoofing={handleDetectSpoofing}
              spoofingDisabled={spoofingDisabled}
              detectingSpoofing={detectingSpoofing}
              onExport={handleExport}
              exportDisabled={exportDisabled}
              onSimulateLowWind={handleSimulateLowWind}
              simulateDisabled={simulateDisabled}
              onCompareOilTypes={() => setCompareOpen(true)}
              compareDisabled={compareDisabled}
            />
            {!physicsGateOn && (
              <div className="border-b border-amber/30 bg-amber/10 px-4 py-1.5 text-center text-xs2 font-medium text-amber">
                Unfiltered model output — not operationally valid.
              </div>
            )}
            {error && (
              <div className="border-b border-hfo-red/30 bg-hfo-red/10 px-4 py-1.5 text-center text-xs2 text-hfo-red">
                {error}
              </div>
            )}
            <div className="relative flex-1">
              <MapView
                scene={selected?.scene ?? selectedScene}
                detection={displayedDetection}
                driftFrames={selected?.incident.backtrack?.frames ?? null}
                activeFrameIndex={activeFrameIndex}
                truthGapResults={selected?.incident.truth_gap_results ?? []}
                candidates={selected?.incident.candidates ?? []}
                showSpoofLinks={showSpoofLinks}
                focusVessel={focusVessel}
              />
              {selected?.incident.backtrack && (
                <DriftTimeline
                  frames={selected.incident.backtrack.frames}
                  activeIndex={activeFrameIndex}
                  onChange={setActiveFrameIndex}
                />
              )}
            </div>
          </>
        )}

        {view === "scenes" && (
          <ScenesView
            scenes={scenes}
            onOpenInMap={(id) => {
              setSelectedSceneId(id);
              setView("map");
            }}
          />
        )}

        {view === "incidents" && (
          <div className="flex h-full">
            <IncidentFeed
              incidents={incidentSummaries}
              selectedId={selectedIncidentId}
              onSelect={selectIncident}
              collapsed={false}
              onToggleCollapsed={() => {}}
            />
            <div className="flex-1 p-6 text-sm text-text-secondary">
              Select an incident to open its Chain of Evidence on the map view.
            </div>
          </div>
        )}

        {view === "vessels" && (
          <VesselsView
            onViewOnMap={(mmsi, track) => {
              setFocusVessel({ mmsi, track });
              setView("map");
            }}
          />
        )}

        {view === "model" && <ModelView />}
        {view === "settings" && <SettingsView />}
      </div>

      {view === "map" && panelOpen && selected && displayedDetection && (
        <EvidencePanel
          scene={selected.scene}
          detection={displayedDetection}
          incident={selected.incident}
          onClose={() => setPanelOpen(false)}
          onInvestigate={handleInvestigate}
          onMarkStatus={handleMarkStatus}
          onExport={handleExport}
        />
      )}

      {backtrackModalOpen && (
        <BacktrackModal onClose={() => setBacktrackModalOpen(false)} onRun={handleBacktrack} running={backtrackRunning} />
      )}

      {compareOpen && displayedDetection && (
        <CompareOilTypesPanel detection={displayedDetection} onClose={() => setCompareOpen(false)} />
      )}
    </div>
  );
}
