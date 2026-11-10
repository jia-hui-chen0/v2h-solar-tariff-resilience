"""SI Figure: change in retail-price cost (a) and emissions (b) of CC and V2H when the dispatch includes a
social cost of carbon (SCC) of $51 or $204/tCO2, relative to the no-SCC run of the same strategy under
current DG compensation rules (Fig_SI_SCC_delta_box).

Paired method: for each (building_id, fname) pair, the 15-year change is 5 x the sum of the 2024, 2030 and
2040 differences; each box shows the 432 per-RGU medians of these changes (diamond = mean). The retail-price
cost of an SCC run excludes the carbon charge: Cost_scc - (SCC/1000 $/kg) * Emissions_scc.

Input: scc_per_rgu_medians.csv (columns dC_retail, dE), written by scc_retail_numbers.py in this folder.
Writes next to this script: Fig_SI_SCC_delta_box.{pdf,png} and Fig_SI_SCC_delta_box_source_data.csv
(the plotted per-RGU values).
Drawn at the printed width (5.95 in); smallest text 8 pt, Arial.
Run: uv run --no-project --python 3.14 --with matplotlib==3.11.2 --with pandas --with numpy python make_fig_scc_delta.py
Add --from-source-data to draw the figure from Fig_SI_SCC_delta_box_source_data.csv instead of
scc_per_rgu_medians.csv; the source-data file is then read, not written.
"""
import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MultipleLocator
from matplotlib.transforms import blended_transform_factory

OUT = os.path.dirname(os.path.abspath(__file__))
matplotlib.rcParams.update({
    'font.family': 'Arial', 'pdf.fonttype': 42, 'ps.fonttype': 42,
    'axes.unicode_minus': True, 'font.size': 8,
    'axes.linewidth': 0.6, 'xtick.major.width': 0.6, 'ytick.major.width': 0.6,
    'xtick.major.size': 2.5, 'ytick.major.size': 2.5,
})
FS = 8          # smallest printed size (figure is drawn at its printed width)
FS_T = 8.5      # panel titles
LABEL = {'cc': 'CC', 'v2h': 'V2H'}
W_IN = 5.95

SRC = os.path.join(OUT, 'Fig_SI_SCC_delta_box_source_data.csv')
FROM_SOURCE = '--from-source-data' in sys.argv[1:]

if FROM_SOURCE:
    # Rebuild the columns of scc_per_rgu_medians.csv that the figure uses; dE back in kg (panel b plots 1e-3 x dE)
    print('Reading', SRC)
    sd = pd.read_csv(SRC)
    key = ['strategy', 'carbon_price_usd_per_tco2', 'rgu']
    d = sd.loc[sd.panel == 'a', key + ['retail_cost_change_15yr_usd']].merge(
        sd.loc[sd.panel == 'b', key + ['emissions_change_15yr_tco2e']], on=key, how='left', validate='one_to_one')
    d = pd.DataFrame({'ci': d['rgu'], 'dC_retail': d['retail_cost_change_15yr_usd'],
                      'dE': d['emissions_change_15yr_tco2e'] / 1e-3, 'strategy': d['strategy'].str.lower(),
                      'scc': d['carbon_price_usd_per_tco2']})
else:
    d = pd.read_csv(os.path.join(OUT, 'scc_per_rgu_medians.csv'))
order = [('cc', 51), ('cc', 204), ('v2h', 51), ('v2h', 204)]
pos = [1.0, 1.6, 2.7, 3.3]

fig, axes = plt.subplots(1, 2, figsize=(W_IN, 2.75))
fig.subplots_adjust(left=0.105, right=0.985, top=0.885, bottom=0.18, wspace=0.42)

panels = [
    (axes[0], 'dC_retail', 'Retail-price cost change', 'USD per EV over 15 years', 'a', 1.0),
    (axes[1], 'dE', 'Emissions change', 'tCO2e per EV over 15 years', 'b', 1e-3),
]
src = []   # source data: one row per plotted value
for ax, col, title, ylab, letter, unit in panels:
    data = [unit * d.loc[(d.strategy == s) & (d.scc == c), col].to_numpy() for s, c in order]
    assert all(len(x) == 432 for x in data)
    vcol = {'dC_retail': 'retail_cost_change_15yr_usd', 'dE': 'emissions_change_15yr_tco2e'}[col]
    for (st, cp), vals in zip(order, data):
        src.append(pd.DataFrame({'panel': letter, 'strategy': LABEL[st], 'carbon_price_usd_per_tco2': cp,
                                 'rgu': d.loc[(d.strategy == st) & (d.scc == cp), 'ci'].to_numpy(), vcol: vals}))
    bp = ax.boxplot(data, positions=pos, widths=0.42, patch_artist=True, showmeans=True,
                    whis=1.5,
                    medianprops=dict(color='black', linewidth=0.9),
                    whiskerprops=dict(color='black', linewidth=0.6),
                    capprops=dict(color='black', linewidth=0.6),
                    boxprops=dict(edgecolor='black', linewidth=0.6),
                    flierprops=dict(marker='o', markersize=1.8, markerfacecolor='#555555',
                                    markeredgewidth=0, linestyle='none'),
                    meanprops=dict(marker='D', markersize=3.2, markerfacecolor='white',
                                   markeredgecolor='black', markeredgewidth=0.6))
    for patch in bp['boxes']:
        patch.set_facecolor('white')
    ax.axhline(0, color='black', linestyle='--', linewidth=0.6, zorder=0)
    ax.axvline(np.mean([pos[1], pos[2]]), color='0.6', linestyle=':', linewidth=0.6)
    ax.set_xlim(0.55, 3.75)
    ax.set_xticks(pos)
    ax.set_xticklabels(['\\$51/t' if c == 51 else '\\$204/t' for _, c in order], fontsize=FS)
    ax.tick_params(axis='both', labelsize=FS, pad=2)
    tr = blended_transform_factory(ax.transData, ax.transAxes)
    for s, x in [('cc', np.mean(pos[:2])), ('v2h', np.mean(pos[2:]))]:
        ax.text(x, -0.135, LABEL[s], transform=tr, ha='center', va='top',
                fontsize=FS, fontweight='bold')
    ax.set_title(title, fontsize=FS_T, pad=4)
    ax.set_ylabel(ylab, fontsize=FS)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v:,.0f}'.replace('-', '\u2212')))
    ax.text(-0.27, 1.07, letter, transform=ax.transAxes, fontsize=9, fontweight='bold',
            va='bottom', ha='left')
    for sp in ['top', 'right']:
        ax.spines[sp].set_visible(False)

axes[0].yaxis.set_major_locator(MultipleLocator(500))
axes[1].yaxis.set_major_locator(MultipleLocator(10))
axes[1].set_ylim(top=2)

for ext, kw in [('pdf', {}), ('png', {'dpi': 300})]:
    fig.savefig(os.path.join(OUT, f'Fig_SI_SCC_delta_box.{ext}'), **kw)
if not FROM_SOURCE:
    pd.concat(src, ignore_index=True).to_csv(os.path.join(OUT, 'Fig_SI_SCC_delta_box_source_data.csv'),
                                             index=False, encoding='utf-8')
print('saved')
