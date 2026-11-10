# all cost in cents/kWh
# EV time series: 2021 date
# URDB: 2025 date
# Home: 2018 date
# harmonize EV and URDB to home time series

import os
import sys
import pandas as pd
import numpy as np
from gams import *
import concurrent.futures
import multiprocessing
from multiprocessing import Manager
import logging

# Setup logging near script start
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "CC_rd.log")
logging.basicConfig(
    filename=log_file,
    filemode='a',
    format='%(asctime)s %(levelname)s %(process)d %(message)s',
    level=logging.ERROR  # Only log errors
)
logger = logging.getLogger(__name__)

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

# Shared RAM cache for files
shared_cache = None

def get_shared_cache():
    global shared_cache
    if shared_cache is None:
        manager = Manager()
        shared_cache = manager.dict()
    return shared_cache

def get_or_load_csv(key, path, col=None, as_numpy=False):
    cache = get_shared_cache()
    if key in cache:
        return cache[key]
    try:
        df = pd.read_csv(path)
        if col is not None:
            arr = df[col].to_numpy() if as_numpy else df[col]
        else:
            arr = df
        cache[key] = arr
        return arr
    except Exception as e:
        logger.error(f"Error loading {path}: {e}")
        print(f"Error loading {path}: {e}", file=sys.stderr)
        raise

# GAMS temp files cleanup is not needed as we want to avoid keeping temp files
# (remove all clear_gams_temp_files functions and calls)

