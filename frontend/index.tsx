import { clsx } from "clsx";

// ── Badge ─────────────────────────────────────────────────────
interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "gold" | "green" | "red" | "muted";
  className?: string;
}
export function Badge({ children, variant = "default", className }: BadgeProps) {
  return (
    <span className={clsx(
      "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
      variant === "default" && "bg-stone-100 text-stone-700",
      variant === "gold"    && "bg-gold-300/20 text-gold-500 border border-gold-300/40",
      variant === "green"   && "bg-emerald-50 text-emerald-700 border border-emerald-200",
      variant === "red"     && "bg-red-50 text-red-600 border border-red-200",
      variant === "muted"   && "bg-stone-50 text-ink-faint border border-stone-200",
      className,
    )}>
      {children}
    </span>
  );
}

// ── Card ──────────────────────────────────────────────────────
interface CardProps {
  children: React.ReactNode;
  className?: string;
  padding?: "sm" | "md" | "lg";
}
export function Card({ children, className, padding = "md" }: CardProps) {
  return (
    <div className={clsx(
      "bg-white rounded-2xl border border-stone-100 shadow-card",
      padding === "sm" && "p-4",
      padding === "md" && "p-6",
      padding === "lg" && "p-8",
      className,
    )}>
      {children}
    </div>
  );
}

// ── Section header ────────────────────────────────────────────
interface SectionHeaderProps {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}
export function SectionHeader({ title, subtitle, action }: SectionHeaderProps) {
  return (
    <div className="flex items-start justify-between mb-6">
      <div>
        <h2 className="font-display text-xl font-semibold text-ink">{title}</h2>
        {subtitle && <p className="text-sm text-ink-muted mt-0.5">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

// ── Stat row ──────────────────────────────────────────────────
interface StatRowProps {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
  className?: string;
}
export function StatRow({ label, value, mono, className }: StatRowProps) {
  return (
    <div className={clsx("flex items-center justify-between py-3 border-b border-stone-50 last:border-0", className)}>
      <span className="text-sm text-ink-muted">{label}</span>
      <span className={clsx("text-sm font-medium text-ink", mono && "font-mono")}>{value}</span>
    </div>
  );
}

// ── Skeleton ──────────────────────────────────────────────────
interface SkeletonProps { className?: string; }
export function Skeleton({ className }: SkeletonProps) {
  return <div className={clsx("skeleton rounded-lg", className)} />;
}

export function SkeletonCard({ lines = 3 }: { lines?: number }) {
  return (
    <Card>
      <Skeleton className="h-5 w-32 mb-5" />
      <div className="space-y-3">
        {Array.from({ length: lines }).map((_, i) => (
          <div key={i} className="flex justify-between">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-4 w-20" />
          </div>
        ))}
      </div>
    </Card>
  );
}

// ── Divider ───────────────────────────────────────────────────
export function Divider({ className }: { className?: string }) {
  return <hr className={clsx("border-stone-100", className)} />;
}
