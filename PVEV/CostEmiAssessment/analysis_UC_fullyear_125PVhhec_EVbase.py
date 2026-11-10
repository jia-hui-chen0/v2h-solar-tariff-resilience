import pandas as pd
import numpy as np
import os
import sys
import logging
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed

homesimnum_sufix = '_5homes_percentile'
coverage_sufix = '_70roofcover'
carbprice = 0
root_loc = r'C:\Users\jiahuic\University of Michigan Dropbox\Jiahui Chen\\'
# root_loc = r'C:\Users\jiahuic\University of Michigan Dropbox\Jiahui Chen\\'
rootdir = root_loc
outputdir = root_loc

ctydf = pd.read_csv(root_loc+r'Ford_CC\\2020_Gaz_counties_national_0728_tempreg.csv')
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
    county_num, year, homeelec_sufixi,uniDGrules = args
    try:
        ctydf_1 = ctydf[ctydf['tempreg'] == uqlst[county_num]]
        countyBA = ctydf_1['reeds_ba'].to_list()[0]
        ctdf_urdb_filtered = ctdf_urdb[ctdf_urdb['tempreg'] == uqlst[county_num]]
        program_label = ctdf_urdb_filtered['urdb_label'].to_numpy()[0]
    except Exception as e:
        tb = traceback.format_exc()
        print(f"Error: County {county_num} not found: {e}\nTraceback:\n{tb}")
        return None

    # utility rate
    try:
        utility_rate = pd.read_csv(
            root_loc + rf'PVEV\\julia\\Utility_structure\\' + program_label + '.csv'
        )['energy_rates'].to_numpy()
        if np.any((utility_rate > 0) & (utility_rate < 1)):
            utility_rate = utility_rate * 100
        utility_rate = Rate_date_adjust(utility_rate)[0:8760]
    except Exception as e:
        tb = traceback.format_exc()
        print(f"Error reading utility rate for county {county_num}: {e}\nTraceback:\n{tb}")
        return None
    # emissions factors
    try:
        cambium_df = pd.read_csv(
            root_loc + r'\\Ford_CC\\Cambium\\hourly_balancingArea\\' + countyBA + '_' + str(year) + '.csv'
        )
        f_emi = cambium_df['srmer_co2e'].to_numpy() / 1000
        f_AER = cambium_df['aer_load_co2e'].to_numpy() / 1000
        f_emi, f_AER = EV_date_adjust(f_emi)[0:8760], EV_date_adjust(f_AER)[0:8760]
    except Exception as e:
        tb = traceback.format_exc()
        print(f"Error reading Cambium for county {county_num}, year {year}: {e}\nTraceback:\n{tb}")
        return None

    i1, i2 = 1, 0
    homeelec_sufix = ['', '_noelec'][homeelec_sufixi]
    netnl_dir = (
        outputdir
        + rf"PVEV\ResStock\netnl{homeelec_sufix}_Y82_PV{homesimnum_sufix}{coverage_sufix}_125PVhhec\\{county_num}_1_0"
    )
    building_ids = []
    try:
        fnamelst_bldgid = os.listdir(netnl_dir)
        building_ids = list(
            dict.fromkeys(
                [
                    fnm.split('_')[0]
                    for fnm in fnamelst_bldgid
                    if fnm.split('_')[0].isdigit()
                ]
            )
        )
    except Exception as e:
        tb = traceback.format_exc()
        msg = f"Error reading building ids from {netnl_dir}: {e}\nTraceback:\n{tb}"
        print(msg, file=sys.stderr)
        logging.error(msg)
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
            rootdir
            + rf'Ford_CC\ResStock\{energy_consumption}{homesimnum_sufix}\\'
            + str(county_num)
            + '_'
            + str(i1)
            + '_'
            + str(i2)
        )
    except Exception as e:
        tb = traceback.format_exc()
        msg = f"Error reading filenames for energy consumption from ResStock dir for county {county_num}: {e}\nTraceback:\n{tb}"
        print(msg, file=sys.stderr)
        logging.error(msg)
        return None

    fnms_ev = fnms_ev[:5]
    selected_building_ids = building_ids[:5]
    selected_fnames = fnms_ev[:5]

    # --- generate results for scenarios: 'uc', 'cc', 'v2h'
    results_uc = []
    results_cc = []
    results_v2h = []
    for scen in ['uc', 'cc', 'v2h']:
        # If scen is 'cc' or 'v2h', and the utility_rate is the same for all the first 24 hours, skip processing (will use uc result)
        # if scen in ['cc', 'v2h'] and np.all(utility_rate[:24] == utility_rate[0]):
        #     if scen == 'cc':
        #         results_cc = results_uc
        #     elif scen == 'v2h':
        #         results_v2h = results_uc
        for i0 in range(1):
            for building_id in selected_building_ids:
                fnm = next((f for f in fnms if str(building_id) in f), None)
                if fnm is None:
                    continue
                try:
                    hhec = pd.read_csv(
                        rootdir
                        + rf'Ford_CC\ResStock\{energy_consumption}{homesimnum_sufix}\\'
                        + str(county_num)
                        + '_'
                        + str(i1)
                        + '_'
                        + str(i2)
                        + '\\'
                        + fnm
                    )['0'].to_numpy()
                    hhec_0 = pd.read_csv(
                        rootdir
                        + rf'Ford_CC\ResStock\indi_noelec_fossilfuel{homesimnum_sufix}\\'
                        + str(county_num)
                        + '_'
                        + str(i1)
                        + '_'
                        + str(i2)
                        + '\\'
                        + fnm)['0'].to_numpy()
                    hhec_total_0 = sum(hhec_0)
                    if hhec_total_0 > 20000:
                        continue
                except Exception as e:
                    tb = traceback.format_exc()
                    msg = f"Error reading HHEC for building {building_id} in county {county_num}: {e}\nTraceback:\n{tb}"
                    print(msg, file=sys.stderr)
                    logging.error(msg)
                    continue
                # EVbase: no on-site PV and no grid export (expo) terms — charging + V2H discharge only.
                baseline_cost_partial = 0.0
                baseline_emissions_partial = 0.0
                baseline_emissions_AER_partial = 0.0
                # No rooftop surplus: UC “net PV” buffer for charging is zero.
                netnlarr = np.zeros(8760, dtype=float)
                # Full retail (reference): volumetric bill using hourly load × TOU rate / Cambium.
                retail_no_ev_cost_c = np.sum(hhec_0 * utility_rate)
                retail_no_ev_emissions = np.sum(hhec_0 * f_emi)
                retail_no_ev_emissions_AER = np.sum(hhec_0 * f_AER)
                retail_with_ev_cost_c = np.sum(hhec * utility_rate)
                retail_with_ev_emissions = np.sum(hhec * f_emi)
                retail_with_ev_emissions_AER = np.sum(hhec * f_AER)
                for fname in selected_fnames:
                    if fname.endswith('_soc.csv'):
                        fname_evhh = fname.replace('_soc', '_50')
                    else:
                        fname_evhh = fname
                    try:
                        if uniDGrules == 'LMP':
                            lmpdg = '_lmpdg'
                        else:
                            lmpdg = ''
                        if scen == 'v2h':
                            res_path = (
                                root_loc
                                + rf'PVEV\\SimulationResults\\Result_{scen}_EVbase_fullyear\\Results_80_Y82'
                                + homeelec_sufix
                                + homesimnum_sufix
                                + coverage_sufix
                                + f'{year}\\'
                                + str(county_num)
                                + '_1_0\\'
                                + str(building_id)
                                + '_'
                                + fname_evhh
                            )
                            res = pd.read_csv(res_path)
                            sc = res['slowCR'].to_numpy()
                            fc = res['fastCR'].to_numpy()
                            scneg = res['scneg'].to_numpy()
                            sd = res['sd'].to_numpy()
                        elif scen == 'cc':
                            res_path = (
                                root_loc
                                + rf'PVEV\\SimulationResults\\Result_{scen}_EVbase_fullyear\\Results_80_Y82'
                                + homeelec_sufix
                                + homesimnum_sufix
                                + coverage_sufix
                                + f'{year}\\'
                                + str(county_num)
                                + '_1_0\\'
                                + str(building_id)
                                + '_'
                                + fname_evhh
                            )
                            res = pd.read_csv(res_path)
                            sc = res['slowCR'].to_numpy()
                            fc = res['fastCR'].to_numpy()
                            scneg = res['scneg'].to_numpy()
                            sd = np.zeros(8760)
                        else:
                            res_path = (
                                root_loc
                                + r'\\Ford_CC\\Results\\Results_80_82_rev\\'
                                + str(county_num)
                                + '\\'
                                + fname
                            )
                            res = pd.read_csv(res_path)
                            sc = res['slowCR'].to_numpy()
                            fc = res['fastCR'].to_numpy()
                            scneg = np.minimum(netnlarr, sc)
                            sc = sc - scneg
                            sd = np.zeros(8760)
                        cost = np.sum(
                            (sc) * utility_rate / 0.95
                            + fc * (utility_rate + 20) / 0.95
                            - (sd * utility_rate * 0.95))
                        emissions = np.sum(
                            (sc) * f_emi / 0.95
                            + fc * (f_emi) / 0.95
                            - (sd * f_emi * 0.95))
                        emissions_AER = np.sum(
                            (sc) * f_AER / 0.95
                            + fc * (f_AER) / 0.95
                            - (sd * f_AER * 0.95))
                        result_entry = {
                            'building_id': building_id,
                            'fname': fname_evhh,
                            # Retail reference: fossil (hhec_0) vs electrified (hhec) home load — same TOU / Cambium hours.
                            'BaselineCost': retail_no_ev_cost_c / 100,
                            'BaselineEmissions': retail_no_ev_emissions,
                            'BaselineEmissions_AER': retail_no_ev_emissions_AER,
                            'RetailWithEV_USD': retail_with_ev_cost_c / 100,
                            'EmissionsRetailWithEV': retail_with_ev_emissions,
                            'EmissionsAER_RetailWithEV': retail_with_ev_emissions_AER,
                            # Marginal ledger (no export / no on-site PV); partial baseline is zero.
                            'Cost': (cost - baseline_cost_partial) / 100,
                            'Emissions': emissions - baseline_emissions_partial,
                            'Emissions_AER': emissions_AER - baseline_emissions_AER_partial,
                            'SelfConsumption': np.nan,
                        }
                        if scen == 'uc':
                            results_uc.append(result_entry)
                        elif scen == 'cc':
                            results_cc.append(result_entry)
                        else:
                            results_v2h.append(result_entry)
                    except Exception as e:
                        tb = traceback.format_exc()
                        msg = f"Error reading {scen} result for {res_path}: {e}\nTraceback:\n{tb}"
                        print(msg, file=sys.stderr)
                        logging.error(msg)
                        continue

    # Save results for this county_num and year to their own CSV files
    if results_uc:
        c_lst_df = pd.DataFrame(results_uc)
        outdir = root_loc + rf'PVEV\\CostEmiAssessment\\csv_trb_detailed\\uc_EVbase_fullyear\\'
        try:
            os.makedirs(outdir, exist_ok=True)
        except Exception as e:
            tb = traceback.format_exc()
            print(f"Error creating output directory {outdir}: {e}\nTraceback:\n{tb}")
        outpath = (
            outdir
            + f"{county_num}_{year}_{homesimnum_sufix}_{coverage_sufix}_{homeelec_sufix}.csv"
        )
        c_lst_df.to_csv(outpath, index=False)
    if results_v2h:
        c_lst_df_v2h = pd.DataFrame(results_v2h)
        outdir_v2h = root_loc + rf'PVEV\\CostEmiAssessment\\csv_trb_detailed\\v2h_EVbase_fullyear\\'
        try:
            os.makedirs(outdir_v2h, exist_ok=True)
        except Exception as e:
            tb = traceback.format_exc()
            print(f"Error creating output directory {outdir_v2h}: {e}\nTraceback:\n{tb}")
        outpath_v2h = (
            outdir_v2h
            + f"{county_num}_{year}_{homesimnum_sufix}_{coverage_sufix}_{homeelec_sufix}.csv"
        )
        c_lst_df_v2h.to_csv(outpath_v2h, index=False)
    if results_cc:
        c_lst_df_cc = pd.DataFrame(results_cc)
        outdir_cc = root_loc + rf'PVEV\\CostEmiAssessment\\csv_trb_detailed\\cc_EVbase_fullyear\\'
        try:
            os.makedirs(outdir_cc, exist_ok=True)
        except Exception as e:
            tb = traceback.format_exc()
            print(f"Error creating output directory {outdir_cc}: {e}\nTraceback:\n{tb}")
        outpath_cc = (
            outdir_cc
            + f"{county_num}_{year}_{homesimnum_sufix}_{coverage_sufix}_{homeelec_sufix}.csv"
        )
        c_lst_df_cc.to_csv(outpath_cc, index=False)
    return None

if __name__ == '__main__':
    all_args = []
    for uniDGrules in [0]:
        for homeelec_sufixi in [1]:
            for county_num in range(0, 432):
                for year in [2024, 2030, 2040]:
                    all_args.append((county_num, year, homeelec_sufixi,uniDGrules))
            max_workers = min(32, os.cpu_count() or 1)
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(process_county_year, args) for args in all_args]
                for future in as_completed(futures):
                    _ = future.result()
    # process_county_year((120, 2024, 0))