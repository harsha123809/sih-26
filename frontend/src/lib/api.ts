import type {
  AttributionResponse,
  Detection,
  Incident,
  Scene,
  VesselProfile,
  VesselTruthGapResult,
} from "../types/api";

const BASE = "/api";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${init?.method ?? "GET"} ${path} failed (${res.status}): ${body}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => req<{ status: string; simulation_mode: boolean }>("/health"),

  listScenes: () => req<Scene[]>("/scenes"),

  analyseScene: (
    sceneId: string,
    opts: { apply_physics_gate?: boolean; force_wind_speed_ms?: number | null } = {}
  ) =>
    req<Detection>(`/scenes/${sceneId}/analyse`, {
      method: "POST",
      body: JSON.stringify({
        apply_physics_gate: opts.apply_physics_gate ?? true,
        force_wind_speed_ms: opts.force_wind_speed_ms ?? null,
      }),
    }),

  sceneTruthGap: (sceneId: string) =>
    req<VesselTruthGapResult[]>(`/scenes/${sceneId}/truth-gap`),

  listDetections: (params?: Record<string, string | number | undefined>) => {
    const qs = params
      ? "?" +
        Object.entries(params)
          .filter(([, v]) => v !== undefined)
          .map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`)
          .join("&")
      : "";
    return req<Detection[]>(`/detections${qs}`);
  },

  getDetection: (id: string) => req<Detection>(`/detections/${id}`),

  listIncidents: () => req<Incident[]>("/incidents"),
  getIncident: (id: string) => req<Incident>(`/incidents/${id}`),

  backtrack: (incidentId: string, hours: number, particleCount: number) =>
    req<Incident["backtrack"]>(`/incidents/${incidentId}/backtrack`, {
      method: "POST",
      body: JSON.stringify({ hours, particle_count: particleCount }),
    }),

  attribution: (incidentId: string) =>
    req<AttributionResponse>(`/incidents/${incidentId}/attribution`),

  evidenceJson: (incidentId: string) => req<unknown>(`/incidents/${incidentId}/evidence`),

  evidencePdfUrl: (incidentId: string) => `${BASE}/incidents/${incidentId}/evidence?format=pdf`,

  updateIncidentStatus: (incidentId: string, status: "CONFIRMED" | "FALSE_POSITIVE" | "OPEN") =>
    req<Incident>(`/incidents/${incidentId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),

  vesselsSpoofing: () =>
    req<Array<VesselTruthGapResult & { scene_id: string; scene_name: string }>>(
      "/vessels/spoofing"
    ),

  listVessels: () => req<VesselProfile[]>("/vessels"),

  vesselTrack: (mmsi: string) =>
    req<{ vessel: VesselProfile; track: unknown[] }>(`/vessels/${mmsi}/track`),

  configThresholds: () => req<Record<string, unknown>>("/config/thresholds"),
};
