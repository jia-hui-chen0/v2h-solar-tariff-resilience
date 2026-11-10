"""SCC-aware analysis: re-computes costs/emissions from SCC optimization result CSVs."""
import pandas as pd
import numpy as np
import os
import sys
import logging
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed

homesimnum_sufix = '_5homes_percentile'
coverage_sufix = '_70roofcover'
CARBON_PRICES = [0, 51, 204]
root_loc = r'C:\Users\jiahuic\University of Michigan Dropbox\Jiahui Chen\\'
rootdir = root_loc
outputdir = root_loc

ctydf = pd.read_csv(root_loc + r'Ford_CC\\2020_Gaz_counties_national_0728_tempreg.csv')
ctdf_urdb = pd.read_csv(root_loc + r"PVEV\\utility_matching\Rates_dgrules_tou.csv")
uqlst = np.unique(ctydf['tempreg'])
ctydf.set_index(keys=ctydf['county_num'], inplace=True)

def EV_date_adjust(arr):
    df2021 = arr
    df2021_1 = np.concatenate((df2021[:1*24], df2021[-4*24:], df2021[1*24:-4*24]))
    for i, j in [(14, 21), (147, 154), (184, 189), (245, 252), (358, 361), (325, 332)]:
        for hi in range(24):
            df2021_1[i*24+hi], df2021_1[j*24+hi] = df2021_1[j*24+hi], df2021_1[i*24+hi]
    return df2021_1

def Rate_date_adjust(arr):
    df2025 = arr
    df2025_1 = np.concatenate((df2025[:1*24], df2025[-2*24:], df2025[1*24:-2*24]))
    return df2025_1

