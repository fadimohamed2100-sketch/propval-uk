"use client";

import {
  useState, useRef, useEffect, useCallback, KeyboardEvent,
} from "react";
import { MapPin, Search, Loader2, X, ChevronRight, Building2 } from "lucide-react";

// ── Types ──────────────────────────────────────────────────────
interface AddressSuggestion {
  id:            string;
  display_line:  string;
  full_address:  string;
  line_1:        string;
  line_2:        string | null;
  city:          string;
  postcode:      string;
  lat:           number | null;
  lng:           number | null;
  property_type: string | null;
  uprn:          string | null;
}

interface AddressSuggestionsResponse {
  query:       string;
  count:       number;
  suggestions: AddressSuggestion[];
  source:      string;
}

interface AddressSearchProps {
  /** Called when the user selects a suggestion */
  onSelect: (suggestion: AddressSuggestion) => void;
  /** Optional placeholder text */
  placeholder?: string;
  /** Called when the user clears the input */
  onClear?: () => void;
  /** Whether the parent is in a loading state */
  loading?: boolean;
  /** Initial value to pre-fill (e.g. from URL params) */
  initialValue?: string;
}

// ── Helpers ────────────────────────────────────────────────────

function propertyTypeLabel(type: string | null): string {
  if (!type) return "Property";
  const map: Record<string, string> = {
    flat:          "Flat",
    terraced:      "Terraced",
    semi_detached: "Semi-detached",
    detached:      "Detached",
    maisonette:    "Maisonette",
    bungalow:      "Bungalow",
  };
  return map[type] ?? type.replace(/_/g, " ");
}

