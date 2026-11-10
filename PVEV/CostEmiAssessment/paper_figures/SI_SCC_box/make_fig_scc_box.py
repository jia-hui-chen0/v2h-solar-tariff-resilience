"""SI Figure: 15-year EV-attributable cost at retail prices (a) and emissions (b) of UC, CC and V2H
dispatched with a social cost of carbon (SCC) of $0, $51 and $204/tCO2 (Fig_SI_SCC_box).

Each box holds one value per RGU: 5 x the sum over 2024, 2030 and 2040 of the median across the RGU's
rows (one row per home and driving profile). RGUs missing a year are dropped.
  Cost: `Cost` (extra cost of the EV after PV) at retail prices. The SCC runs add the carbon price to the
        hourly import and export prices (analysis_UC_fullyear_125PVhhec_scc.py, lines 70 and 93-94), so
        Cost_retail = Cost - (SCC/1000 $/kg) x Emissions
  Emissions: `Emissions` / 1000, in tCO2e.
UC charging does not respond to the SCC, so its three boxes are the same.

Inputs (relative to the project root):
    PVEV/CostEmiAssessment/csv_trb_detailed/{uc,cc,v2h}_125PVhhec_fullyear{,_scc51,_scc204}/
        <rgu>_<year>__5homes_percentile__70roofcover__noelec.csv
    Ford_CC/2020_Gaz_counties_national_0728_tempreg.csv   (number of RGUs)

Writes next to this script: Fig_SI_SCC_box.{pdf,png}, Fig_SI_SCC_box_source_data.csv (the plotted per-RGU
values) and scc_box_summary.csv (n, mean, 5th/95th percentiles and median of each box; also printed).
Drawn at the printed width (5.95 in); all text Arial, 8.5 pt or larger.
Run: uv run --no-project --python 3.14 --with matplotlib==3.11.2 --with pandas --with numpy python make_fig_scc_box.py
Add --from-source-data to draw the figure from Fig_SI_SCC_box_source_data.csv instead of the per-RGU model
results; the source-data file is then read, not written.
"""
import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker

matplotlib.rcParams["axes.unicode_minus"] = False
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["font.family"] = "Arial"

OUT = os.path.dirname(os.path.abspath(__file__))
CSV = r"F:\University of Michigan Dropbox\Jiahui Chen\PVEV\CostEmiAssessment\csv_trb_detailed"
CTY = r"F:\University of Michigan Dropbox\Jiahui Chen\Ford_CC\2020_Gaz_counties_national_0728_tempreg.csv"
YEARS, LCA = [2024, 2030, 2040], 5
SRC = os.path.join(OUT, "Fig_SI_SCC_box_source_data.csv")
FROM_SOURCE = "--from-source-data" in sys.argv[1:]
SCEN = ["uc", "cc", "v2h"]
SCC = [0, 51, 204]
FS = 8.5


def level(scen, scc, metric):
    """Per-RGU 15-year level: LCA x sum over YEARS of the median across the RGU's rows."""
    folder = f"{scen}_125PVhhec_fullyear" + ("" if scc == 0 else f"_scc{scc}")
    out = {}
    for ci in range(N_RGU):
        vals = []
        for yr in YEARS:
            p = os.path.join(CSV, folder, f"{ci}_{yr}__5homes_percentile__70roofcover__noelec.csv")
            if not os.path.exists(p):
                continue
            d = pd.read_csv(p)
            if metric == "cost":
                col = d["Cost"] - (scc / 1000.0) * d["Emissions"]   # retail-price cost
            else:
                col = d["Emissions"] / 1000.0                          # tCO2e
            vals.append(col.median())
        if len(vals) == len(YEARS):
            out[ci] = np.sum(vals) * LCA
    return pd.Series(out)


if FROM_SOURCE:
    print("Reading", SRC)
    sd = pd.read_csv(SRC)
    data = {}
    for m, tag, vcol in [("cost", "a", "ev_cost_retail_15yr_usd"), ("emis", "b", "ev_emissions_15yr_tco2e")]:
        for s in SCEN:
            for c in SCC:
                sel = sd[(sd["panel"] == tag) & (sd["strategy"] == s.upper()) & (sd["carbon_price_usd_per_tco2"] == c)]
                data[(m, s, c)] = pd.Series(sel[vcol].to_numpy(), index=sel["rgu"].to_numpy())