def CC(num0, num1, years, ctydf, root_loc, ctdf_urdb, system_directory, homeelec_sufix, homesimnum_sufix, coverage_sufix,scen):
    year = years

    def get_model_text():
        # GAMS model for CC, adapted for discharge items
        return '''
$GDXIN _gams_py_gdb0.gdx
Sets
    h   Hours;

Parameters
    modelStatus   model status
    sc_cr(h)   charging upper limit at hour h
    fc_cr(h)
    vIni
    sc_ec(h)   charging cost
    fc_ec(h)
    PV_ec(h)   export electricity price at hour h
    SDrop(h)   SOC drop at hour h   
    sd_dr(h)  discharge upper limit at hour h (precalculated 0 if neaative netload else home load-PVout)
    negnl(h)  absolute value of netload at hour h if NEGATIVE else 0  ;

$load h sc_cr fc_cr sc_ec fc_ec SDrop vIni sd_dr negnl PV_ec

Variables
    sc(h)  slow charging rate at hour h 
    scneg(h)  slow charging rate at hour h absorbing negative netload
    fc(h)  fast charging rate at hour h 
    sd(h)  discharging rate at hour h
    netload(h)  net load at hour h
    Expo(h)   export to grid at hour h

    vSOC(h)   vehicle SOC in kWh
    z         total costs;
    scneg.lo(h) = 0;
    scneg.up(h) = sc_cr(h);
    sc.lo(h) = 0;
    sc.up(h) = sc_cr(h);
    fc.lo(h) = 0;
    fc.up(h) = fc_cr(h);
    sd.lo(h) = 0;
    sd.up(h) = sd_dr(h);
    vSOC.lo(h) = 0.2 *82;
    vSOC.up(h) = 0.8 * 82;
    vSOC.fx(h) $ (ord(h) eq 1) = vIni;
    Expo.lo(h) = 0;
    Expo.up(h) = negnl(h);
Equations
    cost      define objective function
    cCapacity(h)   observe capacity limit at hour h
    cNetload1(h)   observe net load limit at hour h
    cscscneg(h)
    cExpo(h);

cost ..        z  =e=  sum(h,(sc(h))*sc_ec(h)/0.95+fc_ec(h)*fc(h)/0.95-(sd(h)*sc_ec(h)*0.95)-PV_ec(h)*Expo(h)*0.85) ;
cCapacity(h).. vSOC(h)$(ord(h) gt 1) =e= vSOC(h-1) + sc(h)+scneg(h) +fc(h) - SDrop(h)-sd(h);
cNetload1(h).. scneg(h) =l= negnl(h);
cscscneg(h).. sc(h)+scneg(h) =l= sc_cr(h);
cExpo(h).. Expo(h)+scneg(h) =e= negnl(h);

Model SCS /all/ ;
Option LP = cplex;
Option threads = 19;
Solve SCS using lp minimizing z ;
modelStatus = SCS.modelStat;
execute_unload "results.gdx" modelStatus sc fc vSOC scneg sd Expo;  '''

    outputdir = root_loc
    vEff = 0.95
    vCR = [10, 10]
    SOC = [82, 153]

    uqlst = np.unique(ctydf['tempreg'])
    ctydf.set_index(keys=ctydf['county_num'], inplace=True)

    for county_num in range(num0, num1):
        try:
            ctydf_1 = ctydf[ctydf['tempreg'] == uqlst[county_num]]
            countyBA = ctydf_1['reeds_ba'].to_list()[0]
            cambium_key = f"cambium_{countyBA}_{year}"
            cambium_path = outputdir + r'Ford_CC\\Cambium\\hourly_balancingArea\\' + countyBA + '_' + str(year) + '.csv'
            cambium_df = get_or_load_csv(cambium_key, cambium_path)
            fnames = [
                '0_0_0_0_0_soc.csv', '0_0_0_10_0_soc.csv', '0_0_0_11_0_soc.csv', '0_0_0_12_0_soc.csv', '0_0_0_13_0_soc.csv',
                '0_0_0_14_0_soc.csv', '0_0_0_15_0_soc.csv', '0_0_0_16_0_soc.csv', '0_0_0_17_0_soc.csv', '0_0_0_18_0_soc.csv',
                '0_0_0_19_0_soc.csv', '0_0_0_1_0_soc.csv', '0_0_0_20_0_soc.csv', '0_0_0_21_0_soc.csv', '0_0_0_22_0_soc.csv'
            ]
            # fnames = ['0_0_0_13_0_soc.csv']
            fnames = fnames[:5]
            ctdf_urdb_filtered = ctdf_urdb[ctdf_urdb['tempreg'] == uqlst[county_num]]
            # DG_rules = ctdf_urdb_filtered['DG Rules'].unique()[0]
            DG_rules = 'LMP' # control case
            program_label = ctdf_urdb_filtered['urdb_label'].to_numpy()[0]
            utility_key = f"utility_{program_label}"
            utility_path = outputdir + r'PVEV\\julia\\Utility_structure\\' + program_label + '.csv'
            utility_rate = get_or_load_csv(utility_key, utility_path, col='energy_rates', as_numpy=True)
            if np.any((utility_rate > 0) & (utility_rate < 1)):
                utility_rate = utility_rate * 100
            utility_rate = Rate_date_adjust(utility_rate)
            cost = utility_rate

            # DG compensation price for excess generation
            if DG_rules == 'LMP':
                DGcostarr = cambium_df['total_cost_enduse'].to_numpy() / 1000 * 100
                DGcostarr = EV_date_adjust(DGcostarr)
            elif DG_rules == 'NEM':
                DGcostarr = utility_rate
            elif DG_rules == 'NEB':
                combined_info = ctdf_urdb_filtered['combined'].unique()[0]
                cleaned_filename = combined_info.replace(':', '').replace('/', '').replace('\\', '')
                dgrate_key = f"dgrate_{cleaned_filename}"
                dgrate_path = root_loc + rf"PVEV\\PVcompensation\rates\{cleaned_filename}.csv"
                DGrate_df = get_or_load_csv(dgrate_key, dgrate_path)
                DGcostarr = DGrate_df['Rate (cent/kWh)'].to_numpy()
                DGcostarr = Rate_date_adjust(DGcostarr)
        except Exception as e:
            import inspect
            logger.error(f"Line {inspect.currentframe().f_lineno}: Error in county_num {county_num} setup: {e}")
            print(f"Line {inspect.currentframe().f_lineno}: Error in county_num {county_num} setup: {e}", file=sys.stderr)
            continue
        # Get building ids from the directory by extracting numbers before the first underscore
        netnl_dir = outputdir + rf"PVEV\ResStock\netnl{homeelec_sufix}_Y82_PV{homesimnum_sufix}{coverage_sufix}_125PVhhec\\{county_num}_1_0"
        building_ids = []
        try:
            fnamelst_bldgid = os.listdir(netnl_dir)
            building_ids = list(dict.fromkeys([fnm.split('_')[0] for fnm in fnamelst_bldgid if fnm.split('_')[0].isdigit()]))
        except Exception as e:
            logger.error(f"Error reading building ids from {netnl_dir}: {e}")
            print(f"Error reading building ids from {netnl_dir}: {e}", file=sys.stderr)
            building_ids = []
        # Only log errors, so remove info log here
        print(building_ids)
        # Generate 5 building_ids and 5 fnames, and all 25 possible pairs (cartesian product)
        selected_building_ids = building_ids[:5]
        selected_fnames = fnames[:5]
        building_fname_pairs = [(b, f) for b in selected_building_ids for f in selected_fnames]
        
        # Loop over building_ids and fnames together
        for building_id, fname in building_fname_pairs:
            try:
                cari = 0
                tcnm = ['_SUV', '_Truck'][cari]
                sc_key = f"sc_{county_num}_{tcnm}_{fname}"
                fc_key = f"fc_{county_num}_{tcnm}_{fname}"
                sc_path = outputdir + r"Ford_CC\\Energy consumption_adjusted_1_2_Y82_db\\" + str(county_num) + "\\SC_opp" + tcnm + '\\' + fname
                fc_path = outputdir + r"Ford_CC\\Energy consumption_adjusted_1_2_Y82_db\\" + str(county_num) + "\\FC_opp" + tcnm + '\\' + fname
                sc_crarr = get_or_load_csv(sc_key, sc_path, col='slowCR', as_numpy=True)
                fc_crarr = get_or_load_csv(fc_key, fc_path, col='fastCR', as_numpy=True)
                netnl_key = f"netnl_{county_num}_{building_id}_{fname}_{homeelec_sufix}_{homesimnum_sufix}_{coverage_sufix}_125PVhhec"
                netnl_path = outputdir + rf"PVEV\\ResStock\\netnl{homeelec_sufix}_Y82_PV{homesimnum_sufix}{coverage_sufix}_125PVhhec\\" + str(county_num) + "_1_0\\" + str(building_id) + '_' + fname
                netnlarr = get_or_load_csv(netnl_key, netnl_path, col='NegNL', as_numpy=True)
                sc_crarr = EV_date_adjust(sc_crarr)
                fc_crarr = EV_date_adjust(fc_crarr)
                netnlarr = EV_date_adjust(netnlarr)
                hr = [str(i + 1) for i in range(8760)]
                slowCR = dict(zip(hr, sc_crarr))
                fastCR = dict(zip(hr, fc_crarr))
                DGcost = dict(zip(hr, DGcostarr))
                sc_ec = cost
                slowEC = dict(zip(hr, sc_ec))
                fc_ec = cost + 20
                fastEC = dict(zip(hr, fc_ec))
                negnlarr = dict(zip(hr, netnlarr))
            except Exception as e:
                logger.error(f"Error in file setup for county_num {county_num}, fname {fname}: {e}")
                print(f"Error in file setup for county_num {county_num}, fname {fname}: {e}", file=sys.stderr)
                continue
            try:
                soc_key = f"soc_{county_num}_{fname}"
                soc_path = outputdir + r"Ford_CC\\Energy consumption_adjusted_1_2_Y82_db\\" + str(county_num) + "\\" + fname
                soc_drop = get_or_load_csv(soc_key, soc_path, col='SOC', as_numpy=True)
                soc_drop = EV_date_adjust(soc_drop)
                soc_drop = dict(zip(hr, soc_drop))
                fname_evhh = fname[:-8] + '_50' + fname[-4:]
            except Exception as e:
                logger.error(f"Error in cambium or soc_drop for county_num {county_num}, fname {fname}: {e}")
                print(f"Error in cambium or soc_drop for county_num {county_num}, fname {fname}: {e}", file=sys.stderr)
                continue

            ttncycle = 1
            try:
                if scen == 'cc':
                    sd_drarr = np.zeros(8760)
                else:
                    sd_drarr = pd.read_csv(outputdir + rf'PVEV\\ResStock\\dischargecons{homeelec_sufix}_Y82_PV{homesimnum_sufix}{coverage_sufix}_125PVhhec\\' + str(county_num) + '_1_0\\' + str(building_id) + '_' + fname)['CR'].to_numpy()
                    sd_drarr = EV_date_adjust(sd_drarr)
                CR = dict(zip(hr, sd_drarr))
                totalresults = [[], [], [], [], [], []]
                vIni_val = SOC[cari] * 0.8
            except Exception as e:
                logger.error(f"Error in dischargecons for county_num {county_num}, fname {fname}: {e}")
                print(f"Error in dischargecons for county_num {county_num}, fname {fname}: {e}", file=sys.stderr)
                continue
            for cyclei in range(ttncycle):
                try:
                    ws = GamsWorkspace(system_directory=system_directory)
                    db = ws.add_database()
                    vIni = db.add_parameter('vIni', 0, 'Initial SOC in kWh')
                    vIni.add_record().value = vIni_val
                    if cyclei != ttncycle - 1:
                        hr1 = hr[cyclei * 24 * 10:cyclei * 24 * 10 + 24 * 20]
                    else:
                        hr1 = hr[cyclei * 24 * 10:8760]

                    h = db.add_set("h", 1, "Hours")
                    sc_cr = db.add_parameter_dc("sc_cr", [h], "upper slow charging rate of hour h")
                    fc_cr = db.add_parameter_dc("fc_cr", [h], "upper fast charging rate of hour h")
                    sc_ec = db.add_parameter_dc("sc_ec", [h], "slow charging energy cost rate of hour h")
                    fc_ec = db.add_parameter_dc("fc_ec", [h], "fast charging energy cost rate of hour h")
                    SDrop = db.add_parameter_dc("SDrop", [h], "SOC drop in hour h")
                    sd_dr = db.add_parameter_dc("sd_dr", [h], "discharge upper limit at hour h (precalculated, 0 if negative netload, else home load-PVout)")
                    negnl = db.add_parameter_dc("negnl", [h], "absolute value of netload at hour h if NEGATIVE, else 0")
                    PV_ec = db.add_parameter_dc("PV_ec", [h], "PV export electricity price at hour h")
                    for hour in hr1:
                        h.add_record(hour)
                        sc_cr.add_record(hour).value = slowCR[hour]
                        sd_dr.add_record(hour).value = CR[hour]
                        fc_cr.add_record(hour).value = fastCR[hour]
                        SDrop.add_record(hour).value = soc_drop[hour]
                        sc_ec.add_record(hour).value = slowEC[hour]
                        fc_ec.add_record(hour).value = fastEC[hour]
                        negnl.add_record(hour).value = negnlarr[hour]
                        PV_ec.add_record(hour).value = DGcost[hour]
                    job = ws.add_job_from_string(get_model_text())
                    opt = ws.add_options()
                    opt.defines["gdxincname"] = db.name

                    job.run(opt, databases=db)
                    # GAMS do not keep temp files: remove all clearing of GAMS temp files
                    try:
                        modelstat = job.out_db["modelStatus"].first_record().value
                        # GAMS modelstat = 1 means optimal, 2 locally optimal, <1 or >2 are warnings
                        if modelstat != 1:
                            logger.error(f"GAMS model status not optimal for county_num {county_num}, fname {fname}, cycle {cyclei}: modelstat={modelstat}")
                            print(f"Warning: GAMS model status not optimal for county_num {county_num}, fname {fname}, cycle {cyclei}: modelstat={modelstat}", file=sys.stderr)
                    except Exception as modelstat_e:
                        logger.error(f"Could not check GAMS modelstat for county_num {county_num}, fname {fname}, cycle {cyclei}: {modelstat_e}")
                        print(f"Warning: Could not check GAMS modelstat for county_num {county_num}, fname {fname}, cycle {cyclei}: {modelstat_e}", file=sys.stderr)
                    results = []
                    symbs = ['sc', 'fc', 'vSOC', 'scneg', 'sd', 'Expo']
                    for symbi in range(6):
                        result = []
                        for ii in job.out_db[symbs[symbi]]:
                            result.append(ii.level)
                        results.append(result)
                        if cyclei != ttncycle - 1:
                            totalresults[symbi] = np.concatenate((np.array(totalresults[symbi]), np.array(result[0:24*10])))
                        else:
                            totalresults[symbi] = np.concatenate((np.array(totalresults[symbi]), np.array(result)))
                    if cyclei != ttncycle - 1:
                        vIni_val = results[2][24*10-1]
                    
                    # No temp file cleanup needed: GAMS does not keep temp files
                except Exception as e:
                    logger.error(f"Error in GAMS optimization for county_num {county_num}, fname {fname}, cycle {cyclei}: {e}")
                    print(f"Error in GAMS optimization for county_num {county_num}, fname {fname}, cycle {cyclei}: {e}", file=sys.stderr)
                    continue
            try:
                df_res = pd.DataFrame(totalresults, index=['slowCR', 'fastCR', 'vSOC', 'scneg', 'sd', 'Exp'], columns=[i for i in range(8760)])
                try:
                    os.mkdir(outputdir + rf'PVEV\\SimulationResults\\Result_{scen}_125PVhhec_fullyear_lmpdg\\')
                except:
                    pass
                try:
                    os.mkdir(outputdir + rf'PVEV\\SimulationResults\\Result_{scen}_125PVhhec_fullyear_lmpdg\\Results_80_Y82{homeelec_sufix}{homesimnum_sufix}{coverage_sufix}{year}\\')
                except:
                    pass
                try:
                    os.mkdir(outputdir + rf'PVEV\\SimulationResults\\Result_{scen}_125PVhhec_fullyear_lmpdg\\Results_80_Y82{homeelec_sufix}{homesimnum_sufix}{coverage_sufix}{year}\\' + str(county_num) + '_1_0' + r'\\')
                except:
                    pass
                # Only log errors, so remove info log here
                print(county_num, building_id, fname)
                df_res.T.to_csv(outputdir + rf'PVEV\\SimulationResults\\Result_{scen}_125PVhhec_fullyear_lmpdg\\Results_80_Y82{homeelec_sufix}{homesimnum_sufix}{coverage_sufix}{year}\\' + str(county_num) + '_1_0' + r'\\' + str(building_id) + '_' + fname_evhh)
            except Exception as e:
                logger.error(f"Error saving results for county_num {county_num}, fname {fname}: {e}")
                print(f"Error saving results for county_num {county_num}, fname {fname}: {e}", file=sys.stderr)
                continue

