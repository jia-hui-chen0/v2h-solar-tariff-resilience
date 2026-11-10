"""Fig_Bill_StrategyImpact and Fig_Emissions_StrategyImpact: paired 15-year change in the household
electricity bill (or CO2 emissions) from switching EV charging strategy.

One panel per figure, three clusters of three boxes:
    EV-only (no PV)      {uc,cc,v2h}_EVbase_fullyear
    EV+PV (Current)      {uc,cc,v2h}_125PVhhec_fullyear          current DG export compensation
    EV+PV (LMP)          {uc,cc,v2h}_125PVhhec_fullyear_lmpdg    LMP-based export rate
    boxes V2H-CC, CC-UC, V2H-UC (first strategy minus second)
UC, CC and V2H are uncontrolled charging, controlled charging and vehicle-to-home.

Value of an RGU: for each (building_id, fname) pair (home and driving profile) and model year (2024, 2030,
2040), the difference between the two strategies of BaselineCost + Cost (emissions: BaselineEmissions +
Emissions); the three yearly differences are summed and multiplied by 5 (15-year change), pairs missing a
year are dropped, and the RGU's value is the median over its pairs, in thousand USD (metric tons CO2).
Each box shows the 432 per-RGU values (whiskers at 1.5 IQR, outliers as dots). The median across RGUs of
each box is printed.

Inputs (relative to the project root):
    PVEV/CostEmiAssessment/csv_trb_detailed/<scenario>/<rgu>_<year>__5homes_percentile__70roofcover__noelec.csv
        for the nine scenario folders above
    Ford_CC/2020_Gaz_counties_national_0728_tempreg.csv   list of RGUs
Outputs, next to this script (for each figure):
    <figure>.pdf, <figure>.png (300 dpi)   5.95 x 3.33 in, Arial, text 8.5-9 pt
    <figure>_source_data.csv               one row per RGU per box

Run: PYTHONIOENCODING=utf-8 uv run --no-project --python 3.14 --with matplotlib==3.10.6 --with pandas==3.0.6
     --with numpy==2.5.3 python make_fig_strategy_impact.py [figure ...]
(draws both figures unless figure names are given).
Add --from-source-data to draw the figures from <figure>_source_data.csv instead of the csv_trb_detailed
results; the source-data files are then read, not written.
"""
import os
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
from matplotlib.transforms import offset_copy

matplotlib.rcParams['axes.unicode_minus'] = False          # ASCII hyphen-minus on negative tick labels
matplotlib.rcParams['pdf.fonttype'] = 42
matplotlib.rcParams['ps.fonttype'] = 42
matplotlib.rcParams['font.family'] = 'Arial'
matplotlib.rcParams['mathtext.fontset'] = 'custom'
matplotlib.rcParams['mathtext.rm'] = 'Arial'
matplotlib.rcParams['mathtext.it'] = 'Arial:italic'
matplotlib.rcParams['mathtext.bf'] = 'Arial:bold'

OUT = os.path.dirname(os.path.abspath(__file__))

ROOT = r'F:\University of Michigan Dropbox\Jiahui Chen'
CSV_D = os.path.join(ROOT, 'PVEV', 'CostEmiAssessment', 'csv_trb_detailed')
FORD = os.path.join(ROOT, 'Ford_CC')

FONTFAMILY = 'Arial'
# ---- page, axes rectangle and type scale ------------------------------------------------------
CLUSTER_DROP_PT = 1.92            # extra space between the tick labels and the cluster labels; the page
                                  # height and bottom margin include it, so the axes keep their size
W, H = 5.95, 3.30 + CLUSTER_DROP_PT / 72   # page size, inches (printed at 100%)
AX_L, AX_R, AX_B, AX_T = 0.70, 0.06, 0.66 + CLUSTER_DROP_PT / 72, 0.07   # axes margins, inches
FS_AXIS_LABEL = 9
FS_TICK = 8.5
FS_CLUSTER = 8.5                  # cluster labels: same size as ticks, bold
FS_SMALL = 8.5
CLUSTER_GAP_PT = 2.5 + CLUSTER_DROP_PT   # gap between bottom of tick labels and top of cluster labels
# ---- box style --------------------------------------------------------------------------------
FLIER = dict(marker='.', markersize=2.2, linestyle='none', alpha=0.3)
MEDIANPROPS = dict(color='black', linewidth=0.8)
C_DIFF = '#B3B3B3'

FROM_SOURCE = '--from-source-data' in sys.argv[1:]

if FROM_SOURCE:
    N_RGU = None      # set by build() from the source data: the number of RGUs in each box
else:
    ctdf = pd.read_csv(os.path.join(FORD, '2020_Gaz_counties_national_0728_tempreg.csv'))
    uqlst = np.unique(ctdf['tempreg'])
    N_RGU = len(uqlst)
