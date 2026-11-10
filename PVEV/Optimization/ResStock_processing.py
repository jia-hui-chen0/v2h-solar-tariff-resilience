import pandas as pd
import numpy as np
import os
from concurrent.futures import ProcessPoolExecutor, as_completed

homesimnum_sufix = '_5homes_percentile'  # five homes per RGU, selected by Ford_CC/ResStock/dataacq_2025_random.py
resstockdir = r'C:\Users\jiahuic\University of Michigan Dropbox\Jiahui Chen\Ford_CC\ResStock\\'

def process_file(args):
    fi_1, cli, vini, areai, fi, lst = args
    input_dir = resstockdir + [rf'Individuals_noelec{homesimnum_sufix}', rf'Individuals{homesimnum_sufix}'][fi_1] + r'\\' + str(cli) + '_' + str(vini) + '_' + str(areai)
    output_dir = resstockdir + [rf'indi_noelec_fossilfuel{homesimnum_sufix}', rf'Indi_Hourly{homesimnum_sufix}'][fi_1] + r'\\' + str(cli) + '_' + str(vini) + '_' + str(areai)
    input_file = input_dir + r'\\' + lst[fi]
    output_file = output_dir + r'\\' + lst[fi][:-8] + '.csv'
    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception:
        pass
    df = pd.read_parquet(input_file)
    arr = np.zeros([4, 8760])
    for hi in range(8760):
        arr[0][hi] = sum(df['out.electricity.total.energy_consumption'][hi*4:hi*4+4])
        arr[2][hi] = sum(df['out.fuel_oil.total.energy_consumption'][hi*4:hi*4+4])
        arr[1][hi] = sum(df['out.natural_gas.total.energy_consumption'][hi*4:hi*4+4])
        arr[3][hi] = sum(df['out.propane.total.energy_consumption'][hi*4:hi*4+4])
    df1 = pd.DataFrame(np.transpose(arr))
    df1.to_csv(output_file)

if __name__ == '__main__':
    for fi_1 in range(2):
        try:
            os.mkdir(resstockdir + [rf'indi_noelec_fossilfuel{homesimnum_sufix}', rf'Indi_Hourly{homesimnum_sufix}'][fi_1])
        except Exception:
            pass

    tasks = []
    for cli in range(432):
        for vini in [1]:
            for areai in [0]:
                for fi_1 in range(2):
                    input_dir = resstockdir + [rf'Individuals_noelec{homesimnum_sufix}', rf'Individuals{homesimnum_sufix}'][fi_1] + r'\\' + str(cli) + '_' + str(vini) + '_' + str(areai)
                    if not os.path.exists(input_dir):
                        continue
                    lst = os.listdir(input_dir)
                    for fi in range(len(lst)):
                        tasks.append((fi_1, cli, vini, areai, fi, lst))

    with ProcessPoolExecutor() as executor:
        futures = [executor.submit(process_file, task) for task in tasks]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as exc:
                print(f'Process generated an exception: {exc}')