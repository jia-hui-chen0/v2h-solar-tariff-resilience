import os
import pandas as pd
import requests
import geopy.distance
import numpy as np
import requests
import zipfile
import io
from bs4 import BeautifulSoup as bs  # import bs, might need to download it separately on pc
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import Pool
import time
from multiprocessing import Process, Queue

def func(num0, num1, weatnum, metdf1, closest_indicesnum, basedir):
    path = 'https://oedi-data-lake.s3.amazonaws.com/nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/2022/resstock_amy2018_release_1/building_energy_models/upgrade%3D0/'
    areasl = [0, 2500]
    areasu = [2500, 5000]
    vintgrp = [['<1940', '1940-59', '1960-79', '1980-99'], ['2000-09', '2010s']]
    num_samples = 5  # Number of samples to select
    quantilepcts = [0.1, 0.3, 0.5, 0.7, 0.9]  # 10th, 30th, 50th, 70th, 90th percentiles

    for regi in range(num0, num1):
        metdf2 = metdf1.loc[metdf1['latlon'] == np.unique(metdf1['latlon'])[int(weatnum[closest_indicesnum - 1][regi])]]
        for i in range(closest_indicesnum):
            if weatnum[i][regi] != -1:
                metdf20 = metdf1.loc[metdf1['latlon'] == np.unique(metdf1['latlon'])[int(weatnum[i][regi])]]
                metdf2 = pd.concat([metdf2, metdf20])
        try:
            os.mkdir(basedir + rf'Ford_CC\ResStock\Individuals_noelec_{num_samples}homes_percentile\\')
        except:
            pass
        try:
            os.mkdir(basedir + rf'Ford_CC\ResStock\Individuals_{num_samples}homes_percentile\\')
        except:
            pass
        for vini in [1]:
            for areai in [0]:
                try:
                    os.mkdir(basedir + rf'Ford_CC\ResStock\Individuals_noelec_{num_samples}homes_percentile\\' + str(regi) + '_' + str(vini) + '_' + str(areai))
                except:
                    pass
                try:
                    os.mkdir(basedir + rf'Ford_CC\ResStock\Individuals_{num_samples}homes_percentile\\' + str(regi) + '_' + str(vini) + '_' + str(areai))
                except:
                    pass
                metdf3 = metdf2.loc[(metdf2['in.sqft'] >= areasl[areai]) & (metdf2['in.sqft'] <= areasu[areai])]
                metdf3 = metdf3.loc[metdf3['in.vintage_acs'].isin(vintgrp[vini])]
                metdf3 = metdf3[~metdf3.index.duplicated(keep='first')]
                # loop until all bldg chosen have roofs
                # Remove buildings without roof info first, then take index list
                buildings_with_roof = []
                for idx in metdf3.index:
                    building_id = metdf3['bldg_id'][idx]
                    name = 'bldg' + str(building_id).zfill(7) + r"-up00.zip"
                    full_url = path + name
                    r = requests.get(full_url)
                    r.raise_for_status()
                    with zipfile.ZipFile(io.BytesIO(r.content)) as zip_file:
                        xml_file_name = "in.xml"
                        with zip_file.open(xml_file_name) as xml_file:
                            out_path = os.path.join(basedir, r'PVEV\\pv_inputs\HomeResStock', name + '.xml')
                            with open(out_path, "wb") as f:
                                f.write(xml_file.read())
                    with open(out_path, 'r') as f:
                        content = f.readlines()
                    content = "".join(content)
                    bs_content = bs(content, "xml")
                    results = bs_content.find_all("Roof")  # extract all roof information
                    if len(results) > 0:
                        buildings_with_roof.append(idx)
                # Now, only keep rows with roof info
                metdf3 = metdf3.loc[buildings_with_roof]
                # Now select indices
                if metdf3.shape[0] < num_samples:
                    indices = metdf3.index.tolist()
                else:
                    # Use out.electricity.total.energy_consumption.kwh as the sort key
                    sorted_df = metdf3.sort_values('out.electricity.total.energy_consumption.kwh')
                    index_list = sorted_df.index.tolist()
                    if len(index_list) <= 5:
                        indices = index_list
                    else:
                        step = len(index_list) // 5
                        indices = [index_list[i * step] for i in range(5)]
                        # If not enough due to rounding, fill from the end
                        while len(indices) < 5:
                            indices.append(index_list[-1])

                for indi, ind in enumerate(indices):
                    state = metdf3['in.state'][ind]
                    building_id = metdf3['bldg_id'][ind]

                    # noelec
                    url = "https://oedi-data-lake.s3.amazonaws.com/nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/2022/resstock_amy2018_release_1/timeseries_individual_buildings/by_state/upgrade=0/state=" + state + "/" + str(building_id) + "-0" + ".parquet"
                    query_parameters = {"downloadformat": "parquet"}
                    response = requests.get(url, params=query_parameters)
                    with open(
                        basedir + rf"Ford_CC\ResStock\Individuals_noelec_{num_samples}homes_percentile\\" + str(regi) + '_' + str(vini) + '_' + str(areai)
                        + '\\' + state + str(building_id) + '_' + str(indi) + r".parquet", mode="wb"
                    ) as file:
                        file.write(response.content)
                    # elec
                    url = "https://oedi-data-lake.s3.amazonaws.com/nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/2022/resstock_amy2018_release_1/timeseries_individual_buildings/by_state/upgrade=7/state=" + state + "/" + str(building_id) + "-7" + ".parquet"
                    query_parameters = {"downloadformat": "parquet"}
                    response = requests.get(url, params=query_parameters)
                    with open(
                        basedir + rf"Ford_CC\ResStock\Individuals_{num_samples}homes_percentile\\" + str(regi) + '_' + str(vini) + '_' + str(areai)
                        + '\\' + state + str(building_id) + '_' + str(indi) + r".parquet", mode="wb"
                    ) as file:
                        file.write(response.content)