function highlightMatch(text: string, query: string): React.ReactNode {
  if (!query.trim()) return text;
  const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "gi");
  const parts = text.split(regex);
  return (
    <>
      {parts.map((part, i) =>
        regex.test(part) ? (
          <mark key={i} className="bg-gold-300/30 text-ink font-semibold rounded-[2px]">
            {part}
          </mark>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </>
  );
}

// ── Main component ─────────────────────────────────────────────

export function AddressSearch({
  onSelect,
  onClear,
  loading = false,
  placeholder = "Start typing an address or postcode…",
  initialValue = "",
}: AddressSearchProps) {
  const [query,       setQuery]       = useState(initialValue);
  const [suggestions, setSuggestions] = useState<AddressSuggestion[]>([]);
  const [open,        setOpen]        = useState(false);
  const [fetching,    setFetching]    = useState(false);
  const [activeIdx,   setActiveIdx]   = useState(-1);
  const [selected,    setSelected]    = useState<AddressSuggestion | null>(null);
  const [error,       setError]       = useState<string | null>(null);

  const inputRef    = useRef<HTMLInputElement>(null);
  const listRef     = useRef<HTMLUListElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortRef    = useRef<AbortController | null>(null);

  // ── Fetch suggestions (debounced 200 ms) ──────────────────────
  const fetchSuggestions = useCallback(async (q: string) => {
    if (q.trim().length < 2) {
      setSuggestions([]);
      setOpen(false);
      return;
    }

    // Cancel any in-flight request
    abortRef.current?.abort();
    abortRef.current = new AbortController();

    setFetching(true);
    setError(null);

    try {
      const res = await fetch(
        `/api/backend/address/search?q=${encodeURIComponent(q)}&limit=8`,
        { signal: abortRef.current.signal },
      );
      if (!res.ok) throw new Error("Search failed");
      const data: AddressSuggestionsResponse = await res.json();
      setSuggestions(data.suggestions);
      setOpen(data.suggestions.length > 0);
      setActiveIdx(-1);
    } catch (err: unknown) {
      if ((err as Error).name !== "AbortError") {
        setError("Could not load suggestions.");
        setOpen(false);
      }
    } finally {
      setFetching(false);
    }
  }, []);

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const val = e.target.value;
    setQuery(val);
    setSelected(null);

    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => fetchSuggestions(val), 200);
  }

  // ── Selection ─────────────────────────────────────────────────
  function handleSelect(suggestion: AddressSuggestion) {
    setQuery(suggestion.full_address);
    setSelected(suggestion);
    setSuggestions([]);
    setOpen(false);
    setActiveIdx(-1);
    onSelect(suggestion);
  }

  function handleClear() {
    setQuery("");
    setSelected(null);
    setSuggestions([]);
    setOpen(false);
    setError(null);
    onClear?.();
    inputRef.current?.focus();
  }

  // ── Keyboard navigation ───────────────────────────────────────
  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (!open || suggestions.length === 0) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIdx((i) => Math.min(i + 1, suggestions.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIdx((i) => Math.max(i - 1, -1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (activeIdx >= 0) {
        handleSelect(suggestions[activeIdx]);
      }
    } else if (e.key === "Escape") {
      setOpen(false);
      setActiveIdx(-1);
    }
  }

  // Scroll active item into view
  useEffect(() => {
    if (activeIdx < 0 || !listRef.current) return;
    const item = listRef.current.children[activeIdx] as HTMLElement;
    item?.scrollIntoView({ block: "nearest" });
  }, [activeIdx]);

  // Close dropdown on outside click
  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (
        listRef.current &&
        !listRef.current.contains(e.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  const showSpinner = fetching || loading;

  return (
    <div className="relative w-full">
      {/* ── Input ───────────────────────────────────────────── */}
      <div className={`
        relative flex items-center bg-white rounded-2xl border-2 transition-all
        shadow-[0_2px_8px_rgba(0,0,0,0.06),0_12px_40px_rgba(0,0,0,0.08)]
        ${open  ? "rounded-b-none border-gold-400 shadow-glow"
                : selected
                ? "border-emerald-300"
                : error
                ? "border-red-300"
                : "border-stone-200 focus-within:border-gold-400"}
      `}>
        {/* Left icon */}
        <div className="absolute left-5 flex items-center pointer-events-none">
          {showSpinner ? (
            <Loader2 size={18} className="text-gold-400 animate-spin" />
          ) : selected ? (
            <Building2 size={18} className="text-emerald-500" />
          ) : (
            <MapPin size={18} className="text-ink-faint" />
          )}
        </div>

        <input
          ref={inputRef}
          type="text"
          role="combobox"
          aria-expanded={open}
          aria-autocomplete="list"
          aria-controls="address-listbox"
          aria-activedescendant={activeIdx >= 0 ? `addr-opt-${activeIdx}` : undefined}
          value={query}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          onFocus={() => suggestions.length > 0 && setOpen(true)}
          placeholder={placeholder}
          disabled={loading}
          autoComplete="off"
          spellCheck={false}
          className={`
            w-full py-5 pl-14 pr-12 text-base bg-transparent outline-none
            placeholder:text-ink-faint text-ink
            ${open ? "rounded-t-2xl" : "rounded-2xl"}
          `}
        />

        {/* Clear button */}
        {query && !loading && (
          <button
            onClick={handleClear}
            aria-label="Clear address"
            className="absolute right-4 p-1.5 rounded-lg text-ink-faint hover:text-ink hover:bg-stone-100 transition-colors"
          >
            <X size={16} />
          </button>
        )}
      </div>

      {/* ── Error ────────────────────────────────────────────── */}
      {error && (
        <p className="mt-2 text-sm text-red-500 pl-1">{error}</p>
      )}

      {/* ── Dropdown ─────────────────────────────────────────── */}
      {open && suggestions.length > 0 && (
        <ul
          ref={listRef}
          id="address-listbox"
          role="listbox"
          aria-label="Address suggestions"
          className="
            absolute z-50 w-full bg-white border-2 border-t-0 border-gold-400
            rounded-b-2xl shadow-card-lg overflow-hidden
            max-h-[340px] overflow-y-auto divide-y divide-stone-50
          "
        >
          {suggestions.map((s, i) => (
            <li
              key={s.id}
              id={`addr-opt-${i}`}
              role="option"
              aria-selected={i === activeIdx}
              onMouseDown={(e) => { e.preventDefault(); handleSelect(s); }}
              onMouseEnter={() => setActiveIdx(i)}
              className={`
                flex items-center gap-3 px-5 py-3.5 cursor-pointer
                transition-colors group
                ${i === activeIdx ? "bg-stone-50" : "hover:bg-stone-50/60"}
              `}
            >
              {/* Pin icon */}
              <div className={`
                w-7 h-7 rounded-lg flex items-center justify-center shrink-0
                transition-colors
                ${i === activeIdx
                  ? "bg-gold-300/30 text-gold-500"
                  : "bg-stone-100 text-ink-faint group-hover:bg-gold-300/20 group-hover:text-gold-500"}
              `}>
                <MapPin size={14} />
              </div>

              {/* Address text */}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-ink truncate leading-snug">
                  {highlightMatch(s.display_line, query)}
                </p>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="font-mono text-xs text-ink-muted">{s.postcode}</span>
                  {s.property_type && (
                    <span className="text-xs text-ink-faint">
                      · {propertyTypeLabel(s.property_type)}
                    </span>
                  )}
                  {s.city && (
                    <span className="text-xs text-ink-faint">· {s.city}</span>
                  )}
                </div>
              </div>

              {/* Chevron */}
              <ChevronRight
                size={14}
                className={`shrink-0 transition-opacity ${
                  i === activeIdx ? "opacity-60" : "opacity-0 group-hover:opacity-40"
                }`}
              />
            </li>
          ))}

          {/* Footer */}
          <li className="px-5 py-2 flex items-center justify-between bg-stone-50/80">
            <span className="text-[10px] text-ink-faint font-mono">
              {suggestions.length} result{suggestions.length !== 1 ? "s" : ""}
            </span>
            <span className="text-[10px] text-ink-faint">
              ↑ ↓ to navigate · ↵ to select · esc to close
            </span>
          </li>
        </ul>
      )}

      {/* No results state */}
      {open && !fetching && suggestions.length === 0 && query.length >= 2 && (
        <div className="
          absolute z-50 w-full bg-white border-2 border-t-0 border-gold-400
          rounded-b-2xl shadow-card-lg px-5 py-6 text-center
        ">
          <Search size={20} className="mx-auto text-ink-faint mb-2" />
          <p className="text-sm text-ink-muted">No addresses found for &ldquo;{query}&rdquo;</p>
          <p className="text-xs text-ink-faint mt-1">
            Try a street name, postcode, or city
          </p>
        </div>
      )}
    </div>
  );
}
