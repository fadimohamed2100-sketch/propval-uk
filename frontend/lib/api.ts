import type {
  AddressSearchRequest,
  AddressSearchResponse,
  ApiError,
  Valuation,
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
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
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
): Promise<Valuation> {
  return request<Valuation>("/valuation/run", {
    method: "POST",
    body:   JSON.stringify(body),
  });
}

export async function getValuation(id: string): Promise<Valuation> {
  return request<Valuation>(`/valuation/${id}`);
}

export function reportPdfUrl(id: string): string {
  return `${BASE}/valuation/${id}/report`;
}

export { ApiClientError };
