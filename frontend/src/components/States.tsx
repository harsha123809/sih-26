import type { ReactNode } from "react";

export function EmptyState({ icon, title, hint }: { icon: string; title: string; hint?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-card border border-dashed border-border px-4 py-8 text-center">
      <span className="text-2xl opacity-40">{icon}</span>
      <p className="text-sm text-text-secondary">{title}</p>
      {hint && <p className="max-w-[28ch] text-xs2 text-text-secondary/70">{hint}</p>}
    </div>
  );
}

export function LoadingState({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2 rounded-card border border-border bg-elevated/50 px-3 py-3 text-xs2 text-text-secondary">
      <span className="relative flex h-2 w-2">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-teal opacity-60" />
        <span className="relative inline-flex h-2 w-2 rounded-full bg-teal" />
      </span>
      {label}
    </div>
  );
}

export function SectionLabel({ children }: { children: ReactNode }) {
  return <div className="label-caps mb-2">{children}</div>;
}

export function ActionButton({
  children,
  onClick,
  disabled,
  title,
  variant = "default",
  active,
}: {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  title?: string;
  variant?: "default" | "primary" | "danger";
  active?: boolean;
}) {
  const base =
    "rounded-input border px-3 py-1.5 text-xs2 font-medium transition-colors duration-150 ease-out disabled:cursor-not-allowed disabled:opacity-40 focus-visible:outline-none";
  const variantClasses =
    variant === "primary"
      ? "border-teal/40 bg-teal/10 text-teal hover:bg-teal/20"
      : variant === "danger"
        ? "border-hfo-red/40 bg-hfo-red/10 text-hfo-red hover:bg-hfo-red/20"
        : active
          ? "border-teal/50 bg-teal/15 text-teal"
          : "border-border bg-elevated text-text-primary hover:border-teal/40 hover:text-teal";
  return (
    <button className={`${base} ${variantClasses}`} onClick={onClick} disabled={disabled} title={title}>
      {children}
    </button>
  );
}
