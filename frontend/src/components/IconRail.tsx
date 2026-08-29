export type ViewKey = "map" | "incidents" | "vessels" | "scenes" | "model" | "settings";

const ITEMS: { key: ViewKey; icon: string; label: string }[] = [
  { key: "map", icon: "◎", label: "Map" },
  { key: "incidents", icon: "▤", label: "Incidents" },
  { key: "vessels", icon: "⛴", label: "Vessels" },
  { key: "scenes", icon: "▦", label: "Scenes" },
  { key: "model", icon: "◈", label: "Model" },
  { key: "settings", icon: "⚙", label: "Settings" },
];

export function IconRail({ active, onChange }: { active: ViewKey; onChange: (v: ViewKey) => void }) {
  return (
    <nav
      className="flex w-14 flex-shrink-0 flex-col items-center gap-1 border-r border-border bg-panel py-3"
      aria-label="Primary navigation"
    >
      <div className="mb-3 text-teal" title="MFOSIS">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path
            d="M3 17c2 1.5 4 1.5 6 0s4-1.5 6 0 4 1.5 6 0M3 12c2 1.5 4 1.5 6 0s4-1.5 6 0 4 1.5 6 0"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
          />
          <circle cx="12" cy="6" r="2.4" stroke="currentColor" strokeWidth="1.6" />
        </svg>
      </div>
      {ITEMS.map((item) => {
        const isActive = item.key === active;
        return (
          <button
            key={item.key}
            onClick={() => onChange(item.key)}
            title={item.label}
            aria-label={item.label}
            aria-current={isActive ? "page" : undefined}
            className={`group relative flex h-10 w-10 flex-col items-center justify-center rounded-input text-lg transition-colors duration-150 focus-visible:outline-none ${
              isActive ? "bg-teal/15 text-teal" : "text-text-secondary hover:bg-elevated hover:text-text-primary"
            }`}
          >
            {isActive && <span className="absolute left-0 h-5 w-0.5 rounded-full bg-teal" style={{ left: -8 }} />}
            <span aria-hidden="true">{item.icon}</span>
          </button>
        );
      })}
    </nav>
  );
}
