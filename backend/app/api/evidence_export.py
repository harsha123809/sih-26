"""Build the exportable evidence package: a JSON+GeoJSON bundle plus a
printable PDF summary of the full chain of evidence."""
from __future__ import annotations

import io

from app.models import Detection, Incident, Scene


def build_evidence_bundle(scene: Scene, detection: Detection, incident: Incident) -> dict:
    return {
        "scene": scene.model_dump(),
        "detection": detection.model_dump(),
        "incident": incident.model_dump(),
        "geojson": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "kind": "detection",
                        "predicted_class": detection.predicted_class.value,
                        "reliability_verdict": detection.reliability.verdict.value,
                    },
                    "geometry": detection.polygon.model_dump(),
                },
                *([{
                    "type": "Feature",
                    "properties": {"kind": "drift_cone", "hours_back": f.hours_back, "timestamp": f.timestamp},
                    "geometry": f.polygon.model_dump(),
                } for f in incident.backtrack.frames] if incident.backtrack else []),
            ],
        },
    }


def build_evidence_pdf(scene: Scene, detection: Detection, incident: Incident) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    y = height - 25 * mm

    def line(text: str, size: int = 10, gap: float = 6 * mm, bold: bool = False):
        nonlocal y
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.drawString(20 * mm, y, text)
        y -= gap

    line("MFOSIS — Maritime Forensic Oil-Spill Intelligence System", 14, bold=True)
    line("Chain of Evidence — Incident Report", 11, bold=True)
    line(f"Incident ID: {incident.id}    Status: {incident.status}", 9)
    line("")

    line("1. Detection", 11, bold=True)
    line(f"Scene: {scene.name}", 9)
    line(f"Acquisition time: {scene.acquisition_time}", 9)
    line(f"Slick area: {detection.area_m2:,.0f} m^2   Centroid: {detection.centroid}", 9)
    line("")

    line("2. Classification", 11, bold=True)
    line(f"Predicted class: {detection.predicted_class.value}", 9)
    line(f"VV/VH ratio: {detection.vv_vh_ratio_db} dB   Has polarimetry: {detection.has_polarimetry}", 9)
    probs = detection.class_probabilities.model_dump()
    line("Class probabilities: " + ", ".join(f"{k}={v:.2f}" for k, v in probs.items()), 8)
    line("")

    line("3. Reliability (Physics Gate)", 11, bold=True)
    line(f"Verdict: {detection.reliability.verdict.value}  (suppressed={detection.reliability.suppressed})", 9)
    for chunk in _wrap(detection.reliability.reason, 95):
        line(chunk, 8, gap=5 * mm)
    line("")

    if incident.backtrack:
        line("4. Back-track", 11, bold=True)
        line(f"Hours traced: {incident.backtrack.hours_traced}   Particles: {incident.backtrack.particle_count}", 9)
        line(f"Origin estimate: {incident.backtrack.origin_estimate}", 9)
        line("")

    line("5. Candidates", 11, bold=True)
    if not incident.candidates:
        line("No attribution candidates computed.", 9)
    for cand in incident.candidates:
        tag = "RULED OUT" if cand.excluded else "CANDIDATE"
        line(f"[{tag}] {cand.vessel.name} (MMSI {cand.vessel.mmsi}) — score {cand.score:.2f}", 9, bold=True)
        for r in cand.reasoning:
            for chunk in _wrap(r, 95):
                line("   " + chunk, 8, gap=5 * mm)
        if y < 30 * mm:
            c.showPage()
            y = height - 25 * mm

    c.showPage()
    c.save()
    return buf.getvalue()


def _wrap(text: str, width: int) -> list[str]:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines
