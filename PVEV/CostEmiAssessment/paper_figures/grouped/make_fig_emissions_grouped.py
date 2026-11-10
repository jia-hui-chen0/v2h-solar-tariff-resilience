"""Fig_Emissions_grouped: change in 15-year household CO2 emissions from adding an EV, rooftop PV or both.

Panel (a), total emissions change relative to the same home with no EV and no PV; four clusters:
    EV-only (no PV)            UC, CC, V2H    E_EV
    PV-only                    one box        S (from the Current-rules run)
    EV+PV (Current), (LMP)     UC, CC, V2H    S + E
Panel (b), EV-attributable emissions change relative to the matched home without an EV:
    EV-only (no PV) E_EV, EV+PV (Current) E, EV+PV (LMP) E; UC, CC, V2H each.
UC, CC and V2H are uncontrolled charging, controlled charging and vehicle-to-home. Current is the
current DG export compensation and LMP the LMP-based export rate. Columns of csv_trb_detailed:
    E_EV  Emissions in {uc,cc,v2h}_EVbase_fullyear
    S     BaselineEmissions in uc_125PVhhec_fullyear[_lmpdg] (the same in the cc and v2h runs)
    E     Emissions in {uc,cc,v2h}_125PVhhec_fullyear[_lmpdg]

Value of an RGU: for each model year (2024, 2030, 2040), the median of the column (kg CO2) across the
RGU's rows (homes x driving profiles); the 15-year value is 5 x the sum of the three yearly medians,
divided by 1000 (metric tons CO2). S + E is the sum of the two per-RGU values. Each box shows the 432
per-RGU values (whiskers at 1.5 IQR, outliers as dots). The printed summary gives the median across RGUs
of each box and of the emissions of the home with no EV and no PV (BaselineEmissions in uc_EVbase_fullyear).

Inputs (relative to the project root):
    PVEV/CostEmiAssessment/csv_trb_detailed/{uc,cc,v2h}_EVbase_fullyear/ and
        {uc,cc,v2h}_125PVhhec_fullyear[_lmpdg]/<rgu>_<year>__5homes_percentile__70roofcover__noelec.csv
    Ford_CC/2020_Gaz_counties_national_0728_tempreg.csv   list of RGUs
Outputs, next to this script:
    Fig_Emissions_grouped.pdf, Fig_Emissions_grouped.png (300 dpi)   5.95 x 6.84 in, Arial, text 8.5-9 pt
    Fig_Emissions_grouped_source_data.csv                             one row per RGU per box
Page geometry, type scale and legend are shared with Fig_Bill_grouped through grouped_layout.py.

Run: PYTHONIOENCODING=utf-8 uv run --no-project --python 3.14 --with matplotlib==3.10.6 --with pandas==3.0.6
     --with numpy==2.5.4 python make_fig_emissions_grouped.py
Add --from-source-data to draw the figure from Fig_Emissions_grouped_source_data.csv instead of the
csv_trb_detailed results; the source-data file is then read, not written, and the printed summary omits the
no-EV no-PV emissions.
"""
import os, numpy as np, pandas as pd, matplotlib, matplotlib.pyplot as plt
matplotlib.use('Agg')
matplotlib.rcParams['axes.unicode_minus'] = False
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grouped_layout as GL  # shared geometry and type scale (sets rcParams: Arial, fonttype 42)

ROOT = r'F:\University of Michigan Dropbox\Jiahui Chen'
CSV_D = os.path.join(ROOT, 'PVEV', 'CostEmiAssessment', 'csv_trb_detailed')
FIGS = os.path.dirname(os.path.abspath(__file__))  # outputs go next to this script
FORD = os.path.join(ROOT, 'Ford_CC')
SRC = os.path.join(FIGS, 'Fig_Emissions_grouped_source_data.csv')
FROM_SOURCE = '--from-source-data' in sys.argv[1:]

