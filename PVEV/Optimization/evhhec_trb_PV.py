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

def xmlid_extract(homesimnum_sufix):
    lst = [[] for i in range(3)]
    # wintage: built after 2000, area 0-2500
    for i in range(432):
        fnmlst = os.listdir(rf'C:\Users\jiahuic\University of Michigan Dropbox\Jiahui Chen\Ford_CC\ResStock\Indi_Hourly{homesimnum_sufix}\{i}_1_0\\')
        fnmlst_1 = [ele.split('_')[0][2:] for ele in fnmlst]
        fnmlst_1 = [ele.zfill(7) for ele in fnmlst_1]
        lst[0] = lst[0] + [ ("bldg"+ ele + "-up00.zip") for ele in fnmlst_1]
        lst[1] = lst[1] + [i] * len(fnmlst)
        lst[2] = lst[2] + [ (ele.split('_')[1][:-4]) for ele in fnmlst]
    df = pd.DataFrame(lst)
    df1 = df.T
    df1.columns=['xmlid', 'tempreg', 'percentile']
    df1.to_csv(rf'C:\Users\jiahuic\University of Michigan Dropbox\Jiahui Chen\PVEV\pv_inputs\xmlid{homesimnum_sufix}.csv')
# xmlid to solar_input
def solar_input(homesimnum_sufix):
    import os
    import pandas as pd
    from bs4 import BeautifulSoup as bs #import bs, might need to download it seperately on pc
    Metadata = pd.read_csv(rootdir + rf'Ford_CC\ResStock\Aggregate_vintage_08.csv')
    path = rootdir + r'PVEV\pv_inputs\HomeResStock\\' #change to your filefolders
    xml_files = pd.read_csv(rootdir + rf'PVEV\pv_inputs\xmlid{homesimnum_sufix}.csv')['xmlid'].to_list()
    # xml_files = [f for f in os.listdir(path) if f.endswith('.xml')] #m
    result_list = []
    for xml_file in xml_files:
        if 'bldg0502293-up00.zip' in xml_file:
            print(xml_file)
        xml_file = xml_file + ".xml"
        xml_path = os.path.join(path, xml_file)
        xml_name = xml_path.replace(path, '')
        bldgid = xml_file.split('bldg')[1].split('-up')[0].lstrip('0')
        # print(Metadata[Metadata['bldg_id'] == int(bldgid)].index.tolist())
        meta_index = Metadata[Metadata['bldg_id'] == int(bldgid)].index.tolist()[0]
        weather_file_latitude = Metadata['in.weather_file_latitude'][meta_index]
        weather_file_longitude = Metadata['in.weather_file_longitude'][meta_index]
        with open(xml_path, 'r') as f:
            content = f.readlines()
        content = "".join(content)
        bs_content = bs(content, "xml")
        result0 = bs_content.find("StateCode") #extract statecode
        result1 = result0.text
        # For BeautifulSoup (Python):
        result0U = bs_content.find("UTCOffset")
        result1U = result0U.text
        result00 = bs_content.find("ZipCode") #extract zipcode
        result11 = result00.text
        results = bs_content.find_all("Roof") #extract all roof information
        results1 = bs_content.find_all("WeatherStation") #extract the name of corresponding weatherfile
        file_result_list = []
        for k, result in enumerate(results1):
            weather_values = []
            weather_tags = result.find_all("Name")
            for weather_tag in weather_tags:
                weather_values.append(weather_tag.text)
        for i, result in enumerate(results):
            area_values = []
            azimuth_values = []
            orientation_values = []

            area_tags = result.find_all("Area") #extract all areas
            azimuth_tags = result.find_all("Azimuth") #extract all azimuth
            orientation_tags = result.find_all("Orientation") #extract all orientation

            for area_tag in area_tags:
                area_values.append(area_tag.text)
            for azimuth_tag in azimuth_tags:
                azimuth_values.append(azimuth_tag.text)
            for orientation_tag in orientation_tags:
                orientation_values.append(orientation_tag.text)

            result_dict = {
                'Filename': xml_name,
                'Roof_num': i,
                'Statecode': result1,
                'UTCTimezone': result1U,
                'Zipcode': result11,
                'Area': area_values[0],
                'Azimuth': azimuth_values[0] if azimuth_values else '180',
                'Orientation': orientation_values[0] if orientation_values else 'south',
                'Weather': weather_values[0],  # Add weather_values here
                'weather_file_latitude' : weather_file_latitude,
                'weather_file_longitude' : weather_file_longitude
            }

            file_result_list.append(result_dict)
        result_list.extend(file_result_list)
    # # Create DataFrame from the list of dictionaries
    buildingdata = pd.DataFrame(result_list)
    # Reset the index for each XML file
    buildingdata = buildingdata.groupby('Filename').apply(lambda x: x.reset_index(drop=True))
    # Print the dataframe
    # print(buildingdata)
    buildingdata.to_csv(rootdir + rf'PVEV\pv_inputs\solar_input{homesimnum_sufix}.csv')
