# Check report

Made by `code/05_check.py`.

| Check | Result | Detail |
|---|---|---|
| Every candidate release was read and coded exactly once | PASS | 65 candidates, 65 review rows |
| Every review row has a valid decision | PASS | 0 invalid |
| Every release left out has a written reason | PASS | 0 without reason |
| Releases coded as actions and the action table agree | PASS | 47 releases coded as actions, 47 releases in the action table |
| Action IDs are unique | PASS | 48 actions |
| Every related action exists | PASS |  |
| Every action belongs to a covered company group | PASS |  |
| Stage is 'resolved' or 'filed' | PASS |  |
| The company name recorded appears word for word in the release | PASS |  |
| Every amount quoted appears word for word in the release | PASS |  |
| Every statement on liability quoted appears word for word in the release | PASS |  |
| Every dollar amount equals the dollar figure(s) in the quoted text (summed where there are several) | PASS |  |
| Amount precision is 'exact', 'approximate' or 'minimum' | PASS |  |
| Link basis is one of the three documented kinds | PASS |  |
| No amount without its quoted source text | PASS |  |
| The 50 companies and their totals match us-guard-spending's published top-50 table | PASS | rank, name and total (to $0.01 million) for all 50 |
| 48 company groups are covered (the two placeholder entries are left out) | PASS |  |
| Clean action table has every coded action | PASS |  |
| Company totals add up to the action table | PASS | $126,213,230 |
| SAM extract is the file downloaded (SHA-256) | PASS | SAM_Exclusions_Public_Extract_V2_26302.ZIP |
| SAM exclusions checked against every UEI and name | PASS | 169,173 active records, 126 UEIs, 119 names, 0 matches |
