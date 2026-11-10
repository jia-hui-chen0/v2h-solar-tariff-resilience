"""Data for the self-consumption vs policy-risk figure (Fig_SelfConsumption_vs_PolicyRisk_NEMNEB).

Defines the project paths, the RGU list, the export-tariff class of each RGU and the 90% hull used by
make_fig_policy_risk.py. Run directly, it writes policy_risk_longdata.csv: one row per county and
strategy with
  x = PV self-consumption ratio under the current tariff
      (PV-only: 1 - exported PV / PV generation, from the no-EV net load; median over the RGU's homes.
       UC/CC/V2H: SelfConsumption in the accounting CSVs, mean over homes, averaged over 2024/2030/2040)
  y = 15-year bill increase from the current tariff to LMP export compensation, k$
      (paired per home and driving profile, median per RGU; PV-only uses BaselineCost, the others
       BaselineCost + Cost)
make_fig_policy_risk.py takes the PV-only x values from this table.

Run: uv run --python 3.14 --with pandas --with numpy --with scipy python policy_risk_data.py
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import ConvexHull

HERE = Path(__file__).resolve().parent
ROOT_CANDIDATES = [  # PVEV project root
    Path(r"F:\University of Michigan Dropbox\Jiahui Chen\PVEV"),
    Path(r"C:\Users\jiahuic\University of Michigan Dropbox\Jiahui Chen\PVEV"),
    Path(r"C:\Users\jiahuic\Dropbox (University of Michigan)\PVEV"),
]


def find_root() -> Path:
    for root in ROOT_CANDIDATES:
        if (root / 'CostEmiAssessment' / 'csv_trb_detailed').exists():
            return root
    raise FileNotFoundError(f'Could not locate PVEV project root from candidates: {ROOT_CANDIDATES}')


# make_fig_policy_risk.py --from-source-data uses only the style constants and the hull below, so the
# project paths and the RGU list are then not looked up (they need the model outputs).
FROM_SOURCE = '--from-source-data' in sys.argv[1:]

if not FROM_SOURCE:
    ROOT = find_root()

    CSV = ROOT / 'CostEmiAssessment' / 'csv_trb_detailed'
    FORD_CANDIDATES = [
        ROOT / 'Ford_CC',
        ROOT.parent / 'Ford_CC',
        Path(r"C:\Users\jiahuic\University of Michigan Dropbox\Jiahui Chen\Ford_CC"),
    ]


    def find_ford() -> Path:
        for base in FORD_CANDIDATES:
            if (base / '2020_Gaz_counties_national_0728_tempreg.csv').exists():
                return base
        raise FileNotFoundError(f'Could not locate Ford_CC base from candidates: {FORD_CANDIDATES}')


    FORD = find_ford()
    HL = FORD / 'ResStock' / 'indi_noelec_fossilfuel_5homes_percentile'
    PVSIM = ROOT / 'PVsimulation' / '2018simu_5homes_percentile_70roofcover'
    NETNL = ROOT / 'ResStock' / 'netnl_noelec_Y82_PV_5homes_percentile_70roofcover_125PVhhec'
    LONGDATA = HERE / 'policy_risk_longdata.csv'

FONT = 'Arial'
COLORS = {
    'uc': '#D55E00',
    'cc': '#E69F00',
    'v2h': '#009E73',
    'solar_only': '#999999',
}
SHORT_LABELS = {
    'uc': 'UC',
    'cc': 'CC',
    'v2h': 'V2H',
    'solar_only': 'PV-only',
}

YEARS = [2024, 2030, 2040]
LCA = 5
homesim_sfx = '_5homes_percentile'
cover_sfx = '_70roofcover'
FN = '{ci}_{yr}__5homes_percentile__70roofcover__noelec.csv'
SCEN = {'uc': 'uc_125PVhhec_fullyear', 'cc': 'cc_125PVhhec_fullyear', 'v2h': 'v2h_125PVhhec_fullyear'}

if not FROM_SOURCE:
    ctdf = pd.read_csv(FORD / '2020_Gaz_counties_national_0728_tempreg.csv')
    ctdf['fips'] = ctdf['fips'].astype(str).str.zfill(5)
    uqlst = np.unique(ctdf['tempreg'])
    N_RGU = len(uqlst)


def tariff_class() -> dict[int, str]:
    """Current export-compensation class (NEM, NEB, LMP) of each RGU: the first 'DG Rules' value in
    file order, the same rule as analysis_UC_fullyear_125PVhhec.py."""
    urdb = pd.read_csv(ROOT / 'utility_matching' / 'Rates_dgrules_tou.csv')
    return {int(t): g['DG Rules'].unique().tolist()[0] for t, g in urdb.groupby('tempreg', sort=False)}


def attach_pv_only_x(df: pd.DataFrame) -> pd.DataFrame:
    """Add x_solar_only to the per-RGU table: the PV-only self-consumption of the row in
    policy_risk_longdata.csv whose PV-only y equals the RGU's y_solar_only."""
    old = pd.read_csv(LONGDATA)
    old = old[old.strategy == 'solar_only'].drop_duplicates(['x', 'y'])
    xs = []
    for y in df['y_solar_only']:
        hit = old[np.isclose(old['y'], y, rtol=0, atol=1e-9)] if pd.notna(y) else old.iloc[0:0]
        xs.append(hit['x'].iloc[0] if len(hit['x'].unique()) == 1 else np.nan)
    df['x_solar_only'] = xs
    return df


