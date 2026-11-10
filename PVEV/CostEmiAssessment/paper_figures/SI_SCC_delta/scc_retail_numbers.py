"""Social cost of carbon (SCC) runs: separate the retail-price cost from the carbon charge.

The SCC runs add the carbon price to the hourly import and export prices
(analysis_UC_fullyear_125PVhhec_scc.py, lines 70, 93-94 and 207-216):
  carbon_arr [cents/kWh] = SRMER [kg/kWh] * SCC [$/t] / 10
  Cost_scc [$] = Cost_retail [$] + (SCC/1000 [$/kg]) * Emissions_scc [kg]
UC dispatch does not depend on SCC, so for UC
  Cost_scc - Cost_noscc == SCC/1000 * Emissions_scc   and   Emissions_scc == Emissions_noscc.

1. Identity: residuals of the equations above, row by row against the no-SCC run of the same strategy.
2. Paired changes of CC and V2H (SCC $51 and $204/t) relative to their no-SCC run: per (RGU, building_id,
   fname) pair, the 15-year change = 5 x sum of the 2024, 2030 and 2040 differences (pairs missing a year
   are dropped), then the median per RGU:
     dC_retail      retail-price cost change, Cost_scc - SCC/1000 * Emissions_scc - Cost_noscc [$]
     dC_billed      cost change including the carbon charge, Cost_scc - Cost_noscc [$]
     carbon_charge  SCC/1000 * Emissions_scc [$]
     dE             emissions change, Emissions_scc - Emissions_noscc [kg]
   Cross-RGU statistics of these medians, and the abatement cost dC_retail / -dE [$/t].
3. Per-RGU levels (5 x sum over years of the per-year median) of cost, retail-price cost and emissions.

Inputs (relative to the project root):
    PVEV/CostEmiAssessment/csv_trb_detailed/{uc,cc,v2h}_125PVhhec_fullyear{,_scc51,_scc204}/
        <rgu>_<year>__5homes_percentile__70roofcover__noelec.csv
    Ford_CC/2020_Gaz_counties_national_0728_tempreg.csv   (number of RGUs)

Writes next to this script: scc_per_rgu_medians.csv (the per-RGU medians of step 2, read by
make_fig_scc_delta.py) and scc_retail_numbers.json (all statistics; a summary is printed).
Run: uv run --no-project --python 3.14 --with pandas --with numpy python scc_retail_numbers.py
"""
import os, json
import numpy as np
import pandas as pd

OUT = os.path.dirname(os.path.abspath(__file__))
PV = r'F:\University of Michigan Dropbox\Jiahui Chen\PVEV'
CSV = os.path.join(PV, 'CostEmiAssessment', 'csv_trb_detailed')
CTY = r'F:\University of Michigan Dropbox\Jiahui Chen\Ford_CC\2020_Gaz_counties_national_0728_tempreg.csv'
YEARS = [2024, 2030, 2040]
LCA = 5
N_RGU = len(np.unique(pd.read_csv(CTY)['tempreg']))
SCCS = [51, 204]


def load_folder(folder):
    frames = []
    for ci in range(N_RGU):
        for yr in YEARS:
            p = os.path.join(CSV, folder, f'{ci}_{yr}__5homes_percentile__70roofcover__noelec.csv')
            if os.path.exists(p):
                d = pd.read_csv(p)
                d['ci'] = ci
                d['year'] = yr
                frames.append(d)
    df = pd.concat(frames, ignore_index=True)
    return df


cache = {}
def get(folder):
    if folder not in cache:
        cache[folder] = load_folder(folder)
    return cache[folder]


KEYS = ['ci', 'year', 'building_id', 'fname']
report = {'N_RGU_table': int(N_RGU)}

