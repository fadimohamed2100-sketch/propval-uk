"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { SignedIn, SignedOut, SignInButton, UserButton, useAuth } from "@clerk/nextjs";
import { Clock, FileText, MapPin } from "lucide-react";
import { getValuationHistory } from "@/lib/api";
import type { ValuationHistoryItem } from "@/lib/types";

function fmtGbp(n: number | null): string {
  if (n === null) return "—";
  return "£" + Math.round(n).toLocaleString("en-GB");
}

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export default function HistoryPage() {
  const { isLoaded, isSignedIn, getToken } = useAuth();
  const [items, setItems] = useState<ValuationHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn) {
      setLoading(false);
      return;
    }
    (async () => {
      try {
        const token = await getToken();
        const data = await getValuationHistory(token);
        setItems(data);
      } catch {
        setError("Couldn't load your valuation history. Please try again.");
      } finally {
        setLoading(false);
      }
    })();
  }, [isLoaded, isSignedIn, getToken]);

  return (
    <main className="min-h-screen flex flex-col">
      <nav className="flex items-center justify-between px-6 py-5 max-w-6xl mx-auto w-full">
        <Link href="/" className="font-display text-xl font-semibold tracking-tight">
          Prop<span className="text-gold-400">Val</span>
        </Link>
        <div className="flex items-center gap-6 text-sm text-ink-muted">
          <Link href="/" className="hover:text-ink transition-colors">New valuation</Link>
          <SignedIn>
            <UserButton afterSignOutUrl="/" />
          </SignedIn>
        </div>
      </nav>

      <section className="flex-1 px-4 py-12 md:py-16 max-w-3xl mx-auto w-full">
        <h1 className="font-display text-3xl md:text-4xl tracking-tight text-ink mb-2">
          Your valuation <span className="text-gold-400 italic">history</span>
        </h1>

        <SignedOut>
          <p className="text-ink-muted mb-8">Sign in to see the properties you've valued.</p>
          <SignInButton mode="modal">
            <button className="bg-ink text-stone-50 px-5 py-3 rounded-full text-sm font-medium hover:bg-stone-800 transition-colors">
              Sign in
            </button>
          </SignInButton>
        </SignedOut>

        <SignedIn>
          <p className="text-ink-muted mb-8">Every property you've valued, most recent first.</p>

          {loading && (
            <div className="flex items-center gap-3 text-ink-muted py-12">
              <div className="w-5 h-5 border-2 border-stone-200 border-t-ink rounded-full animate-spin" />
              Loading your valuations…
            </div>
          )}

          {!loading && error && (
            <p className="text-red-500 py-8">{error}</p>
          )}

          {!loading && !error && items.length === 0 && (
            <div className="bg-white border border-stone-200 rounded-2xl p-10 text-center">
              <p className="text-ink-muted mb-4">You haven't valued any properties yet.</p>
              <Link
                href="/"
                className="inline-block bg-ink text-stone-50 px-5 py-3 rounded-full text-sm font-medium hover:bg-stone-800 transition-colors"
              >
                Value your first property
              </Link>
            </div>
          )}

          <div className="flex flex-col gap-3">
            {items.map((item) => (
              <Link
                key={item.id}
                href={`/results/${item.id}`}
                className="bg-white border border-stone-200 rounded-2xl px-6 py-5 flex items-center justify-between gap-4 hover:border-gold-400 transition-colors shadow-card"
              >
                <div className="flex items-start gap-3 min-w-0">
                  <MapPin className="text-ink-faint mt-0.5 flex-shrink-0" size={18} />
                  <div className="min-w-0">
                    <p className="text-ink font-medium truncate">{item.address_line}</p>
                    <div className="flex items-center gap-3 text-xs text-ink-muted mt-1 font-mono uppercase tracking-wider">
                      <span>{item.postcode}</span>
                      <span className="flex items-center gap-1">
                        <Clock size={12} />
                        {fmtDate(item.created_at)}
                      </span>
                      {item.pdf_url && (
                        <span className="flex items-center gap-1">
                          <FileText size={12} />
                          PDF
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="text-right flex-shrink-0">
                  <p className="font-display text-xl text-ink">
                    {fmtGbp(item.estimated_value_gbp)}
                  </p>
                  <p className="text-xs text-ink-muted">
                    {fmtGbp(item.range_low_gbp)} – {fmtGbp(item.range_high_gbp)}
                  </p>
                </div>
              </Link>
            ))}
          </div>
        </SignedIn>
      </section>
    </main>
  );
}
