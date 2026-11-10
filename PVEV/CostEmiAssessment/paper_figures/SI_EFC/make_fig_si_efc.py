"""SI Figure: annual equivalent full cycles of the EV battery (Fig_SI_EFC_box).

EFC per home and driving profile = (slowCR + fastCR [+ scneg]) / 82 kWh over 2024.
Per-RGU value = median over the five homes x five driving profiles (UC: over the five
driving profiles of Results_80_82_rev, which has no home or year dimension).

Inputs (dispatch results, 2024):
    UC  : Ford_CC/Results/Results_80_82_rev            (same charging with or without PV)
    CC  : SimulationResults/Result_cc_125PVhhec_fullyear
    V2H : SimulationResults/Result_v2h_125PVhhec_fullyear

Writes Fig_SI_EFC_box.{pdf,png} and Fig_SI_EFC_box_source_data.csv (the per-RGU values) next to this script.
Typography: drawn at the 5.95 in \\columnwidth; include with width=\\columnwidth.
Smallest printed text 8 pt (box-element note); all other text 9 pt; Arial.
Run: uv run --python 3.14 --with matplotlib==3.11.2 --with pandas --with numpy python make_fig_si_efc.py
Add --from-source-data to draw the figure from Fig_SI_EFC_box_source_data.csv instead of the dispatch
results; the source-data file is then read, not written.
"""
import os
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))

matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['pdf.fonttype'] = 42
matplotlib.rcParams['font.family'] = 'Arial'

ROOTS = [  # (PVEV root, Ford_CC root)
    (r'F:\University of Michigan Dropbox\Jiahui Chen\PVEV', r'F:\University of Michigan Dropbox\Jiahui Chen\Ford_CC'),
    (r'C:\Users\jiahuic\University of Michigan Dropbox\Jiahui Chen\PVEV', r'C:\Users\jiahuic\University of Michigan Dropbox\Jiahui Chen\Ford_CC'),
]
OUT = HERE
SRC = os.path.join(OUT, 'Fig_SI_EFC_box_source_data.csv')
FROM_SOURCE = '--from-source-data' in sys.argv[1:]

homesim, cover = '_5homes_percentile', '_70roofcover'
EV_CONFIGS = ['0', '10', '11', '12', '13']
FLIER = dict(marker='.', markersize=4, linestyle='none')
KEYS = ['UC', 'CC', 'V2H']

FIG_W_IN = 5.95
FIG_H_IN = 3.0
FS = 9
FS_NOTE = 8


def _read_efc(base_path, ev_configs):
    vals = []
    if not os.path.exists(base_path): return vals
    files = os.listdir(base_path)
    bldgs = sorted(set(f.split('_')[0] for f in files if f.split('_')[0].isdigit()))
    if not bldgs: return vals
    for bldg in bldgs:
        for evc in ev_configs:
            fpath = os.path.join(base_path, f'{bldg}_0_0_0_{evc}_0_50.csv')
            if os.path.exists(fpath):
                df = pd.read_csv(fpath)
                vals.append((df['slowCR'].sum() + df['fastCR'].sum() + df['scneg'].sum()) / 82)
    return vals


def compute(ROOT, FORD):
    """Per-RGU EFC for each strategy; returns {strategy: [values]}, {strategy: [RGU ids]}."""
    SIM = os.path.join(ROOT, 'SimulationResults')
    efc_data = {k: [] for k in KEYS}
    efc_rgu = {k: [] for k in KEYS}
    for ci in range(432):
        uc_vals = []
        base_uc = os.path.join(FORD, 'Results', 'Results_80_82_rev', str(ci))
        for evc in EV_CONFIGS:
            fpath = os.path.join(base_uc, f'0_0_0_{evc}_0_soc.csv')
            if os.path.exists(fpath):
                df = pd.read_csv(fpath)
                uc_vals.append((df['slowCR'].sum() + df['fastCR'].sum()) / 82)
        if uc_vals:
            efc_data['UC'].append(np.median(uc_vals))
            efc_rgu['UC'].append(ci)
        for key, scen_dir in [('CC', 'cc'), ('V2H', 'v2h')]:
            base = os.path.join(SIM, f'Result_{scen_dir}_125PVhhec_fullyear',
                                f'Results_80_Y82_noelec{homesim}{cover}2024', f'{ci}_1_0')
            vals = _read_efc(base, EV_CONFIGS)
            if vals:
                efc_data[key].append(np.median(vals))
                efc_rgu[key].append(ci)
    return efc_data, efc_rgu


