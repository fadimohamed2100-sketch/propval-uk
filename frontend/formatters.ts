// ─── Currency ────────────────────────────────────────────────

export function formatGBP(value: number | null | undefined, compact = false): string {
  if (value == null) return "N/A";
  if (compact && value >= 1_000_000)
    return `£${(value / 1_000_000).toFixed(2)}m`;
  if (compact && value >= 1_000)
    return `£${Math.round(value / 1_000)}k`;
  return new Intl.NumberFormat("en-GB", {
    style:    "currency",
    currency: "GBP",
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatGBPPerM2(value: number | null | undefined): string {
  if (value == null) return "N/A";
  return `${formatGBP(value)}/m²`;
}

// ─── Dates ───────────────────────────────────────────────────

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "N/A";
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric", month: "short", year: "numeric",
  }).format(new Date(iso));
}

export function formatMonthYear(iso: string | null | undefined): string {
  if (!iso) return "N/A";
  return new Intl.DateTimeFormat("en-GB", {
    month: "short", year: "numeric",
  }).format(new Date(iso));
}

export function timeAgo(iso: string | null | undefined): string {
  if (!iso) return "";
  const diffMs   = Date.now() - new Date(iso).getTime();
  const diffDays = Math.floor(diffMs / 86_400_000);
  if (diffDays < 30)  return `${diffDays}d ago`;
  if (diffDays < 365) return `${Math.floor(diffDays / 30)}mo ago`;
  return `${Math.floor(diffDays / 365)}yr ago`;
}

// ─── Property labels ─────────────────────────────────────────

export function formatPropertyType(type: string | null | undefined): string {
  if (!type) return "Property";
  return type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function formatTenure(tenure: string | null | undefined): string {
  if (!tenure) return "N/A";
  return tenure.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function formatFloorArea(m2: number | null | undefined): string {
  if (m2 == null) return "N/A";
  const sqft = Math.round(m2 * 10.764);
  return `${m2} m² (${sqft} sq ft)`;
}

export function formatDistance(metres: number | null | undefined): string {
  if (metres == null) return "N/A";
  if (metres < 1000) return `${metres}m`;
  return `${(metres / 1000).toFixed(1)}km`;
}

// ─── Confidence ──────────────────────────────────────────────

export function confidenceLabel(score: number): string {
  if (score >= 0.80) return "High";
  if (score >= 0.60) return "Medium";
  return "Low";
}

export function confidenceColor(score: number): string {
  if (score >= 0.80) return "text-emerald-600";
  if (score >= 0.60) return "text-amber-500";
  return "text-red-500";
}

export function confidenceBg(score: number): string {
  if (score >= 0.80) return "bg-emerald-500";
  if (score >= 0.60) return "bg-amber-400";
  return "bg-red-400";
}

// ─── EPC ─────────────────────────────────────────────────────

export function epcColor(rating: string | null | undefined): string {
  const map: Record<string, string> = {
    A: "bg-emerald-500 text-white",
    B: "bg-green-400 text-white",
    C: "bg-lime-400 text-stone-900",
    D: "bg-yellow-400 text-stone-900",
    E: "bg-orange-400 text-white",
    F: "bg-red-400 text-white",
    G: "bg-red-600 text-white",
  };
  return map[rating?.toUpperCase() ?? ""] ?? "bg-stone-200 text-stone-700";
}