if __name__ == '__main__':

    basedir = r'C:\Users\jiahuic\University of Michigan Dropbox\Jiahui Chen\\'
    metdf1 = pd.read_csv(basedir + r"Ford_CC\ResStock\Aggregate_vintage_08.csv")
    df = pd.read_csv(basedir + r'Ford_CC\\2020_Gaz_counties_national_0728_tempreg.csv')
    numtempreg = len(np.unique(df['tempreg']))
    metdf1['latlon'] = metdf1.apply(lambda x: str(x['in.weather_file_latitude']) + '_' + str(x['in.weather_file_longitude']), axis=1)
    latlon1 = [ii.split('_', 2) for ii in np.unique(metdf1['latlon'])]
    latlon = [(float(i[0]), float(i[1])) for i in latlon1]
    # weather file number
    closest_indicesnum = 6
    weatnum = [np.ones(432) * -1 for i in range(closest_indicesnum)]
    from concurrent.futures import ThreadPoolExecutor, as_completed
    homesimnum_sufix = '_5homes_percentile'
    ids = pd.read_csv(basedir + rf"PVEV\\pv_inputs\xmlid{homesimnum_sufix}.csv")["xmlid"].to_numpy() if os.path.exists(basedir + rf"PVEV\\pv_inputs\xmlid{homesimnum_sufix}.csv") else None
    content = basedir + r'PVEV\\pv_inputs\HomeResStock'
    
    for regi in range(432):
        df1 = df.loc[df['tempreg'] == np.unique(df['tempreg'])[regi]]
        lon = np.mean(df1['INTPTLONG'].to_numpy())
        lat = np.mean(df1['INTPTLAT'].to_numpy())
        dist = np.array([geopy.distance.geodesic((lat, lon), i).km for i in latlon])
        for i in range(closest_indicesnum):
            if sorted(dist)[i] <= 200:
                weatnum[i][regi] = np.where(dist == sorted(dist)[i])[0][0]
            else:
                pass
    # args = [191, 192, weatnum, metdf1, closest_indicesnum, basedir]
    # func(*args)
    import warnings
    warnings.filterwarnings("ignore")
    from concurrent.futures import ProcessPoolExecutor, as_completed
    a = 48
    b = 9
    tasks = []
    with ProcessPoolExecutor() as executor:
        for i in range(a):
            if i != a - 1:
                args = [i * b, i * b + b, weatnum, metdf1, closest_indicesnum, basedir]
            else:
                args = [i * b, 432, weatnum, metdf1, closest_indicesnum, basedir]
            tasks.append(executor.submit(func, *args))
        for future in as_completed(tasks):
            try:
                future.result()
            except Exception as exc:
                print(f'Process generated an exception: {exc}')

    # processing 
    resstockdir = basedir + r'Ford_CC\ResStock\\'
    import sys

    for fi_1 in range(2):
        try:
            os.mkdir(resstockdir + [rf'indi_noelec_fossilfuel{homesimnum_sufix}', rf'Indi_Hourly{homesimnum_sufix}'][fi_1])
        except:
            pass
    for cli in range(432):
        for vini in [1]:
            for areai in [0]:
                for fi_1 in range(2):
                    lst = os.listdir(resstockdir + [rf'Individuals_noelec{homesimnum_sufix}', rf'Individuals{homesimnum_sufix}'][fi_1] + r'\\' + str(cli) + '_' + str(vini) + '_' + str(areai))

                    for fi in range(len(lst)):
                        parquet_path = resstockdir + [rf'Individuals_noelec{homesimnum_sufix}', rf'Individuals{homesimnum_sufix}'][fi_1] + r'\\' + str(cli) + '_' + str(vini) + '_' + str(areai) + r'\\' + lst[fi]
                        try:
                            df = pd.read_parquet(parquet_path)
                        except Exception as e:
                            print(f"Error: Failed to open parquet file: {parquet_path}\nException: {e}")
                            sys.exit(1)
                        arr = np.zeros([4, 8760])
                        for hi in range(8760):
                            arr[0][hi] = sum(df['out.electricity.total.energy_consumption'][hi * 4:hi * 4 + 4])
                            arr[2][hi] = sum(df['out.fuel_oil.total.energy_consumption'][hi * 4:hi * 4 + 4])
                            arr[1][hi] = sum(df['out.natural_gas.total.energy_consumption'][hi * 4:hi * 4 + 4])
                            arr[3][hi] = sum(df['out.propane.total.energy_consumption'][hi * 4:hi * 4 + 4])
                        df1 = pd.DataFrame(np.transpose(arr))
                        try:
                            os.mkdir(resstockdir + [rf'indi_noelec_fossilfuel{homesimnum_sufix}', rf'Indi_Hourly{homesimnum_sufix}'][fi_1] + r'\\' + str(cli) + '_' + str(vini) + '_' + str(areai))
                        except:
                            pass
                        df1.to_csv(resstockdir + [rf'indi_noelec_fossilfuel{homesimnum_sufix}', rf'Indi_Hourly{homesimnum_sufix}'][fi_1] + r'\\' + str(cli) + '_' + str(vini) + '_' + str(areai) + r'\\' + lst[fi][:-8] + '.csv')