# ── Style ────────────────────────────────────────────────────────────
FONTFAMILY = GL.FONTFAMILY
FS_PANEL_TITLE = GL.FS_PANEL_TITLE   # 9 pt, bold
FS_AXIS_LABEL = GL.FS_AXIS_LABEL     # 9 pt
FS_TICK = GL.FS_TICK                 # 8.5 pt
FS_SMALL = GL.FS_SMALL               # 8.5 pt
FLIER = dict(marker='.', markersize=3.0, linestyle='none', alpha=0.4)
MEDIANPROPS = dict(color='black', linewidth=0.8)

if not FROM_SOURCE:  # the RGU list is read only with the model results
    uqlst = np.unique(pd.read_csv(os.path.join(FORD, '2020_Gaz_counties_national_0728_tempreg.csv'))['tempreg'])
homesim, cover = '_5homes_percentile', '_70roofcover'
YEARS = [2024, 2030, 2040]
LCA = 5

# ── Okabe & Ito colorblind-safe palette ──────────────────────────────
C_UC   = '#D55E00'
C_CC   = '#E69F00'
C_V2H  = '#009E73'
C_PV   = '#999999'


def load_15yr(scen_dir, col='Emissions'):
    data = {}
    for ci in range(len(uqlst)):
        vals = []
        for yr in YEARS:
            fn = f'{ci}_{yr}__{homesim[1:]}__{cover[1:]}__noelec.csv'
            p = os.path.join(CSV_D, scen_dir, fn)
            if os.path.exists(p):
                df = pd.read_csv(p)
                vals.append(df[col].median())
        if len(vals) == len(YEARS):
            data[ci] = np.sum(vals) * LCA
    return data


# ═══════════════════════════════════════════════════════════════════════
# Load
# ═══════════════════════════════════════════════════════════════════════
if FROM_SOURCE:
    print('Reading', SRC)
    src = pd.read_csv(SRC)

    def _box(panel, case, policy, strategy):
        # one box of the source data (rows in RGU order), back in kg CO2: the plot divides by 1000
        sel = src[(src['panel'] == panel) & (src['case'] == case) & (src['policy'] == policy)
                  & (src['strategy'] == strategy)]
        return sel['emissions_change_15yr_tco2'].to_numpy() * 1000

    ev_d_uc, ev_d_cc, ev_d_v2h = (_box('a', 'EV-only', 'no PV', s) for s in ['UC', 'CC', 'V2H'])
    pv_cur_d = _box('a', 'PV-only', 'Current', 'no EV')
    evpv_cur_uc_d, evpv_cur_cc_d, evpv_cur_v2h_d = (_box('a', 'EV+PV', 'Current', s) for s in ['UC', 'CC', 'V2H'])
    evpv_lmp_uc_d, evpv_lmp_cc_d, evpv_lmp_v2h_d = (_box('a', 'EV+PV', 'LMP', s) for s in ['UC', 'CC', 'V2H'])

    def _arr(d, strat):
        return _box('b', 'EV+PV', 'LMP' if d == '_lmpdg' else 'Current', strat.upper())
else:
    print('Loading data...')
    house_bc = np.array(list(load_15yr('uc_EVbase_fullyear', 'BaselineEmissions').values()))

    # EV-only incremental emissions
    ev_d_uc  = np.array(list(load_15yr('uc_EVbase_fullyear', 'Emissions').values()))
    ev_d_cc  = np.array(list(load_15yr('cc_EVbase_fullyear', 'Emissions').values()))
    ev_d_v2h = np.array(list(load_15yr('v2h_EVbase_fullyear', 'Emissions').values()))

    # The PV-only change (BaselineEmissions of the 125PVhhec runs) is the same in the uc, cc and v2h runs;
    # the uc runs supply it for both the Current and LMP export cases.
    pv_cur_bc = np.array(list(load_15yr('uc_125PVhhec_fullyear', 'BaselineEmissions').values()))
    pv_lmp_bc = np.array(list(load_15yr('uc_125PVhhec_fullyear_lmpdg', 'BaselineEmissions').values()))
    pv_cur_d = pv_cur_bc
    pv_lmp_d = pv_lmp_bc

    def _arr(d, strat):
        return np.array(list(load_15yr(f'{strat}_125PVhhec_fullyear{d}', 'Emissions').values()))

    # PV BaselineEmissions is the change from the matched no-PV household.
    # EV+PV Emissions is the additional change from adding the EV after PV.
    evpv_cur_uc_d  = pv_cur_bc + _arr('', 'uc')
    evpv_cur_cc_d  = pv_cur_bc + _arr('', 'cc')
    evpv_cur_v2h_d = pv_cur_bc + _arr('', 'v2h')
    evpv_lmp_uc_d  = pv_lmp_bc + _arr('_lmpdg', 'uc')
    evpv_lmp_cc_d  = pv_lmp_bc + _arr('_lmpdg', 'cc')
    evpv_lmp_v2h_d = pv_lmp_bc + _arr('_lmpdg', 'v2h')