homesim, cover = '_5homes_percentile', '_70roofcover'
YEARS = [2024, 2030, 2040]
LCA = 5


def _filename(ci, yr):
    return f'{ci}_{yr}__{homesim[1:]}__{cover[1:]}__noelec.csv'


def paired_15yr_diff(scen_a, scen_b, base_col, inc_col):
    """Per-RGU median of the paired 15-year difference scen_a - scen_b of base_col + inc_col.

    Rows of the two scenarios are paired on (building_id, fname); a pair's yearly differences are summed
    over YEARS and multiplied by LCA. Pairs missing a year are dropped. Returns {rgu: median}."""
    data = {}
    for ci in range(N_RGU):
        pairs = {}
        for yr in YEARS:
            fn = _filename(ci, yr)
            fa = os.path.join(CSV_D, scen_a, fn)
            fb = os.path.join(CSV_D, scen_b, fn)
            if not (os.path.exists(fa) and os.path.exists(fb)):
                continue
            merged = pd.read_csv(fa).merge(pd.read_csv(fb), on=['building_id', 'fname'], suffixes=('_a', '_b'))
            for _, row in merged.iterrows():
                key = (row['building_id'], row['fname'])
                total_a = row[f'{base_col}_a'] + row[f'{inc_col}_a']
                total_b = row[f'{base_col}_b'] + row[f'{inc_col}_b']
                pairs.setdefault(key, []).append(total_a - total_b)
        vals = [sum(v) * LCA for v in pairs.values() if len(v) == len(YEARS)]
        if vals:
            data[ci] = np.median(vals)
    return data


clusters = [
    ('EV-only\n(no PV)', 'EV-only (no PV)', {
        'UC': 'uc_EVbase_fullyear', 'CC': 'cc_EVbase_fullyear', 'V2H': 'v2h_EVbase_fullyear'}),
    ('EV+PV\n(Current)', 'EV+PV (Current)', {
        'UC': 'uc_125PVhhec_fullyear', 'CC': 'cc_125PVhhec_fullyear', 'V2H': 'v2h_125PVhhec_fullyear'}),
    ('EV+PV\n(LMP)', 'EV+PV (LMP)', {
        'UC': 'uc_125PVhhec_fullyear_lmpdg', 'CC': 'cc_125PVhhec_fullyear_lmpdg', 'V2H': 'v2h_125PVhhec_fullyear_lmpdg'}),
]
pairs = [
    ('V2H-CC', 'V2H', 'CC', C_DIFF),
    ('CC-UC', 'CC', 'UC', C_DIFF),
    ('V2H-UC', 'V2H', 'UC', C_DIFF),
]

FIGS = {
    'Fig_Bill_StrategyImpact': dict(
        base_col='BaselineCost', inc_col='Cost', ystep=5,
        ylabel='Change in 15-yr Household Electricity Bill\n(k$, paired strategy difference)'),
    'Fig_Emissions_StrategyImpact': dict(
        base_col='BaselineEmissions', inc_col='Emissions', ystep=10,
        ylabel='Change in 15-yr Household CO2 Emissions\n(metric tons, paired strategy difference)'),
}


