"use client";

import { useRef } from "react";

// ─────────────────────────────────────────────────────────────────
// DEFAULT DATA  — swap for live props
// ─────────────────────────────────────────────────────────────────
const DEFAULT_REPORT = {
  agent: {
    name:       "JBrown Property UK",
    address:    "Unit F, Residence Tower, Woodberry Grove, London N4 2LZ",
    phone:      "020 3981 7181",
    email:      "contact@jbrown.com",
    website:    "jbrownpropertyuk.co.uk",
    reportDate: "23 Feb 2026",
  },
  property: {
    address1:   "Flat 307 Jigger Mast House",
    address2:   "Mast Quay London",
    postcode:   "SE18 5NH",
    type:       "Flat/Maisonette",
    floorArea:  "752 sqft",
    yearBuilt:  "2010",
    receptions: 1,
    bedrooms:   2,
    bathrooms:  2,
  },
  market: {
    area:            "Greenwich",
    askingPricePct:  96,
    weeksOnMarket:   17,
    searches:        "565,196",
    searchArea:      "SE18",
    postcodeSector:  "SE18 5",
    bedrooms:        2,
    propertyType:    "flats/maisonettes",
    chart: {
      // £k values  Jan-21 → Jan-26
      subject: [415, 418, 410, 395, 365, 328],
      areaAvg: [415, 415, 408, 388, 360, 340],
      labels:  ["Jan-21","Jan-22","Jan-23","Jan-24","Jan-25","Jan-26"],
    },
  },
  comparables: [
    { street: "Mast Quay",       distance: "0.02 miles", type: "flat/maisonette",          size: "828 sqft", price: "£325,000", date: "January 2024"  },
    { street: "Europe Road",     distance: "0.12 miles", type: "2 bedroom flat/maisonette", size: "839 sqft", price: "£165,000", date: "November 2021" },
    { street: "Leda Road",       distance: "0.15 miles", type: "1 bedroom flat/maisonette", size: "581 sqft", price: "£157,000", date: "August 2023"   },
    { street: "St. Mary Street", distance: "0.18 miles", type: "2 bedroom flat/maisonette", size: "667 sqft", price: "£255,000", date: "May 2022"      },
    { street: "Powis Street",    distance: "0.23 miles", type: "1 bedroom flat/maisonette", size: "602 sqft", price: "£265,000", date: "April 2024"    },
    { street: "Kingsman Street", distance: "0.23 miles", type: "2 bedroom flat/maisonette", size: "753 sqft", price: "£320,000", date: "March 2025"    },
  ],
  valuation: {
    capitalValue:  "£328,000",
    rangeLow:      "£312,000",
    rangeHigh:     "£344,000",
    confidence:    "high",
    lastSalePrice: "£228,500",
    lastSaleDate:  "February 2010",
    priceChange:   "+ £99,500",
    rentalValue:   "£1,960 pcm",
    grossYield:    "7.2%",
  },
};

// ─────────────────────────────────────────────────────────────────
// BRAND COLOURS  (all from the original PDF)
// ─────────────────────────────────────────────────────────────────
const B = {
  headerBg: "#2B1649",   // section header bar background
  purple:   "#4B2590",   // body text, some metric values
  orange:   "#E8522A",   // capital value, rental value highlight
  pageBg:   "#EBEBEB",   // light grey page background
  footer:   "#4B2590",   // footer bar background
};

// ─────────────────────────────────────────────────────────────────
// SHARED SUB-COMPONENTS
// ─────────────────────────────────────────────────────────────────

/**
 * Section header: dark-purple box left + purple rule extending right
 * Identical to every section header across all four PDF pages.
 */
function SectionHeader({ title }) {
  return (
    <div className="flex items-center mb-5 mt-1">
      <div
        className="text-white text-xs font-bold px-3 py-1.5 shrink-0 tracking-wide"
        style={{ backgroundColor: B.headerBg }}
      >
        {title}
      </div>
      <div
        className="flex-1 ml-0"
        style={{ height: 2, backgroundColor: "#7C3AED" }}
      />
    </div>
  );
}