def process_county_year(args):
    county_num, year, homeelec_sufixi, uniDGrules, carbon_price = args
    try:
        ctydf_1 = ctydf[ctydf['tempreg'] == uqlst[county_num]]
        countyBA = ctydf_1['reeds_ba'].to_list()[0]
        ctdf_urdb_filtered = ctdf_urdb[ctdf_urdb['tempreg'] == uqlst[county_num]]
        if uniDGrules == 'LMP':
            DG_rules = 'LMP'
        else:
            DG_rules = ctdf_urdb_filtered['DG Rules'].unique().tolist()[0]
        program_label = ctdf_urdb_filtered['urdb_label'].to_numpy()[0]
    except Exception as e:
        print(f"Error: County {county_num} not found: {e}")
        return None

    try:
        utility_rate = pd.read_csv(
            root_loc + rf'PVEV\\julia\\Utility_structure\\' + program_label + '.csv'
        )['energy_rates'].to_numpy()
        if np.any((utility_rate > 0) & (utility_rate < 1)):
            utility_rate = utility_rate * 100
        utility_rate = Rate_date_adjust(utility_rate)[0:8760]
    except Exception as e:
        print(f"Error reading utility rate for county {county_num}: {e}")
        return None

    try:
        cambium_df = pd.read_csv(
            root_loc + rf'Ford_CC\\Cambium\\hourly_balancingArea\\{countyBA}_{year}.csv'
        )
        f_emi = cambium_df['srmer_co2e'].to_numpy() / 1000
        f_AER = cambium_df['aer_load_co2e'].to_numpy() / 1000
        f_emi, f_AER = EV_date_adjust(f_emi)[0:8760], EV_date_adjust(f_AER)[0:8760]
        emission_arr = cambium_df['srmer_co2e'].to_numpy() / 1000
        emission_arr = EV_date_adjust(emission_arr)[0:8760]
        carbon_arr = emission_arr * carbon_price / 10.0
    except Exception as e:
        print(f"Error reading Cambium for county {county_num}, year {year}: {e}")
        return None

    try:
        if DG_rules == 'LMP':
            DGcostarr = cambium_df['total_cost_enduse'].to_numpy() / 1000 * 100
            DGcostarr = EV_date_adjust(DGcostarr)[0:8760]
        elif DG_rules == 'NEM':
            DGcostarr = utility_rate
        elif DG_rules == 'NEB':
            combined_info = ctdf_urdb_filtered['combined'].unique().tolist()[0]
            cleaned_filename = combined_info.replace(':', '').replace('/', '').replace('\\', '')
            DGrate_df = pd.read_csv(root_loc + rf"PVEV\\PVcompensation\rates\\{cleaned_filename}.csv")
            DGcostarr = DGrate_df['Rate (cent/kWh)'].to_numpy()
            DGcostarr = Rate_date_adjust(DGcostarr)[0:8760]
        else:
            DGcostarr = utility_rate
    except Exception as e:
        print(f"Error reading DG cost for county {county_num}: {e}")
        return None

    sc_ec = utility_rate + carbon_arr
    DG_export = DGcostarr + carbon_arr

    i1, i2 = 1, 0
    homeelec_sufix = ['', '_noelec'][homeelec_sufixi]
    netnl_dir = (
        outputdir
        + rf"PVEV\ResStock\netnl{homeelec_sufix}_Y82_PV{homesimnum_sufix}{coverage_sufix}_125PVhhec\\{county_num}_1_0"
    )
    building_ids = []
    try:
        fnamelst_bldgid = os.listdir(netnl_dir)
        building_ids = list(dict.fromkeys([fnm.split('_')[0] for fnm in fnamelst_bldgid if fnm.split('_')[0].isdigit()]))
    except Exception as e:
        building_ids = []
    if not building_ids:
        return None

    fnms_ev = [
        '0_0_0_0_0_soc.csv', '0_0_0_10_0_soc.csv', '0_0_0_11_0_soc.csv', '0_0_0_12_0_soc.csv', '0_0_0_13_0_soc.csv',
        '0_0_0_14_0_soc.csv', '0_0_0_15_0_soc.csv', '0_0_0_16_0_soc.csv', '0_0_0_17_0_soc.csv', '0_0_0_18_0_soc.csv',
        '0_0_0_19_0_soc.csv', '0_0_0_1_0_soc.csv', '0_0_0_20_0_soc.csv', '0_0_0_21_0_soc.csv', '0_0_0_22_0_soc.csv'
    ]
    energy_consumption = ['Indi_Hourly', 'indi_noelec_fossilfuel'][homeelec_sufixi]
    try:
        fnms = os.listdir(
            rootdir + rf'Ford_CC\ResStock\{energy_consumption}{homesimnum_sufix}\\{county_num}_{i1}_{i2}'
        )
    except Exception as e:
        return None

    fnms_ev = fnms_ev[:5]
    selected_building_ids = building_ids[:5]
    selected_fnames = fnms_ev[:5]

    if carbon_price == 0:
        scc_sfx = ''
    else:
        scc_sfx = f'_scc{carbon_price}'

    results_uc, results_cc, results_v2h = [], [], []
    for scen in ['uc', 'cc', 'v2h']:
        for building_id in selected_building_ids:
            fnm = next((f for f in fnms if str(building_id) in f), None)
            if fnm is None:
                continue
            fnm_2 = fnm[2:][:-4] + '.csv'
            try:
                hhec = pd.read_csv(
                    rootdir + rf'Ford_CC\ResStock\{energy_consumption}{homesimnum_sufix}\\{county_num}_{i1}_{i2}\\{fnm}'
                )['0'].to_numpy()
                hhec_0 = pd.read_csv(
                    rootdir + rf'Ford_CC\ResStock\indi_noelec_fossilfuel{homesimnum_sufix}\\{county_num}_{i1}_{i2}\\{fnm}'
                )['0'].to_numpy()
                hhec_total_0 = sum(hhec_0)
                if hhec_total_0 > 20000:
                    continue
            except Exception as e:
                continue
            try:
                PVout = pd.read_csv(
                    rootdir + rf'PVEV\PVsimulation\2018simu{homesimnum_sufix}{coverage_sufix}\\{county_num}\\{fnm_2}'
                )
                PVout.columns = ['PVout']
                PVout = PVout['PVout'].to_numpy()[0:8760]
                PVout_total = sum(PVout)
                if PVout_total > 1.25 * hhec_total_0:
                    PVout = PVout * hhec_total_0 / PVout_total * 1.25
            except Exception as e:
                continue

            PVsupply = np.minimum(PVout, hhec)
            netexport = np.maximum(PVout - hhec, 0)
            netnlarr = np.maximum(PVout - hhec, 0)

            baselinecost = np.sum(-netexport * DG_export * 0.9 - PVsupply * sc_ec)
            baselineemissions = np.sum(-f_emi * netexport * 0.9 - PVsupply * f_emi)
            baselineemissions_AER = np.sum(-f_AER * netexport * 0.9 - PVsupply * f_AER)

            for fname in selected_fnames:
                fname_evhh = fname[:-8] + '_50' + fname[-4:] if fname.endswith('_soc.csv') else fname
                try:
                    if scen == 'v2h':
                        res_path = (
                            root_loc
                            + rf'PVEV\\SimulationResults\\Result_{scen}_125PVhhec_fullyear{scc_sfx}\\Results_80_Y82'
                            + homeelec_sufix + homesimnum_sufix + coverage_sufix + f'{year}\\'
                            + f'{county_num}_1_0\\{building_id}_{fname_evhh}'
                        )
                        res = pd.read_csv(res_path)
                        sc, fc, expo, scneg, sd = res['slowCR'].to_numpy(), res['fastCR'].to_numpy(), res['Exp'].to_numpy(), res['scneg'].to_numpy(), res['sd'].to_numpy()
                    elif scen == 'cc':
                        res_path = (
                            root_loc
                            + rf'PVEV\\SimulationResults\\Result_{scen}_125PVhhec_fullyear{scc_sfx}\\Results_80_Y82'
                            + homeelec_sufix + homesimnum_sufix + coverage_sufix + f'{year}\\'
                            + f'{county_num}_1_0\\{building_id}_{fname_evhh}'
                        )
                        res = pd.read_csv(res_path)
                        sc, fc, expo, scneg = res['slowCR'].to_numpy(), res['fastCR'].to_numpy(), res['Exp'].to_numpy(), res['scneg'].to_numpy()
                        sd = np.zeros(8760)
                    else:
                        res_path = root_loc + rf'Ford_CC\\Results\\Results_80_82_rev\\{county_num}\\{fname}'
                        res = pd.read_csv(res_path)
                        sc = res['slowCR'].to_numpy()
                        fc = res['fastCR'].to_numpy()
                        scneg = np.minimum(netnlarr, sc)
                        sc = sc - scneg
                        sd = np.zeros(8760)
                        expo = netnlarr - scneg

                    PVsupply_EV = PVout - expo - scneg

                    # Cost with SCC added to electricity prices
                    cost = np.sum(
                        sc * sc_ec / 0.95 + fc * (sc_ec + 20) / 0.95
                        - sd * sc_ec * 0.95
                        - DG_export * expo * 0.9
                        - PVsupply_EV * sc_ec
                    )
                    emissions = np.sum(
                        sc * f_emi / 0.95 + fc * f_emi / 0.95 - sd * f_emi * 0.95
                        - f_emi * expo * 0.9 - PVsupply_EV * f_emi
                    )
                    emissions_AER = np.sum(
                        sc * f_AER / 0.95 + fc * f_AER / 0.95 - sd * f_AER * 0.95
                        - f_AER * expo * 0.9 - PVsupply_EV * f_AER
                    )

                    entry = {
                        'building_id': building_id, 'fname': fname_evhh,
                        'BaselineCost': baselinecost / 100,
                        'BaselineEmissions': baselineemissions,
                        'BaselineEmissions_AER': baselineemissions_AER,
                        'Cost': cost / 100 - baselinecost / 100,
                        'Emissions': emissions - baselineemissions,
                        'Emissions_AER': emissions_AER - baselineemissions_AER,
                        'SelfConsumption': np.sum(PVout - expo) / np.sum(PVout),
                    }
                    if scen == 'uc':
                        results_uc.append(entry)
                    elif scen == 'cc':
                        results_cc.append(entry)
                    else:
                        results_v2h.append(entry)
                except Exception as e:
                    continue

    for results, scen in [(results_uc, 'uc'), (results_cc, 'cc'), (results_v2h, 'v2h')]:
        if not results:
            continue
        df = pd.DataFrame(results)
        outdir = root_loc + rf'PVEV\\CostEmiAssessment\\csv_trb_detailed\\{scen}_125PVhhec_fullyear{scc_sfx}\\'
        os.makedirs(outdir, exist_ok=True)
        outpath = outdir + f"{county_num}_{year}_{homesimnum_sufix}_{coverage_sufix}_{homeelec_sufix}.csv"
        df.to_csv(outpath, index=False)
    return None

if __name__ == '__main__':
    all_args = []
    for cp in [51, 204]:
        for homeelec_sufixi in [1]:
            for county_num in range(0, 432):
                for year in [2024, 2030, 2040]:
                    all_args.append((county_num, year, homeelec_sufixi, 0, cp))
            max_workers = min(32, os.cpu_count() or 1)
            print(f"cp={cp} homeelec={homeelec_sufixi}: {len(all_args)} tasks, {max_workers} workers")
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(process_county_year, args) for args in all_args]
                for future in as_completed(futures):
                    _ = future.result()
            all_args = []
    print("Done.")