def minimum_area_fraction_hull(points: np.ndarray, keep_fraction: float = 0.90) -> tuple[np.ndarray, np.ndarray]:
    """Greedy approximation to the minimum-area convex hull containing a point fraction.

    Repeatedly removes the current hull vertex whose deletion gives the largest
    hull-area reduction until `keep_fraction` of points remain. Interior points
    stay because they do not affect the hull boundary.
    """
    if len(points) < 4:
        return points, points
    target_n = max(4, int(math.ceil(len(points) * keep_fraction)))
    keep_idx = np.arange(len(points))
    while len(keep_idx) > target_n:
        pts = points[keep_idx]
        hull = ConvexHull(pts)
        best_pos = None
        best_area = hull.volume
        for pos in hull.vertices:
            trial = np.delete(pts, pos, axis=0)
            if len(trial) < 4:
                continue
            area = ConvexHull(trial).volume
            if area < best_area:
                best_area = area
                best_pos = pos
        if best_pos is None:
            centroid = pts.mean(axis=0)
            d = np.linalg.norm(pts[hull.vertices] - centroid, axis=1)
            best_pos = hull.vertices[int(np.argmax(d))]
        keep_idx = np.delete(keep_idx, best_pos)
    core = points[keep_idx]
    verts = core[ConvexHull(core).vertices]
    return core, verts


# ---------------- policy_risk_longdata.csv ----------------

def paired_rgu_delta(scen_a: str, scen_b: str, col_fn) -> dict[int, float]:
    """Median over a RGU's (home, driving profile) pairs of the 15-year paired difference."""
    out = {}
    for ci in range(N_RGU):
        diffs = []
        for year in YEARS:
            fn = f'{ci}_{year}__{homesim_sfx[1:]}__{cover_sfx[1:]}__noelec.csv'
            pa = CSV / scen_a / fn
            pb = CSV / scen_b / fn
            if not (pa.exists() and pb.exists()):
                diffs = []
                break
            dfa = pd.read_csv(pa)
            dfb = pd.read_csv(pb)
            merged = dfa.merge(dfb, on=['building_id', 'fname'], suffixes=('_cur', '_lmp'))
            if merged.empty:
                diffs = []
                break
            diffs.append(merged.apply(col_fn, axis=1).to_numpy())
        if len(diffs) != len(YEARS):
            continue
        pair_15yr = np.sum(np.vstack(diffs), axis=0) * LCA
        out[ci] = float(np.median(pair_15yr))
    return out


