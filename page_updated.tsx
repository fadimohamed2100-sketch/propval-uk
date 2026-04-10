"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Building2, TrendingUp, Sparkles, ArrowRight } from "lucide-react";
import { AddressSearch } from "@/components/AddressSearch";
import { runValuation } from "@/lib/api";
import { ApiClientError } from "@/lib/api";

const STATS = [
  { label: "Properties valued",  value: "280k+", icon: Building2  },
  { label: "Data accuracy",      value: "94%",   icon: TrendingUp },
  { label: "Comparable sources", value: "3",     icon: Sparkles   },
];

export default function HomePage() {
  const router  = useRouter();
  const [selectedAddress, setSelectedAddress] = useState<string | null>(null);
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState<string | null>(null);

  async function handleAddressSelect(suggestion: { full_address: string }) {
    setSelectedAddress(suggestion.full_address);
    setError(null);

    setLoading(true);
    try {
      const result = await runValuation({ address: suggestion.full_address });
      router.push(`/results/${result.id}`);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err.detail);
      } else {
        setError("Something went wrong. Please try again.");
      }
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex flex-col">

      {/* Nav */}
      <nav className="flex items-center justify-between px-6 py-5 max-w-6xl mx-auto w-full">
        <span className="font-display text-xl font-semibold tracking-tight">
          Prop<span className="text-gold-400">Val</span>
        </span>
        <div className="flex items-center gap-6 text-sm text-ink-muted">
          <a href="#how" className="hover:text-ink transition-colors">How it works</a>
          <a href="#"   className="hover:text-ink transition-colors">API</a>
          <button className="bg-ink text-stone-50 px-4 py-2 rounded-full text-sm font-medium hover:bg-stone-800 transition-colors">
            Sign in
          </button>
        </div>
      </nav>

      {/* Hero */}
      <section className="flex-1 flex flex-col items-center justify-center px-4 py-20 md:py-32">
        <div className="w-full max-w-2xl text-center">

          <div className="inline-flex items-center gap-2 bg-gold-300/20 text-gold-500 border border-gold-300/40 rounded-full px-4 py-1.5 text-xs font-mono uppercase tracking-widest mb-8">
            <span className="w-1.5 h-1.5 rounded-full bg-gold-400 animate-pulse" />
            Powered by Land Registry data
          </div>

          <h1 className="font-display text-5xl md:text-6xl lg:text-7xl leading-[1.08] tracking-tight text-ink mb-6">
            What&apos;s your
            <br />
            <span className="text-gold-400 italic">property worth?</span>
          </h1>

          <p className="text-ink-muted text-lg md:text-xl leading-relaxed mb-12 max-w-xl mx-auto">
            Instant, data-driven valuations for any UK property. Compare
            comparable sales, estimate rental yield, and download a branded report.
          </p>

          {/* Address search */}
          <AddressSearch
            onSelect={handleAddressSelect}
            onClear={() => { setSelectedAddress(null); setError(null); }}
            loading={loading}
            placeholder="Start typing an address or postcode…"
          />

          {/* Status feedback */}
          {loading && selectedAddress && (
            <div className="mt-4 flex items-center justify-center gap-2 text-sm text-ink-muted animate-fade-in">
              <span className="w-4 h-4 border-2 border-stone-200 border-t-gold-400 rounded-full animate-spin" />
              Valuing <span className="font-medium text-ink truncate max-w-xs">{selectedAddress}</span>…
            </div>
          )}
          {error && (
            <p className="mt-3 text-sm text-red-500 text-center animate-fade-in">{error}</p>
          )}

          {/* Quick picks */}
          {!loading && (
            <div className="mt-6">
              <p className="text-xs text-ink-faint mb-3 uppercase tracking-wider">Try an example</p>
              <div className="flex flex-wrap justify-center gap-2">
                {[
                  "Flat 307, Jigger Mast House, SE18 5NH",
                  "15 Forest Road, E17 6JF",
                  "34 Palatine Road, M20 3JH",
                  "7 Caledonia Place, BS8 4DN",
                ].map((addr) => {
                  const short = addr.split(",")[0];
                  return (
                    <button
                      key={addr}
                      onClick={() => handleAddressSelect({ full_address: addr })}
                      disabled={loading}
                      className="flex items-center gap-1.5 text-xs text-ink-muted bg-stone-100 hover:bg-stone-200
                                 border border-stone-200 px-3 py-1.5 rounded-full transition-colors
                                 disabled:opacity-40"
                    >
                      {short}
                      <ArrowRight size={11} className="text-ink-faint" />
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Stats strip */}
      <section className="border-t border-stone-100 py-12 px-4">
        <div className="max-w-4xl mx-auto grid grid-cols-3 divide-x divide-stone-100">
          {STATS.map(({ label, value, icon: Icon }) => (
            <div key={label} className="flex flex-col items-center gap-2 px-8">
              <Icon size={18} className="text-gold-400" />
              <span className="font-display text-3xl font-semibold text-ink">{value}</span>
              <span className="text-xs text-ink-muted uppercase tracking-wider">{label}</span>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="bg-ink py-20 px-4">
        <div className="max-w-5xl mx-auto">
          <h2 className="font-display text-3xl md:text-4xl text-stone-50 text-center mb-16">
            Three methods. One precise estimate.
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            {[
              { num: "01", title: "Comparable sales",    body: "Recent sold prices within 1km, weighted by property similarity, distance, and recency." },
              { num: "02", title: "Price per m²",        body: "Local price-per-square-metre from EPC and Land Registry data, adjusted for features."  },
              { num: "03", title: "Growth projection",   body: "Your property's last recorded sale price forward-projected using local HPI indices."     },
            ].map(({ num, title, body }) => (
              <div key={num} className="group">
                <div className="font-mono text-xs text-gold-400 mb-4 tracking-widest">{num}</div>
                <h3 className="font-display text-xl text-stone-100 mb-3 group-hover:text-gold-300 transition-colors">{title}</h3>
                <p className="text-stone-400 text-sm leading-relaxed">{body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-stone-100 py-8 px-6">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4 text-xs text-ink-faint">
          <span>© 2024 PropVal. Not a RICS-compliant valuation.</span>
          <div className="flex gap-6">
            <a href="#" className="hover:text-ink transition-colors">Privacy</a>
            <a href="#" className="hover:text-ink transition-colors">Terms</a>
            <a href="#" className="hover:text-ink transition-colors">API Docs</a>
          </div>
        </div>
      </footer>
    </main>
  );
}