# download weather data
def download_weather_data(id):

    
    sample = f'{id}_2018.csv' #make sure they have the same format

    data_path = path+sample
    print(data_path)
    data = pd.read_csv(data_path)

    save = content+sample
    data.to_csv(save)
# PV output simulation
def PVoutput(coverage_sufix,homesimnum_sufix):
    # Read the input data
    missingcalc0 = pd.read_csv(
        rootdir +rf'PVEV\pv_inputs\solar_input{homesimnum_sufix}.csv'
    )
    
    efficiency = 0.2  # conversion efficiency
    roof_coverage = float(coverage_sufix[1:3])/100
    area_required = 1 / efficiency  # area required to generate 1kw
    
    # Filter data based on azimuth
    missingcalc1 = missingcalc0[(missingcalc0['Azimuth'] >= 135) & (missingcalc0['Azimuth'] <= 315)]
    unique_filenames = missingcalc1['Filename'].unique()
    
    # Read the filename-tempreg csv
    tempreg = pd.read_csv(
        rootdir +rf'PVEV\pv_inputs\xmlid{homesimnum_sufix}.csv'
    )
    
    for filename in unique_filenames:
        # Get tempreg values for this filename
        xmlid = filename.replace('.xml', '')
        tempreg_values = tempreg[tempreg['xmlid'] == xmlid]['tempreg'].values
        
        for tempreg_value in tempreg_values:
            # Get percentile values
            quant_values = tempreg[
                (tempreg['xmlid'] == xmlid) & (tempreg['tempreg'] == tempreg_value)
            ]['percentile'].values
            
            # Filter data for current filename
            missingcalc = missingcalc1[missingcalc1['Filename'] == filename]
            
            for i in range(len(missingcalc)):
                # print(f"Processing data for filename: {filename}")
                
                # Get building data
                longitude = float(missingcalc.iloc[i]['weather_file_longitude'])
                latitude = float(missingcalc.iloc[i]['weather_file_latitude'])
                weatherfilename = missingcalc.iloc[i]['Weather']
                
                sitename = rootdir +rf'PVEV/pv_inputs/weatherdata/{weatherfilename}_2018.csv'
                # print(sitename)
                if os.path.exists(sitename):
                    # Read the weather file and perform calculations
                    site = pd.read_csv(sitename)
                    
                    # Convert date_time to datetime
                    site['date_time'] = pd.to_datetime(site['date_time'], format='%Y-%m-%d %H:%M:%S', utc=True)
                    site['year'] = site['date_time'].dt.year
                    site['month'] = site['date_time'].dt.month
                    site['day'] = site['date_time'].dt.day
                    site['hour'] = site['date_time'].dt.hour
                    
                    # Calculate solar declination
                    site['delta'] = (23.45 * np.sin((360 / 365) * (284 + site['day']) * np.pi / 180)) * np.pi / 180
                    
                    beta = float(latitude)
                    beta_r = float(latitude * np.pi / 180)
                    phi = float(latitude * np.pi / 180)
                    
                    # Calculate angle of elevation in radians
                    site['alpha'] = site['delta'] + np.pi / 2 - phi
                    
                    deltaTGMT = missingcalc.iloc[i]['UTCTimezone']
                    lstm = 15 * deltaTGMT
                    site['b'] = 360 / 365 * (site['day'] - 81) * np.pi / 180
                    site['eot'] = 9.87 * np.sin(2 * site['b']) - 7.53 * np.cos(site['b']) - 1.5 * np.sin(site['b'])
                    site['tc'] = 4 * (longitude - lstm) + site['eot']
                    
                    # Convert tc from minutes to timedelta
                    site['lst'] = site['date_time'] + pd.to_timedelta(site['tc'], unit='minutes')
                    
                    # Create noon time for each day
                    site['noon'] = pd.to_datetime(
                        site[['year', 'month', 'day']].assign(hour=12, minute=0, second=0),
                        utc=True
                    )
                    
                    # Calculate hour angle
                    site['hra'] = 15 * (site['lst'] - site['noon']).dt.total_seconds() / 3600 * np.pi / 180
                    
                    # Calculate azimuth angle
                    if 'psi' not in missingcalc.columns:
                        missingcalc = missingcalc.assign(psi=np.zeros(missingcalc.shape[0]))
                    psi = np.deg2rad(180 - missingcalc.iloc[i]['Azimuth'])
                    missingcalc.at[missingcalc.index[i], 'psi'] = psi
                    
                    # Calculate beam radiation
                    site['beam'] = site['Direct Normal Radiation [W/m2]'] * (
                        np.sin(site['delta']) * np.sin(phi) * np.cos(beta_r) -
                        np.sin(site['delta']) * np.cos(phi) * np.sin(beta_r) * np.cos(psi) +
                        np.cos(site['delta']) * np.cos(phi) * np.cos(beta_r) * np.cos(site['hra']) +
                        np.cos(site['delta']) * np.sin(phi) * np.sin(beta_r) * np.cos(psi) * np.cos(site['hra']) +
                        np.cos(site['delta']) * np.sin(psi) * np.sin(site['hra']) * np.sin(beta_r)
                    )
                    
                    # Ensure beam radiation is non-negative
                    site['beam'] = np.maximum(0, site['beam'])
                    
                    # Calculate diffuse radiation
                    site['diffuse'] = site['Diffuse Horizontal Radiation [W/m2]'] * (180 - beta) / 180
                    
                    # Calculate total solar energy
                    site['solarE'] = (site['beam'] + site['diffuse']) / 1000
                    
                    # Calculate actual energy
                    inusearea = missingcalc.iloc[i]['Area'] * roof_coverage * 0.09290304
                    actualE = (inusearea / area_required) * site['solarE']
                    
                    filename_col = missingcalc.iloc[i]['Filename']
                    # print(f"{filename_col}, {i}")
                    
                    if i == 0:
                        # Create new dataframe for first iteration
                        actualE_df = pd.DataFrame({'actualE': actualE})
                        actualE_df.columns = [filename_col]
                    else:
                        # Add to existing dataframe
                        actualE_df[filename_col] = actualE_df[filename_col] + actualE
                
                else:
                    print(f"Weather file not found for Building: {i}")
            
            # Create output directory
            dir_path = os.path.join(
                rootdir +rf'PVEV/PVsimulation/2018simu{homesimnum_sufix}{coverage_sufix}',
                str(tempreg_value)+'\\'
            )
            
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
            
            # Extract building ID and create output filename
            bldgid = filename.replace('bldg', '').split('-')[0].lstrip('0')
            
            for quant_value in quant_values:
                output_file = os.path.join(dir_path, f"{bldgid}_{quant_value}.csv")
                actualE_df.to_csv(output_file, index=False)

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
                    os.mkdir(rootdir +rf'PVEV\ResStock\dischargecons{homeelec_sufix}_Y82_PV{homesimnum_sufix}{coverage_sufix}\\')
                except:pass
                try:
                    os.mkdir(rootdir +rf'PVEV\ResStock\netnl{homeelec_sufix}_Y82_PV{homesimnum_sufix}{coverage_sufix}\\')
                except:pass
                try:
                    os.mkdir(rootdir +rf'PVEV\ResStock\dischargecons{homeelec_sufix}_Y82_PV{homesimnum_sufix}{coverage_sufix}\\'+str(county_num)+'_'+
                                                                str(i1)+'_'+str(i2)+'\\')
                except:pass
                try:
                    os.mkdir(rootdir +rf'PVEV\ResStock\netnl{homeelec_sufix}_Y82_PV{homesimnum_sufix}{coverage_sufix}\\'+str(county_num)+'_'+
                                                                str(i1)+'_'+str(i2)+'\\')
                except:pass
                # fnm = next(f for f in fnms if '_50.csv' in f) singlerep
                for fnm in fnms:
                    hhec = pd.read_csv(rootdir +rf'Ford_CC\ResStock\{energy_consumption}{homesimnum_sufix}\\'+str(county_num)
                                +'_'+str(i1)+'_'+str(i2)+'\\'+fnm)['0'].to_numpy()
                    fnm_2 = fnm[2:][:-4] + '.csv'
                    PVout = pd.read_csv(rootdir +rf'PVEV\PVsimulation\2018simu{homesimnum_sufix}{coverage_sufix}\\'+str(county_num)+'\\'+fnm_2)
                    PVout.columns = ['PVout']
                    PVout = PVout['PVout'].to_numpy()
                    for fnm_ev_i in range(len(fnms_ev)):
                        evcr = pd.read_csv(rootdir +r'Ford_CC\Energy consumption_adjusted_1_2_Y82_db\\'+str(county_num)+'\\SC_opp_SUV\\'+fnms_ev[fnm_ev_i])['slowCR'].to_numpy()
                        evcr = EV_date_adjust(evcr)
                        cons = np.zeros(8760)
                        cons1 = np.zeros(8760)
                        for i in range(8760):
                            cons[i] = min(evcr[i],max(0,hhec[i]-PVout[i]))
                            cons1[i] = max(PVout[i] - hhec[i],0)
                        pd.DataFrame(cons,columns=['CR']).to_csv(rootdir +rf'PVEV\ResStock\dischargecons{homeelec_sufix}_Y82_PV{homesimnum_sufix}{coverage_sufix}\\'+str(county_num)+'_'+
                                                                str(i1)+'_'+str(i2)+'\\'+ fnm_2[:-6]+'_'+
                                                                fnms_ev[fnm_ev_i])
                        pd.DataFrame(cons1,columns=['NegNL']).to_csv(rootdir +rf'PVEV\ResStock\netnl{homeelec_sufix}_Y82_PV{homesimnum_sufix}{coverage_sufix}\\'+str(county_num)+'_'+
                                                                str(i1)+'_'+str(i2)+'\\'+ fnm_2[:-6]+'_'+
                                                                fnms_ev[fnm_ev_i])
