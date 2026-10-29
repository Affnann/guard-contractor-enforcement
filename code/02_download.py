"""Download the three official sources into data/raw/.

1. SAM.gov Exclusions public extract (GSA): every exclusion currently active, the list of
   people and companies barred from federal contracts. Only the latest daily file is public,
   so the file name records the date (V2_YYDDD).
2. U.S. Department of Justice press releases, from the justice.gov press-release API, for
   every release whose title contains one of the search terms in code/common.py.
3. U.S. Equal Employment Opportunity Commission (EEOC) press releases, from the EEOC newsroom
   search, for every release the search returns for one of the terms.

Usage: python code/02_download.py [sam] [doj] [eeoc]   (no argument = all three)
"""
import gzip
import hashlib
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from common import COMPANY_TERMS, GENERAL_TERMS, RAW, UA, eeoc_date

LOG = RAW / "download_log.json"


def fetch(url, tries=4, timeout=180):
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read()
        except Exception:
            if attempt == tries - 1:
                raise
            time.sleep(3 * (attempt + 1))


def log(key, **info):
    d = json.loads(LOG.read_text()) if LOG.exists() else {}
    d[key] = info
    LOG.write_text(json.dumps(d, indent=1))


def sam():
    # The public extract is published daily as SAM_Exclusions_Public_Extract_V2_YYDDD.ZIP
    day = time.strftime("%y") + time.strftime("%j")
    name = f"SAM_Exclusions_Public_Extract_V2_{day}.ZIP"
    url = ("https://sam.gov/api/prod/fileextractservices/v1/api/download/Exclusions/Public%20V2/"
           + name + "?privacy=Public")
    data = fetch(url, timeout=600)
    (RAW / "sam").mkdir(parents=True, exist_ok=True)
    (RAW / "sam" / name).write_bytes(data)
    log("sam/" + name, url=url, bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
        accessed=time.strftime("%Y-%m-%d"))
    print("SAM", name, f"{len(data):,} bytes")


DOJ_KEEP = ["uuid", "title", "date", "url", "body", "teaser", "component", "topic", "number"]


def doj():
    out = RAW / "doj" / "doj_press_releases.jsonl.gz"
    out.parent.mkdir(parents=True, exist_ok=True)
    seen, counts = {}, {}
    for term in GENERAL_TERMS + COMPANY_TERMS:
        page, n = 0, None
        while True:
            q = urllib.parse.urlencode({"pagesize": 50, "page": page, "parameters[title]": term})
            d = json.loads(fetch("https://www.justice.gov/api/v1/press_releases.json?" + q))
            n = int(d["metadata"]["resultset"]["count"])
            for r in d.get("results", []):
                rec = seen.setdefault(r["uuid"], {k: r.get(k) for k in DOJ_KEEP} | {"search_terms": []})
                rec["search_terms"].append(term)
            page += 1
            if page * 50 >= n:
                break
            time.sleep(0.3)
        counts[term] = n
        print(f"DOJ {term!r}: {n}", flush=True)
    with gzip.open(out, "wt", encoding="utf-8") as fh:
        for rec in sorted(seen.values(), key=lambda r: (r["date"] or "", r["uuid"])):
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    log("doj/doj_press_releases.jsonl.gz", api="https://www.justice.gov/api/v1/press_releases.json",
        filter="parameters[title]=TERM", results_per_term=counts, unique_releases=len(seen),
        accessed=time.strftime("%Y-%m-%d"))
    print("DOJ unique releases:", len(seen))


EEOC = "https://www.eeoc.gov"


def eeoc():
    out = RAW / "eeoc" / "eeoc_press_releases.jsonl.gz"
    out.parent.mkdir(parents=True, exist_ok=True)
    found, counts = {}, {}
    # EEOC searches full text, where words such as "discrimination" occur in nearly every
    # release, so only the first three general terms are used there
    # "Day &" is reduced to "day" by the EEOC search, which then returns almost every release;
    # "Zimmermann" already finds Day & Zimmermann
    for term in GENERAL_TERMS[:3] + [t for t in COMPANY_TERMS if t != "Day &"]:
        page, links = 0, []
        while True:
            q = urllib.parse.urlencode({"keywords": term, "page": page})
            t = fetch(f"{EEOC}/newsroom/search?{q}").decode("utf-8", "replace")
            # results are the newsroom links inside the search view, not the menus around it
            view = t[t.find('views-exposed-form-newsroom-block-1'):]
            new = [h for h in re.findall(r'href="(/newsroom/[a-z0-9-]+)"', view)
                   if h not in ("/newsroom/search",) and h not in links]
            links += new
            if not new or f"page={page + 1}" not in t:
                break
            page += 1
            time.sleep(0.5)
        counts[term] = len(links)
        for h in links:
            found.setdefault(h, []).append(term)
        print(f"EEOC {term!r}: {len(links)}", flush=True)
    print(f"EEOC fetching {len(found)} releases", flush=True)
    def one(item):
        h, terms = item
        t = fetch(EEOC + h).decode("utf-8", "replace")
        title = html.unescape(re.search(r"<title>(.*?)\s*\|", t, re.S).group(1)).strip()
        m = re.search(r"<article.*?</article>", t, re.S)
        body = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(0) if m else ""))).strip()
        time.sleep(0.5)
        return {"url": EEOC + h, "title": title, "date": eeoc_date(body),
                "body": body, "search_terms": terms}

    with ThreadPoolExecutor(4) as pool:  # four requests at a time, each followed by a pause
        recs = list(pool.map(one, sorted(found.items())))
    with gzip.open(out, "wt", encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    log("eeoc/eeoc_press_releases.jsonl.gz", search=f"{EEOC}/newsroom/search?keywords=TERM",
        results_per_term=counts, unique_releases=len(recs), accessed=time.strftime("%Y-%m-%d"))
    print("EEOC unique releases:", len(recs))


if __name__ == "__main__":
    todo = sys.argv[1:] or ["sam", "doj", "eeoc"]
    for job in todo:
        {"sam": sam, "doj": doj, "eeoc": eeoc}[job]()
