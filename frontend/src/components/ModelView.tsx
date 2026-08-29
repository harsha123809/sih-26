import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { SectionLabel } from "./States";

export function ModelView() {
  const [health, setHealth] = useState<{ status: string; simulation_mode: boolean } | null>(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
  }, []);

  return (
    <div className="scrollbar-thin h-full overflow-y-auto p-6">
      <div className="mb-6 flex items-center gap-3">
        <SectionLabel>Model Status</SectionLabel>
        {health && (
          <span
            className={`rounded-input border px-2 py-0.5 text-xs2 ${
              health.simulation_mode ? "border-amber/30 bg-amber/10 text-amber" : "border-teal/30 bg-teal/10 text-teal"
            }`}
          >
            {health.simulation_mode ? "SIMULATION_MODE" : "LIVE WEIGHTS"}
          </span>
        )}
      </div>

      {health?.simulation_mode && (
        <div className="mb-6 max-w-[70ch] rounded-card border border-amber/30 bg-amber/10 px-4 py-3 text-xs2 leading-relaxed text-amber">
          No trained checkpoint is loaded — no GPU / labelled training corpus (e.g. the Krestenitis SAR
          oil-spill dataset) was available at build time. Every number in this app is either a deterministic
          simulated inference over the seeded demo scenes, or an honest "--" placeholder. Accuracy/F1/IoU are
          never fabricated. Point <code className="mono-num">MODEL_WEIGHTS_PATH</code> at a trained checkpoint
          and flip <code className="mono-num">SIMULATION_MODE=False</code> in{" "}
          <code className="mono-num">backend/app/core/ml/infer.py</code> to go live — no other code changes
          required.
        </div>
      )}

      <SectionLabel>Architecture — Env-Attention U-Net</SectionLabel>
      <div className="mb-6 grid grid-cols-1 gap-3 md:grid-cols-2">
        <ArchCard
          title="Vision Branch"
          body="ResNet-34 encoder over a 4-channel 512×512 tensor: sigma0_VV (dB), sigma0_VH (dB), VV/VH ratio (dB, the oil-type fingerprint), and a per-pixel wind-speed map."
        />
        <ArchCard
          title="Context Branch"
          body="MLP over [mean wind speed, wind dir sin/cos, SST, incidence angle, wave height, has_polarimetry] → FiLM (γ, β) vectors."
        />
        <ArchCard
          title="Fusion — FiLM Gating"
          body="z = γ·z + β at the bottleneck. Multiplicative modulation lets environment SUPPRESS oil-feature channels outright — not just nudge them, which concatenation-based fusion cannot do."
        />
        <ArchCard
          title="Decoder"
          body="U-Net with skip connections, softmax over 6 classes: Open water, Crude oil, Heavy fuel oil, Look-alike, Ship, Land."
        />
      </div>

      <SectionLabel>Training Objective (not yet run)</SectionLabel>
      <div className="mb-6 rounded-card border border-border bg-panel p-4 text-xs2 leading-relaxed text-text-secondary">
        <code className="mono-num text-text-primary">
          Loss = 0.6 × WeightedFocalLoss(γ=2.0) + 0.3 × SoftDiceLoss + 0.1 × AuxSceneClassifier
        </code>
        <p className="mt-2">
          Class weights up-weight Crude Oil and HFO against the dominant open-water background class. A
          learned temperature-scaling parameter calibrates confidence post-hoc.
        </p>
      </div>

      <SectionLabel>Preprocessing</SectionLabel>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {["Lee speckle filter", "Frost speckle filter", "Sigma0 calibration", "Incidence-angle normalisation", "512² tiling + overlap", "Feathered stitching"].map(
          (s) => (
            <div key={s} className="rounded-input border border-border bg-elevated px-3 py-2 text-xs2 text-text-secondary">
              {s}
            </div>
          )
        )}
      </div>
    </div>
  );
}

function ArchCard({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-card border border-border bg-panel p-4">
      <h3 className="mb-1.5 text-sm font-semibold text-teal">{title}</h3>
      <p className="text-xs2 leading-relaxed text-text-secondary">{body}</p>
    </div>
  );
}
