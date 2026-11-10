"""Compute ALL paper numbers from fixed analysis CSVs using paired 15-year diffs."""
import os
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
DATA_ROOT = PROJECT_ROOT.parent
CSV = HERE / 'csv_trb_detailed'
homesim, cover = '_5homes_percentile', '_70roofcover'
YEARS = [2024, 2030, 2040]
LCA = 5

TEMPREG_CSV = DATA_ROOT / 'Ford_CC' / '2020_Gaz_counties_national_0728_tempreg.csv'
uqlst = np.unique(pd.read_csv(TEMPREG_CSV)['tempreg'])

def load_medians(scen_dir):
    """Per-RGU median of standalone stats (no pairing)."""
    data = {}
    for ci in range(len(uqlst)):
        costs, emis, bcosts, bemis, scs = [], [], [], [], []
        for yr in YEARS:
            p = os.path.join(CSV, scen_dir, f'{ci}_{yr}_{homesim}_{cover}__noelec.csv')
            if os.path.exists(p):
                df = pd.read_csv(p)
                costs.append(df['Cost'].median())
                emis.append(df['Emissions'].median())
                bcosts.append(df['BaselineCost'].median())
                bemis.append(df['BaselineEmissions'].median())
                scs.append(df['SelfConsumption'].median())
        if costs:
            data[ci] = {
                'Cost': sum(costs) * LCA,
                'Emissions': sum(emis) * LCA,
                'BaselineCost': sum(bcosts) * LCA,
                'BaselineEmissions': sum(bemis) * LCA,
                'SelfConsumption': np.mean(scs),
                'TotalCost': sum(bcosts) * LCA + sum(costs) * LCA,
            }
    return data

def paired_15yr_median(scen_a, scen_b, col_fn):
    """Per-RGU median of per-pair 15yr diffs = sum(yr_diffs) * LCA.
    
    col_fn(merged_row_with_suffixes_ab) returns per-year diff.
    """
    data = {}
    for ci in range(len(uqlst)):
        pairs = {}
        for yr in YEARS:
            fa = os.path.join(CSV, scen_a, f'{ci}_{yr}_{homesim}_{cover}__noelec.csv')
            fb = os.path.join(CSV, scen_b, f'{ci}_{yr}_{homesim}_{cover}__noelec.csv')
            if not (os.path.exists(fa) and os.path.exists(fb)):
                continue
            merged = pd.read_csv(fa).merge(pd.read_csv(fb), on=['building_id','fname'], suffixes=('_a','_b'))
            for _, row in merged.iterrows():
                key = (row['building_id'], row['fname'])
                pairs.setdefault(key, []).append(col_fn(row))
        vals = [sum(d) * LCA for d in pairs.values() if len(d) == len(YEARS)]
        if vals:
            data[ci] = np.median(vals)
    return data

def paired_15yr_pct(scen_a, scen_b, col_fn_num, col_fn_den):
    """Per-RGU median of per-pair 15yr pct = sum(num_yrs)/abs(sum(den_yrs))*100."""
    data = {}
    for ci in range(len(uqlst)):
        pairs = {}
        for yr in YEARS:
            fa = os.path.join(CSV, scen_a, f'{ci}_{yr}_{homesim}_{cover}__noelec.csv')
            fb = os.path.join(CSV, scen_b, f'{ci}_{yr}_{homesim}_{cover}__noelec.csv')
            if not (os.path.exists(fa) and os.path.exists(fb)):
                continue
            merged = pd.read_csv(fa).merge(pd.read_csv(fb), on=['building_id','fname'], suffixes=('_a','_b'))
            for _, row in merged.iterrows():
                key = (row['building_id'], row['fname'])
                pairs.setdefault(key, []).append((col_fn_num(row), col_fn_den(row)))
        pcts = []
        for yr_vals in pairs.values():
            if len(yr_vals) == len(YEARS):
                num = sum(v[0] for v in yr_vals) * LCA
                den = abs(sum(v[1] for v in yr_vals) * LCA)
                if den > 1:
                    pcts.append(num / den * 100)
        if pcts:
            data[ci] = np.median(pcts)
    return data

