# MFOSIS — Maritime Forensic Oil-Spill Intelligence System

Most oil-spill tools answer one question: *is there a dark patch here?* MFOSIS
is built to answer three harder ones instead: **what type of pollutant is
this** (crude vs. heavy fuel oil vs. a natural look-alike), **can we trust
this detection given the weather**, and **which vessel — including a vessel
lying about its own position — is forensically responsible**.

It ships as a working full-stack app: a FastAPI backend implementing the
detection → reliability → attribution pipeline, and a React/TypeScript
"maritime operations centre" dashboard on top of it. Six seeded scenarios
make every feature clickable and demonstrable without a live satellite feed.

## Why it's built this way

Standard approaches treat this as a computer-vision problem: segment the
dark patch, blame the nearest ship. Two things break that in practice:

1. **All oil is not the same.** Crude and heavy fuel oil dampen the ocean
   surface differently at the radar wavelength. If you only look for "dark
   pixels," you can't tell them apart, and you can't rule out a vessel whose
   cargo makes one but not the other physically plausible.
2. **Wind, not oil, explains most dark patches.** Below about 1.5 m/s the
   sea is glassy and looks like a slick regardless of what's on it; above
   about 14 m/s wave action breaks slicks up and hides real ones. A model
   that never sees wind speed will confidently mislabel both.

So the pipeline is built around two ideas: a **polarimetric fingerprint**
(the VV/VH ratio) to separate oil types, and a **physics gate** that can
veto the model's own output when the weather makes the detection physically
unreliable — enforced as a wrapper function, not a training-time hope.

Attribution follows the same logic: instead of "nearest ship," it back-tracks
the slick to a probable origin (Lagrangian drift, run in reverse), checks
which vessels' AIS tracks were actually there, and — the forensic step —
checks whether each candidate's cargo or bunker fuel could plausibly produce
the *specific* pollutant detected. A container feeder can't leak crude oil
cargo it was never carrying; ruling it out is a result, not a discarded null.
On top of that, an independent radar pass (CFAR) finds physically-present
hulls and cross-references them against AIS, which is how it catches a
vessel that's radar-visible but either transmitting no AIS at all ("dark")
or transmitting AIS from a materially different position ("spoofing").

## Repository layout

```
backend/app/
  core/ml/           Env-Attention U-Net model, preprocessing, loss, SIMULATION_MODE inference
  core/physics/       physics-gate reliability filter, Lagrangian back-tracking
  core/geo/           CFAR ship detection, AIS truth-gap / spoofing cross-reference
  core/attribution/   cargo-aware candidate scoring
  api/                FastAPI routes, evidence export (JSON/GeoJSON + PDF)
  config/             thresholds.py — every tunable number, outside model/scoring code
  data/               seed.py (6 demo scenes, vessels, AIS tracks), in-memory store
frontend/src/
  components/         MapView (MapLibre GL), EvidencePanel, IncidentFeed, TopBar, etc.
  lib/                api client, theme tokens, local types
```

## Running it

