"""SI Fig_SI_degradation_box: 15-year EV battery capacity loss by charging strategy and chemistry.

Four panels (NMC 75Ah, NMC B1, NMC B2, LFP 250Ah), each with one box per strategy (UC, CC, V2H) under
current export tariffs. The value of an RGU is the second-highest total capacity loss (calendar + cycle)
among the RGU's simulated cases, in percent (a file with a single valid case gives that case). Each box
summarizes the per-RGU values; the y axis starts at 0.

Input (relative to the project root):
    Ford_CC/DegradationAssessment_revision/Deginterm_pvev/   degradation results (scc and lmpdg runs skipped)
Outputs, next to this script:
    Fig_SI_degradation_box.pdf, Fig_SI_degradation_box.png (300 dpi)   5.95 x 2.7 in, Arial, text 8.5-9 pt
    Fig_SI_degradation_box_source_data.csv                             one row per RGU per box

Run: PYTHONIOENCODING=utf-8 uv run --no-project --python 3.14 --with matplotlib==3.11.2 --with numpy==2.5.4
     --with pandas==3.1.1 python make_fig_si_degradation_box.py
Add --from-source-data to draw the figure from Fig_SI_degradation_box_source_data.csv instead of the degradation
results; the source-data file is then read, not written.
"""
import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

matplotlib.rcParams["axes.unicode_minus"] = False
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["font.family"] = "Arial"

OUT = os.path.dirname(os.path.abspath(__file__))
DEG_D = r"F:\University of Michigan Dropbox\Jiahui Chen\Ford_CC\DegradationAssessment_revision\Deginterm_pvev"
SCENS, BATTERIES = ["UC", "CC", "V2H"], ["75AhA", "B1", "B2", "LFP"]
BATT_NAMES = ["NMC 75Ah", "NMC B1", "NMC B2", "LFP 250Ah"]
FS = 8.5

SRC = os.path.join(OUT, "Fig_SI_degradation_box_source_data.csv")
FROM_SOURCE = "--from-source-data" in sys.argv[1:]

if FROM_SOURCE:
    # Restore the order the results are read in (directory listing of <rgu>_80Y82_..., i.e. RGU sorted as
    # text): it sets the drawing order of overlapping outlier dots
    print("Reading", SRC)
    src = pd.read_csv(SRC)
    deg = {}
    for bt in BATTERIES:
        for st in SCENS:
            sel = src[(src["battery_file_tag"] == bt) & (src["strategy"] == st)]
            sel = sel.sort_values("rgu_index", key=lambda r: r.astype(str) + "_")
            deg[(st, bt)] = pd.Series(sel["capacity_loss_pct"].to_numpy(), index=sel["rgu_index"].to_numpy())
else:
    # Per-RGU capacity loss (%): file rows 1 and 2 are calendar and cycle loss (fractions), one column per case
    files = [f for f in os.listdir(DEG_D) if f.endswith(".csv")]
    deg = {}
    for bt in BATTERIES:
        for st in SCENS:
            d = {}
            for f in files:
                if f"_{st}_" in f and f"_{bt}_" in f and "scc" not in f and "lmpdg" not in f:
                    ci = int(f.split("_")[0])
                    df = pd.read_csv(os.path.join(DEG_D, f))
                    total = df.iloc[1].to_numpy(dtype=float) + df.iloc[2].to_numpy(dtype=float)
                    valid = total[~np.isnan(total)]
                    if len(valid) >= 2:
                        d[ci] = np.sort(valid)[-2] * 100
                    elif len(valid) == 1:
                        d[ci] = valid[0] * 100
            deg[(st, bt)] = pd.Series(d)

fig, axes = plt.subplots(1, 4, figsize=(5.95, 2.7), sharey=True)
for ax, bt, nm in zip(axes, BATTERIES, BATT_NAMES):
    ax.boxplot([deg[(s, bt)].to_numpy() for s in SCENS], positions=[1, 2, 3], widths=0.6,
               boxprops=dict(color="black", linewidth=0.8), whiskerprops=dict(color="black", linewidth=0.8),
               capprops=dict(color="black", linewidth=0.8), medianprops=dict(color="black", linewidth=1.0),
               flierprops=dict(marker=".", markersize=3, markerfacecolor="0.4", markeredgecolor="0.4", linestyle="none"))
    ax.set_xticks([1, 2, 3])
    ax.set_xticklabels(SCENS, fontsize=FS)
    ax.tick_params(axis="both", labelsize=FS)
    ax.set_title(nm, fontsize=FS + 0.5, fontweight="bold")
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
# Source data: the values each box summarizes, one row per RGU per box (rows sorted by RGU within a box)
if not FROM_SOURCE:
    pd.concat([pd.DataFrame({"battery": nm, "battery_file_tag": bt, "strategy": s,
                             "rgu_index": deg[(s, bt)].sort_index().index,
                             "capacity_loss_pct": deg[(s, bt)].sort_index().to_numpy()})
               for bt, nm in zip(BATTERIES, BATT_NAMES) for s in SCENS], ignore_index=True).to_csv(
        os.path.join(OUT, "Fig_SI_degradation_box_source_data.csv"), index=False, encoding="utf-8")
axes[0].set_ylabel("Total capacity loss after 15 years (%)", fontsize=FS)
axes[0].set_ylim(bottom=0)
fig.tight_layout(w_pad=0.6)
fig.savefig(os.path.join(OUT, "Fig_SI_degradation_box.pdf"))
fig.savefig(os.path.join(OUT, "Fig_SI_degradation_box.png"), dpi=300)
print("saved", os.path.join(OUT, "Fig_SI_degradation_box.pdf"))