def paired_mitigation(scen_cur, scen_lmp):
    """Per-RGU median of per-pair (solar_d - ev_d) / solar_d * 100.
    
    solar_d = BaselineCost_lmp - BaselineCost_cur (no-EV baseline change)
    ev_d    = TotalCost_lmp - TotalCost_cur (EV scenario change)
    Both from the same scenario's cur/lmp CSVs.
    """
    data = {}
    for ci in range(len(uqlst)):
        pairs = {}
        for yr in YEARS:
            f_cur = os.path.join(CSV, scen_cur, f'{ci}_{yr}_{homesim}_{cover}__noelec.csv')
            f_lmp = os.path.join(CSV, scen_lmp, f'{ci}_{yr}_{homesim}_{cover}__noelec.csv')
            if not (os.path.exists(f_cur) and os.path.exists(f_lmp)):
                continue
            merged = pd.read_csv(f_cur).merge(pd.read_csv(f_lmp), on=['building_id','fname'], suffixes=('_cur','_lmp'))
            for _, row in merged.iterrows():
                key = (row['building_id'], row['fname'])
                solar_d_yr = row['BaselineCost_lmp'] - row['BaselineCost_cur']
                ev_d_yr = (row['BaselineCost_lmp'] + row['Cost_lmp']) - (row['BaselineCost_cur'] + row['Cost_cur'])
                pairs.setdefault(key, []).append((solar_d_yr, ev_d_yr))
        mit_vals = []
        for yr_vals in pairs.values():
            if len(yr_vals) == len(YEARS):
                solar_d = sum(v[0] for v in yr_vals) * LCA
                ev_d = sum(v[1] for v in yr_vals) * LCA
                if solar_d > 0:
                    mit_vals.append((solar_d - ev_d) / solar_d * 100)
        if mit_vals:
            data[ci] = np.median(mit_vals)
    return data

def stats(vals, fmt='auto'):
    arr = np.array(list(vals))
    if fmt == 'k':
        return f'mean={arr.mean()/1000:.1f}k, med={np.median(arr)/1000:.1f}k, p5={np.percentile(arr,5)/1000:.1f}k, p95={np.percentile(arr,95)/1000:.1f}k'
    elif fmt == 'pct':
        return f'mean={arr.mean():.0f}%, {np.percentile(arr,5):.0f}--{np.percentile(arr,95):.0f}%'
    else:
        return f'mean={arr.mean():.0f}, med={np.median(arr):.0f}, p5={np.percentile(arr,5):.0f}, p95={np.percentile(arr,95):.0f}'

# ═══════════════════════════════════════════════
# LOAD DATA
# ═══════════════════════════════════════════════

# Standalone medians (absolute levels)
uc_cur = load_medians('uc_125PVhhec_fullyear')
cc_cur = load_medians('cc_125PVhhec_fullyear')
v2h_cur = load_medians('v2h_125PVhhec_fullyear')
uc_lmp = load_medians('uc_125PVhhec_fullyear_lmpdg')
cc_lmp = load_medians('cc_125PVhhec_fullyear_lmpdg')
v2h_lmp = load_medians('v2h_125PVhhec_fullyear_lmpdg')

# Paired cost reductions: CC|V2H vs UC (negative = savings)
cc_v_uc_cur   = paired_15yr_median('cc_125PVhhec_fullyear',           'uc_125PVhhec_fullyear',           lambda r: r['Cost_a'] - r['Cost_b'])
v2h_v_uc_cur  = paired_15yr_median('v2h_125PVhhec_fullyear',          'uc_125PVhhec_fullyear',           lambda r: r['Cost_a'] - r['Cost_b'])
cc_v_uc_lmp   = paired_15yr_median('cc_125PVhhec_fullyear_lmpdg',     'uc_125PVhhec_fullyear_lmpdg',     lambda r: r['Cost_a'] - r['Cost_b'])
v2h_v_uc_lmp  = paired_15yr_median('v2h_125PVhhec_fullyear_lmpdg',    'uc_125PVhhec_fullyear_lmpdg',     lambda r: r['Cost_a'] - r['Cost_b'])

# Paired cost reduction percentages
# num = (Cost_uc - Cost_cc) = -(Cost_cc - Cost_uc), den = |Cost_uc|
cc_v_uc_pct_cur   = paired_15yr_pct('cc_125PVhhec_fullyear',       'uc_125PVhhec_fullyear',       lambda r: -(r['Cost_a'] - r['Cost_b']), lambda r: r['Cost_b'])
v2h_v_uc_pct_cur  = paired_15yr_pct('v2h_125PVhhec_fullyear',      'uc_125PVhhec_fullyear',       lambda r: -(r['Cost_a'] - r['Cost_b']), lambda r: r['Cost_b'])
cc_v_uc_pct_lmp   = paired_15yr_pct('cc_125PVhhec_fullyear_lmpdg', 'uc_125PVhhec_fullyear_lmpdg', lambda r: -(r['Cost_a'] - r['Cost_b']), lambda r: r['Cost_b'])
v2h_v_uc_pct_lmp  = paired_15yr_pct('v2h_125PVhhec_fullyear_lmpdg','uc_125PVhhec_fullyear_lmpdg', lambda r: -(r['Cost_a'] - r['Cost_b']), lambda r: r['Cost_b'])