def build(name, spec):
    global N_RGU
    SRC = os.path.join(OUT, f'{name}_source_data.csv')
    if FROM_SOURCE:
        print('Reading', SRC)
        src = pd.read_csv(SRC)
        value_col = src.columns[-1]       # paired_bill_change_15yr_kusd or paired_emissions_change_15yr_tco2
        N_RGU = src['rgu'].nunique()
        series = {}
        for _, cluster_label, _ in clusters:
            case, policy = cluster_label[:-1].split(' (')
            series[cluster_label] = {}
            for pair_label, _, _, _ in pairs:
                sel = src[(src['case'] == case) & (src['policy'] == policy) & (src['comparison'] == pair_label)]
                # {rgu: value} in RGU order, back in USD (kg CO2): box_data below divides by 1000
                series[cluster_label][pair_label] = dict(zip(sel['rgu'], sel[value_col].to_numpy() * 1000))
    else:
        print(f'{name}: computing paired strategy differences...')
        series = {}
        for _, cluster_label, dirs in clusters:
            series[cluster_label] = {}
            for pair_label, a, b, _ in pairs:
                d = paired_15yr_diff(dirs[a], dirs[b], spec['base_col'], spec['inc_col'])
                if len(d) != N_RGU:
                    raise RuntimeError(f'{cluster_label} {pair_label}: expected {N_RGU} RGUs, got {len(d)}')
                series[cluster_label][pair_label] = d

    box_data, box_colors, positions, cluster_centers, xtick_labels = [], [], [], [], []
    BOX_GAP = 0.55
    CLUSTER_GAP = 1.5
    x = 1.0
    for cluster_tick, cluster_label, _ in clusters:
        positions.extend([x, x + BOX_GAP, x + 2 * BOX_GAP])
        cluster_centers.append(x + BOX_GAP)
        for pair_label, _, _, color in pairs:
            box_data.append(np.array(list(series[cluster_label][pair_label].values())) / 1000)
            box_colors.append(color)
            xtick_labels.append(pair_label.replace('-', '-\n'))
        x += 2 * BOX_GAP + CLUSTER_GAP

    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([AX_L / W, AX_B / H, (W - AX_L - AX_R) / W, (H - AX_B - AX_T) / H])
    bp = ax.boxplot(box_data, positions=positions, widths=0.42,
                    flierprops=FLIER, patch_artist=True, medianprops=MEDIANPROPS)
    for patch, c in zip(bp['boxes'], box_colors):
        patch.set_facecolor(c)
        patch.set_alpha(0.88)
        patch.set_linewidth(0.6)

    for i in [2, 5]:
        sx = (positions[i] + positions[i + 1]) / 2
        ax.axvline(x=sx, color='gray', linestyle='--', linewidth=0.6, alpha=0.5)

    ax.axhline(y=0, color='black', linestyle='dashed', linewidth=0.7)
    ax.set_xticks(positions)
    ax.set_xticklabels(xtick_labels, fontfamily=FONTFAMILY, fontsize=FS_TICK)
    ax.tick_params(axis='x', pad=4)
    ax.yaxis.set_major_locator(MultipleLocator(spec['ystep']))

    ax.set_ylabel(spec['ylabel'], fontfamily=FONTFAMILY, fontsize=FS_AXIS_LABEL, labelpad=8)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontfamily(FONTFAMILY)
        label.set_fontsize(FS_TICK)
    # cluster labels: CLUSTER_GAP_PT below the measured bottom of the two-line tick labels
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    tick_bottom_px = min(t.get_window_extent(r).y0 for t in ax.get_xticklabels() if t.get_text())
    ax_bottom_px = ax.get_window_extent(r).y0
    drop_pt = (ax_bottom_px - tick_bottom_px) * 72 / fig.dpi + CLUSTER_GAP_PT
    trans = offset_copy(ax.get_xaxis_transform(), fig=fig, y=-drop_pt, units='points')
    for cx, (cluster_tick, _, _) in zip(cluster_centers, clusters):
        ax.text(cx, 0, cluster_tick, transform=trans, ha='center', va='top',
                fontfamily=FONTFAMILY, fontsize=FS_CLUSTER, fontweight='bold')

    ax.grid(axis='y', alpha=0.12)

    # Two lines, so the box stays inside the EV-only cluster, left of the first dashed separator,
    # and below the lowest EV-only values.
    ax.text(0.02, 0.04, f'Total number of regions\nn={N_RGU}',
            transform=ax.transAxes, fontfamily=FONTFAMILY, fontsize=FS_SMALL,
            va='bottom', ha='left',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='white', alpha=0.88, edgecolor='gray'))

    fig.savefig(os.path.join(OUT, f'{name}.pdf'))
    fig.savefig(os.path.join(OUT, f'{name}.png'), dpi=300)

    # source data: every value passed to ax.boxplot (per-RGU median of the paired 15-yr differences),
    # one row per RGU, walked in the same cluster x pair order that filled box_data; RGU ids are the
    # series keys (ci = file prefix in csv_trb_detailed). comparison 'V2H-CC' = V2H minus CC.
    if not FROM_SOURCE:
        value_col = {'Fig_Bill_StrategyImpact': 'paired_bill_change_15yr_kusd',
                     'Fig_Emissions_StrategyImpact': 'paired_emissions_change_15yr_tco2'}[name]
        src, k = [], 0
        for _, cluster_label, _ in clusters:
            case, policy = cluster_label[:-1].split(' (')
            for pair_label, _, _, _ in pairs:
                rgus = list(series[cluster_label][pair_label].keys())
                assert len(rgus) == len(box_data[k])
                for ci, v in zip(rgus, box_data[k]):
                    src.append({'case': case, 'policy': policy, 'comparison': pair_label, 'rgu': int(ci), value_col: v})
                k += 1
        assert k == len(box_data)
        pd.DataFrame(src).to_csv(os.path.join(OUT, f'{name}_source_data.csv'),
                                 index=False, encoding='utf-8', lineterminator='\n')
        print(f'  saved {name}_source_data.csv ({len(src)} rows)')
    plt.close(fig)
    for cluster_label, vals in series.items():
        print(f'  {cluster_label:18s} ' + '  '.join(
            f'{p}={np.median(np.array(list(vals[p].values())) / 1000):.2f}' for p, _, _, _ in pairs))
    print(f'  saved {name}.pdf/png')


if __name__ == '__main__':
    import sys
    only = [a for a in sys.argv[1:] if a != '--from-source-data'] or list(FIGS)
    for nm in only:
        build(nm, FIGS[nm])
