"""Draw figures/enforcement_actions.png from data/clean/enforcement_actions.csv.

One mark per resolved action, by year and company group; filled marks state an amount.

Usage: python code/06_figure.py
"""
import csv

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from common import CLEAN, ROOT

rows = [r for r in csv.DictReader(open(CLEAN / "enforcement_actions.csv", encoding="utf-8")) if r["stage"] == "resolved"]
groups = sorted({r["company_group"] for r in rows}, key=lambda g: min(int(r["group_rank"]) for r in rows if r["company_group"] == g))
y = {g: i for i, g in enumerate(reversed(groups))}
colour = {"DOJ": "#15171A", "EEOC": "#8B2E2E"}

fig, ax = plt.subplots(figsize=(10, 0.42 * len(groups) + 1.4))
for r in rows:
    yr = int(r["date"][:4]) + (int(r["date"][5:7]) - 0.5) / 12
    filled = bool(r["amount_usd"])
    ax.scatter(yr, y[r["company_group"]], s=46, marker="o", zorder=3,
               facecolor=colour[r["agency"]] if filled else "white", edgecolor=colour[r["agency"]], linewidth=1.4)
ax.set_yticks(range(len(groups)))
LABEL = {"THE GEO GROUP, INC.": "GEO Group", "G4S PLC": "G4S plc", "AKAL SECURITY, INC.": "Akal Security",
         "SECURITAS AB": "Securitas AB", "SRS CRITICAL INFRASTRUCTURE SECURITY LLC": "SRS Critical Infrastructure Security",
         "TRIPLE CANOPY INC": "Triple Canopy", "MVM, INC.": "MVM", "THE DAY & ZIMMERMANN GROUP, INC": "Day & Zimmermann Group",
         "BCEC - GW HOLDINGS (GUERNSEY) LP": "BCEC - GW Holdings (GardaWorld)",
         "UNIVERSAL PROTECTION SERVICE, LIMITED PARTNERSHIP": "Universal Protection Service LP",
         "AMENTUM JOINT VENTURE LP": "Amentum Joint Venture LP", "AFOGNAK NATIVE CORP": "Afognak Native Corp",
         "UNIVERSAL PROTECTION GP, LLC": "Universal Protection GP"}
ax.set_yticklabels([LABEL.get(g, g.title()) for g in reversed(groups)], fontsize=9)
ax.grid(axis="x", color="#D9D5CE", lw=0.6)
ax.spines[["top", "right", "left"]].set_visible(False)
ax.tick_params(axis="y", length=0)
ax.set_title("Resolved federal enforcement actions announced against the largest U.S. guard contractors",
             loc="left", fontsize=11, x=-0.3)
for k, c in colour.items():
    ax.scatter([], [], s=46, color=c, label={"DOJ": "Department of Justice", "EEOC": "Equal Employment Opportunity Commission"}[k])
ax.scatter([], [], s=46, facecolor="white", edgecolor="#4A4F57", label="no amount stated")
ax.legend(frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(0, -0.08), ncol=3)
fig.text(0.01, 0.005, "Actions announced in DOJ and EEOC press releases. Many settlements say the claims are allegations "
         "with no finding of liability. Company groups as reported in USAspending.", fontsize=7.5, color="#4A4F57")
fig.tight_layout(rect=(0, 0.03, 1, 1))
(ROOT / "figures").mkdir(exist_ok=True)
fig.savefig(ROOT / "figures" / "enforcement_actions.png", dpi=150)
print("figures/enforcement_actions.png")
