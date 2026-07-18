"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

function fmt(n: number) {
  return "£" + Math.round(n).toLocaleString("en-GB");
}

function ConfidenceBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const label = pct >= 80 ? "High" : pct >= 60 ? "Medium" : "Low";
  const color = pct >= 80 ? "#22c55e" : pct >= 60 ? "#f59e0b" : "#ef4444";
  return (
    <span style={{ background: color + "20", color, border: `1px solid ${color}40`, borderRadius: 6, padding: "2px 10px", fontSize: 13, fontWeight: 600 }}>
      {label} Confidence · {pct}%
    </span>
  );
}

export default function ResultsPage() {
  const params = useParams();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (params?.id) {
      fetch(`/api/backend/valuation/${params.id}`)
        .then(r => r.json())
        .then(d => { setData(d); setLoading(false); })
        .catch(() => setLoading(false));
    }
  }, [params?.id]);

  if (loading) return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#faf9f6" }}>
      <div style={{ textAlign: "center" }}>
        <div style={{ width: 48, height: 48, border: "3px solid #e5e5e5", borderTop: "3px solid #1a1a1a", borderRadius: "50%", animation: "spin 0.8s linear infinite", margin: "0 auto 16px" }} />
        <p style={{ color: "#888", fontSize: 15 }}>Calculating valuation…</p>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    </div>
  );

  if (!data || data.detail) return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#faf9f6" }}>
      <p style={{ color: "#888" }}>Valuation not found.</p>
    </div>
  );

  const prop = data.property;
  const method = data.methodology || {};
  const comps = data.comparables || [];
  const address = method.address_norm || prop?.address?.display_address || prop?.address?.address_norm || "Property";

  return (
    <main style={{ background: "#faf9f6", minHeight: "100vh", fontFamily: "'Georgia', serif" }}>
      <style>{`
        * { box-sizing: border-box; margin: 0; padding: 0; }
        .card { background: white; border-radius: 16px; border: 1px solid #ebebeb; padding: 28px; margin-bottom: 20px; }
        .label { font-size: 12px; color: #999; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 6px; font-family: sans-serif; }
        .value { font-size: 15px; color: #1a1a1a; font-family: sans-serif; }
        .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .grid3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; }
        @media (max-width: 640px) { .grid2, .grid3 { grid-template-columns: 1fr 1fr; } }
        table { width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 14px; }
        th { text-align: left; padding: 10px 12px; border-bottom: 2px solid #f0f0f0; color: #999; font-size: 11px; letter-spacing: 0.06em; text-transform: uppercase; font-weight: 500; }
        td { padding: 12px; border-bottom: 1px solid #f7f7f7; color: #1a1a1a; }
        tr:last-child td { border-bottom: none; }
        tr:hover td { background: #fafafa; }
        a { color: #1a1a1a; text-decoration: none; }
        a:hover { text-decoration: underline; }
      `}</style>

      <div style={{ background: "white", borderBottom: "1px solid #ebebeb", padding: "16px 24px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <a href="/" style={{ fontSize: 18, fontWeight: 700, letterSpacing: "-0.03em" }}>PropValue</a>
        <span style={{ fontSize: 13, color: "#999", fontFamily: "sans-serif" }}>Property Valuation Report</span>
      </div>

      <div style={{ maxWidth: 880, margin: "0 auto", padding: "32px 20px" }}>
        <div style={{ marginBottom: 24, display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
          <div>
            <p style={{ fontSize: 13, color: "#999", fontFamily: "sans-serif", marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.06em" }}>Valuation Report</p>
            <h1 style={{ fontSize: 26, fontWeight: 700, letterSpacing: "-0.02em", color: "#1a1a1a", marginBottom: 8 }}>{address}</h1>
            <ConfidenceBadge score={data.confidence_score} />
          </div>
          <div style={{ textAlign: "right" }}>
            <a
              href={"/api/backend/valuation/" + params?.id + "/report"}
              download
              style={{
                display: "inline-flex", alignItems: "center", gap: 8,
                background: "#1a1a1a", color: "white", fontFamily: "sans-serif",
                fontSize: 14, fontWeight: 600, padding: "12px 20px",
                borderRadius: 10, textDecoration: "none",
              }}
            >
              Download PDF Report
            </a>
            <p style={{ fontSize: 12, color: "#aaa", fontFamily: "sans-serif", marginTop: 6 }}>
              Takes a few seconds to generate
            </p>
          </div>
        </div>

        <div className="card" style={{ background: "#1a1a1a", color: "white", borderColor: "#1a1a1a" }}>
          <div className="grid3">
            <div>
              <p style={{ fontSize: 12, color: "#888", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 8, fontFamily: "sans-serif" }}>Estimated Value</p>
              <p style={{ fontSize: 36, fontWeight: 700, letterSpacing: "-0.03em" }}>{fmt(data.estimated_value_gbp)}</p>
            </div>
            <div>
              <p style={{ fontSize: 12, color: "#888", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 8, fontFamily: "sans-serif" }}>Value Range</p>
              <p style={{ fontSize: 18, fontWeight: 600 }}>{fmt(data.range_low_gbp)}</p>
              <p style={{ fontSize: 13, color: "#666", fontFamily: "sans-serif" }}>to {fmt(data.range_high_gbp)}</p>
            </div>
            <div>
              <p style={{ fontSize: 12, color: "#888", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 8, fontFamily: "sans-serif" }}>Rental Estimate</p>
              <p style={{ fontSize: 18, fontWeight: 600 }}>{fmt(data.rental_monthly_gbp)}<span style={{ fontSize: 13, color: "#888" }}> /mo</span></p>
              <p style={{ fontSize: 13, color: "#666", fontFamily: "sans-serif" }}>{data.rental_yield?.toFixed(1)}% gross yield</p>
            </div>
          </div>
        </div>

        <div className="card">
          <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 20, letterSpacing: "-0.01em" }}>Property Details</h2>
          <div className="grid3">
            <div><p className="label">Property Type</p><p className="value" style={{ textTransform: "capitalize" }}>{method.subject_type || prop?.property_type || "—"}</p></div>
            <div><p className="label">Bedrooms</p><p className="value">{method.subject_bedrooms ?? prop?.bedrooms ?? "—"}</p></div>
            <div><p className="label">Floor Area</p><p className="value">{method.subject_floor_area_m2 ? `${method.subject_floor_area_m2} m²` : "—"}</p></div>
            <div><p className="label">EPC Rating</p><p className="value">{prop?.epc_rating || "—"}</p></div>
            <div><p className="label">Comparables Used</p><p className="value">{method.comps_used} of {method.comps_considered}</p></div>
            <div><p className="label">Data Sources</p><p className="value" style={{ textTransform: "capitalize" }}>{(data.source_apis || []).join(", ") || "—"}</p></div>
          </div>
        </div>

        {comps.length > 0 && (
          <div className="card">
            <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 20, letterSpacing: "-0.01em" }}>Recent Comparable Sales</h2>
            <div style={{ overflowX: "auto" }}>
              <table>
                <thead>
                  <tr>
                    <th>Address</th>
                    <th>Postcode</th>
                    <th>Sold Price</th>
                    <th>Date</th>
                    <th>Type</th>
                  </tr>
                </thead>
                <tbody>
                  {comps.map((c: any) => (
                    <tr key={c.id}>
                      <td style={{ textTransform: "capitalize" }}>{c.source_url ? <a href={c.source_url} target="_blank" rel="noopener noreferrer" style={{ color: "#1a1a1a", textDecoration: "underline" }}>{c.address_snapshot}</a> : c.address_snapshot}</td>
                      <td style={{ fontFamily: "monospace", fontSize: 13 }}>{c.postcode_snapshot}</td>
                      <td style={{ fontWeight: 600 }}>{fmt(c.sale_price_gbp)}</td>
                      <td style={{ color: "#888", fontSize: 13 }}>{c.sale_date ? new Date(c.sale_date).toLocaleDateString("en-GB", { month: "short", year: "numeric" }) : "—"}</td>
                      <td style={{ textTransform: "capitalize", color: "#888", fontSize: 13 }}>{c.property_type || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        <p style={{ textAlign: "center", fontSize: 12, color: "#bbb", fontFamily: "sans-serif", marginTop: 32 }}>
          Report generated {new Date(data.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })} · Powered by PropValue
        </p>
      </div>
    </main>
  );
}
