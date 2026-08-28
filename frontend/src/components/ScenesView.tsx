import type { Scene } from "../types/api";
import { ActionButton, SectionLabel } from "./States";

export function ScenesView({ scenes, onOpenInMap }: { scenes: Scene[]; onOpenInMap: (id: string) => void }) {
  return (
    <div className="scrollbar-thin h-full overflow-y-auto p-6">
      <SectionLabel>Seeded Demo Scenes</SectionLabel>
      <p className="mb-4 max-w-[70ch] text-sm text-text-secondary">
        Six scenarios covering the required cases: a confirmed crude spill, an HFO spill attributed via
        bunker fuel, a low-wind false positive the physics gate suppresses, an AIS spoofing event, a fully
        dark ship, and a crude spill where the nearest vessel is correctly ruled out on cargo grounds.
      </p>
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        {scenes.map((s) => (
          <div key={s.id} className="rounded-card border border-border bg-panel p-4">
            <div className="mb-1 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-text-primary">{s.name}</h3>
            </div>
            <p className="mb-3 text-xs2 leading-relaxed text-text-secondary">{s.description}</p>
            <div className="mb-3 grid grid-cols-2 gap-x-4 gap-y-1 text-xs2">
              <Env label="Wind" value={`${s.environment.wind_speed_ms.toFixed(1)} m/s`} />
              <Env label="SST" value={`${s.environment.sea_surface_temp_c.toFixed(1)} °C`} />
              <Env label="Incidence" value={`${s.environment.incidence_angle_deg.toFixed(1)}°`} />
              <Env label="Wave" value={`${s.environment.wave_height_m.toFixed(1)} m`} />
            </div>
            <ActionButton variant="primary" onClick={() => onOpenInMap(s.id)}>
              Open in Map
            </ActionButton>
          </div>
        ))}
      </div>
    </div>
  );
}

function Env({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-text-secondary">{label}</span>
      <span className="mono-num text-text-primary">{value}</span>
    </div>
  );
}
