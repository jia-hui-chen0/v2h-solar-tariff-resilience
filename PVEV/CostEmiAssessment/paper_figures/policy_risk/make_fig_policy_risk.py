"""Main-text figure Fig_SelfConsumption_vs_PolicyRisk_NEMNEB: PV self-consumption vs the bill increase
from a switch to LMP export compensation, for RGUs currently under net energy metering (NEM, left) and
net energy billing (NEB, right). RGUs already on LMP export are not shown.

One point per RGU and strategy (PV-only without an EV, UC, CC, V2H):
  x = PV self-consumption ratio under the current tariff: mean over 2024/2030/2040 of the per-year
      median across homes (the statistic _paper_numbers.py reports); PV-only x from
      policy_risk_longdata.csv (see policy_risk_data.py)
  y = 15-year bill increase from the current tariff to LMP export, k$: per (building_id, fname) pair,
      5 x sum of the yearly differences, then the median per RGU (PV-only: BaselineCost;
      others: BaselineCost + Cost)
Diamonds mark the median x and median y across RGUs; shaded regions are the smallest hulls covering 90%
of RGUs. Drawn at the printed width (5.95 in), Arial 8 pt.

Writes Fig_SelfConsumption_vs_PolicyRisk_NEMNEB.{pdf,png} and the plotted values
(Fig_SelfConsumption_vs_PolicyRisk_NEMNEB_source_data.csv) next to this script.
Run: uv run --python 3.14 --with matplotlib==3.11.2 --with pandas --with numpy --with scipy
     python make_fig_policy_risk.py
Add --from-source-data to draw the figure from Fig_SelfConsumption_vs_PolicyRisk_NEMNEB_source_data.csv instead
of the csv_trb_detailed results; the source-data file is then read, not written.
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["axes.unicode_minus"] = False
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Polygon

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import policy_risk_data as prd  # noqa: E402

NAME = "Fig_SelfConsumption_vs_PolicyRisk_NEMNEB"
SRC = HERE / f"{NAME}_source_data.csv"
FROM_SOURCE = "--from-source-data" in sys.argv[1:]
FONT, COLORS, SHORT = prd.FONT, prd.COLORS, prd.SHORT_LABELS
W, H = 5.95, 3.15
LABEL_OFFSET = {"solar_only": (-6, -13), "uc": (6, 5), "cc": (6, 5), "v2h": (6, 5)}


def rgu_rows_median():
    rec = []
    for ci in range(prd.N_RGU):
        row = {"ci": ci, "tempreg": int(prd.uqlst[ci])}
        for tag, scen in prd.SCEN.items():
            tot, bas, sc, ok = [], [], [], True
            for yr in prd.YEARS:
                pc = prd.CSV / scen / prd.FN.format(ci=ci, yr=yr)
                pl = prd.CSV / f"{scen}_lmpdg" / prd.FN.format(ci=ci, yr=yr)
                if not (pc.exists() and pl.exists()):
                    ok = False
                    break
                dc, dl = pd.read_csv(pc), pd.read_csv(pl)
                m = dc.merge(dl, on=["building_id", "fname"], suffixes=("_cur", "_lmp"))
                tot.append(((m.BaselineCost_lmp + m.Cost_lmp) - (m.BaselineCost_cur + m.Cost_cur)).to_numpy())
                bas.append((m.BaselineCost_lmp - m.BaselineCost_cur).to_numpy())
                sc.append(dc["SelfConsumption"].median())
            if not ok:
                continue
            row[f"y_{tag}"] = float(np.median(np.sum(np.vstack(tot), axis=0) * prd.LCA)) / 1000
            row[f"x_{tag}"] = float(np.mean(sc))
            if tag == "uc":
                row["y_solar_only"] = float(np.median(np.sum(np.vstack(bas), axis=0) * prd.LCA)) / 1000
        rec.append(row)
    return pd.DataFrame(rec)


def panel(ax, sub, title, ylim, show_ylabel):
    ax.set_xlim(0.25, 1.0)
    ax.set_ylim(*ylim)
    ax.grid(axis="y", color="#d9d9d9", linewidth=0.45)
    ax.axhline(0, color="#727272", ls=(0, (3, 2)), lw=0.7, zorder=0)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    for tag in ["solar_only", "uc", "cc", "v2h"]:
        pts = sub[[f"x_{tag}", f"y_{tag}"]].dropna().to_numpy()
        if len(pts) < 10:
            continue
        _, verts = prd.minimum_area_fraction_hull(pts, keep_fraction=0.90)
        ax.add_patch(Polygon(verts, closed=True, facecolor=COLORS[tag], edgecolor=COLORS[tag],
                             linewidth=0.9, alpha=0.08 if tag == "solar_only" else 0.14, zorder=1))
        ax.scatter(pts[:, 0], pts[:, 1], s=3, alpha=0.4, c=COLORS[tag], edgecolors="none", zorder=2)
        mx, my = np.median(pts, axis=0)
        ax.scatter([mx], [my], s=26, marker="D", c=COLORS[tag], edgecolors="white", linewidths=0.7, zorder=4)
        ax.annotate(SHORT[tag], (mx, my), xytext=LABEL_OFFSET[tag], textcoords="offset points",
                    ha="right" if tag == "solar_only" else "left", fontfamily=FONT, fontsize=8,
                    fontweight="bold", color="black", zorder=5,
                    bbox=dict(boxstyle="round,pad=0.15", facecolor="white", edgecolor=COLORS[tag], lw=0.6))
    ax.set_title(f"{title} (n = {len(sub)})", fontfamily=FONT, fontsize=8.5, loc="left")
    ax.set_xlabel("PV self-consumption ratio", fontfamily=FONT, fontsize=8)
    if show_ylabel:
        ax.set_ylabel("15-yr bill increase, current → LMP (k\\$)", fontfamily=FONT, fontsize=8)
    for lab in ax.get_xticklabels() + ax.get_yticklabels():
        lab.set_fontfamily(FONT)
        lab.set_fontsize(8)


def main():
    if FROM_SOURCE:
        print("Reading", SRC)
        src = pd.read_csv(SRC)
        parts = []
        for t, title in [("NEM", "Net energy metering"), ("NEB", "Net energy billing")]:
            s = src[src.panel == title]
            wide = None
            for tag in ["solar_only", "uc", "cc", "v2h"]:
                pts = s[s.strategy == SHORT[tag]][["rgu", "tempreg", "pv_self_consumption_ratio",
                                                   "bill_increase_current_to_lmp_15yr_kusd"]]
                pts.columns = ["ci", "tempreg", f"x_{tag}", f"y_{tag}"]
                wide = pts if wide is None else wide.merge(pts, on=["ci", "tempreg"], how="outer")
            wide["tariff"] = t
            parts.append(wide.sort_values("ci"))   # RGU order within a panel, as in the per-RGU table
        plot = pd.concat(parts, ignore_index=True)
    else:
        df = rgu_rows_median()
        df["tariff"] = df["tempreg"].map(prd.tariff_class())
        df = prd.attach_pv_only_x(df)
        plot = df[df["tariff"].isin(["NEM", "NEB"])]
    ys = plot[[f"y_{t}" for t in ["solar_only", "uc", "cc", "v2h"]]].to_numpy().ravel()
    ys = ys[np.isfinite(ys)]
    ylim = (min(-1.5, float(np.floor(ys.min()))), float(np.ceil(ys.max())))

    if not FROM_SOURCE:
        # Source data: one row per plotted point (same selection as panel()).
        rows = []
        for t, title in [("NEM", "Net energy metering"), ("NEB", "Net energy billing")]:
            s = plot[plot.tariff == t]
            for tag in ["solar_only", "uc", "cc", "v2h"]:
                pts = s[["ci", "tempreg", f"x_{tag}", f"y_{tag}"]].dropna()
                if len(pts) < 10:
                    continue
                rows.append(pd.DataFrame({"panel": title, "strategy": SHORT[tag], "rgu": pts["ci"],
                                          "tempreg": pts["tempreg"],
                                          "pv_self_consumption_ratio": pts[f"x_{tag}"],
                                          "bill_increase_current_to_lmp_15yr_kusd": pts[f"y_{tag}"]}))
        pd.concat(rows).to_csv(HERE / f"{NAME}_source_data.csv", index=False)

    fig, axes = plt.subplots(1, 2, figsize=(W, H), sharey=True)
    panel(axes[0], plot[plot.tariff == "NEM"], "Net energy metering", ylim, True)
    panel(axes[1], plot[plot.tariff == "NEB"], "Net energy billing", ylim, False)
    fig.tight_layout(w_pad=1.0)
    for ext in ["pdf", "png"]:
        fig.savefig(HERE / f"{NAME}.{ext}", dpi=300 if ext == "png" else 150)
        print("saved", HERE / f"{NAME}.{ext}")
    plt.close(fig)

    print("counts:", plot["tariff"].value_counts().to_dict(), "| ylim:", ylim)
    for t in ["NEM", "NEB"]:
        s = plot[plot.tariff == t]
        print(t, "diamonds (median x, median y):",
              {k: (round(s[f"x_{k}"].median(), 3), round(s[f"y_{k}"].median(), 2)) for k in ["solar_only", "uc", "cc", "v2h"]})


if __name__ == "__main__":
    main()
