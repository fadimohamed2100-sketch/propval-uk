"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { Search, MapPin, TrendingUp, Building2, Sparkles } from "lucide-react";
import { runValuation } from "@/lib/api";
import { ApiClientError } from "@/lib/api";

const EXAMPLE_ADDRESSES = [
  "W11 2DA",
  "EH1 2JL",
  "M3 2FF",
  "LS1 5JF",
];

const STATS = [
  { label: "Properties valued", value: "280k+", icon: Building2 },
  { label: "Data accuracy", value: "94%", icon: TrendingUp },
  { label: "Comparable sources", value: "3", icon: Sparkles },
];

export default function HomePage() {
  const router = useRouter();
  const [address, setAddress] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [bedrooms, setBedrooms] = useState("");
  const [bathrooms, setBathrooms] = useState("");
  const [propertyType, setPropertyType] = useState("");
  const [unitIdentifier, setUnitIdentifier] = useState("");
  const [selectedUprn, setSelectedUprn] = useState("");
  const [unitOptions, setUnitOptions] = useState<{uprn: string; address: string}[]>([]);
  const [loadingUnits, setLoadingUnits] = useState(false);
  const [tenure, setTenure] = useState("");
  const [leaseYears, setLeaseYears] = useState("");
  const [condition, setCondition] = useState("");
  const [driveway, setDriveway] = useState(false);
  const [outdoorSpace, setOutdoorSpace] = useState("none");
  const inputRef = useRef<HTMLInputElement>(null);

  function extractPostcode(text: string): string | null {
    const match = text.match(/[A-Za-z]{1,2}[0-9][0-9A-Za-z]?\s*[0-9][A-Za-z]{2}/);
    return match ? match[0].toUpperCase().replace(/\s+/g, " ").trim() : null;
  }

  async function loadUnits() {
    const postcode = extractPostcode(address);
    if (!postcode) {
      setUnitOptions([]);
      return;
    }
    setLoadingUnits(true);
    try {
      const base = process.env.NEXT_PUBLIC_API_BASE_URL || "https://propval-uk-production.up.railway.app";
      const res = await fetch(`${base}/api/v1/address/units?postcode=${encodeURIComponent(postcode)}`);
      const data = await res.json();
      const opts = (data.addresses || []).map((a: any) => ({ uprn: String(a.uprn), address: a.address }));
      setUnitOptions(opts);
    } catch {
      setUnitOptions([]);
    } finally {
      setLoadingUnits(false);
    }
  }

  async function handleSubmit(e: React.FormEvent | null, overrideAddress?: string) {
    e?.preventDefault();
    const query = (overrideAddress ?? address).trim();
    if (!query) { inputRef.current?.focus(); return; }
    if (!propertyType) { setError("Please select a property type."); return; }
    if (!bedrooms) { setError("Please select the number of bedrooms."); return; }
    setLoading(true);
    setError(null);
    try {
      const payload: any = { address: query };
      if (bedrooms) payload.bedrooms = parseInt(bedrooms);
      if (bathrooms) payload.bathrooms = parseInt(bathrooms);
      if (propertyType) payload.property_type = propertyType;
      if (unitIdentifier) payload.unit_identifier = unitIdentifier;
      if (selectedUprn) payload.uprn = selectedUprn;
      if (tenure) payload.tenure = tenure;
      if (leaseYears) payload.lease_years = parseInt(leaseYears);
      if (condition) payload.condition = condition;
      if (driveway) payload.parking = "single";
      if (outdoorSpace) payload.outdoor_space = outdoorSpace;
      const result = await runValuation(payload);
      router.push(`/results/${result.id}`);
    } catch (err) {
      if (err instanceof ApiClientError) setError(err.detail);
      else setError("Something went wrong. Please try again.");
      setLoading(false);
    }
  }

  const selectClass = "w-full bg-stone-50 border border-stone-200 rounded-xl px-4 py-3 text-sm text-ink outline-none focus:border-gold-400 transition-colors cursor-pointer";
  const labelClass = "block text-xs text-ink-muted uppercase tracking-wider mb-2 font-mono";

  return (
    <main className="min-h-screen flex flex-col">
      <nav className="flex items-center justify-between px-6 py-5 max-w-6xl mx-auto w-full">
        <span className="font-display text-xl font-semibold tracking-tight">
          Prop<span className="text-gold-400">Val</span>
        </span>
        <div className="flex items-center gap-6 text-sm text-ink-muted">
          <a href="#how" className="hover:text-ink transition-colors">How it works</a>
          <a href="#" className="hover:text-ink transition-colors">API</a>
          <button className="bg-ink text-stone-50 px-4 py-2 rounded-full text-sm font-medium hover:bg-stone-800 transition-colors">Sign in</button>
        </div>
      </nav>

      <section className="flex-1 flex flex-col items-center justify-center px-4 py-20 md:py-32">
        <div className="w-full max-w-2xl text-center">
          <div className="inline-flex items-center gap-2 bg-gold-300/20 text-gold-500 border border-gold-300/40 rounded-full px-4 py-1.5 text-xs font-mono uppercase tracking-widest mb-8">
            <span className="w-1.5 h-1.5 rounded-full bg-gold-400 animate-pulse" />
            Powered by PropertyData & EPC
          </div>
          <h1 className="font-display text-5xl md:text-6xl lg:text-7xl leading-[1.08] tracking-tight text-ink mb-6">
            What&apos;s your<br />
            <span className="text-gold-400 italic">property worth?</span>
          </h1>
          <p className="text-ink-muted text-lg md:text-xl leading-relaxed mb-12 max-w-xl mx-auto">
            Instant, data-driven valuations for any UK property. Compare comparable sales, estimate rental yield, and download a branded report.
          </p>

          <form onSubmit={handleSubmit} className="w-full text-left">
            <div className={`relative flex items-center bg-white rounded-2xl border-2 transition-all shadow-card-lg mb-3 ${error ? "border-red-300" : "border-stone-200 focus-within:border-gold-400"}`}>
              <MapPin className="absolute left-5 text-ink-faint" size={20} />
              <input
                ref={inputRef}
                type="text"
                value={address}
                onChange={(e) => {
                  const cleaned = e.target.value.toUpperCase().replace(/[^A-Z0-9 ]/g, "").slice(0, 8);
                  setAddress(cleaned);
                  setError(null);
                }}
                onBlur={() => loadUnits()}
                placeholder="e.g. EH1 2JL"
                className="flex-1 py-5 pl-14 pr-4 text-base md:text-lg bg-transparent outline-none placeholder:text-ink-faint rounded-2xl"
                disabled={loading}
                autoComplete="off"
              />
              <button
                type="submit"
                disabled={loading || !address.trim()}
                className="m-2 flex items-center gap-2 bg-ink text-stone-50 px-6 py-3.5 rounded-xl font-medium text-sm hover:bg-stone-800 disabled:opacity-40 disabled:cursor-not-allowed transition-all active:scale-[0.98]"
              >
                {loading ? (
                  <><span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />Valuing…</>
                ) : (
                  <><Search size={16} />Value it</>
                )}
              </button>
            </div>

            <div style={{display: "flex", alignItems: "center", gap: 8, background: "#fef9ec", border: "1px solid #f5e4a0", borderRadius: 10, padding: "10px 14px", marginBottom: 12}}><span style={{fontSize: 16}}>💡</span><p style={{fontSize: 13, color: "#7a6a1a", fontFamily: "sans-serif", margin: 0}}>Enter a postcode, then pick your exact address from the list below — e.g. <strong>SE18 5QH</strong></p></div>
            {error && <p className="mb-3 text-sm text-red-500 pl-1">{error}</p>}

            <div className="bg-white rounded-2xl border border-stone-200 p-5 mb-3 grid grid-cols-2 md:grid-cols-3 gap-4">
                <div>
                  <label className={labelClass}>Property Type</label>
                  <select
                    value={propertyType}
                    onChange={e => {
                      setPropertyType(e.target.value);
                      if (e.target.value) loadUnits();
                      else { setUnitOptions([]); setSelectedUprn(""); setUnitIdentifier(""); }
                    }}
                    className={selectClass}
                  >
                    <option value="">Unknown</option>
                    <option value="terraced">Terraced</option>
                    <option value="semi-detached">Semi-Detached</option>
                    <option value="detached">Detached</option>
                    <option value="flat">Flat</option>
                  </select>
                </div>
                {(loadingUnits || unitOptions.length > 0) && (
                  <div>
                    <label className={labelClass}>Specific Address</label>
                    {loadingUnits ? (
                      <div className={selectClass + " flex items-center text-stone-400"}>Loading units…</div>
                    ) : unitOptions.length > 0 ? (
                      <select
                        value={selectedUprn}
                        onChange={e => {
                          const uprn = e.target.value;
                          setSelectedUprn(uprn);
                          const match = unitOptions.find(o => o.uprn === uprn);
                          setUnitIdentifier(match ? match.address : "");
                          if (match) setAddress(match.address);
                        }}
                        className={selectClass}
                      >
                        <option value="">Select your exact address…</option>
                        {unitOptions.map(o => (
                          <option key={o.uprn} value={o.uprn}>{o.address}</option>
                        ))}
                      </select>
                    ) : (
                      <input
                        type="text"
                        value={unitIdentifier}
                        onChange={e => setUnitIdentifier(e.target.value)}
                        placeholder="e.g. Flat 23 or Apartment 5B"
                        className={selectClass}
                      />
                    )}
                  </div>
                )}
                <div>
                  <label className={labelClass}>Bedrooms</label>
                  <select value={bedrooms} onChange={e => setBedrooms(e.target.value)} className={selectClass}>
                    <option value="">Unknown</option>
                    {[1,2,3,4,5,6,7,8,9,10,11,12].map(n => <option key={n} value={n}>{n}</option>)}
                    <option value="custom">12+</option>
                  </select>
                  {bedrooms === "custom" && (
                    <input type="number" min="13" placeholder="Enter bedrooms" className={selectClass + " mt-2"} onChange={e => setBedrooms(e.target.value)} />
                  )}
                </div>
                <div>
                  <label className={labelClass}>Bathrooms</label>
                  <select value={bathrooms} onChange={e => setBathrooms(e.target.value)} className={selectClass}>
                    <option value="">Unknown</option>
                    {[1,2,3,4,5,6,7,8].map(n => <option key={n} value={n}>{n}</option>)}
                    <option value="custom">8+</option>
                  </select>
                  {bathrooms === "custom" && (
                    <input type="number" min="9" placeholder="Enter bathrooms" className={selectClass + " mt-2"} onChange={e => setBathrooms(e.target.value)} />
                  )}
                </div>
                <div>
                  <label className={labelClass}>Condition</label>
                  <select value={condition} onChange={e => setCondition(e.target.value)} className={selectClass}>
                    <option value="">Unknown</option>
                    <option value="average">Poor</option>
                    <option value="good">Average</option>
                    <option value="excellent">Good</option>
                  </select>
                </div>
                <div>
                  <label className={labelClass}>Tenure</label>
                  <select value={tenure} onChange={e => { setTenure(e.target.value); if (e.target.value !== "leasehold") setLeaseYears(""); }} className={selectClass}>
                    <option value="">Unknown</option>
                    <option value="freehold">Freehold</option>
                    <option value="leasehold">Leasehold</option>
                  </select>
                </div>
                {tenure === "leasehold" && (
                  <div>
                    <label className={labelClass}>Lease Years Left</label>
                    <input
                      type="number"
                      value={leaseYears}
                      onChange={e => setLeaseYears(e.target.value)}
                      placeholder="e.g. 85"
                      className={selectClass}
                      min="1"
                      max="999"
                    />
                  </div>
                )}
                <div className="flex items-center gap-3 pt-5">
                  <input
                    type="checkbox"
                    id="driveway"
                    checked={driveway}
                    onChange={e => setDriveway(e.target.checked)}
                    className="w-4 h-4 accent-stone-800 cursor-pointer"
                  />
                  <label htmlFor="driveway" className={labelClass + " mb-0 cursor-pointer"}>Has Driveway</label>
                </div>
                <div>
                  <label className={labelClass}>Outdoor Space</label>
                  <select value={outdoorSpace} onChange={e => setOutdoorSpace(e.target.value)} className={selectClass}>
                    <option value="none">None</option>
                    <option value="balcony">Balcony</option>
                    <option value="garden">Garden</option>
                  </select>
                </div>
              </div>

            <div className="flex flex-wrap gap-2 pl-1">
              {EXAMPLE_ADDRESSES.map((addr) => (
                <button
                  key={addr}
                  type="button"
                  onClick={() => { setAddress(addr); loadUnits(); }}
                  disabled={loading}
                  className="text-xs text-ink-muted bg-stone-100 hover:bg-stone-200 border border-stone-200 px-3 py-1.5 rounded-full transition-colors disabled:opacity-40"
                >
                  {addr.split(",")[0]}
                </button>
              ))}
            </div>
          </form>
        </div>
      </section>

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

      <section id="how" className="bg-ink py-20 px-4">
        <div className="max-w-5xl mx-auto">
          <h2 className="font-display text-3xl md:text-4xl text-stone-50 text-center mb-16">Three methods. One precise estimate.</h2>
          <div className="grid md:grid-cols-3 gap-8">
            {[
              { num: "01", title: "Comparable sales", body: "We analyse recent sold prices within 1km, weighted by property similarity, distance, and recency." },
              { num: "02", title: "Price per m²", body: "Using local price-per-square-metre rates from EPC and PropertyData, adjusted for property features." },
              { num: "03", title: "Growth projection", body: "Your property's last recorded sale price is forward-projected using local HPI indices." },
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

      <footer className="border-t border-stone-100 py-8 px-6">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4 text-xs text-ink-faint">
          <span>© 2026 PropVal. Not a RICS-compliant valuation.</span>
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
