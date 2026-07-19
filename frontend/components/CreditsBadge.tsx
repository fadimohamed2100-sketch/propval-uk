"use client";
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { getCredits } from "@/lib/api";

/**
 * Persistent credit counter for the nav bar.
 *
 * - Fetches the live balance from GET /api/v1/credits on mount
 * - Refetches whenever a "credits:refresh" window event fires
 *   (dispatched via notifyCreditsChanged() after any valuation / PDF)
 * - Amber below 10 credits, red at 0 - so agents see it coming
 * - Renders nothing while signed out or before the first load
 */
export default function CreditsBadge() {
  const { getToken, isSignedIn } = useAuth();
  const [credits, setCredits] = useState<number | null>(null);

  const refresh = useCallback(async () => {
    try {
      const token = await getToken();
      if (!token) return;
      const info = await getCredits(token);
      setCredits(info.credits_remaining);
    } catch {
      /* keep last known value on transient errors */
    }
  }, [getToken]);

  useEffect(() => {
    if (!isSignedIn) return;
    refresh();
    const handler = () => refresh();
    window.addEventListener("credits:refresh", handler);
    return () => window.removeEventListener("credits:refresh", handler);
  }, [isSignedIn, refresh]);

  if (!isSignedIn || credits === null) return null;

  const empty = credits <= 0;
  const low = credits < 10;
  const color = empty ? "#dc2626" : low ? "#d97706" : "#1a1a1a";
  const bg = empty ? "#fef2f2" : low ? "#fffbeb" : "#f5f5f4";
  const border = empty ? "#fecaca" : low ? "#fde68a" : "#e7e5e4";

  return (
    <span
      title={
        empty
          ? "You're out of credits - contact us to top up"
          : "Valuation: 1 credit · PDF report: 3 credits total"
      }
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        background: bg,
        border: `1px solid ${border}`,
        color,
        borderRadius: 999,
        padding: "4px 12px",
        fontSize: 13,
        fontWeight: 600,
        fontFamily: "sans-serif",
        whiteSpace: "nowrap",
      }}
    >
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3 3" />
      </svg>
      {credits.toLocaleString("en-GB")} credit{credits === 1 ? "" : "s"}
    </span>
  );
}
