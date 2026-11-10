# for PVEV project, calculate the discharge upper limit at hour h (precalculated, 0 if neaative netload, else home load-PVout)
# discharge upper limit at hour h (precalculated, 0 if neaative netload, else home load-PVout)
# all cost in cents/kWh
# EV time series: 2021 date
# URDB: 2025 date
# Home: 2018 date
# harmonize EV and URDB to home time series
from multiprocessing import Process
import pandas as pd 
import numpy as np
import os
rootdir = r'C:\Users\jiahuic\University of Michigan Dropbox\Jiahui Chen\\'
# xmlid
import os
import pandas as pd
import numpy as np


def EV_date_adjust(arr):
    df2021 = arr
    df2021_1 = np.concatenate((df2021[:1*24], df2021[-4*24:], df2021[1*24:-4*24]))
    for i,j in [(14,21),(147,154),(184,189),(245,252),(358,361),(325,332)]:
        for hi in range(24):
            df2021_1[i*24+hi], df2021_1[j*24+hi] = df2021_1[j*24+hi], df2021_1[i*24+hi] 
    return df2021_1
def Rate_date_adjust(arr):
    df2025 = arr
    df2025_1 = np.concatenate((df2025[:1*24], df2025[-2*24:], df2025[1*24:-2*24]))
    return df2025_1
def CC(num0,num1,homeelec_sufixi,homesimnum_sufix,coverage_sufix):
    energy_consumption = ['Indi_Hourly','indi_noelec_fossilfuel'][homeelec_sufixi]
    for county_num in range(num0,num1):
        for i1 in [1]:
            for i2 in [0]:
                fnms = os.listdir(rootdir +rf'Ford_CC\ResStock\{energy_consumption}{homesimnum_sufix}\\'+str(county_num)
                                +'_'+str(i1)+'_'+str(i2))
                fnms_ev = ['0_0_0_0_0_soc.csv', '0_0_0_10_0_soc.csv', '0_0_0_11_0_soc.csv', '0_0_0_12_0_soc.csv', '0_0_0_13_0_soc.csv', '0_0_0_14_0_soc.csv', '0_0_0_15_0_soc.csv', '0_0_0_16_0_soc.csv', '0_0_0_17_0_soc.csv', '0_0_0_18_0_soc.csv', '0_0_0_19_0_soc.csv', '0_0_0_1_0_soc.csv', '0_0_0_20_0_soc.csv', '0_0_0_21_0_soc.csv', '0_0_0_22_0_soc.csv'][:5]
                # fnms_ev = [i[6:-10] for i in fnms_ev]
                # fnms_ev = [i for i in fnms_ev if i not in os.listdir(r'C:\Users\jiahuic\Dropbox (University of Michigan)\PVEV\\Results\Results_80_82\\'+str(county_num)+r'\\')]
                homeelec_sufix = ['','_noelec'][homeelec_sufixi]
                try:
                    os.mkdir(rootdir +rf'PVEV\ResStock\dischargecons{homeelec_sufix}_Y82_PV{homesimnum_sufix}{coverage_sufix}_EVbase\\')
                except:pass

                try:
                    os.mkdir(rootdir +rf'PVEV\ResStock\dischargecons{homeelec_sufix}_Y82_PV{homesimnum_sufix}{coverage_sufix}_EVbase\\'+str(county_num)+'_'+
                                                                str(i1)+'_'+str(i2)+'\\')
                except:pass

                # fnm = next(f for f in fnms if '_50.csv' in f) singlerep
                for fnm in fnms:
                    fnm_2 = fnm[2:][:-4] + '.csv'
                    hhec = pd.read_csv(rootdir +rf'Ford_CC\ResStock\{energy_consumption}{homesimnum_sufix}\\'+str(county_num)
                                +'_'+str(i1)+'_'+str(i2)+'\\'+fnm)['0'].to_numpy()
                    for fnm_ev_i in range(len(fnms_ev)):
                        evcr = pd.read_csv(rootdir +r'Ford_CC\Energy consumption_adjusted_1_2_Y82_db\\'+str(county_num)+'\\SC_opp_SUV\\'+fnms_ev[fnm_ev_i])['slowCR'].to_numpy()
                        # evcr = EV_date_adjust(evcr)
                        cons = np.zeros(8760)
                        for i in range(8760):
                            cons[i] = min(evcr[i],hhec[i])
                        pd.DataFrame(cons,columns=['CR']).to_csv(rootdir +rf'PVEV\ResStock\dischargecons{homeelec_sufix}_Y82_PV{homesimnum_sufix}{coverage_sufix}_EVbase\\'+str(county_num)+'_'+
                                                                str(i1)+'_'+str(i2)+'\\'+ fnm_2[:-6]+'_'+
                                                                fnms_ev[fnm_ev_i])

if __name__ == '__main__':
    import warnings
    warnings.filterwarnings("ignore")
    homesimnum_sufix = '_5homes_percentile'
    # xmlid_extract(homesimnum_sufix)

    # solar_input(homesimnum_sufix)
    # # # download weather data
    # ids = pd.read_csv(rootdir + rf'PVEV\pv_inputs\solar_input{homesimnum_sufix}.csv')['Weather'].to_numpy()

    # content=rootdir + r'PVEV\pv_inputs\\weatherdata\\'
    # #example:'https://oedi-data-lake.s3.amazonaws.com/nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/2023/comstock_amy2018_release_1/weather/amy2018/G0100010_2018.csv'
    # path = 'https://oedi-data-lake.s3.amazonaws.com/nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/2023/comstock_amy2018_release_1/weather/amy2018/' #change upgrade= to number

    # from concurrent.futures import ThreadPoolExecutor, as_completed
    # max_workers = min(8, len(ids))  # Use up to 8 threads or as many as needed
    # with ThreadPoolExecutor(max_workers=max_workers) as executor:
    #     futures = [executor.submit(download_weather_data, i) for i in ids]
    #     for future in as_completed(futures):
    #         result = future.result()
    coverage_sufix = '_70roofcover'
    # for coverage_sufix in ['_70roofcover']:
    # PVoutput(coverage_sufix,homesimnum_sufix)
    # homeelec_sufixi = 0
    for homeelec_sufixi in [0,1]:
        procs = []

        for i in range(48):
            if i != 47:
                p = Process(target=CC, args=([i*9,i*9+9,homeelec_sufixi,homesimnum_sufix,coverage_sufix]))
            else:
                p = Process(target=CC,args=([i*9,432,homeelec_sufixi,homesimnum_sufix,coverage_sufix]))
            p.start()
            procs.append(p)
        for p in procs:
            p.join() # this blocks until the process terminates 