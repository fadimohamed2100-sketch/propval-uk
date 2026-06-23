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

export { ApiClientError };