# Paired emission reductions: CC|V2H vs UC
cc_v_uc_emis_cur   = paired_15yr_median('cc_125PVhhec_fullyear',      'uc_125PVhhec_fullyear',      lambda r: r['Emissions_a'] - r['Emissions_b'])
v2h_v_uc_emis_cur  = paired_15yr_median('v2h_125PVhhec_fullyear',     'uc_125PVhhec_fullyear',      lambda r: r['Emissions_a'] - r['Emissions_b'])
cc_v_uc_emis_lmp   = paired_15yr_median('cc_125PVhhec_fullyear_lmpdg','uc_125PVhhec_fullyear_lmpdg',lambda r: r['Emissions_a'] - r['Emissions_b'])
v2h_v_uc_emis_lmp  = paired_15yr_median('v2h_125PVhhec_fullyear_lmpdg','uc_125PVhhec_fullyear_lmpdg',lambda r: r['Emissions_a'] - r['Emissions_b'])

# Paired emission reduction percentages
# num = (Emis_uc - Emis_cc) = -(Emis_cc - Emis_uc)
cc_v_uc_emis_pct_cur  = paired_15yr_pct('cc_125PVhhec_fullyear',       'uc_125PVhhec_fullyear',       lambda r: -(r['Emissions_a'] - r['Emissions_b']), lambda r: r['Emissions_b'])
v2h_v_uc_emis_pct_cur = paired_15yr_pct('v2h_125PVhhec_fullyear',      'uc_125PVhhec_fullyear',       lambda r: -(r['Emissions_a'] - r['Emissions_b']), lambda r: r['Emissions_b'])
cc_v_uc_emis_pct_lmp  = paired_15yr_pct('cc_125PVhhec_fullyear_lmpdg', 'uc_125PVhhec_fullyear_lmpdg', lambda r: -(r['Emissions_a'] - r['Emissions_b']), lambda r: r['Emissions_b'])
v2h_v_uc_emis_pct_lmp = paired_15yr_pct('v2h_125PVhhec_fullyear_lmpdg','uc_125PVhhec_fullyear_lmpdg', lambda r: -(r['Emissions_a'] - r['Emissions_b']), lambda r: r['Emissions_b'])

# Policy cost increases (LMP - Current) per scenario
# a = LMP, b = Current
uc_pol   = paired_15yr_median('uc_125PVhhec_fullyear_lmpdg',   'uc_125PVhhec_fullyear',
                              lambda r: (r['BaselineCost_a'] + r['Cost_a']) - (r['BaselineCost_b'] + r['Cost_b']))
cc_pol   = paired_15yr_median('cc_125PVhhec_fullyear_lmpdg',   'cc_125PVhhec_fullyear',
                              lambda r: (r['BaselineCost_a'] + r['Cost_a']) - (r['BaselineCost_b'] + r['Cost_b']))
v2h_pol  = paired_15yr_median('v2h_125PVhhec_fullyear_lmpdg',  'v2h_125PVhhec_fullyear',
                              lambda r: (r['BaselineCost_a'] + r['Cost_a']) - (r['BaselineCost_b'] + r['Cost_b']))

# Solar-only policy increase (no EV) using BaselineCost
solar_pol = paired_15yr_median('uc_125PVhhec_fullyear_lmpdg', 'uc_125PVhhec_fullyear',
                               lambda r: r['BaselineCost_a'] - r['BaselineCost_b'])

# Mitigation percentages (per-pair ratio, then median per RGU)
uc_mit   = paired_mitigation('uc_125PVhhec_fullyear',   'uc_125PVhhec_fullyear_lmpdg')
cc_mit   = paired_mitigation('cc_125PVhhec_fullyear',   'cc_125PVhhec_fullyear_lmpdg')
v2h_mit  = paired_mitigation('v2h_125PVhhec_fullyear',  'v2h_125PVhhec_fullyear_lmpdg')

