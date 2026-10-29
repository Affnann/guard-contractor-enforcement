"""Shared settings: paths, search terms and company-name matching."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"
CODING = ROOT / "data" / "coding"
CLEAN = ROOT / "data" / "clean"
UA = {"User-Agent": "Mozilla/5.0 (research data download)"}

# Words searched for in press-release titles (DOJ) or in the full text (EEOC search).
# General terms catch releases that describe a company without naming it in the title;
# the company terms catch releases that name it.
GENERAL_TERMS = ["Contractor", "Security", "Guard", "False Claims", "Bid Rigging", "Kickback",
                 "Discrimination", "USERRA"]
COMPANY_TERMS = [
    "Academi", "Acadia Protective", "Afognak", "Ahtna", "Akal", "Akima", "Allied Universal", "Alutiiq",
    "Amentum", "American Eagle", "American Security", "ArmorGroup", "Armor Group", "Asset Protection",
    "Blackwater", "CDA", "Canopy", "Centerra", "Chenega", "Coastal International", "Constellis",
    "Continuity Global", "CoreCivic", "Cornell", "Corrections Corporation", "Correctional Services",
    "Covenant", "Day &", "Diamond Group", "Diversified Protection", "FJC", "G4S", "GEO Group", "Garda",
    "Global Precision", "Golden", "Guardsmark", "IDS International", "Inter-Con", "Kerberos",
    "Lockwood Hills", "MVM", "Management & Training", "Master Security", "Metropolitan Security", "NANA",
    "North American Security", "Omniplex", "Paragon", "Paragon Professional", "Pond", "SecTek",
    "Securitas", "Security Consultants", "Spectrum Security", "Themis", "Torres", "Tri-S",
    "Universal Protection", "Vendtech", "Wackenhut", "Zimmermann",
]

# Legal-form words removed before names are compared.
SUFFIXES = {"INC", "INCORPORATED", "LLC", "L L C", "LP", "L P", "LIMITED", "PARTNERSHIP", "CORP",
            "CORPORATION", "CO", "COMPANY", "LTD", "PLC", "GMBH", "SA", "S A", "SAC", "S A C", "NV",
            "AB", "A S", "THE", "JOINT", "VENTURE"}
# A name reduced to a single word is only searched for if that word is distinctive enough
# not to occur in ordinary text. Every match is then read by hand (data/coding/).
DISTINCTIVE = {"G4S", "AKAL", "SECTEK", "SECURITAS", "CONSTELLIS", "CENTERRA", "CORECIVIC", "ACADEMI",
               "GUARDSMARK", "AMENTUM", "VENDTECH SGI", "OMNIPLEX", "MVM", "CHENEGA", "AFOGNAK", "AHTNA",
               "ALUTIIQ", "KERBEROS", "GARDAWORLD", "ARMORGROUP", "WACKENHUT", "BLACKWATER"}
# Names whose brand also covers sister companies with other suffixes (e.g. "Securitas GmbH
# Werkschutz", "G4S Secure Solutions NV", "Day & Zimmermann NPS"). A match on these is marked
# match_basis = "group brand" and the release is checked by hand.
BRANDS = {"G4S", "SECURITAS", "AKAL", "CHENEGA", "ALUTIIQ", "AHTNA", "AKIMA", "CENTERRA", "CONSTELLIS",
          "TRIPLE CANOPY", "DAY & ZIMMERMANN", "GEO GROUP", "CORECIVIC", "UNIVERSAL PROTECTION",
          "ALLIED UNIVERSAL", "GARDAWORLD", "PARAGON SYSTEMS", "WACKENHUT", "ARMORGROUP", "ARMOR GROUP",
          "ACADEMI", "BLACKWATER", "AMENTUM", "OMNIPLEX", "GUARDSMARK"}


def norm(text):
    """Upper case, '&' kept as a word, every other non-alphanumeric character a space."""
    t = text.upper().replace("&AMP;", "&")
    t = re.sub(r"&", " & ", t)
    t = re.sub(r"[^A-Z0-9&]+", " ", t)
    return " " + re.sub(r"\s+", " ", t).strip() + " "


def core_name(name):
    """A company name without legal-form words, e.g. 'THE GEO GROUP, INC.' -> 'GEO GROUP'."""
    words = norm(name).split()
    # drop legal-form words at the start and end only, so 'MANAGEMENT & TRAINING CORPORATION'
    # keeps its middle
    while words and words[0] in SUFFIXES:
        words = words[1:]
    # trailing legal-form words, including spelled-out forms such as 'L L C' or 'S A'
    while words and (words[-1] in SUFFIXES or len(words[-1]) == 1):
        words = words[:-1]
    return " ".join(words)


def searchable(core):
    """Is a core name specific enough to search for in free text?"""
    return len(core.split()) >= 2 or core in DISTINCTIVE


def eeoc_date(body):
    """Release date from an EEOC page: 'Press Release 12-01-2010' or, on older pages,
    'PRESS RELEASE 1-7-00' (month-day-two-digit-year). Returns YYYY-MM-DD or ''."""
    m = re.search(r"Press Release (\d\d)-(\d\d)-(\d{4})", body)
    if m:
        return f"{m.group(3)}-{m.group(1)}-{m.group(2)}"
    m = re.search(r"PRESS RELEASE\s+(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})\b", body, re.I)
    if m:
        y = int(m.group(3))
        y = y if y > 999 else (1900 + y if y >= 90 else 2000 + y)
        return f"{y}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    return ""
