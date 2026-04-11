"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { Search, MapPin, TrendingUp, ChevronRight, Building2, Sparkles } from "lucide-react";
import { runValuation } from "@/lib/api";
import { ApiClientError } from "@/lib/api";

const EXAMPLE_ADDRESSES = [
  "42 Portobello Road, London, W11 2DA",
  "15 Victoria Street, Edinburgh, EH1 2JL",
  "8 Deansgate, Manchester, M3 2FF",
  "22 Park Row, Leeds, LS1 5JF",
];

const STATS = [
  { label: "Properties valued",  value: "280k+",  icon: Building2 },
  { label: "Data accuracy",      value: "94%",     icon: TrendingUp },
  { label: "Comparable sources", value: "3",       icon: Sparkles },
];

export default function HomePage() {
  const router = useRouter();
  const [address, setAddress] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleSubmit(e: React.FormEvent | null, overrideAddress?: string) {
    e?.preventDefault();
    const query = (overrideAddress ?? address).trim();
    if (!query) {
      inputRef.current?.focus();
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await runValuation({ address: query });
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

      {/* ── Nav ───────────────────────────────────────────── */}
      <nav className="flex items-center justify-between px-6 py-5 max-w-6xl mx-auto w-full">
        <span className="font-display text-xl font-semibold tracking-tight">
          Prop<span className="text-gold-400">Val</span>
        </span>
        <div className="flex items-center gap-6 text-sm text-ink-muted">
          <a href="#how" className="hover:text-ink transition-colors">How it works</a>
          <a href="#" className="hover:text-ink transition-colors">API</a>
          <button className="bg-ink text-stone-50 px-4 py-2 rounded-full text-sm font-medium hover:bg-stone-800 transition-colors">
            Sign in
          </button>
        </div>
      </nav>

      {/* ── Hero ──────────────────────────────────────────── */}
      <section className="flex-1 flex flex-col items-center justify-center px-4 py-20 md:py-32">
        <div className="w-full max-w-2xl text-center stagger">

          {/* Eyebrow */}
          <div className="inline-flex items-center gap-2 bg-gold-300/20 text-gold-500 border border-gold-300/40 rounded-full px-4 py-1.5 text-xs font-mono uppercase tracking-widest mb-8">
            <span className="w-1.5 h-1.5 rounded-full bg-gold-400 animate-pulse" />
            Powered by Land Registry data
          </div>

          {/* Headline */}
          <h1 className="font-display text-5xl md:text-6xl lg:text-7xl leading-[1.08] tracking-tight text-ink mb-6">
            What&apos;s your
            <br />
            <span className="text-gold-400 italic">property worth?</span>
          </h1>

          <p className="text-ink-muted text-lg md:text-xl leading-relaxed mb-12 max-w-xl mx-auto">
            Instant, data-driven valuations for any UK property.
            Compare comparable sales, estimate rental yield, and download a branded report.
          </p>

          {/* Search form */}
          <form onSubmit={handleSubmit} className="relative w-full">
            <div className={`
              relative flex items-center bg-white rounded-2xl border-2 transition-all shadow-card-lg
              ${error ? "border-red-300" : "border-stone-200 focus-within:border-gold-400"}
            `}>
              <MapPin className="absolute left-5 text-ink-faint" size={20} />
              <input
                ref={inputRef}
                type="text"
                value={address}
                onChange={(e) => { setAddress(e.target.value); setError(null); }}
                placeholder="Enter a UK address or postcode…"
                className="flex-1 py-5 pl-14 pr-4 text-base md:text-lg bg-transparent outline-none placeholder:text-ink-faint rounded-2xl"
                disabled={loading}
                autoComplete="off"
              />
              <button
                type="submit"
                disabled={loading || !address.trim()}
                className="m-2 flex items-center gap-2 bg-ink text-stone-50 px-6 py-3.5 rounded-xl font-medium text-sm
                           hover:bg-stone-800 disabled:opacity-40 disabled:cursor-not-allowed transition-all
                           active:scale-[0.98]"
              >
                {loading ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Valuing…
                  </>
                ) : (
                  <>
                    <Search size={16} />
                    Value it
                  </>
                )}
              </button>
            </div>

            {error && (
              <p className="mt-3 text-sm text-red-500 text-left pl-1 animate-fade-in">
                {error}
              </p>
            )}
          </form>

          {/* Example addresses */}
          <div className="mt-5 flex flex-wrap justify-center gap-2">
            {EXAMPLE_ADDRESSES.map((addr) => (
              <button
                key={addr}
                onClick={() => { setAddress(addr); handleSubmit(null, addr); }}
                disabled={loading}
                className="text-xs text-ink-muted bg-stone-100 hover:bg-stone-200 border border-stone-200
                           px-3 py-1.5 rounded-full transition-colors disabled:opacity-40"
              >
                {addr.split(",")[0]}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* ── Stats strip ───────────────────────────────────── */}
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

      {/* ── How it works ──────────────────────────────────── */}
      <section id="how" className="bg-ink py-20 px-4">
        <div className="max-w-5xl mx-auto">
          <h2 className="font-display text-3xl md:text-4xl text-stone-50 text-center mb-16">
            Three methods. One precise estimate.
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                num: "01",
                title: "Comparable sales",
                body: "We analyse recent sold prices within 1km, weighted by property similarity, distance, and recency.",
              },
              {
                num: "02",
                title: "Price per m²",
                body: "Using local price-per-square-metre rates from EPC and Land Registry data, adjusted for features.",
              },
              {
                num: "03",
                title: "Growth projection",
                body: "Your property's last recorded sale price is forward-projected using local HPI indices.",
              },
            ].map(({ num, title, body }) => (
              <div key={num} className="group">
                <div className="font-mono text-xs text-gold-400 mb-4 tracking-widest">{num}</div>
                <h3 className="font-display text-xl text-stone-100 mb-3 group-hover:text-gold-300 transition-colors">
                  {title}
                </h3>
                <p className="text-stone-400 text-sm leading-relaxed">{body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA footer ────────────────────────────────────── */}
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