/** Zoopla + Hometrack footer bar, identical on every page */
function PageFooter() {
  return (
    <div
      className="flex items-center justify-between px-7 py-3.5"
      style={{ backgroundColor: B.footer }}
    >
      {/* Zoopla wordmark */}
      <span className="text-white font-bold text-2xl tracking-tight" style={{ fontFamily: "sans-serif" }}>
        Zoopla
      </span>

      {/* Hometrack mark */}
      <div className="flex items-center gap-2">
        <span className="text-white text-xs opacity-80">Valuation powered by</span>
        {/* Simplified bar-chart icon */}
        <div className="flex items-end gap-[2px] ml-1">
          {[8, 12, 16, 12, 8].map((h, i) => (
            <div
              key={i}
              className="w-1.5 rounded-sm bg-white"
              style={{ height: h }}
            />
          ))}
        </div>
        <span className="text-white text-sm font-semibold tracking-tight">hometrack</span>
      </div>
    </div>
  );
}

/** A4 page wrapper. Each section is a self-contained "page". */
function Page({ children, noPad = false }) {
  return (
    <div
      className="bg-white w-full flex flex-col shadow-md print:shadow-none print:mb-0 mb-6 break-after-page overflow-hidden"
      style={{ maxWidth: 794, minHeight: 1123 }}
    >
      {noPad ? children : (
        <div className="flex-1 flex flex-col" style={{ backgroundColor: B.pageBg }}>
          {children}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// PROPERTY ATTRIBUTE ICONS  (SVG, matching the purple icon style)
// ─────────────────────────────────────────────────────────────────
function IconHouse() {
  return (
    <svg viewBox="0 0 44 44" className="w-11 h-11">
      <path d="M22 5L3 19.5V22h4v16h10V28h10v10h10V22h4v-2.5L22 5z"
            fill="none" stroke={B.purple} strokeWidth="2" strokeLinejoin="round"/>
      <rect x="17" y="28" width="10" height="10" fill="none" stroke={B.purple} strokeWidth="1.5"/>
    </svg>
  );
}
function IconFloorplan() {
  return (
    <svg viewBox="0 0 44 44" className="w-11 h-11">
      <rect x="5" y="5" width="34" height="34" rx="1" fill="none" stroke={B.purple} strokeWidth="2"/>
      <polyline points="5,22 25,22 25,5" fill="none" stroke={B.purple} strokeWidth="2"/>
      <line x1="25" y1="22" x2="25" y2="39" stroke={B.purple} strokeWidth="2"/>
      <line x1="15" y1="22" x2="15" y2="39" stroke={B.purple} strokeWidth="1.5"/>
    </svg>
  );
}
function IconClock() {
  return (
    <svg viewBox="0 0 44 44" className="w-11 h-11">
      <circle cx="22" cy="22" r="16" fill="none" stroke={B.purple} strokeWidth="2"/>
      <circle cx="22" cy="22" r="1.5" fill={B.purple}/>
      <line x1="22" y1="22" x2="22" y2="10" stroke={B.purple} strokeWidth="2" strokeLinecap="round"/>
      <line x1="22" y1="22" x2="30" y2="22" stroke={B.purple} strokeWidth="2" strokeLinecap="round"/>
      {/* Tick marks at 12/3/6/9 */}
      {[0,90,180,270].map((deg) => {
        const r = deg * Math.PI / 180;
        const x1 = 22 + 14 * Math.sin(r); const y1 = 22 - 14 * Math.cos(r);
        const x2 = 22 + 16 * Math.sin(r); const y2 = 22 - 16 * Math.cos(r);
        return <line key={deg} x1={x1} y1={y1} x2={x2} y2={y2} stroke={B.purple} strokeWidth="1.5"/>;
      })}
    </svg>
  );
}
function IconSofa() {
  return (
    <svg viewBox="0 0 44 44" className="w-11 h-11">
      <rect x="9"  y="18" width="26" height="12" rx="3" fill="none" stroke={B.purple} strokeWidth="2"/>
      <rect x="5"  y="22" width="7"  height="8"  rx="2" fill="none" stroke={B.purple} strokeWidth="2"/>
      <rect x="32" y="22" width="7"  height="8"  rx="2" fill="none" stroke={B.purple} strokeWidth="2"/>
      <rect x="9"  y="14" width="26" height="6"  rx="2" fill="none" stroke={B.purple} strokeWidth="1.5"/>
      <line x1="12" y1="30" x2="12" y2="36" stroke={B.purple} strokeWidth="2" strokeLinecap="round"/>
      <line x1="32" y1="30" x2="32" y2="36" stroke={B.purple} strokeWidth="2" strokeLinecap="round"/>
    </svg>
  );
}
function IconBed() {
  return (
    <svg viewBox="0 0 44 44" className="w-11 h-11">
      <rect x="4"  y="24" width="36" height="11" rx="2" fill="none" stroke={B.purple} strokeWidth="2"/>
      <rect x="4"  y="16" width="5"  height="12" rx="1" fill="none" stroke={B.purple} strokeWidth="2"/>
      <rect x="15" y="19" width="12" height="8"  rx="2" fill="none" stroke={B.purple} strokeWidth="1.5"/>
      <rect x="29" y="19" width="11" height="8"  rx="2" fill="none" stroke={B.purple} strokeWidth="1.5"/>
      <line x1="4"  y1="35" x2="4"  y2="40" stroke={B.purple} strokeWidth="2" strokeLinecap="round"/>
      <line x1="40" y1="35" x2="40" y2="40" stroke={B.purple} strokeWidth="2" strokeLinecap="round"/>
    </svg>
  );
}
function IconBath() {
  return (
    <svg viewBox="0 0 44 44" className="w-11 h-11">
      <path d="M6 22h32v6a7 7 0 01-7 7H13a7 7 0 01-7-7v-6z"
            fill="none" stroke={B.purple} strokeWidth="2"/>
      <path d="M11 22V14a4 4 0 018 0v2"
            fill="none" stroke={B.purple} strokeWidth="2" strokeLinecap="round"/>
      <line x1="8"  y1="35" x2="6"  y2="40" stroke={B.purple} strokeWidth="2" strokeLinecap="round"/>
      <line x1="36" y1="35" x2="38" y2="40" stroke={B.purple} strokeWidth="2" strokeLinecap="round"/>
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────────
// PAGE 1 — COVER
// ─────────────────────────────────────────────────────────────────
function CoverPage({ report }) {
  const { agent, property } = report;
  return (
    <Page>
      <div className="flex-1 p-10">
        {/* JBrown logo */}
        <div
          className="inline-flex flex-col items-center justify-center px-5 py-3 mb-10"
          style={{ backgroundColor: "#1A1A2E", minWidth: 130 }}
        >
          <span className="text-white font-bold text-xl leading-none tracking-wide">
            JBrown
          </span>
          <span className="text-xs tracking-widest mt-0.5" style={{ color: "#D4A4A4" }}>
            International
          </span>
        </div>

        {/* Title + address card */}
        <div className="bg-white rounded-sm shadow-sm p-8 mb-10">
          <h1
            className="text-[40px] font-extrabold leading-none mb-8"
            style={{ color: B.headerBg }}
          >
            Property Valuation
          </h1>

          {/* Two-column split with dashed divider */}
          <div
            className="grid grid-cols-2 gap-0 pt-6"
            style={{ borderTop: "1.5px dashed #C8C0D8" }}
          >
            <div style={{ color: B.purple }} className="text-sm leading-7 pr-6">
              <p>{property.address1}</p>
              <p>{property.address2}</p>
              <p>{property.postcode}</p>
            </div>
            <div
              style={{ color: B.purple, borderLeft: "1.5px dashed #C8C0D8" }}
              className="text-sm leading-7 pl-6"
            >
              <p>Created by</p>
              <p>{agent.name}</p>
              <p>{agent.reportDate}</p>
            </div>
          </div>
        </div>

        {/* Agent profile section */}
        <SectionHeader title="Agent profile" />
        <div className="bg-white rounded-sm shadow-sm p-6">
          <p className="text-sm text-gray-700 leading-relaxed mb-4">
            Your agent has generated this in-depth valuation report using data from Zoopla and
            Hometrack. Hometrack are the UK's largest valuer of residential property for
            professionals.
          </p>
          <p className="text-sm text-gray-700 leading-relaxed">
            Having seen your property, your agent will be able to give you an expert opinion on
            the recommended asking price.
          </p>
        </div>
      </div>
      <PageFooter />
    </Page>
  );
}

// ─────────────────────────────────────────────────────────────────
// PAGE 2 — PROPERTY SUMMARY + MARKET INSIGHTS
// ─────────────────────────────────────────────────────────────────

/** SVG line chart matching the Hometrack price history chart */
function PriceChart({ chart, sector, bedrooms, type }) {
  const W = 240, H = 130;
  const yMin = 300, yMax = 500;
  const xPad = 44, yPad = 10;
  const plotW = W - xPad - 6;
  const plotH = H - yPad - 20;
  const n = chart.labels.length;
  const xStep = plotW / (n - 1);
  const toX = (i) => xPad + i * xStep;
  const toY = (v) => yPad + plotH - ((v - yMin) / (yMax - yMin)) * plotH;

  const subjectPts = chart.subject.map((v, i) => `${toX(i)},${toY(v)}`).join(" ");
  const avgPts     = chart.areaAvg.map((v, i)  => `${toX(i)},${toY(v)}`).join(" ");
  const yTicks = [500,480,460,440,420,400,380,360,340,320,300];

  return (
    <div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full"
        style={{ height: 140 }}
        aria-label="Property price history chart"
      >
        {/* Y axis ticks + grid */}
        {yTicks.map((v) => {
          const y = toY(v);
          return (
            <g key={v}>
              <line x1={xPad} y1={y} x2={W - 6} y2={y}
                    stroke="#E5E7EB" strokeWidth="0.5" />
              <text x={xPad - 3} y={y + 2.5} textAnchor="end"
                    fontSize="5.5" fill="#888">
                £{v}k
              </text>
            </g>
          );
        })}

        {/* Area average line (gray) */}
        <polyline points={avgPts} fill="none" stroke="#9CA3AF" strokeWidth="1.3"
                  strokeLinejoin="round" />
        {chart.areaAvg.map((v, i) => (
          <circle key={i} cx={toX(i)} cy={toY(v)} r="2.2" fill="#9CA3AF" />
        ))}

        {/* Subject property line (dark purple) */}
        <polyline points={subjectPts} fill="none" stroke={B.headerBg} strokeWidth="1.3"
                  strokeLinejoin="round" />
        {chart.subject.map((v, i) => (
          <circle key={i} cx={toX(i)} cy={toY(v)} r="2.2" fill={B.headerBg} />
        ))}

        {/* X axis labels */}
        {chart.labels.map((lbl, i) => (
          <text key={lbl} x={toX(i)} y={H - 3} textAnchor="middle"
                fontSize="5.5" fill="#888">
            {lbl}
          </text>
        ))}
      </svg>

      {/* Legend */}
      <div className="flex flex-col gap-1 mt-1">
        <div className="flex items-center gap-1.5">
          <div className="w-4 border-t-2 rounded" style={{ borderColor: B.headerBg }} />
          <span className="text-[10px] text-gray-500">Estimated value of this property</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-4 border-t-2 border-gray-400 rounded" />
          <span className="text-[10px] text-gray-500">
            Average value of {bedrooms} bedroom {type} in {sector}
          </span>
        </div>
      </div>
      <p className="text-[10px] text-gray-600 mt-2">
        Price change over the last 5 years of{" "}
        {bedrooms} bedroom {type} in <strong>{sector}</strong>
      </p>
    </div>
  );
}

function SummaryPage({ report }) {
  const { property, market } = report;

  const attrs = [
    { icon: <IconHouse />,     label: "Property type",    value: property.type       },
    { icon: <IconFloorplan />, label: "Total floor area", value: property.floorArea  },
    { icon: <IconClock />,     label: "Year built",       value: property.yearBuilt  },
    { icon: <IconSofa />,      label: "Receptions",       value: property.receptions },
    { icon: <IconBed />,       label: "Bedrooms",         value: property.bedrooms   },
    { icon: <IconBath />,      label: "Bathrooms",        value: property.bathrooms  },
  ];

  return (
    <Page>
      <div className="flex-1 p-8">
        {/* ── Property summary ── */}
        <SectionHeader title="Your property summary" />

        <p className="text-sm text-gray-700 leading-relaxed mb-5">
          This exclusive report provides a unique up-to-date insight into the value of your
          property and analysis of the local market, for{" "}
          <strong>
            {property.address1} {property.address2}, {property.postcode}
          </strong>
        </p>

        {/* 3×2 attribute grid */}
        <div className="grid grid-cols-3 gap-3 mb-7">
          {attrs.map(({ icon, label, value }) => (
            <div
              key={label}
              className="bg-white rounded-sm border border-gray-200 shadow-sm py-5 px-3 flex flex-col items-center text-center"
            >
              <div className="mb-3">{icon}</div>
              <p className="text-xs text-gray-500 mb-1">{label}</p>
              <p className="text-lg font-extrabold" style={{ color: B.headerBg }}>
                {value}
              </p>
            </div>
          ))}
        </div>

        {/* ── Market insights ── */}
        <SectionHeader title="Market insights" />

        <div
          className="bg-white rounded-sm border border-gray-200 shadow-sm overflow-hidden"
        >
          <div className="grid grid-cols-2 divide-x divide-dashed divide-gray-300">

            {/* LEFT: asking price % + chart */}
            <div className="p-5">
              <p className="text-[10px] text-gray-500 mb-2 font-medium">{market.area}</p>

              {/* Big % box */}
              <div
                className="inline-block px-6 py-2 rounded-sm mb-3"
                style={{ backgroundColor: B.purple }}
              >
                <span className="text-white text-4xl font-extrabold leading-none">
                  {market.askingPricePct}%
                </span>
              </div>

              <p className="text-sm mb-5 leading-relaxed" style={{ color: B.purple }}>
                Properties near you are achieving an average of{" "}
                <strong>{market.askingPricePct}%</strong> of the asking price
              </p>

              <div className="border-t border-dashed border-gray-300 pt-4">
                <PriceChart
                  chart={market.chart}
                  sector={market.postcodeSector}
                  bedrooms={market.bedrooms}
                  type={market.propertyType}
                />
              </div>
            </div>

            {/* RIGHT: weeks on market + searches */}
            <div className="p-5">
              {/* Weeks on market */}
              <div className="flex items-start gap-3 mb-3">
                <div
                  className="border-2 rounded-sm flex items-center justify-center px-3 py-2 shrink-0"
                  style={{ borderColor: B.purple }}
                >
                  <span className="text-2xl font-extrabold leading-none" style={{ color: B.purple }}>
                    {market.weeksOnMarket}
                  </span>
                </div>
                <div>
                  <p className="text-2xl font-extrabold leading-none" style={{ color: B.purple }}>
                    weeks
                  </p>
                  <p className="text-sm text-gray-500">on market</p>
                </div>
              </div>

              <p className="text-sm leading-relaxed mb-7" style={{ color: B.purple }}>
                Properties near you spend an average time on the market of{" "}
                <strong>{market.weeksOnMarket} weeks</strong>
              </p>

              {/* Searches */}
              <div className="border-t border-dashed border-gray-300 pt-5">
                <div className="flex items-center gap-2 mb-3">
                  <div
                    className="border-2 rounded-sm px-3 py-2"
                    style={{ borderColor: B.purple }}
                  >
                    <span className="font-extrabold text-base" style={{ color: B.purple }}>
                      {market.searches} searches
                    </span>
                  </div>
                  <div
                    className="border-2 rounded-sm p-2"
                    style={{ borderColor: B.purple }}
                  >
                    {/* Search icon */}
                    <svg viewBox="0 0 20 20" className="w-5 h-5">
                      <circle cx="9" cy="9" r="5.5" fill="none"
                              stroke={B.purple} strokeWidth="2"/>
                      <line x1="13.5" y1="13.5" x2="17" y2="17"
                            stroke={B.purple} strokeWidth="2" strokeLinecap="round"/>
                    </svg>
                  </div>
                </div>

                <p className="text-sm leading-relaxed" style={{ color: B.purple }}>
                  There were <strong>{market.searches} searches</strong> for properties
                  in {market.searchArea} on Zoopla over the past 28 days
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
      <PageFooter />
    </Page>
  );
}

// ─────────────────────────────────────────────────────────────────
// PAGE 3 — COMPARABLES + VALUATION
// ─────────────────────────────────────────────────────────────────

/** Single comparable property card (image placeholder + details) */
function ComparableCard({ comp, borderRight, borderBottom }) {
  return (
    <div
      className="flex gap-3 p-4"
      style={{
        borderRight:  borderRight  ? "1.5px dashed #D1D5DB" : undefined,
        borderBottom: borderBottom ? "1.5px dashed #D1D5DB" : undefined,
      }}
    >
      {/* Street View placeholder */}
      <div
        className="w-28 h-20 shrink-0 rounded-sm overflow-hidden relative flex items-end justify-between p-1.5"
        style={{
          background:
            "linear-gradient(135deg, #C8C4C0 0%, #A8A4A0 40%, #B8B4B0 100%)",
        }}
      >
        {/* Faint window-like shapes */}
        <svg viewBox="0 0 112 80" className="absolute inset-0 w-full h-full opacity-20">
          <rect x="20" y="15" width="28" height="22" rx="1" fill="none" stroke="white" strokeWidth="2"/>
          <rect x="64" y="15" width="28" height="22" rx="1" fill="none" stroke="white" strokeWidth="2"/>
          <rect x="34" y="50" width="18" height="20" rx="1" fill="none" stroke="white" strokeWidth="1.5"/>
          <rect x="60" y="50" width="18" height="20" rx="1" fill="none" stroke="white" strokeWidth="1.5"/>
        </svg>
        <span
          className="text-white text-[8px] font-medium px-1 py-0.5 rounded relative z-10"
          style={{ background: "rgba(0,0,0,0.45)" }}
        >
          Google
        </span>
      </div>

      {/* Details */}
      <div className="text-xs leading-[1.7]">
        <p className="font-bold text-sm" style={{ color: B.purple }}>
          {comp.street}
        </p>
        <p className="text-gray-600">Distance: {comp.distance}</p>
        <p className="text-gray-600">Type: {comp.type}</p>
        <p className="text-gray-600">Size: {comp.size}</p>
        <p className="font-semibold mt-0.5 text-gray-800">
          Last sold price: {comp.price}
        </p>
        <p className="text-gray-600">Sold date: {comp.date}</p>
      </div>
    </div>
  );
}

/** Single valuation metric card */
function ValCard({ label, value, sub, valueColor }) {
  return (
    <div className="bg-white rounded-sm border border-gray-200 shadow-sm p-5 text-center flex flex-col items-center justify-center min-h-[90px]">
      <p className="text-xs text-gray-500 mb-2 leading-snug">{label}</p>
      <p
        className="text-2xl font-extrabold leading-snug"
        style={{ color: valueColor }}
      >
        {value}
      </p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}

function ComparablesPage({ report }) {
  const { comparables, valuation } = report;

  return (
    <Page>
      <div className="flex-1 p-8">
        {/* ── Recent activity ── */}
        <SectionHeader title="Recent activity near you" />

        <div className="bg-white rounded-sm border border-gray-200 shadow-sm overflow-hidden mb-7">
          <div className="grid grid-cols-2">
            {comparables.map((comp, i) => (
              <ComparableCard
                key={comp.street + i}
                comp={comp}
                borderRight={i % 2 === 0}
                borderBottom={i < comparables.length - 2}
              />
            ))}
          </div>
        </div>

        {/* ── Valuation ── */}
        <SectionHeader title="Your valuation powered by Hometrack" />

        <div className="space-y-3">
          {/* Row 1 — 3 columns */}
          <div className="grid grid-cols-3 gap-3">
            <ValCard
              label="Estimated capital value"
              value={valuation.capitalValue}
              valueColor={B.orange}
            />
            <ValCard
              label="Estimated value range"
              value={`${valuation.rangeLow} to ${valuation.rangeHigh}`}
              valueColor={B.purple}
            />
            <ValCard
              label={"Confidence\nin valuation estimate"}
              value={valuation.confidence}
              valueColor={B.headerBg}
            />
          </div>

          {/* Row 2 — 2 columns */}
          <div className="grid grid-cols-2 gap-3">
            <ValCard
              label="Last sale"
              value={valuation.lastSalePrice}
              sub={valuation.lastSaleDate}
              valueColor={B.purple}
            />
            <ValCard
              label={"Price change\nsince last sale"}
              value={valuation.priceChange}
              valueColor={B.purple}
            />
          </div>

          {/* Row 3 — 2 columns */}
          <div className="grid grid-cols-2 gap-3">
            <ValCard
              label={"Estimated\nrental value"}
              value={valuation.rentalValue}
              valueColor={B.orange}
            />
            <ValCard
              label={"Estimated gross\nrental yield"}
              value={valuation.grossYield}
              valueColor={B.headerBg}
            />
          </div>
        </div>
      </div>
      <PageFooter />
    </Page>
  );
}

// ─────────────────────────────────────────────────────────────────
// PAGE 4 — BACK PAGE
// ─────────────────────────────────────────────────────────────────

/** 2×3 mosaic of stylised property window photos */
function ImageMosaic() {
  // Approximate the 6-panel window photo mosaic from the PDF
  const panels = [
    { bg: "#C8B96A", wall: "#D4C880" },  // yellow ochre wall
    { bg: "#E8E2D8", wall: "#F0EAE0" },  // white render
    { bg: "#C05A38", wall: "#CC6040" },  // terracotta
    { bg: "#DCDCD8", wall: "#E8E8E4" },  // light grey
    { bg: "#E4DDD0", wall: "#EDE6D8" },  // cream
    { bg: "#A89888", wall: "#B4A898" },  // stone
  ];

  return (
    <div className="grid grid-cols-3 grid-rows-2" style={{ height: 240 }}>
      {panels.map((p, i) => (
        <div
          key={i}
          className="relative overflow-hidden flex items-center justify-center"
          style={{ backgroundColor: p.bg }}
        >
          {/* Brick texture lines */}
          <svg viewBox="0 0 140 120" className="absolute inset-0 w-full h-full opacity-10">
            {[20,40,60,80,100].map(y => (
              <line key={y} x1="0" y1={y} x2="140" y2={y} stroke="#000" strokeWidth="0.5"/>
            ))}
            {[0,2,4].map(row => (
              [15,45,75,105,135].map(x => (
                <line key={`${row}-${x}`} x1={x} y1={row*20} x2={x} y2={row*20+20}
                      stroke="#000" strokeWidth="0.5"/>
              ))
            ))}
          </svg>

          {/* Window frame */}
          <svg viewBox="0 0 80 70" className="w-20 relative z-10">
            {/* Outer frame */}
            <rect x="5" y="5" width="70" height="60" rx="1"
                  fill={p.wall} stroke="#888" strokeWidth="2"/>
            {/* Panes */}
            <rect x="8"  y="8"  width="31" height="27" rx="0" fill="#B8D4E8" fillOpacity="0.7" stroke="#666" strokeWidth="1"/>
            <rect x="41" y="8"  width="31" height="27" rx="0" fill="#B8D4E8" fillOpacity="0.7" stroke="#666" strokeWidth="1"/>
            <rect x="8"  y="37" width="31" height="25" rx="0" fill="#B8D4E8" fillOpacity="0.5" stroke="#666" strokeWidth="1"/>
            <rect x="41" y="37" width="31" height="25" rx="0" fill="#B8D4E8" fillOpacity="0.5" stroke="#666" strokeWidth="1"/>
            {/* Glazing bars */}
            <line x1="23" y1="8"  x2="23" y2="35" stroke="#777" strokeWidth="0.8"/>
            <line x1="56" y1="8"  x2="56" y2="35" stroke="#777" strokeWidth="0.8"/>
            <line x1="23" y1="37" x2="23" y2="62" stroke="#777" strokeWidth="0.8"/>
            <line x1="56" y1="37" x2="56" y2="62" stroke="#777" strokeWidth="0.8"/>
            <line x1="8"  y1="21" x2="39" y2="21" stroke="#777" strokeWidth="0.8"/>
            <line x1="41" y1="21" x2="72" y2="21" stroke="#777" strokeWidth="0.8"/>
          </svg>
        </div>
      ))}
    </div>
  );
}

function BackPage({ report }) {
  const { agent } = report;
  return (
    <Page noPad>
      <div className="flex-1 flex flex-col" style={{ backgroundColor: B.pageBg }}>
        <div className="p-8">
          {/* JBrown logo */}
          <div
            className="inline-flex flex-col items-center justify-center px-5 py-2.5 mb-7"
            style={{ backgroundColor: "#1A1A2E", minWidth: 120 }}
          >
            <span className="text-white font-bold text-lg leading-none">JBrown</span>
            <span className="text-[9px] tracking-widest mt-0.5" style={{ color: "#D4A4A4" }}>
              International
            </span>
          </div>

          {/* Two-column card */}
          <div className="bg-white rounded-sm border border-gray-200 shadow-sm p-6 mb-0">
            <div className="grid grid-cols-2 gap-6">
              <div>
                <p className="text-sm text-gray-700 leading-relaxed">
                  Hometrack are the UK's largest valuer of residential property for professionals,
                  trusted by 80% of major mortgage lenders. In 2017 they became part of Zoopla
                  Property Group.
                </p>
              </div>
              <div className="border-l border-gray-200 pl-6">
                <p className="text-sm font-semibold text-gray-800 mb-2">{agent.name}</p>
                <p className="text-sm text-gray-600 leading-relaxed">
                  {agent.address}
                  <br /><br />
                  {agent.phone}
                  <br />
                  {agent.email}
                  <br />
                  {agent.website}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Window image mosaic — full bleed */}
        <ImageMosaic />

        {/* Disclaimer */}
        <div className="p-8">
          <p className="text-sm font-semibold text-gray-800 leading-relaxed mb-3">
            This report was created by Hometrack, the UK's largest automated valuer of
            residential property. Hometrack's data is relied upon by 85% of UK mortgage
            lenders today.
          </p>
          <p className="text-[11px] text-gray-500 leading-relaxed mb-2">
            The estimated valuations in this report were generated using Hometrack's automated
            valuation model — a computer model which generates estimated valuations by
            combining statistical techniques with market data.
          </p>
          <p className="text-[11px] text-gray-500 leading-relaxed mb-2">
            This report is intended only for private, non-commercial use by the individual for
            whom it was generated. The estimated valuations are for general information only
            and are produced by computers without any inspection of the property or any legal
            documents relating to it. Hometrack cannot verify the data used to generate the
            valuation and does not guarantee that this report is accurate, complete or suitable
            for your intended use.
          </p>
          <p className="text-[11px] text-gray-500 leading-relaxed mb-3">
            You should not rely on this report. You should seek professional advice before
            making any financial or other decision in relation to the property.
          </p>
          <p className="text-[10px] text-gray-400">
            Copyright © 2026 Hometrack Data Systems Limited.
          </p>
        </div>
      </div>
      <PageFooter />
    </Page>
  );
}

// ─────────────────────────────────────────────────────────────────
// ROOT EXPORT
// ─────────────────────────────────────────────────────────────────

/**
 * PropertyValuationReport
 *
 * Usage:
 *   <PropertyValuationReport />                     // uses default demo data
 *   <PropertyValuationReport report={yourData} />   // pass live data
 *
 * PDF export:
 *   Call window.print() — each Page is styled with break-after-page.
 *   Add to globals.css:
 *     @media print { body { background: white; } }
 */
export default function PropertyValuationReport({ report = DEFAULT_REPORT }) {
  const ref = useRef(null);

  function handlePrint() {
    window.print();
  }

  return (
    <>
      {/* Print styles injected inline to avoid CSS file dependency */}
      <style>{`
        @media print {
          .no-print { display: none !important; }
          body { background: white !important; }
          .break-after-page { page-break-after: always; break-after: page; }
        }
        @page { size: A4; margin: 0; }
      `}</style>

      {/* Print button — hidden on print */}
      <div className="no-print flex justify-end px-4 py-3 bg-white border-b border-gray-200 sticky top-0 z-50">
        <button
          onClick={handlePrint}
          className="flex items-center gap-2 text-white text-sm font-medium px-5 py-2 rounded"
          style={{ backgroundColor: B.purple }}
        >
          {/* Printer icon */}
          <svg viewBox="0 0 20 20" className="w-4 h-4 fill-current">
            <path d="M5 4v3H4a2 2 0 00-2 2v5a2 2 0 002 2h1v2a1 1 0 001 1h8a1 1 0 001-1v-2h1a2 2 0 002-2V9a2 2 0 00-2-2h-1V4a1 1 0 00-1-1H6a1 1 0 00-1 1zm2 0h6v3H7V4zm-1 9H5v-1h1v1zm9 0h-1v-1h1v1zm-8 0v3h6v-3H7z"/>
          </svg>
          Export PDF
        </button>
      </div>

      {/* Report pages */}
      <div
        ref={ref}
        className="flex flex-col items-center py-8 px-4 min-h-screen"
        style={{ backgroundColor: "#D4D0CC" }}
      >
        <CoverPage      report={report} />
        <SummaryPage    report={report} />
        <ComparablesPage report={report} />
        <BackPage       report={report} />
      </div>
    </>
  );
}