# ═══════════════════════════════════════════════════════════════════════
# Plot — Two panels: (a) Total emissions change, (b) EV emissions
# ═══════════════════════════════════════════════════════════════════════
print('Plotting...')

fig, ax1, ax2 = GL.make_figure(plt)  # fixed 5.95 in page, panels at shared positions

# ───────────────────────────────────────────────────────────────────────
# Panel (a): Total household emissions change
# ───────────────────────────────────────────────────────────────────────
box_counts_a = [3, 1, 3, 3]
BOX_GAP = 0.55
CLUSTER_GAP = 1.5

positions_a = []
cluster_centers_a = []
x = 1.0
for n in box_counts_a:
    for i in range(n):
        positions_a.append(x + i * BOX_GAP)
    cluster_centers_a.append(x + (n - 1) * BOX_GAP / 2)
    x += (n - 1) * BOX_GAP + CLUSTER_GAP

box_data_a = [
    ev_d_uc/1000, ev_d_cc/1000, ev_d_v2h/1000,
    pv_cur_d/1000,
    evpv_cur_uc_d/1000, evpv_cur_cc_d/1000, evpv_cur_v2h_d/1000,
    evpv_lmp_uc_d/1000, evpv_lmp_cc_d/1000, evpv_lmp_v2h_d/1000,
]
box_colors_a = [
    C_UC, C_CC, C_V2H,
    C_PV,
    C_UC, C_CC, C_V2H,
    C_UC, C_CC, C_V2H,
]

ax = ax1

bp = ax.boxplot(box_data_a, positions=positions_a, widths=0.42,
                flierprops=FLIER, patch_artist=True, medianprops=MEDIANPROPS)

for patch, c in zip(bp['boxes'], box_colors_a):
    patch.set_facecolor(c)
    patch.set_alpha(0.88)
    patch.set_linewidth(0.6)

# Separators
for i in [2, 3, 6]:
    sx = (positions_a[i] + positions_a[i+1]) / 2
    ax.axvline(x=sx, color='gray', linestyle='--', linewidth=0.6, alpha=0.5)

ax.axhline(y=0, color='black', linestyle='dashed', linewidth=0.7)
GL.set_y_major_locator(ax)

# X-axis ticks
xtick_labels_a = []
for n in box_counts_a:
    xtick_labels_a.extend(['UC', 'CC', 'V2H'] if n == 3 else ['\u2014'])
ax.set_xticks(positions_a)
ax.set_xticklabels(xtick_labels_a, fontfamily=FONTFAMILY, fontsize=FS_TICK)
ax.tick_params(axis='x', pad=4)

# Cluster labels below x-axis
cluster_names_a = [
    'EV-only\n(no PV)', 'PV-only',
    'EV+PV\n(Current)', 'EV+PV\n(LMP)',
]
trans = GL.cluster_label_transform(ax, fig)  # fixed point offset below the axis
for cx, name in zip(cluster_centers_a, cluster_names_a):
    ax.text(cx, 0, name, transform=trans, ha='center', va='top',
            fontfamily=FONTFAMILY, fontsize=FS_TICK, fontweight='bold')

