"""Regenerate CC_75AhA base pvev.csv for RGUs 0-9 (the 10 broken ones)."""
import sys, os, pandas as pd, numpy as np
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, r'C:\Users\jiahuic\University of Michigan Dropbox\Jiahui Chen\Ford_CC\DegradationAssessment_revision\blast_bkup')
from blast import models

root_dir = r'C:\Users\jiahuic\University of Michigan Dropbox\Jiahui Chen\\'
sim_dir = os.path.join(root_dir, 'PVEV', 'SimulationResults')
homesim = '_5homes_percentile'
cover = '_70roofcover'
cap = 82
years = [2024, 2030, 2040]
scen_key = 'CC'
batt_name = 'NMC_Gr_75Ah_A'
batt_class = models.NMC_Gr_75Ah_A
batt_tag = '75AhA'
cp = 0
lmp = False
scc_sfx = ''
lmp_sfx = ''

base_dir = os.path.join(sim_dir, 'Result_cc_125PVhhec_fullyear')
output_dir = os.path.join(root_dir, 'Ford_CC', 'DegradationAssessment_revision', 'Deginterm_pvev')

evfns_soc = [
    '0_0_0_0_0_soc.csv', '0_0_0_10_0_soc.csv', '0_0_0_11_0_soc.csv', '0_0_0_12_0_soc.csv', '0_0_0_13_0_soc.csv',
    '0_0_0_14_0_soc.csv', '0_0_0_15_0_soc.csv', '0_0_0_16_0_soc.csv', '0_0_0_17_0_soc.csv', '0_0_0_18_0_soc.csv',
    '0_0_0_19_0_soc.csv', '0_0_0_1_0_soc.csv', '0_0_0_20_0_soc.csv', '0_0_0_21_0_soc.csv', '0_0_0_22_0_soc.csv'
][:15]

for county_num in range(10):
    out_name = f'{county_num}_80Y{cap}_{scen_key}_{batt_tag}{scc_sfx}{lmp_sfx}_pvev.csv'
    out_path = os.path.join(output_dir, out_name)
    print(f'Processing RGU {county_num}...', end=' ', flush=True)

    # Get result directory
    result_dir = os.path.join(base_dir, f'Results_80_Y82_noelec{homesim}{cover}2024', f'{county_num}_1_0')
    if not os.path.exists(result_dir):
        print(f'SKIP: no result dir')
        continue

    bldgs = sorted(set(f.split('_')[0] for f in os.listdir(result_dir) if f.split('_')[0].isdigit()))
    if not bldgs:
        print(f'SKIP: no buildings')
        continue
    bldg = bldgs[0]

    # Load temperature
    temp_path = os.path.join(root_dir, 'Ford_CC', 'tempAdjusted', f'{county_num}.csv')
    try:
        temp = pd.read_csv(temp_path)['0'].to_list() * 16
    except Exception as e:
        print(f'SKIP: temp error {e}')
        continue

    lifecty, qcallst, qcyclst = [], [], []
    n_processed = 0
    for vi in range(15):
        soc_list = []
        for year in years:
            rdir = os.path.join(base_dir, f'Results_80_Y82_noelec{homesim}{cover}{year}', f'{county_num}_1_0')
            fname_evhh = evfns_soc[vi][:-8] + '_50.csv'
            fpath = os.path.join(rdir, f'{bldg}_{fname_evhh}')
            if not os.path.exists(fpath):
                continue
            soc_df = pd.read_csv(fpath)
            repeat = 5 if year in [2024, 2030] else 6
            soc_list.extend(soc_df['vSOC'].to_list() * repeat)

        if len(soc_list) != 8760 * 16:
            continue

        data = {'Time_s': np.arange(8760 * 16) * 3600, 'SOC': np.array(soc_list) / cap, 'Temperature_C': np.array(temp)}
        cell = batt_class()
        cell.simulate_battery_life(data)
        h = 0
        while cell.outputs['q'][h] > .7 and h < 365 * 15:
            h += 1
        lifecty.append(h / 365)
        qcallst.append(1 - cell.outputs['q_t'][-1])
        qcyclst.append(1 - cell.outputs['q_EFC'][-1])
        n_processed += 1

    if lifecty:
        pd.DataFrame([lifecty, qcallst, qcyclst]).to_csv(out_path, index=False)
        print(f'OK: {n_processed} vehicles, {len(lifecty)} results')
    else:
        print(f'FAIL: no data')

print('Done!')
