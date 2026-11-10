"""Statistics for the SI battery degradation table (Table/degradation_table.tex, current-tariff rows).

For each battery (NMC 75Ah, NMC B1, NMC B2, LFP 250Ah) and charging strategy (UC, CC, V2H), the value of
an RGU is the second-highest total 15-year capacity loss (calendar + cycle) among the RGU's simulated
cases, in percent. Printed across RGUs: mean, 5th and 95th percentiles, median and number of RGUs; the
table reports mean (5th-95th percentile).
Also printed: the same statistics for the per-RGU differences V2H minus CC and V2H minus UC (percentage
points), the values drawn in Fig_degradation_box.

Input (relative to the project root):
    Ford_CC/DegradationAssessment_revision/Deginterm_pvev/   degradation results (scc and lmpdg runs skipped)
Output: printed only.

Run: PYTHONIOENCODING=utf-8 uv run --no-project --python 3.14 --with numpy==2.5.4 --with pandas==3.1.1
     python degradation_table_stats.py
"""
import os
import numpy as np
import pandas as pd

DEG_D = r'F:\University of Michigan Dropbox\Jiahui Chen\Ford_CC\DegradationAssessment_revision\Deginterm_pvev'

SCENS = ['UC', 'CC', 'V2H']
BATTERIES = ['75AhA', 'B1', 'B2', 'LFP']
BATT_NAMES = ['NMC 75Ah', 'NMC B1', 'NMC B2', 'LFP 250Ah']


def load_deg_battery(battery):
    """Return dict scenario -> {rgu_index: capacity loss in %} (second-highest case per RGU).

    Each file holds one RGU; rows 1 and 2 are calendar and cycle loss (fractions), one column per case.
    """
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


deg = {bt: load_deg_battery(bt) for bt in BATTERIES}

# Paired per-RGU differences, over the RGUs with results for both strategies
deltas_cc, deltas_uc = {}, {}
for bt in BATTERIES:
    dv2h, dcc, duc = deg[bt]['V2H'], deg[bt]['CC'], deg[bt]['UC']
    deltas_cc[bt] = np.array([dv2h[ci] - dcc[ci] for ci in sorted(set(dv2h) & set(dcc))])
    deltas_uc[bt] = np.array([dv2h[ci] - duc[ci] for ci in sorted(set(dv2h) & set(duc))])

print('=== Capacity loss after 15 years (%), second-highest case per RGU ===')
print(f'{"Battery":>12} {"Scenario":>6} {"Mean":>8} {"P5":>8} {"P95":>8} {"Median":>8} {"n":>5}')
for bt, btname in zip(BATTERIES, BATT_NAMES):
    for st in SCENS:
        vals = np.array(list(deg[bt][st].values()))
        if len(vals):
            print(f'{btname:>12} {st:>6} {np.mean(vals):>8.1f} {np.percentile(vals,5):>8.1f} '
                  f'{np.percentile(vals,95):>8.1f} {np.median(vals):>8.1f} {len(vals):>5}')

print('\n=== V2H minus reference strategy, per RGU (pp) ===')
print(f'{"Battery":>12} {"Delta":>8} {"Mean":>8} {"P5":>8} {"P95":>8} {"Median":>8} {"n":>5}')
for bt, btname in zip(BATTERIES, BATT_NAMES):
    for tag, arr in [('V2H-CC', deltas_cc[bt]), ('V2H-UC', deltas_uc[bt])]:
        if len(arr):
            print(f'{btname:>12} {tag:>8} {np.mean(arr):>8.2f} {np.percentile(arr,5):>8.2f} '
                  f'{np.percentile(arr,95):>8.2f} {np.median(arr):>8.2f} {len(arr):>5}')