**Backend**
```
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend**
```
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` to `localhost:8000`, so open the printed
`localhost:5173` URL and everything works together. No API keys are needed —
the map uses CARTO's free dark basemap tiles, not Mapbox.

## The ML model: Env-Attention U-Net

- **Vision branch:** ResNet-34 encoder over a 4-channel 512×512 input —
  σ⁰VV (dB), σ⁰VH (dB), the VV/VH ratio (dB, the oil-type fingerprint), and
  a per-pixel wind-speed map.
- **Context branch:** an MLP over scene-level scalars (wind speed, wind
  direction sin/cos, sea-surface temperature, incidence angle, wave height,
  `has_polarimetry`) that outputs FiLM `(γ, β)` vectors.
- **Fusion:** `z = γ·z + β` at the bottleneck — *multiplicative*, not
  concatenated. This is deliberate: it lets extreme weather drive an oil
  feature channel to zero, which concatenation-based fusion can't guarantee.
- **Decoder:** U-Net with skip connections, softmax over six classes — open
  water, crude oil, heavy fuel oil, look-alike, ship, land.
- **Loss (for the training run this repo doesn't yet include):**
  `0.6 × WeightedFocalLoss(γ=2.0) + 0.3 × SoftDiceLoss + 0.1 × AuxSceneClassifier`,
  with class weights favoring crude/HFO over the dominant open-water class,
  plus a learned temperature-scaling parameter for calibrated confidence.
- **No fabricated polarimetry:** when `has_polarimetry` is false (VH
  channel unavailable), the API reports oil type as `UNRESOLVED` rather than
  guessing crude vs. HFO from VV alone.

## SIMULATION_MODE — read this before judging the numbers

**No trained checkpoint is loaded.** No GPU or labelled training corpus was
available at build time — training on the real Krestenitis SAR oil-spill
dataset (or an equivalent) is the next step, not something this repo fakes.
`backend/app/core/ml/infer.py` implements a deterministic simulated-inference
path instead: each seeded scene carries a ground-truth scenario tag, and the
wrapper produces physically-plausible class probabilities and a segmentation
polygon from it, then runs that output through the *same* physics-gate and
FiLM-shaped pipeline the real model would use. Nothing about accuracy, F1,
or IoU is displayed anywhere in the UI — those require an actual training
run, so the frontend shows `--` rather than a fabricated number.

To go live: point `MODEL_WEIGHTS_PATH` at a trained checkpoint and flip
`SIMULATION_MODE = False` in `infer.py`. No other code changes are required
— the API contract, physics gate, and attribution engine are unchanged.

## The physics gate

A pure function (`core/physics/gate.py`), config-driven from
`config/thresholds.py`, that runs on *every* prediction before it becomes a
reported detection:

| Wind speed | Verdict | Effect |
|---|---|---|
| < 1.5 m/s | `UNRELIABLE_LOW_WIND` | Suppressed, confidence forced to 0 |
| 1.5–3.0 m/s | `DEGRADED_LOW` | Confidence × 0.5 (× 0.15 if slick area is also small) |
| 3.0–10.0 m/s | `OPTIMAL` | Full confidence |
| 10.0–14.0 m/s | `DEGRADED_HIGH` | Confidence × 0.6 (oil begins emulsifying) |
| > 14.0 m/s | `UNRELIABLE_HIGH_WIND` | Suppressed — dark regions are more likely wave shadow |

Incidence angle outside 20–45° downgrades one level; precipitation above
2 mm/hr is flagged as a possible rain artefact. Every verdict carries a
plain-English reason string, shown verbatim in the UI — an operator should
always be able to see *why* the system stayed silent, and a suppressed
detection is shown recessed in the interface, never hidden.

The **"Simulate Low Wind Scenario"** button in the toolbar exists specifically
to demonstrate this: it re-runs the selected scene with wind forced to
1.0 m/s and shows the gate correctly overriding the raw model output to
`open_water` / `UNRELIABLE_LOW_WIND`.

## Attribution: back-tracking, truth-gap, and cargo scoring

- **Lagrangian back-tracking** (`core/physics/backtrack.py`) seeds particles
  in the detected slick and integrates backward in time (ocean current +
  windage, HFO windage lower than crude since it sits deeper) with a
  turbulent-diffusion random-walk term, producing a widening sequence of
  drift-cone polygons — the widening *is* the uncertainty, rendered as such.
- **CFAR ship detection + Truth Gap** (`core/geo/cfar.py`) implements a real
  cell-averaging CFAR detector against synthetic Rayleigh clutter (the
  algorithm is genuine and unit-testable; it's the *scene* passed to it
  that's simulated in demo mode). Radar-visible hulls are cross-referenced
  against AIS: within 500 m is `MATCHED`; a claimed AIS position materially
  displaced from the radar-confirmed one is `SPOOFING_SUSPECTED`, scored by
  a **Deception Index** (the distance between the two); no AIS at all is
  `DARK_SHIP`.
- **Cargo-aware scoring** (`core/attribution/scoring.py`) combines
  spatiotemporal overlap, cargo/bunker-fuel compatibility with the detected
  oil type, normalized deception index, and behavioural anomaly into a
  weighted score. A vessel whose cargo *can't* explain the detected
  pollutant (e.g. a container feeder with no crude capacity, when the spill
  is crude) is excluded with a recorded reason, not silently dropped — the
  "Ruled Out" section in the evidence panel is exactly this.

## Seeded demo scenarios

| Scene | Demonstrates |
|---|---|
| Mumbai High Offshore | Confirmed crude spill, laden tanker matched via AIS |
| Gulf of Kutch | HFO spill attributed via bunker fuel, not cargo manifest |
| Goa Coastal Waters | Physics gate suppressing a low-wind (1.0 m/s) false positive |
| Kochi Approaches | AIS spoofing — ~40 km gap between claimed and radar-true position |
| Mangalore Offshore | Fully dark ship — radar-visible, zero AIS |
| Chennai Shipping Lane | Crude spill where the only nearby vessel is correctly ruled out |

## Known limitations

- **No trained model weights** — see SIMULATION_MODE above. This is the
  single biggest gap between this repo and an operational system.
- **In-memory store** — detections/incidents reset on backend restart; the
  code is structured so swapping in PostgreSQL/PostGIS or MongoDB is a
  `data/store.py` change, not a rewrite.
- **CFAR runs on synthetic clutter, not downlinked SAR amplitude data** —
  the detector itself is real; wiring it to an actual Sentinel-1 product is
  the remaining step.
- **Drift-cone geometry is a radius-from-centroid approximation**, not a
  true particle-density KDE contour — adequate for visualization, not for
  operational-grade uncertainty bounds.
- **Attribution candidates are scene-scoped, not a live PostGIS spatial
  query** — seeded demo data fixes which vessels are "nearby" per scene;
  production use needs the real spatial intersect against the drift cone.