else:
    N_RGU = len(np.unique(pd.read_csv(CTY)["tempreg"]))
    data = {(m, s, c): level(s, c, m) for m in ["cost", "emis"] for s in SCEN for c in SCC}

    rows = []
    for (m, s, c), v in data.items():
        rows.append(dict(metric=m, strategy=s, scc=c, n=len(v), mean=v.mean(), p5=np.percentile(v, 5),
                         p95=np.percentile(v, 95), median=v.median()))
    summ = pd.DataFrame(rows)
    summ.to_csv(os.path.join(OUT, "scc_box_summary.csv"), index=False)
    print(summ.round(2).to_string(index=False))
    # UC charging ignores the SCC: its SCC $204 and $0 levels should agree to rounding
    for m in ["cost", "emis"]:
        a, b = data[(m, "uc", 0)], data[(m, "uc", 204)]
        print(f"UC {m}: max |SCC204 - noSCC| across RGUs = {np.abs((b - a).dropna()).max():.3g}")

# ---------------------------------------------------------------- figure
BOX_GAP, GROUP_GAP = 0.42, 0.75
pos, centers = [], []
for g in range(3):
    base = 1 + g * (2 * BOX_GAP + GROUP_GAP)
    pos += [base + k * BOX_GAP for k in range(3)]
    centers.append(base + BOX_GAP)

fig, axes = plt.subplots(2, 1, figsize=(5.95, 5.2), sharex=True)
src = []   # source data: one row per plotted value
for ax, m, ylab, tag in [(axes[0], "cost", "15-yr EV-attributable cost\nat retail prices (USD)", "a"),
                         (axes[1], "emis", "15-yr EV-attributable\nemissions (tCO2e)", "b")]:
    boxes = [data[(m, s, c)].dropna().to_numpy() for s in SCEN for c in SCC]
    vcol = {"cost": "ev_cost_retail_15yr_usd", "emis": "ev_emissions_15yr_tco2e"}[m]
    for (s, c), vals in zip([(s, c) for s in SCEN for c in SCC], boxes):
        src.append(pd.DataFrame({"panel": tag, "strategy": s.upper(), "carbon_price_usd_per_tco2": c,
                                 "rgu": data[(m, s, c)].dropna().index.to_numpy(), vcol: vals}))
    ax.boxplot(boxes, positions=pos, widths=0.3,
               boxprops=dict(color="black", linewidth=0.8), whiskerprops=dict(color="black", linewidth=0.8),
               capprops=dict(color="black", linewidth=0.8), medianprops=dict(color="black", linewidth=1.0),
               flierprops=dict(marker=".", markersize=3, markerfacecolor="0.4", markeredgecolor="0.4", linestyle="none"))
    for g in range(1, 3):
        ax.axvline((pos[3 * g - 1] + pos[3 * g]) / 2, color="0.6", linestyle=":", linewidth=0.6)
    ax.axhline(0, color="black", linestyle="--", linewidth=0.6, zorder=0)
    ax.set_ylabel(ylab, fontsize=FS)
    ax.tick_params(axis="both", labelsize=FS)
    ax.text(-0.13, 1.02, tag, transform=ax.transAxes, fontsize=10, fontweight="bold", va="bottom")
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
axes[1].set_xticks(pos)
axes[1].set_xticklabels(["$0/t", "$51/t", "$204/t"] * 3, fontsize=FS)
axes[0].yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
for cx, name in zip(centers, ["UC", "CC", "V2H"]):
    axes[1].text(cx, -0.2, name, transform=axes[1].get_xaxis_transform(), ha="center", va="top",
                 fontsize=FS + 0.5, fontweight="bold")
fig.tight_layout(h_pad=1.2)
fig.subplots_adjust(bottom=0.13)
fig.savefig(os.path.join(OUT, "Fig_SI_SCC_box.pdf"))
fig.savefig(os.path.join(OUT, "Fig_SI_SCC_box.png"), dpi=300)
if not FROM_SOURCE:
    pd.concat(src, ignore_index=True).to_csv(os.path.join(OUT, "Fig_SI_SCC_box_source_data.csv"),
                                             index=False, encoding="utf-8")
print("saved", os.path.join(OUT, "Fig_SI_SCC_box.pdf"))
