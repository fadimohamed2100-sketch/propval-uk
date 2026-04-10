"""
address_search_data.py
~~~~~~~~~~~~~~~~~~~~~~
Static address list for the mock address search endpoint.
Covers all seeded properties plus surrounding streets so autocomplete
feels realistic for any of the demo postcodes.

Each entry has the fields returned by the real Postcode API / EPC API:
  id, line_1, line_2, city, postcode, lat, lng, property_type, uprn

Replace this file with a real API call (Ideal Postcodes, GetAddress.io,
or OS Places) when you move to production.
"""
from __future__ import annotations
from typing import Any

MOCK_ADDRESSES: list[dict[str, Any]] = [

    # ── SE18 — Woolwich / Greenwich ──────────────────────────────
    {"id": "se18-001", "line_1": "Flat 307, Jigger Mast House, Mast Quay", "line_2": "Woolwich Riverside", "city": "London", "postcode": "SE18 5NH", "lat": 51.4930, "lng": 0.0620, "property_type": "flat",          "uprn": "100023456789"},
    {"id": "se18-002", "line_1": "Flat 204, Warrior House, Mast Quay",      "line_2": "Woolwich Riverside", "city": "London", "postcode": "SE18 5NL", "lat": 51.4932, "lng": 0.0622, "property_type": "flat",          "uprn": "100023456801"},
    {"id": "se18-003", "line_1": "42 Mast Quay",                            "line_2": None,                 "city": "London", "postcode": "SE18 5NJ", "lat": 51.4935, "lng": 0.0625, "property_type": "flat",          "uprn": "100023456790"},
    {"id": "se18-004", "line_1": "Flat 11, Argyll Court, Mast Quay",        "line_2": None,                 "city": "London", "postcode": "SE18 5NF", "lat": 51.4934, "lng": 0.0619, "property_type": "flat",          "uprn": "100023456802"},
    {"id": "se18-005", "line_1": "14 Samuel Street",                        "line_2": None,                 "city": "London", "postcode": "SE18 5NP", "lat": 51.4940, "lng": 0.0630, "property_type": "flat",          "uprn": "100023456803"},
    {"id": "se18-006", "line_1": "Flat 22, Harbour Exchange",               "line_2": None,                 "city": "London", "postcode": "SE18 5TQ", "lat": 51.4925, "lng": 0.0660, "property_type": "flat",          "uprn": "100023456804"},
    {"id": "se18-007", "line_1": "14 Europe Road",                          "line_2": None,                 "city": "London", "postcode": "SE18 7JY", "lat": 51.4958, "lng": 0.0741, "property_type": "flat",          "uprn": "100023456791"},
    {"id": "se18-008", "line_1": "8 Leda Road",                             "line_2": None,                 "city": "London", "postcode": "SE18 6SW", "lat": 51.4920, "lng": 0.0755, "property_type": "flat",          "uprn": "100023456792"},
    {"id": "se18-009", "line_1": "19 Powis Street",                         "line_2": None,                 "city": "London", "postcode": "SE18 6LH", "lat": 51.4915, "lng": 0.0748, "property_type": "flat",          "uprn": "100023456805"},
    {"id": "se18-010", "line_1": "29 Kingsman Street",                      "line_2": None,                 "city": "London", "postcode": "SE18 5QH", "lat": 51.4945, "lng": 0.0680, "property_type": "flat",          "uprn": "100023456793"},
    {"id": "se18-011", "line_1": "Flat 3, 6 St Mary Street",                "line_2": None,                 "city": "London", "postcode": "SE18 6RD", "lat": 51.4918, "lng": 0.0762, "property_type": "flat",          "uprn": "100023456806"},
    {"id": "se18-012", "line_1": "Flat 9, Gallions View",                   "line_2": None,                 "city": "London", "postcode": "SE18 5QJ", "lat": 51.4950, "lng": 0.0690, "property_type": "flat",          "uprn": "100023456807"},

    # ── E17 — Walthamstow ────────────────────────────────────────
    {"id": "e17-001", "line_1": "15 Forest Road",            "line_2": "Walthamstow",        "city": "London", "postcode": "E17 6JF", "lat": 51.5844, "lng": -0.0195, "property_type": "terraced",      "uprn": "200034567890"},
    {"id": "e17-002", "line_1": "87 Forest Road",            "line_2": None,                 "city": "London", "postcode": "E17 6JH", "lat": 51.5848, "lng": -0.0192, "property_type": "terraced",      "uprn": "200034567901"},
    {"id": "e17-003", "line_1": "Flat 4, 88 Hoe Street",    "line_2": None,                 "city": "London", "postcode": "E17 4QT", "lat": 51.5812, "lng": -0.0202, "property_type": "flat",          "uprn": "200034567891"},
    {"id": "e17-004", "line_1": "Flat 2, 45 Hoe Street",    "line_2": None,                 "city": "London", "postcode": "E17 4QT", "lat": 51.5810, "lng": -0.0205, "property_type": "flat",          "uprn": "200034567902"},
    {"id": "e17-005", "line_1": "72 Orford Road",            "line_2": "Walthamstow Village","city": "London", "postcode": "E17 9NJ", "lat": 51.5835, "lng": -0.0175, "property_type": "semi_detached", "uprn": "200034567892"},
    {"id": "e17-006", "line_1": "103 Orford Road",           "line_2": None,                 "city": "London", "postcode": "E17 9NL", "lat": 51.5840, "lng": -0.0170, "property_type": "terraced",      "uprn": "200034567903"},
    {"id": "e17-007", "line_1": "31 Coppermill Lane",        "line_2": None,                 "city": "London", "postcode": "E17 7HB", "lat": 51.5798, "lng": -0.0220, "property_type": "terraced",      "uprn": "200034567904"},
    {"id": "e17-008", "line_1": "52 Jewel Road",             "line_2": None,                 "city": "London", "postcode": "E17 4QN", "lat": 51.5808, "lng": -0.0208, "property_type": "terraced",      "uprn": "200034567905"},

    # ── M20 — Manchester / Didsbury ───────────────────────────────
    {"id": "m20-001", "line_1": "34 Palatine Road",           "line_2": "Didsbury",           "city": "Manchester", "postcode": "M20 3JH", "lat": 53.4142, "lng": -2.2281, "property_type": "semi_detached", "uprn": "300045678901"},
    {"id": "m20-002", "line_1": "58 Palatine Road",           "line_2": "Didsbury",           "city": "Manchester", "postcode": "M20 3JH", "lat": 53.4146, "lng": -2.2276, "property_type": "semi_detached", "uprn": "300045678910"},
    {"id": "m20-003", "line_1": "Flat 2, 19 School Lane",     "line_2": "Didsbury Village",   "city": "Manchester", "postcode": "M20 6RD", "lat": 53.4198, "lng": -2.2318, "property_type": "flat",          "uprn": "300045678902"},
    {"id": "m20-004", "line_1": "Flat 8, Didsbury Park",      "line_2": None,                 "city": "Manchester", "postcode": "M20 5LH", "lat": 53.4185, "lng": -2.2350, "property_type": "flat",          "uprn": "300045678911"},
    {"id": "m20-005", "line_1": "8 Barlow Moor Road",         "line_2": None,                 "city": "Manchester", "postcode": "M20 2PQ", "lat": 53.4155, "lng": -2.2240, "property_type": "detached",      "uprn": "300045678903"},
    {"id": "m20-006", "line_1": "24 Barlow Moor Road",        "line_2": None,                 "city": "Manchester", "postcode": "M20 2PQ", "lat": 53.4158, "lng": -2.2235, "property_type": "detached",      "uprn": "300045678912"},
    {"id": "m20-007", "line_1": "12 Wilmslow Road",           "line_2": "Didsbury",           "city": "Manchester", "postcode": "M20 3BX", "lat": 53.4170, "lng": -2.2300, "property_type": "semi_detached", "uprn": "300045678913"},
    {"id": "m20-008", "line_1": "7 Lapwing Lane",             "line_2": None,                 "city": "Manchester", "postcode": "M20 2NT", "lat": 53.4162, "lng": -2.2260, "property_type": "terraced",      "uprn": "300045678914"},

    # ── B17 — Birmingham / Harborne ───────────────────────────────
    {"id": "b17-001", "line_1": "56 High Street",             "line_2": "Harborne",           "city": "Birmingham", "postcode": "B17 9NE", "lat": 52.4638, "lng": -1.9502, "property_type": "terraced",      "uprn": "400056789012"},
    {"id": "b17-002", "line_1": "64 High Street",             "line_2": "Harborne",           "city": "Birmingham", "postcode": "B17 9NE", "lat": 52.4641, "lng": -1.9498, "property_type": "terraced",      "uprn": "400056789020"},
    {"id": "b17-003", "line_1": "Apartment 12, Harborne Gate","line_2": "Harborne Road",      "city": "Birmingham", "postcode": "B17 0HH", "lat": 52.4655, "lng": -1.9478, "property_type": "flat",          "uprn": "400056789013"},
    {"id": "b17-004", "line_1": "Apartment 7, Harborne Gate", "line_2": "Harborne Road",      "city": "Birmingham", "postcode": "B17 0HH", "lat": 52.4653, "lng": -1.9480, "property_type": "flat",          "uprn": "400056789021"},
    {"id": "b17-005", "line_1": "3 Serpentine Road",          "line_2": None,                 "city": "Birmingham", "postcode": "B17 9RE", "lat": 52.4671, "lng": -1.9488, "property_type": "detached",      "uprn": "400056789014"},
    {"id": "b17-006", "line_1": "18 Vivian Road",             "line_2": None,                 "city": "Birmingham", "postcode": "B17 0DX", "lat": 52.4660, "lng": -1.9471, "property_type": "semi_detached", "uprn": "400056789022"},
    {"id": "b17-007", "line_1": "9 Metchley Lane",            "line_2": None,                 "city": "Birmingham", "postcode": "B17 0JF", "lat": 52.4648, "lng": -1.9510, "property_type": "detached",      "uprn": "400056789023"},

    # ── LS6 — Leeds / Headingley ──────────────────────────────────
    {"id": "ls6-001", "line_1": "22 Cardigan Road",           "line_2": "Headingley",         "city": "Leeds", "postcode": "LS6 3AG", "lat": 53.8215, "lng": -1.5742, "property_type": "terraced",      "uprn": "500067890123"},
    {"id": "ls6-002", "line_1": "36 Cardigan Road",           "line_2": "Headingley",         "city": "Leeds", "postcode": "LS6 3AG", "lat": 53.8218, "lng": -1.5738, "property_type": "terraced",      "uprn": "500067890130"},
    {"id": "ls6-003", "line_1": "Flat 6, 45 Otley Road",      "line_2": "Headingley",         "city": "Leeds", "postcode": "LS6 2AL", "lat": 53.8244, "lng": -1.5768, "property_type": "flat",          "uprn": "500067890124"},
    {"id": "ls6-004", "line_1": "Flat 3, 62 Otley Road",      "line_2": "Headingley",         "city": "Leeds", "postcode": "LS6 2AW", "lat": 53.8248, "lng": -1.5772, "property_type": "flat",          "uprn": "500067890131"},
    {"id": "ls6-005", "line_1": "48 Bennett Road",            "line_2": None,                 "city": "Leeds", "postcode": "LS6 3HN", "lat": 53.8225, "lng": -1.5755, "property_type": "terraced",      "uprn": "500067890132"},
    {"id": "ls6-006", "line_1": "19 Headingley Lane",         "line_2": None,                 "city": "Leeds", "postcode": "LS6 1BL", "lat": 53.8260, "lng": -1.5780, "property_type": "semi_detached", "uprn": "500067890133"},

    # ── BS8 — Bristol / Clifton ───────────────────────────────────
    {"id": "bs8-001", "line_1": "7 Caledonia Place",          "line_2": "Clifton",            "city": "Bristol", "postcode": "BS8 4DN", "lat": 51.4575, "lng": -2.6120, "property_type": "flat",          "uprn": "600078901234"},
    {"id": "bs8-002", "line_1": "3 Caledonia Place",          "line_2": "Clifton",            "city": "Bristol", "postcode": "BS8 4DN", "lat": 51.4573, "lng": -2.6118, "property_type": "flat",          "uprn": "600078901240"},
    {"id": "bs8-003", "line_1": "19 Pembroke Road",           "line_2": "Clifton",            "city": "Bristol", "postcode": "BS8 3BB", "lat": 51.4580, "lng": -2.6142, "property_type": "semi_detached", "uprn": "600078901235"},
    {"id": "bs8-004", "line_1": "28 Pembroke Road",           "line_2": "Clifton",            "city": "Bristol", "postcode": "BS8 3BB", "lat": 51.4583, "lng": -2.6138, "property_type": "semi_detached", "uprn": "600078901241"},
    {"id": "bs8-005", "line_1": "Flat 9, Goldney Hall",       "line_2": None,                 "city": "Bristol", "postcode": "BS8 4BH", "lat": 51.4565, "lng": -2.6130, "property_type": "flat",          "uprn": "600078901242"},
    {"id": "bs8-006", "line_1": "11 Clifton Park Road",       "line_2": "Clifton",            "city": "Bristol", "postcode": "BS8 3HN", "lat": 51.4592, "lng": -2.6105, "property_type": "detached",      "uprn": "600078901243"},
]
