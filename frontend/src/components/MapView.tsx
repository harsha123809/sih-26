import maplibregl from "maplibre-gl";
import { useEffect, useRef } from "react";
import type {
  AISPosition,
  AttributionCandidate,
  Detection,
  DriftConeFrame,
  Scene,
  VesselTruthGapResult,
} from "../types/api";
import { OIL_COLORS } from "../lib/theme";

// Esri's public "World Dark Gray" canvas — free, no API key, no rate-limit
// gate (unlike CARTO's basemaps.cartocdn.com, which now requires a paid key).
// Note the tile path is {z}/{y}/{x}, NOT the usual {z}/{x}/{y} — that's Esri's
// REST tile convention, not a typo.
const DARK_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    esri_dark_base: {
      type: "raster",
      tiles: [
        "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
      ],
      tileSize: 256,
      maxzoom: 16,
      attribution:
        '© <a href="https://www.esri.com" target="_blank">Esri</a> — Esri, HERE, Garmin, © OpenStreetMap contributors',
    },
    esri_dark_labels: {
      type: "raster",
      tiles: [
        "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}",
      ],
      tileSize: 256,
      maxzoom: 16,
    },
  },
  layers: [
    { id: "bg", type: "background", paint: { "background-color": "#0A0E14" } },
    { id: "esri_dark_base_layer", type: "raster", source: "esri_dark_base", paint: { "raster-opacity": 0.9 } },
    { id: "esri_dark_labels_layer", type: "raster", source: "esri_dark_labels", paint: { "raster-opacity": 0.8 } },
  ],
};

const EMPTY_FC: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };

export interface MapViewProps {
  scene: Scene | null;
  detection: Detection | null;
  driftFrames: DriftConeFrame[] | null;
  activeFrameIndex: number;
  truthGapResults: VesselTruthGapResult[];
  candidates: AttributionCandidate[];
  showSpoofLinks: boolean;
  focusVessel: { mmsi: string; track: AISPosition[] } | null;
}

