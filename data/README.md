# Data sources

All sources were accessed on 29 October 2026. Addresses, sizes, SHA-256 fingerprints and the number of results for each search term are in [`raw/download_log.json`](raw/download_log.json).

| File | Source | What it is |
|---|---|---|
| `raw/universe/universe.json`, `raw/universe/top50_parents.csv` | [us-guard-spending v1.0.0](https://doi.org/10.5281/zenodo.23750993) (Mercenomics), from USAspending.gov | The 50 largest recipients of federal guard-service contracts (product and service code S206), fiscal years 2008-2026, grouped by parent company, with every recipient name and Unique Entity ID under each |
| `raw/sam/SAM_Exclusions_Public_Extract_V2_26302.ZIP` | U.S. General Services Administration, SAM.gov public exclusions extract (`https://sam.gov/api/prod/fileextractservices/v1/api/download/Exclusions/Public%20V2/`) | Every exclusion active on 29 October 2026 (day 302 of 2026): people and companies barred from federal contracts and assistance. 169,173 records |
| `raw/doj/doj_press_releases.jsonl.gz` | U.S. Department of Justice, press-release API (`https://www.justice.gov/api/v1/press_releases.json`) | Every release whose title contains one of the 70 search terms in `code/common.py`: 10,210 releases dated 12 January 2009 to 28 October 2026, with title, date, issuing office and full text. The service holds few releases before 2013 |
| `raw/eeoc/eeoc_press_releases.jsonl.gz` | U.S. Equal Employment Opportunity Commission, newsroom search (`https://www.eeoc.gov/newsroom/search`) | Every release the newsroom search returned for 64 terms: 3,180 releases dated 1995 to 2026, with title, date and text as shown on the page |

**Terms:** all three sources are works of the U.S. government and are in the public domain.

## Notes

- **EEOC pages:** 49 of the 3,180 pages had little readable text or no date (mostly speeches and announcements). Their titles were still searched for company names, and none named a covered company. Dates on older pages are written as `PRESS RELEASE 9-22-09` and are converted to `2009-09-22`.
- **EEOC search terms:** "Day &" is reduced to "day" by the EEOC search and returns almost every release, so it was not used there; "Zimmermann" finds Day & Zimmermann. "Management & Training" returned 2,282 releases for the same reason. They were all downloaded and searched, and only those naming a covered company were kept as candidates.
- **Not included:** the Department of Labor (wage-and-hour and OSHA cases). Its website (dol.gov) refused automated requests from the workspace used, and its data service (data.dol.gov) requires a registered key. Federal contractor performance records (FAPIIS) and contract terminations also require a registered SAM.gov key. These are the obvious additions for a later version.
