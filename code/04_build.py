"""Build the clean tables from the hand-coded actions.

Inputs:  data/raw/universe/universe.json, data/interim/candidates.csv, data/interim/sam_matches.csv,
         data/coding/release_review.csv, data/coding/actions.csv
Outputs: data/clean/enforcement_actions.csv, data/clean/companies.csv

Usage: python code/04_build.py
"""
import csv
import json
from collections import defaultdict

from common import CLEAN, CODING, INTERIM, RAW

ACTION_COLS = ["action_id", "date", "agency", "office", "company_group", "group_rank", "entity_named",
               "link_basis", "group_note", "track", "action", "stage", "law", "conduct", "customer",
               "amount_usd", "amount_precision", "amount_text", "liability", "related_action",
               "source_url", "source_title"]


def read(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main():
    CLEAN.mkdir(parents=True, exist_ok=True)
    groups = json.loads((RAW / "universe" / "universe.json").read_text())["groups"]
    cands = {(r["source"], r["release_id"]): r for r in read(INTERIM / "candidates.csv")}
    actions = read(CODING / "actions.csv")
    sam = read(INTERIM / "sam_matches.csv")

    out = []
    for a in actions:
        c = cands[(a["source"], a["release_id"])]
        out.append({**{k: a.get(k, "") for k in ACTION_COLS},
                    "date": c["date"], "agency": a["source"], "office": c["office"],
                    "group_rank": groups[a["company_group"]]["rank"],
                    "source_url": c["url"], "source_title": c["title"]})
    out.sort(key=lambda r: (r["date"], r["action_id"]))
    with open(CLEAN / "enforcement_actions.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=ACTION_COLS)
        w.writeheader()
        w.writerows(out)

    n_cand = defaultdict(lambda: defaultdict(int))
    for c in cands.values():
        for g in c["company_groups"].split("; "):
            n_cand[g][c["source"]] += 1
    by = defaultdict(list)
    for a in out:
        by[a["company_group"]].append(a)
    rows = []
    for g, info in sorted(groups.items(), key=lambda kv: kv[1]["rank"]):
        res = [a for a in by[g] if a["stage"] == "resolved"]
        rows.append({
            "rank": info["rank"], "company_group": g,
            "guard_contract_obligations_usd_fy2008_2026": f'{info["obligations_usd"]:.2f}',
            "names_in_contract_data": len(info["names"]),
            "ueis_checked": len(set(info["recipient_uei"] + info["parent_uei"])),
            "doj_releases_naming_group": n_cand[g]["DOJ"], "eeoc_releases_naming_group": n_cand[g]["EEOC"],
            "actions_resolved": len(res),
            "actions_filed_unresolved_in_release": sum(a["stage"] == "filed" for a in by[g]),
            "amount_usd_resolved_stated": f'{sum(float(a["amount_usd"]) for a in res if a["amount_usd"]):.0f}',
            "resolved_without_stated_amount": sum(not a["amount_usd"] for a in res),
            "resolved_linked_by_brand_name_only": sum(a["link_basis"].startswith("brand") for a in res),
            "sam_active_exclusions": sum(s["company_group"] == g for s in sam),
        })
    with open(CLEAN / "companies.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(out)} actions -> data/clean/enforcement_actions.csv; {len(rows)} groups -> data/clean/companies.csv")


if __name__ == "__main__":
    main()
