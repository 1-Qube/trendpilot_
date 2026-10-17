"""Demo companies. They are profiles, not claimed clients."""

from __future__ import annotations

PROFILES: dict[str, dict[str, str]] = {
    "Blank company": {
        "name": "",
        "industry": "",
        "size": "small",
        "city": "Taraz",
        "offer": "",
        "customer": "",
        "channel": "",
        "constraint": "",
        "competitors": "",
        "language": "Russian",
    },
    "Clinic — Satti Med": {
        "name": "Satti Med",
        "industry": "private outpatient clinic",
        "size": "small",
        "city": "Taraz",
        "offer": "paid checkups, pediatrics, and basic diagnostics",
        "customer": "families who already use Instagram and 2GIS to pick a clinic",
        "channel": "Instagram and a 2GIS card",
        "constraint": "two doctors, weekday evenings only, no ad budget",
        "competitors": "other private clinics listed on 2GIS in Taraz",
        "language": "Russian",
    },
    "Yard — Karatau Materials": {
        "name": "Karatau Materials",
        "industry": "building materials yard",
        "size": "small",
        "city": "Taraz",
        "offer": "cement, insulation, drywall, and delivery inside the city",
        "customer": "small crews and households doing repairs",
        "channel": "WhatsApp and a 2GIS card",
        "constraint": "thin cash, one truck, cannot stock a new category on a guess",
        "competitors": "other building-material yards in Taraz",
        "language": "Russian",
    },
    "Desk — Aksu routes": {
        "name": "Aksu Route Desk",
        "industry": "small tour desk",
        "size": "micro",
        "city": "Taraz",
        "offer": "day trips toward Aksu-Zhabagly and the Karatau foothills",
        "customer": "visitors and local families booking by phone",
        "channel": "Instagram and phone",
        "constraint": "two guides, weekends only, no marketplace fees",
        "competitors": "other Taraz tour desks and regional park tours",
        "language": "Russian",
    },
}

SIZES = ["micro", "small", "mid", "large"]
LANGUAGES = ["Russian", "Kazakh", "English"]
