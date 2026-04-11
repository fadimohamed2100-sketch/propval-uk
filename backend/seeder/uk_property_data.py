"""
uk_property_data.py
~~~~~~~~~~~~~~~~~~~
Realistic UK property mock data for seeding the PropVal database.

Covers 6 cities across England with accurate postcodes, price bands,
property types, floor areas, and market conditions — all calibrated
against real 2024 Land Registry and EPC data.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

# ─────────────────────────────────────────────────────────────────────
# CITY / AREA PROFILES
# ─────────────────────────────────────────────────────────────────────

@dataclass
class AreaProfile:
    city:             str
    area:             str
    postcode_prefix:  str
    avg_price_flat:   int        # £ median 2-bed flat
    avg_price_semi:   int        # £ median 3-bed semi
    avg_price_det:    int        # £ median 4-bed detached
    price_per_m2:     int        # £/m² local average
    gross_yield:      float      # average gross rental yield
    weeks_on_market:  int
    asking_price_pct: int        # % of asking price achieved
    annual_searches:  int        # monthly Zoopla searches
    hpi_5yr_pct:      float      # 5-year HPI % change

AREA_PROFILES: list[AreaProfile] = [
    AreaProfile(
        city="London", area="Greenwich",
        postcode_prefix="SE18",
        avg_price_flat=335_000,  avg_price_semi=580_000, avg_price_det=920_000,
        price_per_m2=5_800,      gross_yield=0.056,
        weeks_on_market=17,      asking_price_pct=96,
        annual_searches=565_196, hpi_5yr_pct=-8.2,
    ),
    AreaProfile(
        city="London", area="Walthamstow",
        postcode_prefix="E17",
        avg_price_flat=390_000,  avg_price_semi=620_000, avg_price_det=950_000,
        price_per_m2=6_100,      gross_yield=0.048,
        weeks_on_market=14,      asking_price_pct=97,
        annual_searches=412_880, hpi_5yr_pct=-5.4,
    ),
    AreaProfile(
        city="Manchester", area="Didsbury",
        postcode_prefix="M20",
        avg_price_flat=215_000,  avg_price_semi=380_000, avg_price_det=650_000,
        price_per_m2=3_400,      gross_yield=0.057,
        weeks_on_market=12,      asking_price_pct=98,
        annual_searches=298_540, hpi_5yr_pct=14.6,
    ),
    AreaProfile(
        city="Birmingham", area="Harborne",
        postcode_prefix="B17",
        avg_price_flat=175_000,  avg_price_semi=290_000, avg_price_det=490_000,
        price_per_m2=2_800,      gross_yield=0.061,
        weeks_on_market=15,      asking_price_pct=95,
        annual_searches=184_320, hpi_5yr_pct=11.3,
    ),
    AreaProfile(
        city="Leeds", area="Headingley",
        postcode_prefix="LS6",
        avg_price_flat=155_000,  avg_price_semi=265_000, avg_price_det=420_000,
        price_per_m2=2_600,      gross_yield=0.068,
        weeks_on_market=11,      asking_price_pct=97,
        annual_searches=156_780, hpi_5yr_pct=18.2,
    ),
    AreaProfile(
        city="Bristol", area="Clifton",
        postcode_prefix="BS8",
        avg_price_flat=290_000,  avg_price_semi=480_000, avg_price_det=780_000,
        price_per_m2=4_600,      gross_yield=0.044,
        weeks_on_market=13,      asking_price_pct=98,
        annual_searches=223_450, hpi_5yr_pct=12.8,
    ),
]

# ─────────────────────────────────────────────────────────────────────
# RAW PROPERTY RECORDS
# ─────────────────────────────────────────────────────────────────────
# Format: dict with all fields needed to populate Address + Property tables.
# Prices in pence throughout to match the DB schema.

PROPERTIES: list[dict[str, Any]] = [

    # ── SE18 5 — Greenwich / Woolwich ─────────────────────────────
    {
        "address": {
            "line_1":      "Flat 307, Jigger Mast House, Mast Quay",
            "line_2":      "Woolwich Riverside",
            "city":        "London",
            "county":      "Greater London",
            "postcode":    "SE18 5NH",
            "lat":         51.4930, "lng": 0.0620,
        },
        "property": {
            "property_type": "flat",
            "bedrooms":      2, "bathrooms": 2,
            "floor_area_m2": 69.9,   # 752 sqft
            "year_built":    2010,
            "epc_rating":    "C",
            "tenure":        "leasehold",
            "lease_years_remaining": 112,
            "is_new_build":  False,
            "council_tax_band": "D",
            "features": {"balcony": True, "lift": True, "concierge": True, "parking": False},
            "external_ids": {"uprn": "100023456789", "title_number": "SY701234"},
        },
        "last_sale": {"price_pence": 22_850_000, "date": date(2010, 2, 15), "type": "new_build"},
        "area_profile": "SE18",
    },
    {
        "address": {
            "line_1": "42 Mast Quay", "line_2": None,
            "city": "London", "county": "Greater London",
            "postcode": "SE18 5NJ",
            "lat": 51.4935, "lng": 0.0625,
        },
        "property": {
            "property_type": "flat",
            "bedrooms": 2, "bathrooms": 1,
            "floor_area_m2": 77.9,   # 839 sqft
            "year_built": 2009,
            "epc_rating": "C", "tenure": "leasehold",
            "lease_years_remaining": 108,
            "is_new_build": False, "council_tax_band": "C",
            "features": {"river_view": True, "balcony": True},
            "external_ids": {"uprn": "100023456790"},
        },
        "last_sale": {"price_pence": 32_500_000, "date": date(2024, 1, 10), "type": "standard"},
        "area_profile": "SE18",
    },
    {
        "address": {
            "line_1": "14 Europe Road", "line_2": None,
            "city": "London", "county": "Greater London",
            "postcode": "SE18 7JY",
            "lat": 51.4958, "lng": 0.0741,
        },
        "property": {
            "property_type": "flat",
            "bedrooms": 2, "bathrooms": 1,
            "floor_area_m2": 78.0,
            "year_built": 2005,
            "epc_rating": "D", "tenure": "leasehold",
            "lease_years_remaining": 80,
            "is_new_build": False, "council_tax_band": "C",
            "features": {"parking": True},
            "external_ids": {"uprn": "100023456791"},
        },
        "last_sale": {"price_pence": 16_500_000, "date": date(2021, 11, 22), "type": "standard"},
        "area_profile": "SE18",
    },
    {
        "address": {
            "line_1": "8 Leda Road", "line_2": None,
            "city": "London", "county": "Greater London",
            "postcode": "SE18 6SW",
            "lat": 51.4920, "lng": 0.0755,
        },
        "property": {
            "property_type": "flat",
            "bedrooms": 1, "bathrooms": 1,
            "floor_area_m2": 54.0,
            "year_built": 1998,
            "epc_rating": "D", "tenure": "leasehold",
            "lease_years_remaining": 72,
            "is_new_build": False, "council_tax_band": "B",
            "features": {},
            "external_ids": {"uprn": "100023456792"},
        },
        "last_sale": {"price_pence": 15_700_000, "date": date(2023, 8, 7), "type": "standard"},
        "area_profile": "SE18",
    },
    {
        "address": {
            "line_1": "29 Kingsman Street", "line_2": None,
            "city": "London", "county": "Greater London",
            "postcode": "SE18 5QH",
            "lat": 51.4945, "lng": 0.0680,
        },
        "property": {
            "property_type": "flat",
            "bedrooms": 2, "bathrooms": 2,
            "floor_area_m2": 69.9,
            "year_built": 2011,
            "epc_rating": "B", "tenure": "leasehold",
            "lease_years_remaining": 115,
            "is_new_build": False, "council_tax_band": "D",
            "features": {"balcony": True, "gym": True, "concierge": True},
            "external_ids": {"uprn": "100023456793"},
        },
        "last_sale": {"price_pence": 32_000_000, "date": date(2025, 3, 14), "type": "standard"},
        "area_profile": "SE18",
    },

    # ── E17 — Walthamstow ────────────────────────────────────────
    {
        "address": {
            "line_1": "15 Forest Road", "line_2": "Walthamstow",
            "city": "London", "county": "Greater London",
            "postcode": "E17 6JF",
            "lat": 51.5844, "lng": -0.0195,
        },
        "property": {
            "property_type": "terraced",
            "bedrooms": 3, "bathrooms": 2,
            "floor_area_m2": 104.0,
            "year_built": 1906,
            "epc_rating": "D", "tenure": "freehold",
            "lease_years_remaining": None,
            "is_new_build": False, "council_tax_band": "D",
            "features": {"garden": True, "off_street_parking": False, "loft": True},
            "external_ids": {"uprn": "200034567890"},
        },
        "last_sale": {"price_pence": 59_500_000, "date": date(2022, 6, 3), "type": "standard"},
        "area_profile": "E17",
    },
    {
        "address": {
            "line_1": "Flat 4, 88 Hoe Street", "line_2": None,
            "city": "London", "county": "Greater London",
            "postcode": "E17 4QT",
            "lat": 51.5812, "lng": -0.0202,
        },
        "property": {
            "property_type": "flat",
            "bedrooms": 2, "bathrooms": 1,
            "floor_area_m2": 68.0,
            "year_built": 1970,
            "epc_rating": "D", "tenure": "leasehold",
            "lease_years_remaining": 79,
            "is_new_build": False, "council_tax_band": "C",
            "features": {"garden": False},
            "external_ids": {"uprn": "200034567891"},
        },
        "last_sale": {"price_pence": 36_500_000, "date": date(2021, 9, 15), "type": "standard"},
        "area_profile": "E17",
    },
    {
        "address": {
            "line_1": "72 Orford Road", "line_2": "Walthamstow Village",
            "city": "London", "county": "Greater London",
            "postcode": "E17 9NJ",
            "lat": 51.5835, "lng": -0.0175,
        },
        "property": {
            "property_type": "semi_detached",
            "bedrooms": 4, "bathrooms": 2,
            "floor_area_m2": 138.0,
            "year_built": 1920,
            "epc_rating": "D", "tenure": "freehold",
            "lease_years_remaining": None,
            "is_new_build": False, "council_tax_band": "E",
            "features": {"garden": True, "off_street_parking": True, "cellar": True},
            "external_ids": {"uprn": "200034567892"},
        },
        "last_sale": {"price_pence": 72_000_000, "date": date(2023, 3, 28), "type": "standard"},
        "area_profile": "E17",
    },

    # ── M20 — Manchester / Didsbury ───────────────────────────────
    {
        "address": {
            "line_1": "34 Palatine Road", "line_2": "Didsbury",
            "city": "Manchester", "county": "Greater Manchester",
            "postcode": "M20 3JH",
            "lat": 53.4142, "lng": -2.2281,
        },
        "property": {
            "property_type": "semi_detached",
            "bedrooms": 3, "bathrooms": 2,
            "floor_area_m2": 112.0,
            "year_built": 1935,
            "epc_rating": "D", "tenure": "freehold",
            "lease_years_remaining": None,
            "is_new_build": False, "council_tax_band": "D",
            "features": {"garden": True, "driveway": True, "garage": True},
            "external_ids": {"uprn": "300045678901"},
        },
        "last_sale": {"price_pence": 39_500_000, "date": date(2021, 5, 18), "type": "standard"},
        "area_profile": "M20",
    },
    {
        "address": {
            "line_1": "Flat 2, 19 School Lane", "line_2": "Didsbury Village",
            "city": "Manchester", "county": "Greater Manchester",
            "postcode": "M20 6RD",
            "lat": 53.4198, "lng": -2.2318,
        },
        "property": {
            "property_type": "flat",
            "bedrooms": 2, "bathrooms": 1,
            "floor_area_m2": 65.0,
            "year_built": 2003,
            "epc_rating": "C", "tenure": "leasehold",
            "lease_years_remaining": 105,
            "is_new_build": False, "council_tax_band": "C",
            "features": {"parking": True, "balcony": False},
            "external_ids": {"uprn": "300045678902"},
        },
        "last_sale": {"price_pence": 21_500_000, "date": date(2022, 11, 4), "type": "standard"},
        "area_profile": "M20",
    },
    {
        "address": {
            "line_1": "8 Barlow Moor Road", "line_2": None,
            "city": "Manchester", "county": "Greater Manchester",
            "postcode": "M20 2PQ",
            "lat": 53.4155, "lng": -2.2240,
        },
        "property": {
            "property_type": "detached",
            "bedrooms": 5, "bathrooms": 3,
            "floor_area_m2": 210.0,
            "year_built": 1895,
            "epc_rating": "E", "tenure": "freehold",
            "lease_years_remaining": None,
            "is_new_build": False, "council_tax_band": "G",
            "features": {"garden": True, "double_garage": True, "driveway": True, "cellar": True},
            "external_ids": {"uprn": "300045678903"},
        },
        "last_sale": {"price_pence": 72_000_000, "date": date(2020, 7, 22), "type": "standard"},
        "area_profile": "M20",
    },

    # ── B17 — Birmingham / Harborne ───────────────────────────────
    {
        "address": {
            "line_1": "56 High Street", "line_2": "Harborne",
            "city": "Birmingham", "county": "West Midlands",
            "postcode": "B17 9NE",
            "lat": 52.4638, "lng": -1.9502,
        },
        "property": {
            "property_type": "terraced",
            "bedrooms": 3, "bathrooms": 1,
            "floor_area_m2": 96.0,
            "year_built": 1930,
            "epc_rating": "D", "tenure": "freehold",
            "lease_years_remaining": None,
            "is_new_build": False, "council_tax_band": "C",
            "features": {"garden": True, "off_street_parking": False},
            "external_ids": {"uprn": "400056789012"},
        },
        "last_sale": {"price_pence": 27_000_000, "date": date(2022, 8, 9), "type": "standard"},
        "area_profile": "B17",
    },
    {
        "address": {
            "line_1": "Apartment 12, Harborne Gate", "line_2": "Harborne Road",
            "city": "Birmingham", "county": "West Midlands",
            "postcode": "B17 0HH",
            "lat": 52.4655, "lng": -1.9478,
        },
        "property": {
            "property_type": "flat",
            "bedrooms": 2, "bathrooms": 2,
            "floor_area_m2": 72.0,
            "year_built": 2018,
            "epc_rating": "B", "tenure": "leasehold",
            "lease_years_remaining": 240,
            "is_new_build": False, "council_tax_band": "C",
            "features": {"lift": True, "parking": True, "balcony": True},
            "external_ids": {"uprn": "400056789013"},
        },
        "last_sale": {"price_pence": 19_500_000, "date": date(2023, 2, 16), "type": "standard"},
        "area_profile": "B17",
    },
    {
        "address": {
            "line_1": "3 Serpentine Road", "line_2": None,
            "city": "Birmingham", "county": "West Midlands",
            "postcode": "B17 9RE",
            "lat": 52.4671, "lng": -1.9488,
        },
        "property": {
            "property_type": "detached",
            "bedrooms": 4, "bathrooms": 2,
            "floor_area_m2": 160.0,
            "year_built": 1958,
            "epc_rating": "D", "tenure": "freehold",
            "lease_years_remaining": None,
            "is_new_build": False, "council_tax_band": "F",
            "features": {"garden": True, "garage": True, "driveway": True},
            "external_ids": {"uprn": "400056789014"},
        },
        "last_sale": {"price_pence": 48_000_000, "date": date(2021, 4, 30), "type": "standard"},
        "area_profile": "B17",
    },

    # ── LS6 — Leeds / Headingley ──────────────────────────────────
    {
        "address": {
            "line_1": "22 Cardigan Road", "line_2": "Headingley",
            "city": "Leeds", "county": "West Yorkshire",
            "postcode": "LS6 3AG",
            "lat": 53.8215, "lng": -1.5742,
        },
        "property": {
            "property_type": "terraced",
            "bedrooms": 4, "bathrooms": 2,
            "floor_area_m2": 118.0,
            "year_built": 1900,
            "epc_rating": "E", "tenure": "freehold",
            "lease_years_remaining": None,
            "is_new_build": False, "council_tax_band": "C",
            "features": {"garden": True, "cellar": True},
            "external_ids": {"uprn": "500067890123"},
        },
        "last_sale": {"price_pence": 27_500_000, "date": date(2023, 5, 12), "type": "standard"},
        "area_profile": "LS6",
    },
    {
        "address": {
            "line_1": "Flat 6, 45 Otley Road", "line_2": "Headingley",
            "city": "Leeds", "county": "West Yorkshire",
            "postcode": "LS6 2AL",
            "lat": 53.8244, "lng": -1.5768,
        },
        "property": {
            "property_type": "flat",
            "bedrooms": 2, "bathrooms": 1,
            "floor_area_m2": 58.0,
            "year_built": 1988,
            "epc_rating": "D", "tenure": "leasehold",
            "lease_years_remaining": 88,
            "is_new_build": False, "council_tax_band": "B",
            "features": {"garden": False, "parking": False},
            "external_ids": {"uprn": "500067890124"},
        },
        "last_sale": {"price_pence": 14_200_000, "date": date(2022, 3, 22), "type": "standard"},
        "area_profile": "LS6",
    },

    # ── BS8 — Bristol / Clifton ───────────────────────────────────
    {
        "address": {
            "line_1": "7 Caledonia Place", "line_2": "Clifton",
            "city": "Bristol", "county": "Bristol",
            "postcode": "BS8 4DN",
            "lat": 51.4575, "lng": -2.6120,
        },
        "property": {
            "property_type": "flat",
            "bedrooms": 2, "bathrooms": 1,
            "floor_area_m2": 78.0,
            "year_built": 1840,
            "epc_rating": "E", "tenure": "leasehold",
            "lease_years_remaining": 94,
            "is_new_build": False, "council_tax_band": "D",
            "features": {"garden": False, "cellar": False},
            "external_ids": {"uprn": "600078901234"},
        },
        "last_sale": {"price_pence": 30_000_000, "date": date(2022, 10, 5), "type": "standard"},
        "area_profile": "BS8",
    },
    {
        "address": {
            "line_1": "19 Pembroke Road", "line_2": "Clifton",
            "city": "Bristol", "county": "Bristol",
            "postcode": "BS8 3BB",
            "lat": 51.4580, "lng": -2.6142,
        },
        "property": {
            "property_type": "semi_detached",
            "bedrooms": 4, "bathrooms": 2,
            "floor_area_m2": 168.0,
            "year_built": 1880,
            "epc_rating": "F", "tenure": "freehold",
            "lease_years_remaining": None,
            "is_new_build": False, "council_tax_band": "G",
            "features": {"garden": True, "parking": True, "cellar": True},
            "external_ids": {"uprn": "600078901235"},
        },
        "last_sale": {"price_pence": 76_000_000, "date": date(2021, 8, 30), "type": "standard"},
        "area_profile": "BS8",
    },
]


# ─────────────────────────────────────────────────────────────────────
# COMPARABLE SALES
# Each record: address near one of the PROPERTIES above, with sale data.
# ─────────────────────────────────────────────────────────────────────

COMPARABLE_SALES: list[dict[str, Any]] = [

    # ── SE18 comparables ──────────────────────────────────────────
    {"address": "Flat 204, Warrior House, Mast Quay",    "postcode": "SE18 5NL",
     "type": "flat",    "bedrooms": 2, "floor_area_m2": 72.0,
     "price_pence": 33_000_000, "date": date(2025, 1, 8),   "distance_m": 60,  "source": "land_registry"},
    {"address": "Flat 11, Argyll Court, Mast Quay",      "postcode": "SE18 5NF",
     "type": "flat",    "bedrooms": 2, "floor_area_m2": 68.5,
     "price_pence": 31_500_000, "date": date(2024, 10, 14), "distance_m": 110, "source": "land_registry"},
    {"address": "19 Powis Street",                        "postcode": "SE18 6LH",
     "type": "flat",    "bedrooms": 1, "floor_area_m2": 55.9,
     "price_pence": 26_500_000, "date": date(2024, 4, 22),  "distance_m": 370, "source": "land_registry"},
    {"address": "28 Kingsman Street",                     "postcode": "SE18 5QH",
     "type": "flat",    "bedrooms": 2, "floor_area_m2": 70.0,
     "price_pence": 32_000_000, "date": date(2025, 3, 5),   "distance_m": 240, "source": "land_registry"},
    {"address": "Flat 3, 6 St Mary Street",               "postcode": "SE18 6RD",
     "type": "flat",    "bedrooms": 2, "floor_area_m2": 61.9,
     "price_pence": 25_500_000, "date": date(2022, 5, 17),  "distance_m": 290, "source": "land_registry"},
    {"address": "Flat 22, Harbour Exchange",               "postcode": "SE18 5TQ",
     "type": "flat",    "bedrooms": 1, "floor_area_m2": 50.0,
     "price_pence": 22_000_000, "date": date(2023, 9, 11),  "distance_m": 450, "source": "land_registry"},
    {"address": "Flat 5, Colmore House, Arsenal Way",     "postcode": "SE18 6TH",
     "type": "flat",    "bedrooms": 2, "floor_area_m2": 73.5,
     "price_pence": 29_500_000, "date": date(2024, 7, 3),   "distance_m": 520, "source": "land_registry"},
    {"address": "14 Samuel Street",                        "postcode": "SE18 5NP",
     "type": "flat",    "bedrooms": 2, "floor_area_m2": 80.5,
     "price_pence": 34_000_000, "date": date(2025, 2, 19),  "distance_m": 180, "source": "land_registry"},
    {"address": "Flat 9, Gallions View",                  "postcode": "SE18 5QJ",
     "type": "flat",    "bedrooms": 3, "floor_area_m2": 95.0,
     "price_pence": 41_000_000, "date": date(2024, 11, 28), "distance_m": 620, "source": "land_registry"},

    # ── E17 comparables ───────────────────────────────────────────
    {"address": "87 Forest Road",                         "postcode": "E17 6JH",
     "type": "terraced", "bedrooms": 3, "floor_area_m2": 100.0,
     "price_pence": 58_000_000, "date": date(2024, 8, 5),   "distance_m": 55,  "source": "land_registry"},
    {"address": "103 Orford Road",                        "postcode": "E17 9NL",
     "type": "terraced", "bedrooms": 3, "floor_area_m2": 106.0,
     "price_pence": 62_500_000, "date": date(2024, 3, 12),  "distance_m": 420, "source": "land_registry"},
    {"address": "31 Coppermill Lane",                     "postcode": "E17 7HB",
     "type": "terraced", "bedrooms": 2, "floor_area_m2": 78.0,
     "price_pence": 47_500_000, "date": date(2023, 11, 21), "distance_m": 680, "source": "land_registry"},
    {"address": "Flat 2, 45 Hoe Street",                  "postcode": "E17 4QT",
     "type": "flat",    "bedrooms": 2, "floor_area_m2": 65.0,
     "price_pence": 36_000_000, "date": date(2024, 6, 18),  "distance_m": 90,  "source": "land_registry"},
    {"address": "15 Buxton Road",                         "postcode": "E17 7EJ",
     "type": "semi_detached", "bedrooms": 4, "floor_area_m2": 135.0,
     "price_pence": 69_500_000, "date": date(2023, 7, 4),   "distance_m": 810, "source": "land_registry"},
    {"address": "52 Jewel Road",                          "postcode": "E17 4QN",
     "type": "terraced", "bedrooms": 3, "floor_area_m2": 92.0,
     "price_pence": 55_000_000, "date": date(2025, 1, 29),  "distance_m": 340, "source": "land_registry"},

    # ── M20 comparables ───────────────────────────────────────────
    {"address": "58 Palatine Road",                       "postcode": "M20 3JH",
     "type": "semi_detached", "bedrooms": 3, "floor_area_m2": 108.0,
     "price_pence": 41_000_000, "date": date(2024, 9, 23),  "distance_m": 80,  "source": "land_registry"},
    {"address": "12 Wilmslow Road",                       "postcode": "M20 3BX",
     "type": "semi_detached", "bedrooms": 4, "floor_area_m2": 142.0,
     "price_pence": 52_000_000, "date": date(2024, 5, 7),   "distance_m": 320, "source": "land_registry"},
    {"address": "Flat 8, Didsbury Park",                  "postcode": "M20 5LH",
     "type": "flat",    "bedrooms": 2, "floor_area_m2": 62.0,
     "price_pence": 22_500_000, "date": date(2023, 12, 14), "distance_m": 490, "source": "land_registry"},
    {"address": "24 Barlow Moor Road",                    "postcode": "M20 2PQ",
     "type": "detached", "bedrooms": 5, "floor_area_m2": 225.0,
     "price_pence": 74_500_000, "date": date(2024, 4, 2),   "distance_m": 130, "source": "land_registry"},
    {"address": "7 Lapwing Lane",                         "postcode": "M20 2NT",
     "type": "terraced", "bedrooms": 3, "floor_area_m2": 95.0,
     "price_pence": 36_500_000, "date": date(2023, 6, 28),  "distance_m": 560, "source": "land_registry"},

    # ── B17 comparables ───────────────────────────────────────────
    {"address": "64 High Street, Harborne",               "postcode": "B17 9NE",
     "type": "terraced", "bedrooms": 3, "floor_area_m2": 92.0,
     "price_pence": 28_000_000, "date": date(2024, 11, 4),  "distance_m": 70,  "source": "land_registry"},
    {"address": "18 Vivian Road",                         "postcode": "B17 0DX",
     "type": "semi_detached", "bedrooms": 3, "floor_area_m2": 102.0,
     "price_pence": 31_500_000, "date": date(2024, 7, 16),  "distance_m": 280, "source": "land_registry"},
    {"address": "Apartment 7, Harborne Gate",             "postcode": "B17 0HH",
     "type": "flat",    "bedrooms": 2, "floor_area_m2": 68.0,
     "price_pence": 20_000_000, "date": date(2025, 1, 17),  "distance_m": 45,  "source": "land_registry"},
    {"address": "9 Metchley Lane",                        "postcode": "B17 0JF",
     "type": "detached", "bedrooms": 4, "floor_area_m2": 172.0,
     "price_pence": 51_000_000, "date": date(2023, 10, 31), "distance_m": 420, "source": "land_registry"},

    # ── LS6 comparables ───────────────────────────────────────────
    {"address": "36 Cardigan Road",                       "postcode": "LS6 3AG",
     "type": "terraced", "bedrooms": 4, "floor_area_m2": 112.0,
     "price_pence": 26_000_000, "date": date(2024, 2, 14),  "distance_m": 50,  "source": "land_registry"},
    {"address": "48 Bennett Road",                        "postcode": "LS6 3HN",
     "type": "terraced", "bedrooms": 3, "floor_area_m2": 98.0,
     "price_pence": 23_500_000, "date": date(2024, 10, 8),  "distance_m": 310, "source": "land_registry"},
    {"address": "Flat 3, 62 Otley Road",                  "postcode": "LS6 2AW",
     "type": "flat",    "bedrooms": 2, "floor_area_m2": 55.0,
     "price_pence": 13_800_000, "date": date(2023, 8, 25),  "distance_m": 195, "source": "land_registry"},
    {"address": "19 Headingley Lane",                     "postcode": "LS6 1BL",
     "type": "semi_detached", "bedrooms": 3, "floor_area_m2": 105.0,
     "price_pence": 28_500_000, "date": date(2024, 5, 22),  "distance_m": 550, "source": "land_registry"},

    # ── BS8 comparables ───────────────────────────────────────────
    {"address": "3 Caledonia Place",                      "postcode": "BS8 4DN",
     "type": "flat",    "bedrooms": 2, "floor_area_m2": 72.0,
     "price_pence": 29_500_000, "date": date(2024, 9, 10),  "distance_m": 65,  "source": "land_registry"},
    {"address": "28 Pembroke Road",                       "postcode": "BS8 3BB",
     "type": "semi_detached", "bedrooms": 4, "floor_area_m2": 162.0,
     "price_pence": 74_000_000, "date": date(2024, 6, 27),  "distance_m": 120, "source": "land_registry"},
    {"address": "Flat 9, Goldney Hall",                   "postcode": "BS8 4BH",
     "type": "flat",    "bedrooms": 1, "floor_area_m2": 48.0,
     "price_pence": 22_500_000, "date": date(2023, 4, 18),  "distance_m": 380, "source": "land_registry"},
    {"address": "11 Clifton Park Road",                   "postcode": "BS8 3HN",
     "type": "detached", "bedrooms": 5, "floor_area_m2": 240.0,
     "price_pence": 118_000_000, "date": date(2024, 1, 31), "distance_m": 640, "source": "land_registry"},
]


# ─────────────────────────────────────────────────────────────────────
# RENTAL LISTINGS
# ─────────────────────────────────────────────────────────────────────

RENTAL_LISTINGS: list[dict[str, Any]] = [
    # SE18
    {"property_idx": 0,  "rent_pence": 196_000, "status": "let",    "source": "rightmove",
     "furnished": "furnished",    "min_tenancy_months": 12, "bills_included": False,
     "listed_date": date(2024, 1, 5), "let_date": date(2024, 2, 1)},
    {"property_idx": 1,  "rent_pence": 205_000, "status": "let",    "source": "zoopla",
     "furnished": "unfurnished",  "min_tenancy_months": 12, "bills_included": False,
     "listed_date": date(2024, 3, 10), "let_date": date(2024, 4, 3)},
    {"property_idx": 2,  "rent_pence": 185_000, "status": "active", "source": "rightmove",
     "furnished": "part_furnished", "min_tenancy_months": 6, "bills_included": False,
     "listed_date": date(2025, 2, 14), "let_date": None},
    {"property_idx": 4,  "rent_pence": 210_000, "status": "let",    "source": "openrent",
     "furnished": "furnished",    "min_tenancy_months": 12, "bills_included": False,
     "listed_date": date(2025, 4, 1),  "let_date": date(2025, 5, 1)},

    # E17
    {"property_idx": 5,  "rent_pence": 250_000, "status": "let",    "source": "rightmove",
     "furnished": "unfurnished",  "min_tenancy_months": 12, "bills_included": False,
     "listed_date": date(2023, 9, 15), "let_date": date(2023, 10, 1)},
    {"property_idx": 6,  "rent_pence": 195_000, "status": "let",    "source": "zoopla",
     "furnished": "furnished",    "min_tenancy_months": 12, "bills_included": False,
     "listed_date": date(2024, 6, 2), "let_date": date(2024, 7, 1)},
    {"property_idx": 7,  "rent_pence": 310_000, "status": "active", "source": "rightmove",
     "furnished": "unfurnished",  "min_tenancy_months": 12, "bills_included": False,
     "listed_date": date(2025, 3, 5), "let_date": None},

    # M20
    {"property_idx": 8,  "rent_pence": 185_000, "status": "let",    "source": "zoopla",
     "furnished": "unfurnished",  "min_tenancy_months": 12, "bills_included": False,
     "listed_date": date(2024, 4, 20), "let_date": date(2024, 5, 15)},
    {"property_idx": 9,  "rent_pence": 130_000, "status": "active", "source": "rightmove",
     "furnished": "part_furnished", "min_tenancy_months": 6, "bills_included": False,
     "listed_date": date(2025, 1, 12), "let_date": None},

    # B17
    {"property_idx": 11, "rent_pence": 140_000, "status": "let",    "source": "zoopla",
     "furnished": "unfurnished",  "min_tenancy_months": 12, "bills_included": False,
     "listed_date": date(2024, 2, 18), "let_date": date(2024, 3, 1)},
    {"property_idx": 12, "rent_pence": 125_000, "status": "active", "source": "rightmove",
     "furnished": "furnished",    "min_tenancy_months": 6,  "bills_included": True,
     "listed_date": date(2025, 2, 28), "let_date": None},

    # LS6
    {"property_idx": 13, "rent_pence": 135_000, "status": "let",    "source": "zoopla",
     "furnished": "unfurnished",  "min_tenancy_months": 12, "bills_included": False,
     "listed_date": date(2024, 5, 20), "let_date": date(2024, 6, 16)},

    # BS8
    {"property_idx": 15, "rent_pence": 148_000, "status": "let",    "source": "rightmove",
     "furnished": "part_furnished", "min_tenancy_months": 12, "bills_included": False,
     "listed_date": date(2024, 9, 28), "let_date": date(2024, 10, 28)},
]


# ─────────────────────────────────────────────────────────────────────
# PRE-BAKED VALUATION RESULTS
# (so the app can serve results without external API calls)
# ─────────────────────────────────────────────────────────────────────

VALUATIONS: list[dict[str, Any]] = [
    {   # SE18 — Flat 307 Jigger Mast House
        "property_idx":    0,
        "estimated_value": 32_800_000,   # £328,000
        "range_low":       31_200_000,
        "range_high":      34_400_000,
        "confidence_score": 0.81,
        "rental_monthly":  19_600,       # £1,960 pcm
        "rental_yield":    7.17,
        "status":          "complete",
        "source_apis":     ["land_registry", "epc"],
        "methodology": {
            "method":             "weighted_comparable_median",
            "comps_considered":   9,
            "comps_used":         6,
            "methods_available":  ["comparable_sales", "price_per_m2", "last_sale_growth"],
            "blend_inputs": [
                {"method": "comparable_sales", "estimate_gbp": 326_000, "base_weight": 0.55, "confidence": 0.79, "effective_weight": 0.562},
                {"method": "price_per_m2",     "estimate_gbp": 333_000, "base_weight": 0.25, "confidence": 0.74, "effective_weight": 0.240},
                {"method": "last_sale_growth",  "estimate_gbp": 318_000, "base_weight": 0.20, "confidence": 0.62, "effective_weight": 0.161},
            ],
            "confidence_sample_size":    0.74,
            "confidence_recency":        0.82,
            "confidence_similarity":     0.78,
            "confidence_method_agreement": 0.88,
            "local_price_per_m2_gbp":   4_692,
            "range_spread_pct":          4.8,
            "supporting": {
                "last_sale_price_gbp":  228_500,
                "last_sale_date":       "2010-02-15",
                "years_elapsed":        15.0,
                "annual_hpi_rate":      0.043,
                "growth_factor":        1.893,
            },
        },
    },
    {   # E17 — 15 Forest Road, Walthamstow
        "property_idx":    5,
        "estimated_value": 61_500_000,
        "range_low":       58_200_000,
        "range_high":      64_800_000,
        "confidence_score": 0.77,
        "rental_monthly":  250_000,
        "rental_yield":    4.88,
        "status":          "complete",
        "source_apis":     ["land_registry", "epc"],
        "methodology": {
            "method":             "weighted_comparable_median",
            "comps_considered":   6,
            "comps_used":         5,
            "methods_available":  ["comparable_sales", "price_per_m2", "last_sale_growth"],
            "blend_inputs": [
                {"method": "comparable_sales", "estimate_gbp": 613_000, "base_weight": 0.55, "confidence": 0.76, "effective_weight": 0.558},
                {"method": "price_per_m2",     "estimate_gbp": 634_000, "base_weight": 0.25, "confidence": 0.69, "effective_weight": 0.229},
                {"method": "last_sale_growth",  "estimate_gbp": 581_000, "base_weight": 0.20, "confidence": 0.71, "effective_weight": 0.189},
            ],
            "confidence_sample_size":    0.70,
            "confidence_recency":        0.78,
            "confidence_similarity":     0.72,
            "confidence_method_agreement": 0.86,
            "local_price_per_m2_gbp":   6_081,
            "range_spread_pct":          5.2,
        },
    },
    {   # M20 — 34 Palatine Road, Didsbury
        "property_idx":    8,
        "estimated_value": 42_000_000,
        "range_low":       39_800_000,
        "range_high":      44_200_000,
        "confidence_score": 0.83,
        "rental_monthly":  185_000,
        "rental_yield":    5.28,
        "status":          "complete",
        "source_apis":     ["land_registry", "epc"],
        "methodology": {
            "method":             "weighted_comparable_median",
            "comps_considered":   5,
            "comps_used":         5,
            "methods_available":  ["comparable_sales", "price_per_m2", "last_sale_growth"],
            "blend_inputs": [
                {"method": "comparable_sales", "estimate_gbp": 418_000, "base_weight": 0.55, "confidence": 0.82, "effective_weight": 0.561},
                {"method": "price_per_m2",     "estimate_gbp": 425_000, "base_weight": 0.25, "confidence": 0.77, "effective_weight": 0.239},
                {"method": "last_sale_growth",  "estimate_gbp": 414_000, "base_weight": 0.20, "confidence": 0.74, "effective_weight": 0.184},
            ],
            "confidence_sample_size":    0.79,
            "confidence_recency":        0.84,
            "confidence_similarity":     0.80,
            "confidence_method_agreement": 0.91,
            "local_price_per_m2_gbp":   3_750,
            "range_spread_pct":          5.0,
        },
    },
]
