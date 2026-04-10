"use client";

import { useState } from "react";
import { ArrowUpDown, ExternalLink } from "lucide-react";
import type { Comparable } from "@/lib/types";
import {
  formatGBP, formatMonthYear, formatDistance,
  formatPropertyType,
} from "@/lib/formatters";
import { Card, SectionHeader, Badge } from "@/components/ui";

interface Props {
  comparables: Comparable[];
}

type SortKey = "sale_price_gbp" | "sale_date" | "distance_m" | "similarity_score";

function SimilarityBar({ score }: { score: number | null }) {
  if (score == null) return <span className="text-ink-faint text-xs">—</span>;
  const pct    = Math.round(score * 100);
  const color  = pct >= 70 ? "bg-emerald-400" : pct >= 50 ? "bg-amber-400" : "bg-stone-300";
  return (
    <div className="flex items-center gap-2 min-w-[80px]">
      <div className="flex-1 h-1.5 bg-stone-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color} transition-all duration-700`}
             style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono text-ink-muted w-9 text-right">{pct}%</span>
    </div>
  );
}

function SortButton({
  label, sortKey, current, onSort,
}: { label: string; sortKey: SortKey; current: SortKey; onSort: (k: SortKey) => void }) {
  return (
    <button
      onClick={() => onSort(sortKey)}
      className={`flex items-center gap-1 text-xs uppercase tracking-wider font-medium transition-colors
        ${current === sortKey ? "text-gold-500" : "text-ink-faint hover:text-ink-muted"}`}
    >
      {label}
      <ArrowUpDown size={11} />
    </button>
  );
}

export function ComparablesList({ comparables }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("similarity_score");
  const [asc, setAsc]         = useState(false);

  function handleSort(key: SortKey) {
    if (key === sortKey) setAsc((a) => !a);
    else { setSortKey(key); setAsc(false); }
  }

  const sorted = [...comparables].sort((a, b) => {
    const va = a[sortKey] ?? -Infinity;
    const vb = b[sortKey] ?? -Infinity;
    return asc
      ? (va as number) - (vb as number)
      : (vb as number) - (va as number);
  });

  if (comparables.length === 0) {
    return (
      <Card>
        <SectionHeader title="Comparable sales" />
        <div className="text-center py-12 text-ink-muted text-sm">
          No comparable sales data available.
        </div>
      </Card>
    );
  }

  return (
    <Card padding="sm">
      <div className="px-2 pt-2 mb-4">
        <SectionHeader
          title="Comparable sales"
          subtitle={`${comparables.length} recent sold properties used in this valuation`}
        />
      </div>

      {/* Sort bar */}
      <div className="flex items-center gap-5 px-3 pb-3 border-b border-stone-100 overflow-x-auto">
        <span className="text-xs text-ink-faint shrink-0">Sort by:</span>
        <SortButton label="Match"   sortKey="similarity_score" current={sortKey} onSort={handleSort} />
        <SortButton label="Price"   sortKey="sale_price_gbp"   current={sortKey} onSort={handleSort} />
        <SortButton label="Date"    sortKey="sale_date"        current={sortKey} onSort={handleSort} />
        <SortButton label="Distance" sortKey="distance_m"      current={sortKey} onSort={handleSort} />
      </div>

      {/* Table */}
      <div className="divide-y divide-stone-50">
        {sorted.map((comp) => (
          <div
            key={comp.id}
            className="grid grid-cols-[1fr_auto] md:grid-cols-[1fr_120px_90px_90px] items-center gap-x-4 px-3 py-4
                       hover:bg-stone-50/60 transition-colors rounded-lg group"
          >
            {/* Address + type */}
            <div className="min-w-0">
              <p className="text-sm font-medium text-ink truncate leading-snug">
                {comp.address_snapshot}
              </p>
              <div className="flex items-center gap-2 mt-1 flex-wrap">
                <span className="font-mono text-xs text-ink-muted">{comp.postcode_snapshot}</span>
                {comp.property_type && (
                  <Badge variant="muted">{formatPropertyType(comp.property_type)}</Badge>
                )}
                {comp.bedrooms != null && (
                  <Badge variant="muted">{comp.bedrooms} bed</Badge>
                )}
                {comp.distance_m != null && (
                  <span className="text-xs text-ink-faint">{formatDistance(comp.distance_m)}</span>
                )}
              </div>
            </div>

            {/* Price */}
            <div className="text-right hidden md:block">
              <p className="font-mono text-sm font-medium text-ink">
                {formatGBP(comp.sale_price_gbp)}
              </p>
              {comp.price_per_m2_gbp && (
                <p className="font-mono text-xs text-ink-faint mt-0.5">
                  {formatGBP(comp.price_per_m2_gbp)}/m²
                </p>
              )}
            </div>

            {/* Date */}
            <div className="hidden md:block text-right">
              <p className="text-xs text-ink-muted">{formatMonthYear(comp.sale_date)}</p>
            </div>

            {/* Similarity */}
            <div className="hidden md:flex justify-end">
              <SimilarityBar score={comp.similarity_score} />
            </div>

            {/* Mobile: price + date */}
            <div className="flex flex-col items-end gap-0.5 md:hidden">
              <p className="font-mono text-sm font-medium text-ink">
                {formatGBP(comp.sale_price_gbp)}
              </p>
              <p className="text-xs text-ink-muted">{formatMonthYear(comp.sale_date)}</p>
              <SimilarityBar score={comp.similarity_score} />
            </div>
          </div>
        ))}
      </div>

      {/* Source footnote */}
      <div className="flex items-center gap-1.5 px-3 pt-3 border-t border-stone-100 text-xs text-ink-faint">
        <ExternalLink size={11} />
        Source: HM Land Registry Price Paid data
      </div>
    </Card>
  );
}