def compute_noelec_ratio() -> pd.Series:
    """PV-only self-consumption per county: median over the RGU's homes of 1 - exported PV / PV generation.
    PV is capped at 125% of the home's annual load, as in the dispatch runs."""
    vals = pd.Series(np.nan, index=ctdf.index, dtype=float)
    for ci in range(N_RGU):
        rgu = int(uqlst[ci])
        hl_dir = HL / f'{ci}_1_0'
        pv_rgu_dir = PVSIM / str(ci)
        netnl_rgu_dir = NETNL / f'{ci}_1_0'
        if not (hl_dir.exists() and pv_rgu_dir.exists() and netnl_rgu_dir.exists()):
            continue
        ratios = []
        for hl_fn in os.listdir(hl_dir):
            if not hl_fn.endswith('.csv'):
                continue
            hhec = pd.read_csv(hl_dir / hl_fn)['0'].to_numpy()
            hh_total = np.sum(hhec)
            pv_path = pv_rgu_dir / (hl_fn[2:][:-4] + '.csv')
            if not pv_path.exists():
                continue
            pv_arr = pd.read_csv(pv_path, header=None, skiprows=1).iloc[:, 0].to_numpy()
            pv_total = np.sum(pv_arr)
            if pv_total > 1.25 * hh_total:
                pv_arr = pv_arr * (hh_total / pv_total) * 1.25
                pv_total = np.sum(pv_arr)
            bid = hl_fn[2:].split('_')[0]
            negnl_path = netnl_rgu_dir / f'{bid}_0_0_0_0_0_soc.csv'
            if negnl_path.exists() and pv_total > 0:
                negnl = pd.read_csv(negnl_path)['NegNL'].to_numpy()
                ratios.append(1 - np.sum(negnl) / pv_total)
        if ratios:
            vals.loc[ctdf['tempreg'] == rgu] = np.median(ratios)
    return vals


def compute_cur_self_consumption(tag: str) -> pd.Series:
    """Self-consumption of strategy `tag` per county: mean over homes, averaged over the three years."""
    series = pd.Series(0.0, index=ctdf.index, dtype=float)
    for year in YEARS:
        for ci in range(N_RGU):
            mask = ctdf['tempreg'] == int(uqlst[ci])
            f = CSV / f'{tag}_125PVhhec_fullyear' / f'{ci}_{year}__{homesim_sfx[1:]}__{cover_sfx[1:]}__noelec.csv'
            if f.exists():
                series.loc[mask] += pd.read_csv(f)['SelfConsumption'].mean()
    return series / 3


def build_long_df() -> pd.DataFrame:
    ctdf2 = ctdf.copy()
    ctdf2['NoElecratio'] = compute_noelec_ratio()
    for tag in ['uc', 'cc', 'v2h']:
        ctdf2[f'{tag}_sc_cur'] = compute_cur_self_consumption(tag)
    total = lambda r: (r['BaselineCost_lmp'] + r['Cost_lmp']) - (r['BaselineCost_cur'] + r['Cost_cur'])
    delta_specs = [
        ('delta_uc_cost', 'uc_125PVhhec_fullyear', 'uc_125PVhhec_fullyear_lmpdg', total),
        ('delta_cc_cost', 'cc_125PVhhec_fullyear', 'cc_125PVhhec_fullyear_lmpdg', total),
        ('delta_v2h_cost', 'v2h_125PVhhec_fullyear', 'v2h_125PVhhec_fullyear_lmpdg', total),
        ('delta_solar_only_cost', 'uc_125PVhhec_fullyear', 'uc_125PVhhec_fullyear_lmpdg',
         lambda r: r['BaselineCost_lmp'] - r['BaselineCost_cur']),
    ]
    for col_name, scen_cur, scen_lmp, fn in delta_specs:
        ctdf2[col_name] = np.nan
        for ci, val in paired_rgu_delta(scen_cur, scen_lmp, fn).items():
            ctdf2.loc[ctdf2['tempreg'] == int(uqlst[ci]), col_name] = val
    records = []
    for tag in ['uc', 'cc', 'v2h', 'solar_only']:
        x = ctdf2['NoElecratio'] if tag == 'solar_only' else ctdf2[f'{tag}_sc_cur']
        y = ctdf2[f'delta_{tag}_cost'] / 1000
        for i in ctdf2.index:
            if pd.notna(x.loc[i]) and pd.notna(y.loc[i]):
                records.append({'strategy': tag, 'x': float(x.loc[i]), 'y': float(y.loc[i])})
    df = pd.DataFrame(records)
    return df[(df['x'].between(0, 1.05)) & np.isfinite(df['y'])].copy()


def main():
    df = build_long_df()
    df.to_csv(LONGDATA, index=False)
    print(f'rows={len(df)} strategies={df.strategy.value_counts().to_dict()} -> {LONGDATA}')


if __name__ == '__main__':
    main()
