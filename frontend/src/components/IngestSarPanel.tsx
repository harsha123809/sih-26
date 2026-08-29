import { useState } from "react";
import { api } from "../lib/api";
import type { Scene } from "../types/api";
import { ActionButton, SectionLabel } from "./States";

export function IngestSarPanel({ onIngested }: { onIngested: (scene: Scene) => void }) {
  const [open, setOpen] = useState(false);
  const [vvFile, setVvFile] = useState<File | null>(null);
  const [vhFile, setVhFile] = useState<File | null>(null);
  const [name, setName] = useState("");
  const [windSpeed, setWindSpeed] = useState("6.0");
  const [incidence, setIncidence] = useState("33.0");
  const [acquired, setAcquired] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // A .SAFE.zip already contains both polarisations, so the separate VH
  // picker is meaningless there.
  const isZip = !!vvFile && vvFile.name.toLowerCase().endsWith(".zip");

  async function submit() {
    if (!vvFile) return;
    setBusy(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("vv_file", vvFile);
      if (vhFile) form.append("vh_file", vhFile);
      form.append("name", name.trim() || vvFile.name);
      form.append("wind_speed_ms", windSpeed);
      form.append("incidence_angle_deg", incidence);
      if (acquired) form.append("acquisition_time", new Date(acquired).toISOString());

      const scene = await api.ingestSar(form);
      onIngested(scene);
      setOpen(false);
      setVvFile(null);
      setVhFile(null);
      setName("");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  if (!open) {
    return (
      <div className="mb-5 flex items-center justify-between rounded-card border border-dashed border-border bg-panel/50 px-4 py-3">
        <div>
          <div className="text-sm font-medium text-text-primary">Ingest a real Sentinel-1 product</div>
          <div className="text-xs2 text-text-secondary">
            Drop in a <code className="mono-num">.SAFE.zip</code> from Copernicus (or a GeoTIFF) to
            run the pipeline on measured backscatter instead of a seeded fixture.
          </div>
        </div>
        <ActionButton variant="primary" onClick={() => setOpen(true)}>
          Ingest SAR
        </ActionButton>
      </div>
    );
  }

  return (
    <div className="mb-5 rounded-card border border-teal/30 bg-panel p-4">
      <div className="mb-3 flex items-center justify-between">
        <SectionLabel>Ingest Sentinel-1 GRD</SectionLabel>
        <button
          onClick={() => setOpen(false)}
          className="text-text-secondary hover:text-text-primary"
          aria-label="Cancel ingestion"
        >
          ✕
        </button>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <Field label=".SAFE.zip, or VV band (required)">
          <input
            type="file"
            accept=".zip,.tif,.tiff,.img,.vrt"
            onChange={(e) => setVvFile(e.target.files?.[0] ?? null)}
            className="w-full text-xs2 text-text-secondary file:mr-2 file:rounded-input file:border file:border-border file:bg-elevated file:px-2 file:py-1 file:text-xs2 file:text-text-primary"
          />
        </Field>
        <Field label={isZip ? "VH band (not needed for a .zip)" : "VH band (optional)"}>
          <input
            type="file"
            accept=".tif,.tiff,.img,.vrt"
            disabled={isZip}
            onChange={(e) => setVhFile(e.target.files?.[0] ?? null)}
            className="w-full text-xs2 text-text-secondary disabled:opacity-40 file:mr-2 file:rounded-input file:border file:border-border file:bg-elevated file:px-2 file:py-1 file:text-xs2 file:text-text-primary"
          />
        </Field>
        <Field label="Scene name">
          <TextInput value={name} onChange={setName} placeholder="defaults to filename" />
        </Field>
        <Field label="Acquisition time (UTC)">
          <TextInput value={acquired} onChange={setAcquired} type="datetime-local" />
        </Field>
        <Field label="Wind speed (m/s) — required">
          <TextInput value={windSpeed} onChange={setWindSpeed} type="number" />
        </Field>
        <Field label="Incidence angle (deg)">
          <TextInput value={incidence} onChange={setIncidence} type="number" />
        </Field>
      </div>

      <p className="mt-3 text-[10px] leading-relaxed text-text-secondary">
        Drop in a Sentinel-1 <code className="mono-num">.SAFE.zip</code> exactly as downloaded from
        Copernicus — the VV and VH measurement bands are found inside automatically. Raw GRD
        products in radar geometry work too; their footprint is approximated from ground control
        points. Wind speed is mandatory because the physics gate cannot judge whether a detection
        is trustworthy without it (use ERA5 or GFS reanalysis at the acquisition time). Without a
        VH band there is no VV/VH ratio, so oil type stays UNRESOLVED.
      </p>

      {error && (
        <div className="mt-3 rounded-input border border-hfo-red/30 bg-hfo-red/10 px-2.5 py-2 text-xs2 text-hfo-red">
          {error}
        </div>
      )}

      <div className="mt-3 flex justify-end gap-2">
        <ActionButton onClick={() => setOpen(false)} disabled={busy}>
          Cancel
        </ActionButton>
        <ActionButton variant="primary" onClick={submit} disabled={!vvFile || busy}>
          {busy ? "Ingesting…" : "Ingest"}
        </ActionButton>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="label-caps mb-1 block">{label}</span>
      {children}
    </label>
  );
}

function TextInput({
  value,
  onChange,
  type = "text",
  placeholder,
}: {
  value: string;
  onChange: (v: string) => void;
  type?: string;
  placeholder?: string;
}) {
  return (
    <input
      type={type}
      value={value}
      placeholder={placeholder}
      onChange={(e) => onChange(e.target.value)}
      className="w-full rounded-input border border-border bg-elevated px-2 py-1.5 text-xs2 text-text-primary placeholder:text-text-secondary/60 focus-visible:outline-none"
    />
  );
}
