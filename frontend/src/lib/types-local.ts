import type { Detection, Incident, OilClass, ReliabilityVerdict } from "../types/api";

export interface IncidentSummary {
  incidentId: string;
  sceneId: string;
  sceneName: string;
  detectionId: string;
  predictedClass: OilClass;
  verdict: ReliabilityVerdict;
  confidence: number;
  status: Incident["status"];
  createdAt: string;
  deceptionIndexM: number | null;
}

export function topConfidence(d: Detection): number {
  return Math.max(...Object.values(d.class_probabilities));
}

export function buildSummary(sceneName: string, detection: Detection, incident: Incident): IncidentSummary {
  const deceptionIndexM =
    incident.truth_gap_results.length > 0
      ? Math.max(...incident.truth_gap_results.map((r) => r.deception_index_m))
      : null;
  return {
    incidentId: incident.id,
    sceneId: incident.scene_id,
    sceneName,
    detectionId: detection.id,
    predictedClass: detection.predicted_class,
    verdict: detection.reliability.verdict,
    confidence: topConfidence(detection),
    status: incident.status,
    createdAt: incident.created_at,
    deceptionIndexM,
  };
}