def CC_wrapper(args):
    # Helper for parallel execution
    return CC(*args)

if __name__ == '__main__':
    # Set up shared cache for all processes
    manager = Manager()
    shared_cache = manager.dict()
    root_loc = r'C:\Users\jiahuic\University of Michigan Dropbox\Jiahui Chen\\'
    ctydf = pd.read_csv(root_loc + r'Ford_CC\\2020_Gaz_counties_national_0728_tempreg.csv')
    ctdf_urdb = pd.read_csv(root_loc + r"PVEV\\utility_matching\Rates_dgrules_tou.csv")
    system_directory = r'C:\GAMS\42'
    homesimnum_sufix = '_5homes_percentile'
    coverage_sufix = '_70roofcover'
    import warnings
    warnings.filterwarnings("ignore")
    # Disable GAMS warning of mismatched version

    # Only log errors, so remove info log here

    # Use all available logical CPUs for parallelism
    num_workers = multiprocessing.cpu_count()  # 48 on your system

    # CC(133, 134, 2030, ctydf, root_loc, ctdf_urdb, system_directory, ['','_noelec'][0], homesimnum_sufix, coverage_sufix)
    # Calculate chunk size for each worker
    total_counties = 432
    # CC(120, 121, 2040, ctydf, root_loc, ctdf_urdb, system_directory, ['','_noelec'][0], homesimnum_sufix, coverage_sufix,'v2h')

    for scen in ['cc', 'v2h']:
        for homeelec_sufixi in [0,1]:
            homeelec_sufix = ['','_noelec'][homeelec_sufixi]
            for yea in [2024, 2030, 2040]:
                # Prepare argument list for each worker
                chunk_size = total_counties // num_workers
                args_list = []
                for i in range(num_workers):
                    start = i * chunk_size
                    if i == num_workers - 1:
                        end = total_counties
                    else:
                        end = (i + 1) * chunk_size
                    args_list.append((start, end, yea, ctydf, root_loc, ctdf_urdb, system_directory, homeelec_sufix, homesimnum_sufix, coverage_sufix, scen))
                # Only log errors, so remove info log here
                # Use ProcessPoolExecutor for better CPU utilization
                with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
                    futures = [executor.submit(CC_wrapper, args) for args in args_list]
                    for future in concurrent.futures.as_completed(futures):
                        try:
                            future.result()
                        except Exception as e:
                            logger.error(f"Error in parallel execution: {e}")
                            print(f"Error in parallel execution: {e}", file=sys.stderr)
                            continue