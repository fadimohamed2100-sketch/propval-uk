import type {
  AddressSearchRequest,
  AddressSearchResponse,
  ApiError,
  Valuation,
  ValuationHistoryItem,
  ValuationRequest,
} from "./types";

const BASE = "/api/backend";

class ApiClientError extends Error {
  status:  number;
  detail:  string;
  code?:   string;

  constructor(status: number, error: ApiError) {
    super(error.detail);
    this.status = status;
    this.detail = error.detail;
    this.code   = error.code;
  }
}

async function request<T>(
  path: string,
  init?: RequestInit,
  token?: string | null,
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string> | undefined),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers,
  });

  if (!res.ok) {
    let errBody: ApiError = { detail: "An unexpected error occurred." };
    try { errBody = await res.json(); } catch { /* ignore */ }
    throw new ApiClientError(res.status, errBody);
  }

  return res.json() as Promise<T>;
}

// ─── Endpoints ───────────────────────────────────────────────

export async function searchAddress(
  body: AddressSearchRequest,
): Promise<AddressSearchResponse> {
  return request<AddressSearchResponse>("/address/search", {
    method: "POST",
    body:   JSON.stringify(body),
  });
}

export async function runValuation(
  body: ValuationRequest,
  token: string | null,
): Promise<Valuation> {
  return request<Valuation>(
    "/valuation/run",
    { method: "POST", body: JSON.stringify(body) },
    token,
  );
}

export async function getValuation(id: string): Promise<Valuation> {
  return request<Valuation>(`/valuation/${id}`);
}

export async function getValuationHistory(
  token: string | null,
): Promise<ValuationHistoryItem[]> {
  return request<ValuationHistoryItem[]>("/valuation/history", undefined, token);
}

export function reportPdfUrl(id: string): string {
  return `${BASE}/valuation/${id}/report`;
}

export interface CreditsInfo {
  credits_remaining: number;
  subscription_tier: string | null;
  credits_reset_at: string | null;
  costs: { valuation: number; pdf_additional: number; pdf_total_with_valuation: number };
}

export async function getCredits(token: string | null): Promise<CreditsInfo> {
  return request<CreditsInfo>("/credits", undefined, token);
}

/**
 * Downloads the PDF via an authenticated fetch (the endpoint charges
 * credits, so it requires the Clerk session token - a bare <a href>
 * can't carry it). Streams the response to a Blob and triggers the
 * browser download. Throws ApiClientError (status 402 = out of credits).
 */
export async function downloadReportPdf(
  id: string,
  token: string | null,
  force = false,
): Promise<void> {
  const res = await fetch(`${BASE}/valuation/${id}/report${force ? "?force=true" : ""}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    let errBody: ApiError = { detail: "An unexpected error occurred." };
    try { errBody = await res.json(); } catch { /* ignore */ }
    throw new ApiClientError(res.status, errBody);
  }
  const disposition = res.headers.get("Content-Disposition") || "";
  const match = disposition.match(/filename="?([^"]+)"?/);
  const filename = match ? match[1] : `valuation_${id}.pdf`;

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/** Fire after any credit-spending action so badges refetch the balance. */
export function notifyCreditsChanged(): void {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent("credits:refresh"));
  }
}

export { ApiClientError };
