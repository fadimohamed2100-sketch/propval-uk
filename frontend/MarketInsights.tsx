"use client";

import { useState } from "react";
import { ChevronDown, Info, CheckCircle2, Database } from "lucide-react";
import type { Valuation } from "@/lib/types";
import { Card, SectionHeader, StatRow } from "@/components/ui";
import { formatGBP, confidenceLabel, confidenceBg } from "@/lib/formatters";

interface Props { valuation: Valuation; }

interface ScoreBarProps {
  label: string;
  value: number;
  tooltip?: string;
}

function ScoreBar({ label, value, tooltip }: ScoreBarProps) {
  const pct   = Math.round(value * 100);
  const color = pct >= 70 ? "bg-emerald-400" : pct >= 50 ? "bg-amber-400" : "bg-red-400";

  return (
    <div className="group relative">
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-1.5">
          <span className="text-sm text-ink-muted">{label}</span>
          {tooltip && (
            <div className="relative">
              <Info size={12} className="text-ink-faint cursor-help" />
              <div className="absolute hidden group-hover:block bottom-full left-0 mb-1 z-10
                              bg-ink text-stone-100 text-xs rounded-lg px-3 py-2 w-48 shadow-lg">
                {tooltip}
              </div>
            </div>
          )}
        </div>
        <span className="font-mono text-xs text-ink-muted">{pct}%</span>
      </div>
      <div className="h-2 bg-stone-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${color} transition-all duration-700`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function MethodChip({ label, value, weight }: { label: string; value: number; weight: number }) {
  return (
    <div className="bg-surface-raised rounded-xl p-4 border border-stone-100">
      <div className="flex items-start justify-between mb-3">
        <p className="text-xs text-ink-muted leading-snug">{label}</p>
        <span className="font-mono text-xs text-ink-faint bg-stone-100 px-1.5 py-0.5 rounded">
          {Math.round(weight * 100)}%
        </span>
      </div>
      <p className="font-mono text-base font-medium text-ink">
        {formatGBP(value)}
      </p>
    </div>
  );
}

export function MarketInsights({ valuation }: Props) {
  const [showMethodology, setShowMethodology] = useState(false);
  const m = valuation.methodology as Record<string, unknown>;
  const blendInputs = (m?.blend_inputs ?? []) as Array<{
    method: string; estimate_gbp: number; effective_weight: number; confidence: number;
  }>;

  const confidenceDrivers: ScoreBarProps[] = [
    {
      label:   "Sample size",
      value:   (m?.confidence_sample_size as number) ?? 0.7,
      tooltip: "How many comparable sales are available. More data = higher confidence.",
    },
    {
      label:   "Recency",
      value:   (m?.confidence_recency as number) ?? 0.75,
      tooltip: "Average age of comparable sales. Recent sales carry more weight.",
    },
    {
      label:   "Property similarity",
      value:   (m?.confidence_similarity as number) ?? 0.65,
      tooltip: "How closely the comparable properties match yours in type, size, and bedrooms.",
    },
    {
      label:   "Method agreement",
      value:   (m?.confidence_method_agreement as number) ?? 0.80,
      tooltip: "How closely the three valuation methods agree. Disagreement widens the range.",
    },
  ];

  const methodLabels: Record<string, string> = {
    comparable_sales:  "Comparable sales",
    price_per_m2:      "Price per m²",
    last_sale_growth:  "Last sale + HPI growth",
  };

  return (
    <div className="space-y-6">

      {/* Confidence breakdown */}
      <Card>
        <SectionHeader
          title="Confidence breakdown"
          subtitle={`Overall: ${Math.round(valuation.confidence_score * 100)}% — ${confidenceLabel(valuation.confidence_score)}`}
        />
        <div className="space-y-4">
          {confidenceDrivers.map((d) => (
            <ScoreBar key={d.label} {...d} />
          ))}
        </div>
      </Card>

      {/* Method blend */}
      {blendInputs.length > 0 && (
        <Card>
          <SectionHeader
            title="Valuation methods"
            subtitle="Three independent approaches blended by confidence weight"
          />
          <div className="grid gap-3">
            {blendInputs.map((b) => (
              <MethodChip
                key={b.method}
                label={methodLabels[b.method] ?? b.method}
                value={b.estimate_gbp}
                weight={b.effective_weight}
              />
            ))}
          </div>
        </Card>
      )}

      {/* Data sources */}
      <Card>
        <SectionHeader title="Data sources" />
        <div className="space-y-3">
          {(valuation.source_apis ?? []).map((api) => (
            <div key={api} className="flex items-center gap-3">
              <CheckCircle2 size={16} className="text-emerald-500 shrink-0" />
              <div>
                <p className="text-sm font-medium text-ink capitalize">
                  {api.replace(/_/g, " ")}
                </p>
                <p className="text-xs text-ink-faint">
                  {api === "land_registry" && "HM Land Registry Price Paid data"}
                  {api === "epc" && "EPC Register — floor area and energy rating"}
                  {api === "nominatim" && "OpenStreetMap geocoding"}
                </p>
              </div>
            </div>
          ))}
        </div>

        {/* Expiry */}
        <div className="mt-4 pt-4 border-t border-stone-50">
          <StatRow
            label="Report generated"
            value={new Date(valuation.created_at).toLocaleDateString("en-GB")}
          />
          <StatRow
            label="Cache expires"
            value={new Date(valuation.expires_at).toLocaleDateString("en-GB")}
          />
          <StatRow
            label="Comparables used"
            value={<span className="font-mono">{valuation.comparables?.length ?? 0}</span>}
          />
        </div>
      </Card>

      {/* Raw methodology toggle */}
      <div className="rounded-2xl border border-stone-100 overflow-hidden">
        <button
          onClick={() => setShowMethodology((s) => !s)}
          className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-stone-50 transition-colors"
        >
          <div className="flex items-center gap-2">
            <Database size={15} className="text-ink-faint" />
            <span className="text-sm font-medium text-ink">Raw methodology</span>
          </div>
          <ChevronDown
            size={16}
            className={`text-ink-faint transition-transform ${showMethodology ? "rotate-180" : ""}`}
          />
        </button>
        {showMethodology && (
          <div className="border-t border-stone-100 bg-stone-950 p-5">
            <pre className="text-xs text-stone-300 overflow-x-auto leading-relaxed font-mono whitespace-pre-wrap">
              {JSON.stringify(valuation.methodology, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
