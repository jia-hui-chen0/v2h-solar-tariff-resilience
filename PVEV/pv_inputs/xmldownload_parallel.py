# Downloads the ResStock building model (in.xml) of each sampled home into pv_inputs/HomeResStock/.
# evhhec_trb_PV*.py read the roof geometry for the rooftop-PV simulation from these files.
import pandas as pd
import numpy as np
import requests
import zipfile
import io
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
homesimnum_sufix = '_5homes_percentile'  # five homes per RGU, selected by Ford_CC/ResStock/dataacq_2025_random.py
# basedir = r'F:\University of Michigan Dropbox\Jiahui Chen\\PVEV\\'
basedir = r'C:\Users\jiahuic\University of Michigan Dropbox\Jiahui Chen\PVEV\\'
ids = pd.read_csv(basedir + rf"pv_inputs\xmlid{homesimnum_sufix}.csv")['xmlid'].to_numpy()
content = basedir + r'pv_inputs\HomeResStock'

path = 'https://oedi-data-lake.s3.amazonaws.com/nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/2022/resstock_amy2018_release_1/building_energy_models/upgrade%3D0/'

def download_and_extract_xml(name):
    try:
        full_url = path + name
        r = requests.get(full_url)
        r.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(r.content)) as zip_file:
            xml_file_name = "in.xml"
            with zip_file.open(xml_file_name) as xml_file:
                out_path = os.path.join(basedir, r'pv_inputs\HomeResStock', name + '.xml')
                with open(out_path, "wb") as f:
                    f.write(xml_file.read())
    except Exception as e:
        print(f"Failed for {name}: {e}")
        # return f"Failed: {name}"

# You can adjust max_workers as needed
max_workers = min(8, len(ids))  # Use up to 8 threads or as many as needed

with ThreadPoolExecutor(max_workers=max_workers) as executor:
    futures = [executor.submit(download_and_extract_xml, name) for name in ids]
    for future in as_completed(futures):
        result = future.result()