# ═══════════════════════════════════════════════
# SECTION 3.1: Cost reductions
# ═══════════════════════════════════════════════

print("="*80)
print("SECTION 3.1: Cost reductions")
print("="*80)

# Solar PV bill reduction (no EV) = -BaselineCost under current tariff
base_savings = np.array([-uc_cur[c]['BaselineCost'] for c in uc_cur])
print(f"Solar only bill reduction: ${stats(base_savings, 'k')}")

# Total bill with EV+PV (negative = savings vs no-PV-no-EV baseline)
for lbl, data in [('UC current', uc_cur), ('CC current', cc_cur), ('V2H current', v2h_cur)]:
    vals = np.array([data[c]['TotalCost'] for c in data])
    print(f"{lbl} total bill change: ${stats(vals, 'k')}")

# Cost reductions: CC|V2H vs UC (paired 15yr diffs)
for lbl, d, d_pct in [
    ('CC vs UC current',  cc_v_uc_cur,   cc_v_uc_pct_cur),
    ('V2H vs UC current', v2h_v_uc_cur,  v2h_v_uc_pct_cur),
    ('CC vs UC LMP',      cc_v_uc_lmp,   cc_v_uc_pct_lmp),
    ('V2H vs UC LMP',     v2h_v_uc_lmp,  v2h_v_uc_pct_lmp),
]:
    arr = np.array(list(d.values()))
    arr_pct = np.array(list(d_pct.values()))
    print(f"{lbl}: cost reduction ${stats(arr, 'k')}, {stats(arr_pct, 'pct')}")

# ═══════════════════════════════════════════════
# SECTION 3.2: Policy mitigation
# ═══════════════════════════════════════════════

print("\n" + "="*80)
print("SECTION 3.2: Policy mitigation")
print("="*80)

# Policy cost increases (LMP - Current) per scenario
for lbl, d in [('Solar-only (no EV)', solar_pol), ('UC', uc_pol), ('CC', cc_pol), ('V2H', v2h_pol)]:
    arr = np.array(list(d.values()))
    print(f"{lbl} policy cost increase: ${stats(arr, 'k')}")

# Mitigation percentages
for lbl, d in [('UC', uc_mit), ('CC', cc_mit), ('V2H', v2h_mit)]:
    arr = np.array(list(d.values()))
    print(f"{lbl} mitigation: {stats(arr, 'pct')}")

# Self-consumption from EV+PV scenario CSVs. PV-only self-consumption must be
# computed independently as NoElecratio from the no-EV household net load.
for lbl, data in [('UC current', uc_cur), ('CC current', cc_cur), ('V2H current', v2h_cur),
                   ('CC LMP', cc_lmp), ('V2H LMP', v2h_lmp)]:
    vals = [data[c]['SelfConsumption'] for c in data]
    arr = np.array(vals)
    print(f"{lbl} self-consumption: mean={arr.mean():.2f}, {np.percentile(arr,5):.2f}--{np.percentile(arr,95):.2f}")

# ═══════════════════════════════════════════════
# SECTION 3.3: Emissions
# ═══════════════════════════════════════════════

print("\n" + "="*80)
print("SECTION 3.3: Emissions")
print("="*80)

# Absolute lifetime charging emissions
for lbl, data in [('UC current', uc_cur), ('CC current', cc_cur), ('V2H current', v2h_cur),
                   ('UC LMP', uc_lmp), ('CC LMP', cc_lmp), ('V2H LMP', v2h_lmp)]:
    vals = [data[c]['Emissions'] for c in data]
    arr = np.array(vals)
    print(f"{lbl} lifetime charging emissions (kg): mean={arr.mean():.0f}, {np.percentile(arr,5):.0f}--{np.percentile(arr,95):.0f}")

# Emission reductions (paired)
for lbl, d, d_pct in [
    ('CC vs UC current',  cc_v_uc_emis_cur,   cc_v_uc_emis_pct_cur),
    ('V2H vs UC current', v2h_v_uc_emis_cur,  v2h_v_uc_emis_pct_cur),
    ('CC vs UC LMP',      cc_v_uc_emis_lmp,   cc_v_uc_emis_pct_lmp),
    ('V2H vs UC LMP',     v2h_v_uc_emis_lmp,  v2h_v_uc_emis_pct_lmp),
]:
    arr = np.array(list(d.values()))
    arr_pct = np.array(list(d_pct.values()))
    print(f"{lbl}: emission reduction {stats(arr)} kg, {stats(arr_pct, 'pct')}")
