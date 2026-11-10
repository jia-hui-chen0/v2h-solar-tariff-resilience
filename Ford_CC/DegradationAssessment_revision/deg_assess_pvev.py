"""Battery degradation assessment for PV+EV paper — CC, V2H, UC scenarios."""
import sys, os, pandas as pd, numpy as np
from multiprocessing import Process
import warnings

sys.path.insert(0, r'C:\Users\jiahuic\University of Michigan Dropbox\Jiahui Chen\Ford_CC\DegradationAssessment_revision\blast_bkup')
from blast import models

root_dir = r'C:\Users\jiahuic\University of Michigan Dropbox\Jiahui Chen\\'
sim_dir = root_dir + r'PVEV\SimulationResults'
homesim = '_5homes_percentile'
cover = '_70roofcover'

battery_models = [
    ("NMC_Gr_75Ah_A", models.NMC_Gr_75Ah_A, "75AhA"),
    ("NMC_Gr_50Ah_B1", models.NMC_Gr_50Ah_B1, "B1"),
    ("NMC_Gr_50Ah_B2", models.NMC_Gr_50Ah_B2, "B2"),
    ("Lfp_Gr_250AhPrismatic", models.Lfp_Gr_250AhPrismatic, "LFP")
]

evfns_soc = [
    '0_0_0_0_0_soc.csv', '0_0_0_10_0_soc.csv', '0_0_0_11_0_soc.csv', '0_0_0_12_0_soc.csv', '0_0_0_13_0_soc.csv',
    '0_0_0_14_0_soc.csv', '0_0_0_15_0_soc.csv', '0_0_0_16_0_soc.csv', '0_0_0_17_0_soc.csv', '0_0_0_18_0_soc.csv',
    '0_0_0_19_0_soc.csv', '0_0_0_1_0_soc.csv', '0_0_0_20_0_soc.csv', '0_0_0_21_0_soc.csv', '0_0_0_22_0_soc.csv'
][:15]

def deg(num0, num1, scen_key, cp=0, lmp=False):
    """Process counties from num0 to num1. cp=0=no SCC, lmp=True=LMP solar tariff."""
    cap = 82
    years = [2024, 2030, 2040]
    scc_sfx = f'_scc{cp}' if cp > 0 else ''
    lmp_sfx = '_lmpdg' if lmp else ''
    output_dir = os.path.join(root_dir, r'Ford_CC\DegradationAssessment_revision\Deginterm_pvev')
    os.makedirs(output_dir, exist_ok=True)

    if scen_key == 'UC':
        base_dir = os.path.join(root_dir, r'Ford_CC\Results\Results_80_82_rev')
    elif scen_key == 'CC':
        base_dir = os.path.join(sim_dir, f'Result_cc_125PVhhec_fullyear{scc_sfx}{lmp_sfx}')
    else:
        base_dir = os.path.join(sim_dir, f'Result_v2h_125PVhhec_fullyear{scc_sfx}{lmp_sfx}')

    for batt_name, batt_class, batt_tag in battery_models:
        for county_num in range(num0, num1):
            out_name = f"{county_num}_80Y{cap}_{scen_key}_{batt_tag}{scc_sfx}{lmp_sfx}_pvev.csv"
            out_path = os.path.join(output_dir, out_name)
            if os.path.exists(out_path):
                continue

            # Get building ID (or None for UC)
            if scen_key == 'UC':
                result_dir = os.path.join(base_dir, str(county_num))
                bldg = None
            else:
                result_dir = os.path.join(base_dir, f'Results_80_Y82_noelec{homesim}{cover}2024', f'{county_num}_1_0')
                if not os.path.exists(result_dir):
                    continue
                bldgs = sorted(set(f.split('_')[0] for f in os.listdir(result_dir) if f.split('_')[0].isdigit()))
                if not bldgs:
                    continue
                bldg = bldgs[0]

            if not os.path.exists(result_dir):
                continue

            # Load temperature
            temp_path = os.path.join(root_dir, r'Ford_CC\tempAdjusted', f'{county_num}.csv')
            try:
                temp = pd.read_csv(temp_path)['0'].to_list() * 16
            except Exception:
                continue

            lifecty, qcallst, qcyclst = [], [], []
            for vi in range(15):
                soc_list = []
                for year in years:
                    if scen_key == 'UC':
                        fpath = os.path.join(base_dir, str(county_num), evfns_soc[vi])
                    else:
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

            if lifecty:
                pd.DataFrame([lifecty, qcallst, qcyclst]).to_csv(out_path, index=False)

if __name__ == '__main__':
    warnings.filterwarnings("ignore")

    for scen in ['UC', 'CC', 'V2H']:
        cp_list = [0] if scen == 'UC' else [0, 51, 204]
        lmp_list = [False] if scen == 'UC' else [False, True]
        for cp in cp_list:
            for lmp in lmp_list:
                if cp > 0 and lmp:
                    continue  # SCC + LMP not run
                ssfx = f'_scc{cp}' if cp > 0 else ''
                lsfx = '_lmpdg' if lmp else ''
                label = f'{scen}{lsfx}{ssfx}'.replace('__', '_')
                print(f'=== {label} ===')
            procs = []
            for i in range(48):
                start = i * 9
                end = 432 if i == 47 else (i + 1) * 9
                p = Process(target=deg, args=(start, end, scen, cp, lmp))
                p.start()
                procs.append(p)
            for p in procs:
                p.join()
            outd = os.path.join(root_dir, r'Ford_CC\DegradationAssessment_revision\Deginterm_pvev')
            ssfx = f'_scc{cp}' if cp > 0 else ''
            lsfx = '_lmpdg' if lmp else ''
            count = sum(1 for f in os.listdir(outd) if f'_{scen}_' in f and ssfx in f and lsfx in f)
            print(f'{label}: {count} output files')
    print('Done.')