if __name__ == '__main__':
    import warnings
    warnings.filterwarnings("ignore")
    # CC(0,1,1,'_90roofcover')
    homesimnum_sufix = '_5homes_percentile'
    xmlid_extract(homesimnum_sufix)

    solar_input(homesimnum_sufix)
    # # download weather data
    ids = pd.read_csv(rootdir + rf'PVEV\pv_inputs\solar_input{homesimnum_sufix}.csv')['Weather'].to_numpy()

    content=rootdir + r'PVEV\pv_inputs\\weatherdata\\'
    #example:'https://oedi-data-lake.s3.amazonaws.com/nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/2023/comstock_amy2018_release_1/weather/amy2018/G0100010_2018.csv'
    path = 'https://oedi-data-lake.s3.amazonaws.com/nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/2023/comstock_amy2018_release_1/weather/amy2018/' #change upgrade= to number

    from concurrent.futures import ThreadPoolExecutor, as_completed
    max_workers = min(8, len(ids))  # Use up to 8 threads or as many as needed
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(download_weather_data, i) for i in ids]
        for future in as_completed(futures):
            result = future.result()
    coverage_sufix = '_70roofcover'
    # for coverage_sufix in ['_70roofcover']:
    PVoutput(coverage_sufix,homesimnum_sufix)
    # homeelec_sufixi = 0
    # CC(0,1,homeelec_sufixi,homesimnum_sufix,coverage_sufix)
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