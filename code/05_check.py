"""Check the dataset and write data/clean/check_report.md.

Usage: python code/05_check.py
"""
import csv
import gzip
import hashlib
import html
import json
import re
import urllib.request

from common import CLEAN, CODING, INTERIM, RAW, UA, norm

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))


def read(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def flat(text):
    """Release text as one line, with HTML removed and typographic quotes made plain."""
    t = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    t = t.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", t.replace("\xa0", " "))


def main():
    groups = json.loads((RAW / "universe" / "universe.json").read_text())["groups"]
    cands = {(r["source"], r["release_id"]): r for r in read(INTERIM / "candidates.csv")}
    review = read(CODING / "release_review.csv")
    actions = read(CODING / "actions.csv")
    clean = read(CLEAN / "enforcement_actions.csv")
    companies = read(CLEAN / "companies.csv")

    texts = {}
    with gzip.open(RAW / "doj" / "doj_press_releases.jsonl.gz", "rt", encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            texts[("DOJ", r["uuid"])] = flat(" ".join([r["title"] or "", r.get("teaser") or "", r["body"] or ""]))
    with gzip.open(RAW / "eeoc" / "eeoc_press_releases.jsonl.gz", "rt", encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            texts[("EEOC", r["url"].rsplit("/", 1)[1])] = flat(r["title"] + " " + r["body"])

    # 1. every candidate reviewed once, nothing reviewed that is not a candidate
    keys = [(r["source"], r["release_id"]) for r in review]
    check("Every candidate release was read and coded exactly once",
          sorted(keys) == sorted(cands) and len(keys) == len(set(keys)),
          f"{len(cands)} candidates, {len(keys)} review rows")
    dec = {(r["source"], r["release_id"]): r["decision"] for r in review}
    bad = [k for k in dec if dec[k] not in ("action", "duplicate", "not an action against a covered company")]
    check("Every review row has a valid decision", not bad, f"{len(bad)} invalid")
    no_reason = [k for k, r in zip(keys, review) if r["decision"] != "action" and not r["reason"].strip()]
    check("Every release left out has a written reason", not no_reason, f"{len(no_reason)} without reason")

    # 2. actions and review agree
    act_keys = {(a["source"], a["release_id"]) for a in actions}
    marked = {k for k, d in dec.items() if d == "action"}
    check("Releases coded as actions and the action table agree", act_keys == marked,
          f"{len(marked)} releases coded as actions, {len(act_keys)} releases in the action table")
    ids = [a["action_id"] for a in actions]
    check("Action IDs are unique", len(ids) == len(set(ids)), f"{len(ids)} actions")
    rel = [a["related_action"] for a in actions if a["related_action"]]
    check("Every related action exists", all(x in ids for r in rel for x in r.split("; ")))
    check("Every action belongs to a covered company group", all(a["company_group"] in groups for a in actions))
    check("Stage is 'resolved' or 'filed'", all(a["stage"] in ("resolved", "filed") for a in actions))

    # 3. the words recorded are the release's own words
    miss_entity = [a["action_id"] for a in actions if a["entity_named"] not in texts[(a["source"], a["release_id"])]]
    check("The company name recorded appears word for word in the release", not miss_entity, ", ".join(miss_entity))
    miss_amt = [a["action_id"] for a in actions if a["amount_text"] and a["amount_text"] not in texts[(a["source"], a["release_id"])]]
    check("Every amount quoted appears word for word in the release", not miss_amt, ", ".join(miss_amt))
    miss_lia = [a["action_id"] for a in actions if a["liability"].startswith('"') and
                a["liability"].strip('"') not in texts[(a["source"], a["release_id"])]]
    check("Every statement on liability quoted appears word for word in the release", not miss_lia, ", ".join(miss_lia))
    bad_amt = []
    for a in actions:
        if a["amount_usd"]:
            nums = [float(x.replace(",", "")) for x in re.findall(r"\$([\d,]+(?:\.\d+)?)(?!\d|[.,]\d| ?(?:million|M\b))", a["amount_text"])]
            nums += [float(x) * 1e6 for x in re.findall(r"\$([\d.]+) ?(?:million|M\b)", a["amount_text"])]
            if abs(float(a["amount_usd"]) - sum(nums)) > 0.5:
                bad_amt.append(a["action_id"])
    check("Every dollar amount equals the dollar figure(s) in the quoted text (summed where there are several)",
          not bad_amt, ", ".join(bad_amt))
    check("Amount precision is 'exact', 'approximate' or 'minimum'",
          all(a["amount_precision"] in ("exact", "approximate", "minimum") for a in actions if a["amount_usd"]))
    check("Link basis is one of the three documented kinds", all(a["link_basis"] in (
        "named company is in the group's contract data", "release states the link", "brand name only")
        for a in actions))
    no_amt = [a["action_id"] for a in actions if a["amount_usd"] and not a["amount_text"]]
    check("No amount without its quoted source text", not no_amt)

    # 4. the company list reproduces us-guard-spending's own top-50 table
    url = "https://github.com/Affnann/us-guard-spending/raw/v1.0.0/output/tables/top50_companies_musd.csv"
    top = list(csv.DictReader(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120)
                              .read().decode().splitlines()))
    mine = read(RAW / "universe" / "top50_parents.csv")
    same = all(a["parent"] == b["parent"] and abs(float(a["obligations_usd_fy2008_2026"]) / 1e6 - float(b["obligations_musd"])) < 0.006
               for a, b in zip(mine, top)) and len(mine) == len(top) == 50
    check("The 50 companies and their totals match us-guard-spending's published top-50 table", same,
          "rank, name and total (to $0.01 million) for all 50")
    check("48 company groups are covered (the two placeholder entries are left out)", len(groups) == 48 == len(companies))

    # 5. clean tables are complete
    check("Clean action table has every coded action", len(clean) == len(actions))
    tot = sum(float(a["amount_usd"]) for a in clean if a["amount_usd"] and a["stage"] == "resolved")
    tot2 = sum(float(c["amount_usd_resolved_stated"]) for c in companies)
    check("Company totals add up to the action table", abs(tot - tot2) < 1, f"${tot:,.0f}")

    # 6. SAM extract matches its download record
    log = json.loads((RAW / "download_log.json").read_text())
    sam_ok = True
    for k, v in log.items():
        if k.startswith("sam/"):
            sam_ok &= hashlib.sha256((RAW / k).read_bytes()).hexdigest() == v["sha256"]
    summ = json.loads((INTERIM / "sam_summary.json").read_text())
    check("SAM extract is the file downloaded (SHA-256)", sam_ok, summ["file"])
    check("SAM exclusions checked against every UEI and name", summ["uei_checked"] > 0,
          f'{summ["records"]:,} active records, {summ["uei_checked"]} UEIs, {summ["names_checked"]} names, {summ["matches"]} matches')

    lines = ["# Check report", "", "Made by `code/05_check.py`.", "", "| Check | Result | Detail |", "|---|---|---|"]
    lines += [f"| {n} | {'PASS' if ok else 'FAIL'} | {d} |" for n, ok, d in results]
    (CLEAN / "check_report.md").write_text("\n".join(lines) + "\n")
    for n, ok, d in results:
        print("PASS" if ok else "FAIL", n, "-", d)
    if not all(ok for _, ok, _ in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