# ---------------------------------------------------------------- 1. identity
ident = {}
for scen in ['uc', 'cc', 'v2h']:
    base = get(f'{scen}_125PVhhec_fullyear')
    for scc in SCCS:
        s = get(f'{scen}_125PVhhec_fullyear_scc{scc}')
        m = s.merge(base, on=KEYS, suffixes=('_s', '_0'), how='inner')
        k = scc / 1000.0  # $/kg
        rec = {'rows_scc': int(len(s)), 'rows_noscc': int(len(base)), 'rows_matched': int(len(m))}
        # S (no-EV PV change) does not depend on dispatch -> identity for every strategy
        rS = (m['BaselineCost_s'] - m['BaselineCost_0']) - k * m['BaselineEmissions_s']
        rec['S_resid_maxabs_usd'] = float(rS.abs().max())
        rec['S_emis_diff_maxabs_kg'] = float((m['BaselineEmissions_s'] - m['BaselineEmissions_0']).abs().max())
        if scen == 'uc':
            r = (m['Cost_s'] - m['Cost_0']) - k * m['Emissions_s']
            rec['C_resid_maxabs_usd'] = float(r.abs().max())
            rec['C_emis_diff_maxabs_kg'] = float((m['Emissions_s'] - m['Emissions_0']).abs().max())
            rec['C_delta_median_usd_per_yr'] = float((m['Cost_s'] - m['Cost_0']).median())
            # units check: fit slope of Cost delta on Emissions_scc
            x, y = m['Emissions_s'].to_numpy(), (m['Cost_s'] - m['Cost_0']).to_numpy()
            rec['fitted_slope_usd_per_kg'] = float(np.dot(x, y) / np.dot(x, x))
            rec['expected_slope_usd_per_kg'] = k
        ident[f'{scen}_scc{scc}'] = rec
report['identity'] = ident

# ---------------------------------------------------------------- 2. paired deltas
def paired(scen, scc):
    s = get(f'{scen}_125PVhhec_fullyear_scc{scc}')
    b = get(f'{scen}_125PVhhec_fullyear')
    m = s.merge(b, on=KEYS, suffixes=('_s', '_0'), how='inner')
    k = scc / 1000.0
    m['dC_billed'] = m['Cost_s'] - m['Cost_0']                          # includes the carbon charge
    m['C_retail_s'] = m['Cost_s'] - k * m['Emissions_s']
    m['dC_retail'] = m['C_retail_s'] - m['Cost_0']                      # retail prices only
    m['dE'] = m['Emissions_s'] - m['Emissions_0']
    m['carbon_charge'] = k * m['Emissions_s']
    g = m.groupby(['ci', 'building_id', 'fname'])
    agg = g[['dC_billed', 'dC_retail', 'dE', 'carbon_charge']].sum() * LCA
    agg['n'] = g.size()
    agg = agg[agg['n'] == len(YEARS)]
    pair_counts = agg.groupby('ci').size()
    med = agg.groupby('ci')[['dC_billed', 'dC_retail', 'dE', 'carbon_charge']].median()
    return med, agg, pair_counts


def stats(a):
    a = np.asarray(a, float)
    return {'mean': float(a.mean()), 'median': float(np.median(a)),
            'p5': float(np.percentile(a, 5)), 'p95': float(np.percentile(a, 95)),
            'min': float(a.min()), 'max': float(a.max()), 'n': int(len(a))}


