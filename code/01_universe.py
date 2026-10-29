"""Build the list of companies covered: the 50 largest recipients of U.S. federal guard-service
contracts (product and service code S206), fiscal years 2008-2026, from the us-guard-spending
dataset (https://doi.org/10.5281/zenodo.23750993), less its two placeholder entries.

Companies are grouped by the parent company USAspending reports, as in us-guard-spending.
For each group the script keeps every recipient name and Unique Entity ID (UEI) that appears
under it, so that releases and exclusions can be matched to any of them.

Usage: python code/01_universe.py
Writes data/raw/universe/top50_parents.csv and data/raw/universe/universe.json
"""
import csv
import gzip
import hashlib
import io
import json
import urllib.request
from collections import defaultdict

from common import RAW, UA

SRC = "https://github.com/Affnann/us-guard-spending/raw/v1.0.0/data/clean/s206_transactions.csv.gz"
PLACEHOLDERS = {"DOMESTIC AWARDEES (UNDISCLOSED)", "MISCELLANEOUS FOREIGN AWARDEES"}
OUT = RAW / "universe"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(SRC, headers=UA)
    data = urllib.request.urlopen(req, timeout=300).read()
    sha = hashlib.sha256(data).hexdigest()
    rows = list(csv.DictReader(io.TextIOWrapper(gzip.GzipFile(fileobj=io.BytesIO(data)), encoding="utf-8")))

    total = defaultdict(float)
    awards = defaultdict(set)
    for r in rows:
        r["parent"] = r["recipient_parent_name"] or r["recipient_name"]
        total[r["parent"]] += float(r["obligation_usd"] or 0)
        awards[r["parent"]].add(r["award_key"])
    top = sorted(total, key=lambda p: -total[p])[:50]

    groups = {}
    for p in top:
        if p in PLACEHOLDERS:
            continue
        sub = [r for r in rows if r["parent"] == p]
        groups[p] = {
            "rank": top.index(p) + 1,
            "obligations_usd": round(total[p], 2),
            "awards": len(awards[p]),
            "parent_uei": sorted({r["recipient_parent_uei"] for r in sub if r["recipient_parent_uei"]}),
            "recipient_uei": sorted({r["recipient_uei"] for r in sub if r["recipient_uei"]}),
            "names": sorted({r["recipient_name"] for r in sub if r["recipient_name"]} | {p}),
        }

    with open(OUT / "top50_parents.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["rank", "parent", "obligations_usd_fy2008_2026", "awards", "included"])
        for i, p in enumerate(top, 1):
            w.writerow([i, p, round(total[p], 2), len(awards[p]), "no (placeholder)" if p in PLACEHOLDERS else "yes"])
    (OUT / "universe.json").write_text(json.dumps(
        {"source": SRC, "source_sha256": sha, "groups": groups}, indent=1, ensure_ascii=False))
    n_uei = len({u for g in groups.values() for u in g["recipient_uei"] + g["parent_uei"]})
    print(f"{len(groups)} company groups, {sum(len(g['names']) for g in groups.values())} names, {n_uei} UEIs")


if __name__ == "__main__":
    main()
