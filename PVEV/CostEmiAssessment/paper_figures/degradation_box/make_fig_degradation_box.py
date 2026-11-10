"""Main-text Fig_degradation_box: change in 15-year EV battery capacity loss from V2H.

One panel with four battery chemistries (NMC 75Ah, NMC B1, NMC B2, LFP 250Ah) and two boxes each:
V2H minus CC and V2H minus UC, in percentage points, under current export tariffs. The capacity loss of
an RGU under one strategy is the second-highest total loss (calendar + cycle) among the RGU's simulated
cases; the difference is taken per RGU, over the RGUs that have results for both strategies. Each box
summarizes these per-RGU differences (whiskers at 1.5 IQR, outliers as dots).

Input (relative to the project root):
    Ford_CC/DegradationAssessment_revision/Deginterm_pvev/   degradation results (scc and lmpdg runs skipped)
Outputs, next to this script:
    Fig_degradation_box.pdf, Fig_degradation_box.png (300 dpi)   5.95 x 3.4 in, Arial, text 8.5-9 pt
    Fig_degradation_box_source_data.csv                          one row per RGU per box

Run: PYTHONIOENCODING=utf-8 uv run --no-project --python 3.14 --with matplotlib==3.11.2 --with numpy==2.5.4
     --with pandas==3.1.1 python make_fig_degradation_box.py
Add --from-source-data to draw the figure from Fig_degradation_box_source_data.csv instead of the degradation
results; the source-data file is then read, not written.
"""
import os, sys, numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

matplotlib.rcParams['axes.unicode_minus'] = True           # negative tick labels use U+2212, like the x labels
matplotlib.rcParams['font.family'] = 'Arial'
matplotlib.rcParams['pdf.fonttype'] = 42
matplotlib.rcParams['ps.fonttype'] = 42
matplotlib.rcParams['mathtext.fontset'] = 'custom'
matplotlib.rcParams['mathtext.rm'] = 'Arial'
matplotlib.rcParams['mathtext.it'] = 'Arial:italic'
matplotlib.rcParams['mathtext.bf'] = 'Arial:bold'

# ── Paths ──────────────────────────────────────────────────────────────
ROOT = r'F:\University of Michigan Dropbox\Jiahui Chen'
FORD = os.path.join(ROOT, 'Ford_CC')
DEG_D = os.path.join(FORD, 'DegradationAssessment_revision', 'Deginterm_pvev')
OUT = os.path.dirname(os.path.abspath(__file__))

# ── Style constants ────────────────────────────────────────────────────
FONTFAMILY = 'Arial'
W, H = 5.95, 3.4              # printed size, inches
FS_PANEL_TITLE = 9            # title — bold
FS_AXIS_LABEL = 9             # Y-axis label
FS_TICK = 8.5                 # tick labels, cluster labels
FS_SMALL = 8.5                # text box
PAD_IN = 0.04                 # white margin around the drawn content

# Plain boxplot props — black lines, no fill
LINE        = dict(color='black', linewidth=0.8)
FLIERPROPS  = dict(marker='.', markersize=3.0, linestyle='none', markerfacecolor='gray',
                   markeredgecolor='gray', alpha=0.6)
BOX_WIDTH   = 0.35
CLUSTER_GAP = 1.3
BOX_GAP     = 0.55

# ── Load degradation data ──────────────────────────────────────────────
SCENS = ['UC', 'CC', 'V2H']
BATTERIES = ['75AhA', 'B1', 'B2', 'LFP']
BATT_NAMES = ['NMC 75Ah', 'NMC B1', 'NMC B2', 'LFP 250Ah']

def load_deg_battery(battery):
    """Return dict scenario -> {rgu_index: degradation_%} (2nd-worst per RGU)."""
    result = {}
    for st in SCENS:
        d = {}
        for f in os.listdir(DEG_D):
            if f'{st}' in f and f'{battery}' in f and 'scc' not in f and 'lmpdg' not in f:
                ci = int(f.split('_')[0])
                try:
                    df = pd.read_csv(os.path.join(DEG_D, f))
                    total = df.iloc[1].to_numpy() + df.iloc[2].to_numpy()
                    valid = total[~np.isnan(total)]
                    if len(valid) >= 2:
                        d[ci] = np.sort(valid)[-2] * 100  # fraction → percent
                except:
                    pass
        result[st] = d
    return result

SRC = os.path.join(OUT, 'Fig_degradation_box_source_data.csv')
FROM_SOURCE = '--from-source-data' in sys.argv[1:]

if FROM_SOURCE:
    print('Reading', SRC)
    src = pd.read_csv(SRC)
    box_data = []
    for bt in BATTERIES:
        for ref in ['CC', 'UC']:
            sel = src[(src['battery_file_tag'] == bt) & (src['reference_strategy'] == ref)]
            box_data.append(sel['delta_capacity_loss_pp'].to_numpy())
    n_rgus_max = max(src.loc[src['battery_file_tag'] == bt, 'rgu_index'].nunique() for bt in BATTERIES)