def find_roots():
    for ROOT, FORD in ROOTS:
        if (os.path.isdir(os.path.join(FORD, 'Results', 'Results_80_82_rev'))
                and os.path.isdir(os.path.join(ROOT, 'SimulationResults'))):
            return ROOT, FORD
    sys.exit('Dispatch results not found; set ROOTS to your PVEV and Ford_CC folders.')


def main():
    if FROM_SOURCE:
        print('Reading', SRC)
        src = pd.read_csv(SRC)
        data_list = [src.loc[src['strategy'] == k, 'annual_equivalent_full_cycles'].to_numpy() for k in KEYS]
    else:
        efc_data, efc_rgu = compute(*find_roots())
        data_list = [np.array(efc_data[k]) for k in KEYS]
        pd.DataFrame([dict(strategy=k, rgu=ci, annual_equivalent_full_cycles=v)
                      for k in KEYS for ci, v in zip(efc_rgu[k], efc_data[k])]
                     ).to_csv(os.path.join(OUT, 'Fig_SI_EFC_box_source_data.csv'), index=False)
    n_per_box = {k: len(v) for k, v in zip(KEYS, data_list)}
    n_note = max(n_per_box.values())
    n_txt = str(n_note) if len(set(n_per_box.values())) == 1 else f'{min(n_per_box.values())}\u2013{n_note}'
    for k, v in zip(KEYS, data_list):
        print(f'  {k:4s} n={len(v)}  median={np.median(v):.3f}  q1={np.percentile(v, 25):.3f}  q3={np.percentile(v, 75):.3f}')

    fig, ax = plt.subplots(1, 1, figsize=(FIG_W_IN, FIG_H_IN), layout='constrained')
    positions = [1, 2.2, 3.4]
    colors = ['white', 'white', 'white']
    labels = ['Uncontrolled\ncharging (UC)', 'Controlled\ncharging (CC)', 'Vehicle-to-\nhome (V2H)']
    widths, alpha = 0.6, 1.0
    bp = ax.boxplot(data_list, positions=positions, widths=widths, flierprops=FLIER, patch_artist=True,
                    medianprops=dict(color='black', linewidth=1.2))
    for patch, c in zip(bp['boxes'], colors):
        patch.set_facecolor(c)
        patch.set_alpha(alpha)
    ax.set_ylim(bottom=0)          # cycles are non-negative; axis starts at zero
    ax.set_xlim(positions[0] - 0.6, positions[-1] + 0.6)
    ax.set_xticks(positions)
    ax.set_xticklabels(labels, fontsize=FS)
    ax.set_ylabel('Annual equivalent full cycles', fontsize=FS)
    ax.tick_params(axis='both', labelsize=FS)
    ax.text(0.015, 0.975,
            f'Total number of RGUs n = {n_txt}\n\nBox plot elements:\n'
            f'\u2022 Box: 25th to 75th percentile (interquartile range)\n'
            f'\u2022 Center line: Median (50th percentile)\n'
            f'\u2022 Whiskers: Extend to most extreme data points within 1.5\u00d7IQR\n'
            f'\u2022 Dots: Outliers beyond whisker limits',
            transform=ax.transAxes, fontsize=FS_NOTE, va='top', ha='left',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8, edgecolor='gray'))

    pdf = os.path.join(OUT, 'Fig_SI_EFC_box.pdf')
    png = os.path.join(OUT, 'Fig_SI_EFC_box.png')
    fig.savefig(pdf)            # no bbox_inches='tight': page stays exactly 5.95 in wide
    fig.savefig(png, dpi=300)
    plt.close(fig)
    print('saved', pdf)
    print('saved', png)


if __name__ == '__main__':
    main()