# Y-axis
ax.set_ylabel('Change in 15-yr Household CO2 Emissions\n(metric tons, vs. no-EV no-PV baseline)',
              fontfamily=FONTFAMILY, fontsize=FS_AXIS_LABEL, labelpad=GL.YLABEL_PAD)
for label in ax.get_xticklabels() + ax.get_yticklabels():
    label.set_fontfamily(FONTFAMILY)
    label.set_fontsize(FS_TICK)
ax.grid(axis='y', alpha=0.12)

# Panel title
ax.set_title('(a) Total household emissions change, compared to a no EV, no PV scenario', fontfamily=FONTFAMILY,
             fontsize=FS_PANEL_TITLE, fontweight='bold', loc='left', pad=GL.TITLE_PAD)

# Text box (top-right)
n_rgus = len(ev_d_uc)
ax.text(0.98, 0.97,
    f'Total number of regions n={n_rgus}',
    transform=ax.transAxes, fontfamily=FONTFAMILY, fontsize=FS_SMALL,
    va='top', ha='right',
    bbox=dict(boxstyle='round,pad=0.4', facecolor='white', alpha=0.88, edgecolor='gray'))


# ───────────────────────────────────────────────────────────────────────
# Panel (b): EV charging emissions only
# ───────────────────────────────────────────────────────────────────────
box_counts_b = [3, 3, 3]
positions_b = []
cluster_centers_b = []
x = 1.0
for n in box_counts_b:
    for i in range(n):
        positions_b.append(x + i * BOX_GAP)
    cluster_centers_b.append(x + (n - 1) * BOX_GAP / 2)
    x += (n - 1) * BOX_GAP + CLUSTER_GAP

box_data_b = [
    ev_d_uc/1000, ev_d_cc/1000, ev_d_v2h/1000,
    _arr('', 'uc')/1000, _arr('', 'cc')/1000, _arr('', 'v2h')/1000,
    _arr('_lmpdg', 'uc')/1000, _arr('_lmpdg', 'cc')/1000, _arr('_lmpdg', 'v2h')/1000,
]
box_colors_b = [
    C_UC, C_CC, C_V2H,
    C_UC, C_CC, C_V2H,
    C_UC, C_CC, C_V2H,
]

ax = ax2

bp = ax.boxplot(box_data_b, positions=positions_b, widths=0.42,
                flierprops=FLIER, patch_artist=True, medianprops=MEDIANPROPS)

for patch, c in zip(bp['boxes'], box_colors_b):
    patch.set_facecolor(c)
    patch.set_alpha(0.88)
    patch.set_linewidth(0.6)

# Separators
for i in [2, 5]:
    sx = (positions_b[i] + positions_b[i+1]) / 2
    ax.axvline(x=sx, color='gray', linestyle='--', linewidth=0.6, alpha=0.5)

ax.axhline(y=0, color='black', linestyle='dashed', linewidth=0.7)
GL.set_y_major_locator(ax)

# X-axis ticks
xtick_labels_b = ['UC', 'CC', 'V2H'] * 3
ax.set_xticks(positions_b)
ax.set_xticklabels(xtick_labels_b, fontfamily=FONTFAMILY, fontsize=FS_TICK)
ax.tick_params(axis='x', pad=4)

# Cluster labels below x-axis
cluster_names_b = ['EV-only\n(no PV)', 'EV+PV\n(Current)', 'EV+PV\n(LMP)']
trans = GL.cluster_label_transform(ax, fig)
for cx, name in zip(cluster_centers_b, cluster_names_b):
    ax.text(cx, 0, name, transform=trans, ha='center', va='top',
            fontfamily=FONTFAMILY, fontsize=FS_TICK, fontweight='bold')

# Y-axis (three lines: as two lines the second would be longer than the 166-pt panel height)
ax.set_ylabel('15-yr EV-Attributable Emissions Change\n(metric tons CO2,\nvs. matched no-EV household)',
              fontfamily=FONTFAMILY, fontsize=FS_AXIS_LABEL, labelpad=GL.YLABEL_PAD)
