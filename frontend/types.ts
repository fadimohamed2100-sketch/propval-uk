// ─── Address ─────────────────────────────────────────────────
export interface Address {
  id:         string;
  line_1:     string;
  line_2:     string | null;
  city:       string;
  county:     string | null;
  postcode:   string;
  country:    string;
  lat:        number | null;
  lng:        number | null;
  created_at: string;
}

// ─── Property ────────────────────────────────────────────────
export interface Property {
  id:                 string;
  address:            Address;
  property_type:      string;
  bedrooms:           number | null;
  bathrooms:          number | null;
  floor_area_m2:      number | null;
  year_built:         number | null;
  epc_rating:         string | null;
  tenure:             string | null;
  lease_years_remaining: number | null;
  is_new_build:       boolean;
  council_tax_band:   string | null;
  features:           Record<string, unknown>;
  created_at:         string;
  updated_at:         string;
}

// ─── Comparable ──────────────────────────────────────────────
export interface Comparable {
  id:                 string;
  address_snapshot:   string;
  postcode_snapshot:  string;
  property_type:      string | null;
  bedrooms:           number | null;
  floor_area_m2:      number | null;
  sale_price_gbp:     number;
  sale_date:          string;
  price_per_m2_gbp:   number | null;
  distance_m:         number | null;
  similarity_score:   number | null;
  adjustment_pct:     number | null;
  source:             string;
}

// ─── Valuation ───────────────────────────────────────────────
export interface Valuation {
  id:                    string;
  property_id:           string;
  property:              Property;
  status:                "pending" | "complete" | "failed";
  estimated_value_gbp:   number;
  range_low_gbp:         number;
  range_high_gbp:        number;
  confidence_score:      number;
  rental_monthly_gbp:    number;
  rental_yield:          number;
  source_apis:           string[];
  comparables:           Comparable[];
  methodology:           Record<string, unknown>;
  pdf_url:               string | null;
  created_at:            string;
  expires_at:            string;
}

// ─── Requests ────────────────────────────────────────────────
export interface ValuationRequest {
  address:       string;
  force_refresh?: boolean;
}

export interface AddressSearchRequest {
  address: string;
}

export interface AddressSearchResponse {
  address:  Address;
  property: Property | null;
  message:  string;
}

// ─── Errors ──────────────────────────────────────────────────
export interface ApiError {
  detail: string;
  code?:  string;
}