else:
    print('Loading degradation data...')
    deg = {}
    for bt in BATTERIES:
        deg[bt] = load_deg_battery(bt)

    deltas_cc, deltas_uc, n_rgus_per_battery = {}, {}, {}
    for bt in BATTERIES:
        dv2h = deg[bt]['V2H']
        dcc  = deg[bt]['CC']
        duc  = deg[bt]['UC']
        common_cc = sorted(set(dv2h.keys()) & set(dcc.keys()))
        common_uc = sorted(set(dv2h.keys()) & set(duc.keys()))
        deltas_cc[bt] = np.array([dv2h[ci] - dcc[ci] for ci in common_cc])
        deltas_uc[bt] = np.array([dv2h[ci] - duc[ci] for ci in common_uc])
        n_rgus_per_battery[bt] = len(set(dv2h.keys()) | set(dcc.keys()) | set(duc.keys()))
    n_rgus_max = max(n_rgus_per_battery.values())

    box_data = []
    for bt in BATTERIES:
        box_data.append(deltas_cc[bt])
        box_data.append(deltas_uc[bt])

    # ── Source data: the values in each box, one row per RGU per box (box_data order) ──
    rows = []
    for k, (bt, name) in enumerate(zip(BATTERIES, BATT_NAMES)):
        for j, ref in enumerate(['CC', 'UC']):
            ids = sorted(set(deg[bt]['V2H']) & set(deg[bt][ref]))       # the RGUs behind box_data[2*k + j]
            rows.append(pd.DataFrame({'battery': name, 'battery_file_tag': bt, 'reference_strategy': ref,
                                      'rgu_index': ids, 'delta_capacity_loss_pp': box_data[2 * k + j]}))
    pd.concat(rows, ignore_index=True).to_csv(SRC, index=False, encoding='utf-8')

positions, cluster_centers, x = [], [], 1.0
for n in [2, 2, 2, 2]:
    positions += [x + i * BOX_GAP for i in range(n)]
    cluster_centers.append(x + (n - 1) * BOX_GAP / 2)
    x += (n - 1) * BOX_GAP + CLUSTER_GAP

# ═══════════════════════════════════════════════════════════════════════
# Figure
# ═══════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(1, 1, figsize=(W, H))

ax.boxplot(box_data, positions=positions, widths=BOX_WIDTH,
           boxprops=LINE, whiskerprops=LINE, capprops=LINE, medianprops=LINE,
           flierprops=FLIERPROPS)

# Separators between battery clusters
for i in [1, 3, 5]:
    sx = (positions[i] + positions[i + 1]) / 2
    ax.axvline(x=sx, color='gray', linestyle='--', linewidth=0.6, alpha=0.5)

ax.axhline(y=0, color='black', linestyle='dashed', linewidth=0.7)

# X-axis ticks — delta labels
ax.set_xticks(positions)
ax.set_xticklabels(['\u2212CC', '\u2212UC'] * 4, fontfamily=FONTFAMILY, fontsize=FS_TICK)
ax.tick_params(axis='x', pad=4)

# Cluster labels (battery names) below the tick labels, a fixed distance in points under the axis
trans = ax.get_xaxis_transform()
for cx, name in zip(cluster_centers, BATT_NAMES):
    ax.annotate(name, xy=(cx, 0), xycoords=trans, xytext=(0, -22), textcoords='offset points',
                ha='center', va='top', fontfamily=FONTFAMILY, fontsize=FS_TICK, fontweight='bold',
                annotation_clip=False)

# Y-axis
ax.set_ylabel('\u0394 Capacity Loss (pp)\nV2H minus reference strategy',
              fontfamily=FONTFAMILY, fontsize=FS_AXIS_LABEL, labelpad=6)
ax.tick_params(axis='y', labelsize=FS_TICK)
for label in ax.get_yticklabels():
    label.set_fontfamily(FONTFAMILY)
ax.grid(axis='y', alpha=0.12)

ax.set_title('V2H degradation penalty', fontfamily=FONTFAMILY,
             fontsize=FS_PANEL_TITLE, fontweight='bold', loc='left', pad=7)

# Text box (top-left: the top-right corner sits on the LFP outliers)
ax.text(0.02, 0.97,
    f'Total number of regions n={n_rgus_max}',
    transform=ax.transAxes, fontfamily=FONTFAMILY, fontsize=FS_SMALL,
    va='top', ha='left',
    bbox=dict(boxstyle='round,pad=0.4', facecolor='white', alpha=0.88, edgecolor='gray'))

# ── Margins: fit the drawn content inside the fixed W x H page with PAD_IN on each side ──
fig.subplots_adjust(left=0.12, right=0.98, bottom=0.15, top=0.92)
for _ in range(6):
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    bb = fig.get_tightbbox(r)                       # inches, everything that is drawn
    sp = fig.subplotpars
    left = sp.left + (PAD_IN - bb.x0) / W
    right = sp.right + (W - PAD_IN - bb.x1) / W
    bottom = sp.bottom + (PAD_IN - bb.y0) / H
    top = sp.top + (H - PAD_IN - bb.y1) / H
    fig.subplots_adjust(left=left, right=right, bottom=bottom, top=top)

fig.savefig(os.path.join(OUT, 'Fig_degradation_box.pdf'))
fig.savefig(os.path.join(OUT, 'Fig_degradation_box.png'), dpi=300)
plt.close(fig)
print('saved', os.path.join(OUT, 'Fig_degradation_box.pdf'))
