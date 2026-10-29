"""Find the press releases and exclusion records that name a covered company.

A release is a candidate if its title or text contains the name of a covered company as whole
words, after legal-form words (Inc., LLC, Corporation ...) are removed from the name. Names
reduced to one word are used only if that word is distinctive (code/common.py). A few group
brands (G4S, Securitas, Akal ...) are also searched, because sister companies with other names
(for example "Securitas GmbH Werkschutz") are not in the contract data under that name.

Every candidate is then read by hand: data/coding/release_review.csv records whether each one
is an enforcement action against a covered company and, if not, why not.

SAM exclusions are matched on Unique Entity ID, and on the company name after legal-form words
are removed (exact equality, not word search).

Usage: python code/03_match.py
Writes data/interim/candidates.csv and data/interim/sam_matches.csv
"""
import csv
import gzip
import html
import io
import json
import re
import zipfile
from datetime import datetime, timezone

from common import BRANDS, INTERIM, RAW, core_name, norm, searchable

# two-word names that are ordinary phrases; for these the full registered name is searched
NEEDS_FULL_NAME = {"CORRECTIONAL SERVICES": "CORRECTIONAL SERVICES CORPORATION"}


def patterns(groups):
    pats = {}  # pattern -> set of groups
    for g, info in groups.items():
        for name in info["names"]:
            c = core_name(name)
            c = NEEDS_FULL_NAME.get(c, c)
            if searchable(c):
                pats.setdefault(c, set()).add(g)
        for b in BRANDS:
            if any(f" {b} " in norm(n) for n in info["names"]):
                pats.setdefault(b, set()).add(g)
    return pats


def releases():
    with gzip.open(RAW / "doj" / "doj_press_releases.jsonl.gz", "rt", encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            date = datetime.fromtimestamp(int(r["date"]), timezone.utc).strftime("%Y-%m-%d") if r["date"] else ""
            comp = "; ".join(c.get("name", "") for c in (r.get("component") or []) if isinstance(c, dict))
            yield {"source": "DOJ", "release_id": r["uuid"], "date": date, "title": r["title"] or "",
                   "url": r["url"], "office": comp, "text": " ".join([r["title"] or "", r.get("teaser") or "", r["body"] or ""])}
    with gzip.open(RAW / "eeoc" / "eeoc_press_releases.jsonl.gz", "rt", encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            yield {"source": "EEOC", "release_id": r["url"].rsplit("/", 1)[1], "date": r["date"],
                   "title": r["title"], "url": r["url"], "office": "EEOC", "text": r["title"] + " " + r["body"]}


def main():
    INTERIM.mkdir(parents=True, exist_ok=True)
    groups = json.loads((RAW / "universe" / "universe.json").read_text())["groups"]
    pats = patterns(groups)

    n, rows = 0, []
    for r in releases():
        n += 1
        text = norm(html.unescape(re.sub(r"<[^>]+>", " ", r["text"])))
        hit = sorted(p for p in pats if f" {p} " in text)
        if hit:
            g = sorted({x for p in hit for x in pats[p]})
            rows.append({k: r[k] for k in ("source", "release_id", "date", "title", "url", "office")}
                        | {"matched_names": "; ".join(hit), "company_groups": "; ".join(g)})
    rows.sort(key=lambda r: (r["date"], r["source"], r["release_id"]))
    with open(INTERIM / "candidates.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{n} releases read, {len(rows)} name a covered company -> data/interim/candidates.csv")

    # SAM exclusions
    ueis = {}
    cores = {}
    for g, info in groups.items():
        for u in info["recipient_uei"] + info["parent_uei"]:
            ueis[u] = g
        for name in info["names"]:
            cores[core_name(name)] = g
    sam_zip = sorted((RAW / "sam").glob("SAM_Exclusions_Public_Extract_V2_*.ZIP"))[-1]
    with zipfile.ZipFile(sam_zip) as z:
        member = [m for m in z.namelist() if m.upper().endswith(".CSV")][0]
        reader = csv.DictReader(io.TextIOWrapper(z.open(member), encoding="utf-8-sig", errors="replace"))
        sam_rows, matches = 0, []
        for s in reader:
            sam_rows += 1
            by_uei = ueis.get(s["Unique Entity ID"])
            by_name = cores.get(core_name(s["Name"])) if s["Name"] else None
            if by_uei or by_name:
                matches.append({"company_group": by_uei or by_name, "match": "uei" if by_uei else "name",
                                "name": s["Name"], "uei": s["Unique Entity ID"], "exclusion_type": s["Exclusion Type"],
                                "excluding_agency": s["Excluding Agency"], "active_date": s["Active Date"],
                                "termination_date": s["Termination Date"], "record_status": s["Record Status"]})
    fields = ["company_group", "match", "name", "uei", "exclusion_type", "excluding_agency", "active_date",
              "termination_date", "record_status"]
    with open(INTERIM / "sam_matches.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(matches)
    (INTERIM / "sam_summary.json").write_text(json.dumps(
        {"file": sam_zip.name, "records": sam_rows, "uei_checked": len(ueis), "names_checked": len(cores),
         "matches": len(matches)}, indent=1))
    print(f"SAM {sam_zip.name}: {sam_rows:,} records, {len(ueis)} UEIs and {len(cores)} names checked, "
          f"{len(matches)} matches")


if __name__ == "__main__":
    main()