for label in ax.get_xticklabels() + ax.get_yticklabels():
    label.set_fontfamily(FONTFAMILY)
    label.set_fontsize(FS_TICK)
ax.grid(axis='y', alpha=0.12)

# Panel title
ax.set_title('(b) EV-attributable emissions change', fontfamily=FONTFAMILY,
             fontsize=FS_PANEL_TITLE, fontweight='bold', loc='left', pad=GL.TITLE_PAD)

# Shared legend at figure bottom (2 x 2)
GL.add_legend(fig, C_UC, C_CC, C_V2H, C_PV)

fig.savefig(os.path.join(FIGS, 'Fig_Emissions_grouped.pdf'))            # no tight bbox: page stays 5.95 in wide
fig.savefig(os.path.join(FIGS, 'Fig_Emissions_grouped.png'), dpi=300)
plt.close(fig)
print('  Saved Fig_Emissions_grouped')

# ── Source data: every value passed to ax.boxplot above, one row per RGU ──
# load_15yr adds RGUs in loop order (ci) and skips any with a missing year; every array holds all
# len(uqlst) RGUs (asserted), so array position i is RGU ci = i (file prefix in csv_trb_detailed).
# The PV-only box (labeled 'PV-only') plots pv_cur_d, i.e. the Current-rules run.
if not FROM_SOURCE:
    S3 = ['UC', 'CC', 'V2H']
    src_boxes_a = ([('EV-only', 'no PV', s) for s in S3] + [('PV-only', 'Current', 'no EV')]
                   + [('EV+PV', p, s) for p in ('Current', 'LMP') for s in S3])
    src_boxes_b = [('EV-only', 'no PV', s) for s in S3] + [('EV+PV', p, s) for p in ('Current', 'LMP') for s in S3]
    src = []
    for panel, compared_to, boxes, box_data in [('a', 'no-EV no-PV baseline', src_boxes_a, box_data_a),
                                                 ('b', 'matched no-EV household', src_boxes_b, box_data_b)]:
        assert len(boxes) == len(box_data)
        for (case, policy, strategy), vals in zip(boxes, box_data):
            assert len(vals) == len(uqlst)
            for ci, v in enumerate(vals):
                src.append({'panel': panel, 'compared_to': compared_to, 'case': case, 'policy': policy,
                            'strategy': strategy, 'rgu': ci, 'emissions_change_15yr_tco2': v})
    pd.DataFrame(src).to_csv(os.path.join(FIGS, 'Fig_Emissions_grouped_source_data.csv'),
                             index=False, encoding='utf-8', lineterminator='\n')
    print(f'  Saved Fig_Emissions_grouped_source_data.csv ({len(src)} rows)')

# ── Summary ──────────────────────────────────────────────────────────
if not FROM_SOURCE:  # the no-EV no-PV emissions themselves are not plotted, so they are not in the source data
    h_t = np.median(house_bc) / 1000
    print(f'\nHouse baseline (no EV, no PV): {h_t:,.1f} metric tons')
print(f'\nChange vs. baseline (15-yr, metric tons):')
print(f'{"":>25}  {"UC":>10}  {"CC":>10}  {"V2H":>10}')
print(f'{"EV-only":>25}  {np.median(ev_d_uc)/1000:10,.1f}  {np.median(ev_d_cc)/1000:10,.1f}  {np.median(ev_d_v2h)/1000:10,.1f}')
print(f'{"PV-only":>25}  {np.median(pv_cur_d)/1000:10,.1f}')
print(f'{"EV+PV (Current)":>25}  {np.median(evpv_cur_uc_d)/1000:10,.1f}  {np.median(evpv_cur_cc_d)/1000:10,.1f}  {np.median(evpv_cur_v2h_d)/1000:10,.1f}')
print(f'{"EV+PV (LMP)":>25}  {np.median(evpv_lmp_uc_d)/1000:10,.1f}  {np.median(evpv_lmp_cc_d)/1000:10,.1f}  {np.median(evpv_lmp_v2h_d)/1000:10,.1f}')
print('\nDone.')
