# Code for "Amid Residential Solar Tariff Uncertainty: How Vehicle-to-Home Can Strengthen Economic Resilience of Residential Solar Customers"

Jiahui Chen, Parth Vaishnav (University of Michigan).

This repository contains the scripts that produced the paper's simulations, bill and emission accounting, numbers and figures. It covers 432 U.S. regions (RGUs), five ResStock homes per region, and three EV charging strategies: uncontrolled (UC), controlled (CC) and vehicle-to-home (V2H). Each strategy is run under current distributed-generation (DG) compensation rules and under an LMP-based export rate, for 2024, 2030 and 2040 grid conditions.

The scripts are the versions that were run for the paper. For this release, API keys were replaced by environment variables, notebook outputs and unused cells were removed, some files were renamed, comments were tidied, and each figure script writes its figure and the plotted values into its own folder. Raw input data and model results are not included. The county-to-RGU mapping, the utility and tariff assignment tables, and the values plotted in each figure are. See [Data](#data).

## Layout

The repository mirrors the author's project folders. `PVEV/` is the paper project and `Ford_CC/` is a sibling project that supplies the driving profiles, uncontrolled-charging runs and battery-degradation step.

| Folder | Stage |
|---|---|
| `Ford_CC/Scripts/` | NHTS trips → driving profiles → hourly charging availability and SOC drop; UC dispatch (`uc_80.py`) |
| `PVEV/Optimization/ResStock_processing.py`, `PVEV/pv_inputs/` | ResStock home loads and building XML download |
| `PVEV/Optimization/evhhec_trb_PV*.py` | Roof geometry, rooftop-PV simulation, net load and V2H discharge limits |
| `PVEV/utility_matching/`, `PVEV/julia/`, `PVEV/PVcompensation/` | County → utility → URDB rate matching, hourly tariffs, DG export compensation |
| `PVEV/Optimization/cc_rd_fullyear*.py` | CC and V2H dispatch (GAMS linear program) |
| `Ford_CC/DegradationAssessment_revision/` | Battery degradation from the simulated SOC profiles (NREL BLAST-Lite) |
| `PVEV/CostEmiAssessment/analysis_*.py` | 15-year bill and emission accounting per home → `csv_trb_detailed/` |
| `PVEV/CostEmiAssessment/_paper_numbers.py` | Inline numbers in the main text |
| `PVEV/CostEmiAssessment/paper_figures/` | Figure scripts (see [Figures](#figures)) |

## Pipeline

Run the stages in this order. Each script reads and writes files under the project root, so later stages depend only on the files earlier stages wrote.

1. **Driving and charging availability** (`Ford_CC/Scripts/`): `partition_2.py` → `activeness_trb.py` → `simulator_trb.py` → `soc_drop_rd_dashboard.py` → `Parkingrecog_db.py` → `hour_to_cr_db.py`. Output: `Energy consumption_adjusted_1_2_Y82_db/`, the hourly charging limits and SOC drop used by every dispatch run.
2. **Homes**: select five homes per RGU from ResStock (`Ford_CC/ResStock/dataacq_2025_random.py`: per RGU it pools ResStock homes from nearby weather stations, keeps homes built in 2000 or later, ≤ 2,500 sq ft and with a roof in `in.xml`, sorts them by annual whole-home electricity, and takes the homes at the 0/20/40/60/80% positions), then `PVEV/Optimization/ResStock_processing.py` converts the ResStock parquet files into hourly loads.
3. **Rooftop PV and net load**: `PVEV/Optimization/evhhec_trb_PV.py` runs `xmlid_extract` → `solar_input` (roof geometry from the building XML, downloaded by `PVEV/pv_inputs/xmldownload_parallel.py`) → weather download → `PVoutput`, writing `PVsimulation/2018simu_5homes_percentile_70roofcover/`. `evhhec_trb_PV_125PVhhec.py` then sizes PV at up to 125% of household consumption and writes the net-load and discharge-limit files; `evhhec_trb_PV_EVbase.py` writes the no-PV discharge limits.
4. **Tariffs** (`PVEV/utility_matching/`, `PVEV/julia/`, `PVEV/PVcompensation/`):
   - `urdb_trim.ipynb` trims the URDB bulk export to residential rates.
   - `aggregate_ctdf_chooserate_auto.ipynb` matches counties to utilities by service territory and EIA-861 sales: each county takes the utility with the largest EIA-861 residential sales among those whose service territory contains the county's Census internal point, and each RGU takes its most common county utility (ties go to the larger sales). Where that utility has no residential rate in URDB, a substitute was chosen by service territory and EIA-861 residential sales. The notebook then picks one rate per RGU and runs the Julia driver `julia/temp_script.jl` (which loads `urdb.jl`, `utils.jl`, `electric_tariff.jl`) to expand each URDB rate into an hourly series in `julia/Utility_structure/`. Its later cells assign rates one utility at a time, so it cannot be re-run start to finish without review.
   - `PVcomp_dgrules.ipynb` assigns DG compensation rules (`Rates_dgrules.csv`, `Rates_dgrules_tou.csv`) and builds net-billing export series in `PVcompensation/rates/`; `PVcomp_neb_series.ipynb` builds the series for NH, New England, NC/VA, MS and MN/ND; `CA.ipynb` builds the California series.
5. **Dispatch** (GAMS):
   - UC: `Ford_CC/Scripts/uc_80.py` → `Ford_CC/Results/Results_80_82_rev/`.
   - CC and V2H, current DG rules: `PVEV/Optimization/cc_rd_fullyear125PVhhec.py` → `SimulationResults/Result_{cc,v2h}_125PVhhec_fullyear/`.
   - LMP export rate: `cc_rd_fullyear125PVhhec_lmpdg.py` → `..._fullyear_lmpdg/`.
   - Carbon price ($51 and $204/tCO2): `cc_rd_fullyear125PVhhec_scc.py --mode full` (the default `--mode pilot` runs three regions in 2024 only) → `..._fullyear_scc{51,204}/`.
   - EV without PV: `cc_rd_fullyear_EVbase.py` → `Result_{cc,v2h}_EVbase_fullyear/`.
6. **Battery degradation**: `Ford_CC/DegradationAssessment_revision/deg_assess_pvev.py` → `Deginterm_pvev/`. `_regenerate_cc75AhA_0_9.py` re-ran the CC 75Ah-A results for RGUs 0–9.
7. **Bill and emission accounting** (`PVEV/CostEmiAssessment/`): `analysis_UC_fullyear_125PVhhec_EVbase.py` (no-PV bill and EV-only cost), `analysis_UC_fullyear_125PVhhec.py` (PV change and EV increment after PV, current and LMP rules) and `analysis_UC_fullyear_125PVhhec_scc.py` write `csv_trb_detailed/<scenario>/<rgu>_<year>__5homes_percentile__70roofcover__noelec.csv`.
8. **Paper numbers and figures**: `_paper_numbers.py` prints the main-text numbers from `csv_trb_detailed/`; figure scripts are listed below.

### Accounting conventions

`BaselineCost` means different things in the two accounting scripts:

| Symbol | Column | Written by | Meaning |
|---|---|---|---|
| B | `BaselineCost` in `{s}_EVbase_fullyear` | `analysis_..._EVbase.py` | Bill of the home with no EV and no PV |
| C_EV | `Cost` in `{s}_EVbase_fullyear` | `analysis_..._EVbase.py` | EV charging cost without PV |
| S | `BaselineCost` in `{s}_125PVhhec_*` | `analysis_..._125PVhhec.py` | Bill change from adding PV (≤ 0) |
| C | `Cost` in `{s}_125PVhhec_*` | `analysis_..._125PVhhec.py` | Extra cost of the EV after PV |

Relative to the home with no EV and no PV: EV only = C_EV, PV only = S, EV + PV = S + C. Emissions follow the same pattern (`BaselineEmissions`, `Emissions`). Only the `__noelec.csv` files (non-electrified home load) are used.

Comparisons between scenarios use paired differences: for each `(building_id, fname)` pair, sum the three yearly differences × 5 (15-year total), take the median per RGU, then report the mean and 5th–95th percentiles across RGUs.

## Figures

Each figure in the manuscript is drawn by the script below. The scripts write their PDF, PNG and `<figure>_source_data.csv` into their own folder. Paths are relative to `PVEV/CostEmiAssessment/`.

| Manuscript figure (file) | Script | Packages |
|---|---|---|
| DG compensation rules map (`DGRules`) | `paper_figures/DGRules/make_fig_DGRules.py` | Python 3.11, plotly 5.24.1, kaleido 0.1.0.post1, pandas 2.2.3, numpy 2.4.6 |
| Grouped bills (`Fig_Bill_grouped`) | `paper_figures/grouped/make_fig_bill_grouped.py` (+ `grouped_layout.py`) | matplotlib 3.10.6, pandas 3.0.6 |
| Strategy impact on bills and emissions (`Fig_Bill_StrategyImpact`, `Fig_Emissions_StrategyImpact`) | `paper_figures/strategy_impact/make_fig_strategy_impact.py` (draws both) | matplotlib 3.10.6, pandas 3.0.6, numpy 2.5.3 |
| Self-consumption vs policy risk (`Fig_SelfConsumption_vs_PolicyRisk_NEMNEB`) | `paper_figures/policy_risk/make_fig_policy_risk.py` (+ `policy_risk_data.py`, which also builds the included `policy_risk_longdata.csv`) | matplotlib 3.11.2, scipy |
| EV charging emissions map (`Fig 3 lifetime emissions`) | `paper_figures/Fig3_lifetime_emissions/make_fig_lifetime_emissions.py` | plotly 5.24.1, kaleido 0.1.0.post1 |
| Grouped emissions (`Fig_Emissions_grouped`) | `paper_figures/grouped/make_fig_emissions_grouped.py` (+ `grouped_layout.py`) | matplotlib 3.10.6, pandas 3.0.6 |
| Battery degradation (`Fig_degradation_box`) | `paper_figures/degradation_box/make_fig_degradation_box.py` | matplotlib 3.11.2 |
| SI: lifetime cost maps (`Fig 1 lifetime costs`) | `paper_figures/Fig1_lifetime_costs/make_fig_lifetime_costs.py` | Python 3.12, plotly 6.3.0, kaleido 1.0.0 |
| SI: carbon-price bills (`Fig_SI_SCC_box`) | `paper_figures/SI_SCC_box/make_fig_scc_box.py` | matplotlib 3.11.2 |
| SI: carbon-price changes (`Fig_SI_SCC_delta_box`) | `paper_figures/SI_SCC_delta/scc_retail_numbers.py`, then `make_fig_scc_delta.py` | matplotlib 3.11.2 |
| SI: equivalent full cycles (`Fig_SI_EFC_box`) | `paper_figures/SI_EFC/make_fig_si_efc.py` | matplotlib 3.11.2 |
| SI: degradation boxes (`Fig_SI_degradation_box`) | `paper_figures/SI_degradation_box/make_fig_si_degradation_box.py` | matplotlib 3.11.2 |
| SI: degradation maps (`Fig_SI_degradation_grid`, `Fig_SI_degradation_delta`) | `paper_figures/SI_degradation_maps/make_fig_si_degradation_{grid,delta}.py` | Python 3.12, plotly 6.3.0, kaleido 1.0.0, pymupdf 2.1, pillow 13.0.0 |

Where not listed: Python 3.14, numpy 2.5.4, pandas 3.1.1. The figures use Arial, and kaleido 1.0.0 needs Google Chrome. Each script's docstring has the full `uv run` command. Add `--from-source-data` to draw a figure from the `<figure>_source_data.csv` in its folder instead of the model outputs. This needs no data outside this repository except the county GeoJSON for the maps. Rerunning each script this way reproduces the manuscript PDF: rasterized at 150 dpi, no pixel differs by more than one intensity level (of 255), and all figures except `Fig_SI_EFC_box` match exactly.

The current-tariff statistics in the SI degradation table are printed by `degradation_table_stats.py`.

The county maps need the plotly county GeoJSON (`https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json`). `DGRules`, `Fig 1 lifetime costs` and `Fig 3 lifetime emissions` download it at run time. The two degradation maps read it from `paper_figures/SI_degradation_maps/geo/geojson-counties-fips.json`, so download it there first.

## Running the code

**Paths.** Scripts hard-code the author's project root, mostly `C:\Users\jiahuic\University of Michigan Dropbox\Jiahui Chen\` (older `Ford_CC` scripts use `C:\Users\jiahuic\Dropbox (University of Michigan)\Ford_CC\`; some use `F:\` or `E:\` roots), and GAMS at `C:\GAMS\42`. The folders in this repository sit under that root exactly as shown, so replacing the root prefix with your own is enough to point a script at your copy of the data.

**Software.**

- Python 3 with the packages in `requirements.txt`.
- GAMS 42 with CPLEX and the GAMS Python API, for the dispatch scripts.
- Julia 1.11 with `CSV`, `DataFrames`, `HTTP`, `JSON`, for the URDB parser.
- NREL BLAST-Lite (`blast-lite`) for the degradation step. The paper runs used a local copy of the `blast` package.

**API keys.** Set them as environment variables:

| Variable | Used by |
|---|---|
| `URDB_API_KEY` | `PVEV/julia/urdb.jl` (OpenEI Utility Rate Database) |
| `NREL_DEVELOPER_API_KEY` | `PVEV/julia/utils.jl` (only for the PVWatts/solar helpers) |

**Compute.** The dispatch and accounting scripts parallelize over RGUs with `multiprocessing`/`concurrent.futures` and were run on a 48-thread Windows workstation.

## Data

Raw input data are not redistributed here. All raw inputs are public:

- NREL ResStock 2022 release 1 (AMY2018): household load profiles, metadata and building XML (`oedi-data-lake` S3 bucket).
- AMY2018 weather files from the same OEDI data lake.
- NREL Cambium: hourly marginal emission rates and end-use costs by balancing area.
- OpenEI Utility Rate Database (URDB), EIA Form 861 retail sales, and an electric retail service-territory shapefile.
- 2017 National Household Travel Survey (NHTS).
- U.S. Census 2020 Gazetteer counties, mapped to RGUs (`Ford_CC/2020_Gaz_counties_national_0728_tempreg.csv`, included).

### Included tables

These tables are included so that the region mapping and the utility, rate and DG-rule assignment do not have to be rebuilt. URDB entries change over time, so the two URDB extracts also fix the rates to the versions used in the paper.

| File | Contents | Read by |
|---|---|---|
| `Ford_CC/2020_Gaz_counties_national_0728_tempreg.csv` | Census 2020 counties with their RGU (`tempreg`) and ReEDS balancing area (`reeds_ba`) | Almost every stage |
| `PVEV/julia/filtered_usurdb.csv` | URDB residential rates used for utility matching | `aggregate_ctdf_chooserate_auto.ipynb` |
| `PVEV/julia/filtered_usurdb_2023later.csv` | URDB residential rates expanded into hourly series | `julia/temp_script.jl`, `aggregate_ctdf_chooserate_auto.ipynb` |
| `PVEV/utility_matching/2020_Gaz_counties_national_0728_tempreg_withutility_usurdb_filled.csv` | County → utility, with substitutes where the utility has no URDB residential rate | `aggregate_ctdf_chooserate_auto.ipynb` |
| `PVEV/utility_matching/2020_Gaz_counties_national_0728_tempreg_withutility_usurdb_filled_sales_filled.csv` | The same, with EIA-861 residential sales, revenue and customer counts | `aggregate_ctdf_chooserate_auto.ipynb` |
| `PVEV/utility_matching/tempreg_withutility_usurdb_filled_sales_state.csv` | Final county → utility table with EIA-861 sales matched by state | `PVcomp_dgrules.ipynb`, `PVcomp_neb_series.ipynb` |
| `PVEV/utility_matching/Rates_dgrules.csv` | County → chosen URDB rate and DG compensation rule | `PVcomp_dgrules.ipynb`, `make_fig_DGRules.py` |
| `PVEV/utility_matching/Rates_dgrules_tou.csv` | The same, with the TOU flag | Dispatch, accounting and figure scripts |

The values plotted in each figure are included as `<figure>_source_data.csv`, in the folder of the script that draws the figure. The full model outputs (per-home dispatch, cost and emission results) are available from the corresponding author on reasonable request.

## Steps without scripts

- Some intermediate tables were completed outside the scripts and are included as files (see [Included tables](#included-tables)): the utility substitutes in `..._usurdb_filled.csv` (chosen by service territory and EIA-861 residential sales), the sales filled in `..._filled_sales_filled.csv`, the URDB extract `julia/filtered_usurdb.csv`, and the starting `Rates_dgrules_tou.csv`, saved from `Rates_dgrules.csv` with one added row (FIPS 46113) for the county map. `PVcomp_dgrules.ipynb` then adds its TOU column.
- `Table/degradation_table.tex` was assembled outside the scripts (`PVEV/CostEmiAssessment/degradation_table_stats.py` prints its current-tariff rows; the two LMP-tariff rows have no script here).
- The Cambium, `tempAdjusted/` temperature and ResStock aggregate inputs were downloaded or prepared outside these scripts.

## Third-party code

`PVEV/julia/electric_tariff.jl`, `urdb.jl` and `utils.jl` are adapted from NREL's [REopt.jl](https://github.com/NREL/REopt.jl), © Alliance for Sustainable Energy, LLC, licensed under the Apache License 2.0. The files were modified for this project. The license and notice are in `PVEV/julia/LICENSE-REopt.txt` and `PVEV/julia/NOTICE-REopt.txt`.

## License

MIT. See [LICENSE](LICENSE). The three REopt-derived Julia files listed under Third-party code stay under the Apache License 2.0.
