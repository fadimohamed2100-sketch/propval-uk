"use client";

import { useEffect, useRef, useState } from "react";
import { Download, RefreshCw } from "lucide-react";
import type { Valuation } from "@/lib/types";
import { formatGBP, confidenceLabel } from "@/lib/formatters";
import { reportPdfUrl } from "@/lib/api";

interface Props {
  valuation: Valuation;
  onRefresh?: () => void;
  refreshing?: boolean;
}

function AnimatedValue({ target }: { target: number }) {
  const [display, setDisplay] = useState(0);
  const frameRef = useRef<number>(0);

  useEffect(() => {
    const duration = 900;
    const start    = performance.now();
    const from     = target * 0.75;

    function tick(now: number) {
      const progress = Math.min((now - start) / duration, 1);
      // Ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(Math.round(from + (target - from) * eased));
      if (progress < 1) frameRef.current = requestAnimationFrame(tick);
    }
    frameRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frameRef.current);
  }, [target]);

  return <>{formatGBP(display)}</>;
}

export function ValuationHero({ valuation, onRefresh, refreshing }: Props) {
  const { estimated_value_gbp, range_low_gbp, range_high_gbp, confidence_score } = valuation;

  // Bar geometry: position the point-estimate dot between low and high
  const range  = range_high_gbp - range_low_gbp;
  const offset = range > 0 ? ((estimated_value_gbp - range_low_gbp) / range) * 100 : 50;
  const confPct = Math.round(confidence_score * 100);

  const confColor =
    confPct >= 80 ? "#10B981"
    : confPct >= 60 ? "#F59E0B"
    : "#EF4444";

  return (
    <div className="bg-ink rounded-3xl p-8 md:p-10 text-stone-50 shadow-glow relative overflow-hidden">

      {/* Subtle grid texture */}
      <div className="absolute inset-0 opacity-[0.03]"
           style={{ backgroundImage: "linear-gradient(#fff 1px,transparent 1px),linear-gradient(90deg,#fff 1px,transparent 1px)", backgroundSize: "40px 40px" }} />

      <div className="relative stagger">

        {/* Label */}
        <p className="font-mono text-xs uppercase tracking-widest text-stone-400 mb-4">
          Estimated market value
        </p>

        {/* Main figure */}
        <div className="flex items-end justify-between gap-4 mb-8 flex-wrap">
          <h2 className="font-display text-5xl md:text-6xl font-semibold text-white leading-none">
            <AnimatedValue target={estimated_value_gbp} />
          </h2>

          <div className="flex items-center gap-3 shrink-0">
            {onRefresh && (
              <button
                onClick={onRefresh}
                disabled={refreshing}
                className="flex items-center gap-1.5 text-xs text-stone-400 hover:text-stone-200 transition-colors disabled:opacity-40"
              >
                <RefreshCw size={14} className={refreshing ? "animate-spin" : ""} />
                Refresh
              </button>
            )}
            <a
              href={reportPdfUrl(valuation.id)}
              download
              className="flex items-center gap-2 bg-stone-700/60 hover:bg-stone-600/60 border border-stone-600
                         text-stone-100 text-sm px-4 py-2 rounded-xl transition-colors"
            >
              <Download size={14} />
              PDF Report
            </a>
          </div>
        </div>

        {/* Range visualiser */}
        <div className="mb-8">
          <div className="flex justify-between text-xs text-stone-400 font-mono mb-3">
            <span>{formatGBP(range_low_gbp, true)}</span>
            <span className="text-stone-300">Valuation range</span>
            <span>{formatGBP(range_high_gbp, true)}</span>
          </div>
          <div className="relative h-2 bg-stone-700 rounded-full">
            {/* Filled range bar */}
            <div className="absolute inset-y-0 rounded-full bg-stone-500/60" style={{ left: 0, right: 0 }} />
            {/* Gold accent within the range */}
            <div
              className="absolute inset-y-0 rounded-full bg-gold-400/70"
              style={{ left: "10%", right: "10%" }}
            />
            {/* Point estimate dot */}
            <div
              className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-4 h-4 rounded-full bg-white shadow-lg ring-2 ring-gold-400 transition-all duration-700"
              style={{ left: `${offset}%` }}
            />
          </div>
        </div>

        {/* Confidence + rental row */}
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">

          {/* Confidence */}
          <div className="bg-stone-800/50 rounded-2xl p-4">
            <p className="text-xs text-stone-400 font-mono uppercase tracking-wider mb-2">Confidence</p>
            <div className="flex items-center gap-2 mb-2">
              <span className="font-display text-2xl font-semibold text-white">{confPct}%</span>
              <span className="text-xs font-medium px-2 py-0.5 rounded-full"
                    style={{ background: confColor + "25", color: confColor }}>
                {confidenceLabel(confidence_score)}
              </span>
            </div>
            <div className="h-1.5 bg-stone-700 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-1000 ease-out"
                style={{ width: `${confPct}%`, background: confColor }}
              />
            </div>
          </div>

          {/* Monthly rental */}
          <div className="bg-stone-800/50 rounded-2xl p-4">
            <p className="text-xs text-stone-400 font-mono uppercase tracking-wider mb-2">Est. monthly rent</p>
            <p className="font-display text-2xl font-semibold text-white">
              {formatGBP(valuation.rental_monthly_gbp)}
            </p>
            <p className="text-xs text-stone-400 mt-1">per calendar month</p>
          </div>

          {/* Gross yield */}
          <div className="bg-stone-800/50 rounded-2xl p-4 col-span-2 md:col-span-1">
            <p className="text-xs text-stone-400 font-mono uppercase tracking-wider mb-2">Gross rental yield</p>
            <p className="font-display text-2xl font-semibold text-white">
              {valuation.rental_yield?.toFixed(1)}%
            </p>
            <p className="text-xs text-stone-400 mt-1">annual, before costs</p>
          </div>
        </div>
      </div>
    </div>
  );
}
