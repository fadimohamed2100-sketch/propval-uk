import { Skeleton, SkeletonCard } from "@/components/ui";

export function ResultsLoadingSkeleton() {
  return (
    <div className="min-h-screen bg-surface">
      {/* Nav */}
      <div className="border-b border-stone-100 bg-white px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <Skeleton className="h-6 w-24" />
          <Skeleton className="h-9 w-48 rounded-xl" />
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10">
        {/* Hero skeleton */}
        <div className="bg-stone-800/20 rounded-3xl p-8 mb-8 animate-pulse">
          <Skeleton className="h-4 w-40 mb-6 bg-stone-700/40" />
          <Skeleton className="h-14 w-64 mb-8 bg-stone-700/40" />
          <div className="grid grid-cols-3 gap-4">
            <Skeleton className="h-24 rounded-2xl bg-stone-700/30" />
            <Skeleton className="h-24 rounded-2xl bg-stone-700/30" />
            <Skeleton className="h-24 rounded-2xl bg-stone-700/30" />
          </div>
        </div>

        {/* Two-column body */}
        <div className="grid lg:grid-cols-[1fr_360px] gap-6">
          <div className="space-y-6">
            <SkeletonCard lines={5} />
            <SkeletonCard lines={8} />
          </div>
          <div className="space-y-6">
            <SkeletonCard lines={4} />
            <SkeletonCard lines={4} />
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Inline skeleton for refreshes ─────────────────────────────
export function InlineLoader() {
  return (
    <div className="flex items-center justify-center py-12 gap-3 text-ink-muted">
      <span className="w-5 h-5 border-2 border-stone-200 border-t-gold-400 rounded-full animate-spin" />
      <span className="text-sm">Refreshing valuation…</span>
    </div>
  );
}