res = {}
per_rgu = []
for scen in ['cc', 'v2h']:
    for scc in SCCS:
        med, agg, pc = paired(scen, scc)
        key = f'{scen}_scc{scc}'
        r = {c: stats(med[c]) for c in ['dC_billed', 'dC_retail', 'dE', 'carbon_charge']}
        r['pairs_total'] = int(len(agg))
        r['pairs_per_rgu_min'] = int(pc.min())
        r['pairs_per_rgu_max'] = int(pc.max())
        r['share_rgu_retail_cost_up'] = float((med['dC_retail'] > 0).mean())
        r['share_rgu_emis_down'] = float((med['dE'] < 0).mean())
        r['share_pairs_retail_cost_neg'] = float((agg['dC_retail'] < 0).mean())
        r['pairs_retail_cost_min'] = float(agg['dC_retail'].min())
        # abatement cost, two definitions
        mc, me = med['dC_retail'].mean(), med['dE'].mean()
        r['abatement_ratio_of_means_usd_per_t'] = float(mc / (-me) * 1000.0)
        ok = med['dE'] < -100.0   # RGUs whose median pair cuts > 100 kg over 15 yr
        ratio = med.loc[ok, 'dC_retail'] / (-med.loc[ok, 'dE']) * 1000.0
        r['abatement_per_rgu_ratio_of_medians'] = stats(ratio)
        r['abatement_per_rgu_n_used'] = int(ok.sum())
        res[key] = r
        t = med.copy(); t['strategy'] = scen; t['scc'] = scc
        per_rgu.append(t.reset_index())
report['paired'] = res
pd.concat(per_rgu).to_csv(os.path.join(OUT, 'scc_per_rgu_medians.csv'), index=False)

# ---------------------------------------------------------------- 3. per-RGU levels
def level(folder, col):
    df = get(folder)
    by = df.groupby(['ci', 'year'])[col].median().groupby('ci')
    return by.sum() * LCA if col != 'SelfConsumption' else by.mean()

lv = {}
for scen in ['uc', 'cc', 'v2h']:
    lv[f'{scen}_noscc_Emissions'] = stats(level(f'{scen}_125PVhhec_fullyear', 'Emissions'))
    lv[f'{scen}_noscc_Cost'] = stats(level(f'{scen}_125PVhhec_fullyear', 'Cost'))
    for scc in SCCS:
        f = f'{scen}_125PVhhec_fullyear_scc{scc}'
        df = get(f).copy()
        df['Cost_retail'] = df['Cost'] - scc / 1000.0 * df['Emissions']
        cache[f + '#r'] = df
        lv[f'{scen}_scc{scc}_Cost_incl_carbon_charge'] = stats(level(f, 'Cost'))
        lv[f'{scen}_scc{scc}_Cost_retail'] = stats(level(f + '#r', 'Cost_retail'))
        lv[f'{scen}_scc{scc}_Emissions'] = stats(level(f, 'Emissions'))
report['levels'] = lv

with open(os.path.join(OUT, 'scc_retail_numbers.json'), 'w') as fh:
    json.dump(report, fh, indent=1)

# ---------------------------------------------------------------- print
print(json.dumps(report['identity'], indent=1))
for k, r in res.items():
    print(f'\n== {k}  pairs={r["pairs_total"]} per RGU {r["pairs_per_rgu_min"]}-{r["pairs_per_rgu_max"]}')
    for c in ['dC_billed', 'dC_retail', 'carbon_charge', 'dE']:
        s = r[c]
        print(f'  {c:14s} mean={s["mean"]:9.0f} med={s["median"]:9.0f} p5={s["p5"]:9.0f} p95={s["p95"]:9.0f} min={s["min"]:9.0f} max={s["max"]:9.0f} n={s["n"]}')
    print(f'  share RGU retail cost up={r["share_rgu_retail_cost_up"]:.3f}  share RGU emis down={r["share_rgu_emis_down"]:.3f}  share pairs retail<0={r["share_pairs_retail_cost_neg"]:.3f} (min {r["pairs_retail_cost_min"]:.0f})')
    a = r['abatement_per_rgu_ratio_of_medians']
    print(f'  abatement ratio of means = {r["abatement_ratio_of_means_usd_per_t"]:.0f} $/t;  per-RGU ratio (n={r["abatement_per_rgu_n_used"]}) mean={a["mean"]:.0f} med={a["median"]:.0f} p5={a["p5"]:.0f} p95={a["p95"]:.0f}')
print()
for k, s in lv.items():
    print(f'{k:42s} mean={s["mean"]:9.0f} p5={s["p5"]:9.0f} p95={s["p95"]:9.0f}')
