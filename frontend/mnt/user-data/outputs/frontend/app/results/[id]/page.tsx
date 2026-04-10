"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, AlertCircle, RotateCcw } from "lucide-react";
import { getValuation, runValuation, ApiClientError } from "@/lib/api";
import type { Valuation } from "@/lib/types";
import { ValuationHero }     from "@/components/sections/ValuationHero";
import { PropertySummary }   from "@/components/sections/PropertySummary";
import { ComparablesList }   from "@/components/sections/ComparablesList";
import { MarketInsights }    from "@/components/sections/MarketInsights";
import { ResultsLoadingSkeleton } from "@/components/sections/LoadingState";

interface Props {
  params: { id: string };
}

export default function ResultsPage({ params }: Props) {
  const router = useRouter();
  const [valuation, setValuation] = useState<Valuation | null>(null);
  const [loading,   setLoading]   = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error,     setError]     = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await getValuation(params.id);
      setValuation(data);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err.detail);
      } else {
        setError("Failed to load valuation.");
      }
    } finally {
      setLoading(false);
    }
  }, [params.id]);

  useEffect(() => { load(); }, [load]);

  async function handleRefresh() {
    if (!valuation) return;
    setRefreshing(true);
    try {
      const refreshed = await runValuation({
        address:       valuation.property.address.line_1
          + ", " + valuation.property.address.postcode,
        force_refresh: true,
      });
      // Navigate to the new valuation ID
      router.push(`/results/${refreshed.id}`);
    } catch (err) {
      if (err instanceof ApiClientError) setError(err.detail);
    } finally {
      setRefreshing(false);
    }
  }

  if (loading) return <ResultsLoadingSkeleton />;

  if (error) {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center px-4">
        <div className="max-w-md w-full text-center">
          <div className="w-14 h-14 rounded-2xl bg-red-50 border border-red-100 flex items-center justify-center mx-auto mb-5">
            <AlertCircle size={24} className="text-red-400" />
          </div>
          <h2 className="font-display text-xl text-ink mb-2">Valuation unavailable</h2>
          <p className="text-ink-muted text-sm mb-8">{error}</p>
          <div className="flex justify-center gap-3">
            <button
              onClick={load}
              className="flex items-center gap-2 bg-ink text-stone-50 px-5 py-2.5 rounded-xl text-sm font-medium hover:bg-stone-800 transition-colors"
            >
              <RotateCcw size={14} />
              Try again
            </button>
            <button
              onClick={() => router.push("/")}
              className="flex items-center gap-2 bg-stone-100 text-ink px-5 py-2.5 rounded-xl text-sm font-medium hover:bg-stone-200 transition-colors"
            >
              <ArrowLeft size={14} />
              New search
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!valuation) return null;

  const { property } = valuation;
  const address = property.address;

  const displayAddress = [address.line_1, address.city, address.postcode]
    .filter(Boolean).join(", ");

  return (
    <div className="min-h-screen bg-surface">

      {/* ── Sticky nav ─────────────────────────────────── */}
      <header className="sticky top-0 z-30 bg-white/90 backdrop-blur-md border-b border-stone-100">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <button
              onClick={() => router.push("/")}
              className="flex items-center gap-1.5 text-ink-muted hover:text-ink transition-colors shrink-0 text-sm"
            >
              <ArrowLeft size={16} />
              <span className="hidden sm:inline">New search</span>
            </button>
            <span className="text-stone-200 hidden sm:block">|</span>
            <span className="font-mono text-xs text-ink-muted truncate hidden sm:block">
              {displayAddress}
            </span>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <span className="font-display text-base font-semibold text-ink">
              Prop<span className="text-gold-400">Val</span>
            </span>
          </div>
        </div>
      </header>

      {/* ── Address breadcrumb (mobile) ─────────────────── */}
      <div className="bg-stone-50 border-b border-stone-100 px-4 py-2.5 sm:hidden">
        <p className="font-mono text-xs text-ink-muted truncate">{displayAddress}</p>
      </div>

      {/* ── Main content ───────────────────────────────── */}
      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8 md:py-10">

        {/* Hero valuation card — full width */}
        <div className="mb-8 animate-fade-up">
          <ValuationHero
            valuation={valuation}
            onRefresh={handleRefresh}
            refreshing={refreshing}
          />
        </div>

        {/* Two-column layout */}
        <div className="grid lg:grid-cols-[1fr_360px] gap-6 items-start">

          {/* Left: property + comparables */}
          <div className="space-y-6 stagger">
            <PropertySummary property={property} />
            <ComparablesList comparables={valuation.comparables ?? []} />
          </div>

          {/* Right: insights sidebar */}
          <div className="stagger">
            <MarketInsights valuation={valuation} />
          </div>
        </div>

        {/* Disclaimer */}
        <p className="mt-10 text-xs text-ink-faint text-center leading-relaxed max-w-2xl mx-auto">
          This valuation is generated automatically using HM Land Registry Price Paid data and EPC
          certificates. It is for informational purposes only and does not constitute a
          RICS-compliant survey or financial advice. Always consult a qualified surveyor for
          mortgage or transaction purposes.
        </p>
      </main>
    </div>
  );
}
