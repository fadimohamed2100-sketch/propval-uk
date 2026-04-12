import { clsx } from "clsx";

export function Badge({ children, variant = "default", className }: { children: React.ReactNode; variant?: string; className?: string }) {
  return <span className={clsx("inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-stone-100 text-stone-700", className)}>{children}</span>;
}

export function Card({ children, className, padding = "md" }: { children: React.ReactNode; className?: string; padding?: string }) {
  return <div className={clsx("bg-white rounded-2xl border border-stone-100 shadow-sm", padding === "sm" && "p-4", padding === "md" && "p-6", padding === "lg" && "p-8", className)}>{children}</div>;
}

export function SectionHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between mb-6">
      <div>
        <h2 className="text-xl font-semibold">{title}</h2>
        {subtitle && <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

export function StatRow({ label, value, mono, className }: { label: string; value: React.ReactNode; mono?: boolean; className?: string }) {
  return (
    <div className={clsx("flex items-center justify-between py-3 border-b border-stone-50 last:border-0", className)}>
      <span className="text-sm text-gray-500">{label}</span>
      <span className={clsx("text-sm font-medium", mono && "font-mono")}>{value}</span>
    </div>
  );
}

export function Divider({ className }: { className?: string }) {
  return <hr className={clsx("border-stone-100", className)} />;
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={clsx("animate-pulse bg-stone-200 rounded-lg", className)} />;
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