export function MapView(props: MapViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markersRef = useRef<maplibregl.Marker[]>([]);
  const readyRef = useRef(false);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: DARK_STYLE,
      center: [72, 15],
      zoom: 4.2,
      attributionControl: false,
    });
    map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-right");
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    map.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");

    map.on("load", () => {
      map.addSource("detection", { type: "geojson", data: EMPTY_FC });
      map.addLayer({
        id: "detection-glow",
        type: "line",
        source: "detection",
        paint: {
          "line-color": ["get", "color"],
          "line-width": 10,
          "line-blur": 8,
          "line-opacity": ["get", "glowOpacity"],
        },
      });
      map.addLayer({
        id: "detection-fill",
        type: "fill",
        source: "detection",
        paint: { "fill-color": ["get", "color"], "fill-opacity": ["get", "fillOpacity"] },
      });
      map.addLayer({
        id: "detection-line",
        type: "line",
        source: "detection",
        paint: { "line-color": ["get", "color"], "line-width": 1.5, "line-opacity": ["get", "lineOpacity"] },
      });

      map.addSource("drift-cone", { type: "geojson", data: EMPTY_FC });
      map.addLayer({
        id: "drift-cone-fill",
        type: "fill",
        source: "drift-cone",
        paint: { "fill-color": "#34D3C4", "fill-opacity": 0.08 },
      });
      map.addLayer({
        id: "drift-cone-line",
        type: "line",
        source: "drift-cone",
        paint: { "line-color": "#34D3C4", "line-width": 1.2, "line-dasharray": [2, 2], "line-opacity": 0.7 },
      });

      map.addSource("spoof-links", { type: "geojson", data: EMPTY_FC });
      map.addLayer({
        id: "spoof-links-line",
        type: "line",
        source: "spoof-links",
        paint: { "line-color": "#C04FD4", "line-width": 2, "line-dasharray": [1, 1.5], "line-opacity": 0.9 },
      });

      map.addSource("focus-track", { type: "geojson", data: EMPTY_FC });
      map.addLayer({
        id: "focus-track-line",
        type: "line",
        source: "focus-track",
        paint: { "line-color": "#34D3C4", "line-width": 2, "line-opacity": 0.85 },
      });

      readyRef.current = true;
    });

    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
      readyRef.current = false;
    };
  }, []);

  // Fit to scene bbox
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !props.scene) return;
    const doFit = () => {
      const [w, s, e, n] = props.scene!.bbox;
      map.fitBounds(
        [
          [w, s],
          [e, n],
        ],
        { padding: 80, duration: 800 }
      );
    };
    if (map.loaded()) doFit();
    else map.once("load", doFit);
  }, [props.scene]);

  // Detection polygon
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !readyRef.current) return;
    const src = map.getSource("detection") as maplibregl.GeoJSONSource | undefined;
    if (!src) return;
    if (!props.detection) {
      src.setData(EMPTY_FC);
      return;
    }
    const d = props.detection;
    const suppressed = d.reliability.suppressed;
    const color = OIL_COLORS[d.predicted_class];
    src.setData({
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          properties: {
            color,
            fillOpacity: suppressed ? 0.04 : 0.22,
            lineOpacity: suppressed ? 0.25 : 0.9,
            glowOpacity: suppressed ? 0 : 0.35,
          },
          geometry: d.polygon as unknown as GeoJSON.Geometry,
        },
      ],
    });
  }, [props.detection]);

  // Drift cone (active frame)
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !readyRef.current) return;
    const src = map.getSource("drift-cone") as maplibregl.GeoJSONSource | undefined;
    if (!src) return;
    const frames = props.driftFrames;
    if (!frames || frames.length === 0) {
      src.setData(EMPTY_FC);
      return;
    }
    const frame = frames[Math.min(props.activeFrameIndex, frames.length - 1)];
    src.setData({
      type: "FeatureCollection",
      features: [{ type: "Feature", properties: {}, geometry: frame.polygon as unknown as GeoJSON.Geometry }],
    });
  }, [props.driftFrames, props.activeFrameIndex]);

  // Vessel markers + spoof links
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];

    const spoofFeatures: GeoJSON.Feature[] = [];

    for (const tg of props.truthGapResults) {
      if (tg.claimed_ais) {
        const el = document.createElement("div");
        el.className = "vessel-marker vessel-marker--ais";
        el.title = `${tg.vessel_profile?.name ?? "Vessel"} — AIS-reported position`;
        const marker = new maplibregl.Marker({ element: el }).setLngLat([tg.claimed_ais.lon, tg.claimed_ais.lat]).addTo(map);
        markersRef.current.push(marker);
      }
      if (tg.radar_target) {
        const el = document.createElement("div");
        const flagged = tg.status !== "MATCHED";
        el.className = `vessel-marker vessel-marker--radar ${flagged ? "vessel-marker--flagged" : ""}`;
        el.title = `Radar-detected hull${tg.vessel_profile ? ` — ${tg.vessel_profile.name}` : " — unidentified"} (${tg.status})`;
        const marker = new maplibregl.Marker({ element: el })
          .setLngLat([tg.radar_target.lon, tg.radar_target.lat])
          .addTo(map);
        markersRef.current.push(marker);
      }
      if (props.showSpoofLinks && tg.status === "SPOOFING_SUSPECTED" && tg.claimed_ais && tg.radar_target) {
        spoofFeatures.push({
          type: "Feature",
          properties: {},
          geometry: {
            type: "LineString",
            coordinates: [
              [tg.claimed_ais.lon, tg.claimed_ais.lat],
              [tg.radar_target.lon, tg.radar_target.lat],
            ],
          },
        });
      }
    }

    if (readyRef.current) {
      const src = map.getSource("spoof-links") as maplibregl.GeoJSONSource | undefined;
      src?.setData({ type: "FeatureCollection", features: spoofFeatures });
    }
  }, [props.truthGapResults, props.showSpoofLinks]);

  // Focused vessel track + flyTo
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !readyRef.current) return;
    const src = map.getSource("focus-track") as maplibregl.GeoJSONSource | undefined;
    if (!src) return;
    if (!props.focusVessel || props.focusVessel.track.length === 0) {
      src.setData(EMPTY_FC);
      return;
    }
    const coords = props.focusVessel.track.map((p) => [p.lon, p.lat]);
    src.setData({
      type: "FeatureCollection",
      features: [{ type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: coords } }],
    });
    const mid = props.focusVessel.track[Math.floor(props.focusVessel.track.length / 2)];
    map.flyTo({ center: [mid.lon, mid.lat], zoom: 9, duration: 1000 });
  }, [props.focusVessel]);

  return (
    <div className="relative h-full w-full">
      <div ref={containerRef} className="h-full w-full" />
      <style>{`
        .vessel-marker { width: 12px; height: 12px; border-radius: 50%; border: 2px solid #0A0E14; box-shadow: 0 0 0 1px rgba(255,255,255,0.15); }
        .vessel-marker--ais { background: #34D3C4; }
        .vessel-marker--radar { background: #E4E9F0; }
        .vessel-marker--flagged { background: #C04FD4; animation: mfosis-pulse 1.6s ease-in-out infinite; }
        @keyframes mfosis-pulse {
          0%, 100% { box-shadow: 0 0 0 0 rgba(192,79,212,0.55); }
          50% { box-shadow: 0 0 0 7px rgba(192,79,212,0); }
        }
        @media (prefers-reduced-motion: reduce) {
          .vessel-marker--flagged { animation: none; }
        }
      `}</style>
    </div>
  );
}
