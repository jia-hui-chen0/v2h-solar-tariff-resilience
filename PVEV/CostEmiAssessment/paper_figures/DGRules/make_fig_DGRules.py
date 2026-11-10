"""County map of the distributed-generation (DG) compensation rules (DGRules).

Each county of the contiguous U.S. is colored by the DG rule that the bill accounting
(analysis_UC_fullyear_125PVhhec.py) applies to its RGU under current export rates:
NEM (net energy metering), NEB (net billing) or LMP (LMP-based export credit). An RGU
takes the first 'DG Rules' value of its rows in Rates_dgrules_tou.csv, and every county
is drawn in the class of its RGU.

Inputs (relative to the project root):
  PVEV/utility_matching/Rates_dgrules.csv               counties to draw, in drawing order
  PVEV/utility_matching/Rates_dgrules_tou.csv           county -> RGU and DG rule
  Ford_CC/2020_Gaz_counties_national_0728_tempreg.csv   list of RGUs
  plotly county GeoJSON, downloaded at run time

Outputs (next to this script):
  DGRules.pdf               5.95 x 2.92 in; Arial, legend entries 8.5 pt, legend title 9 pt
  DGRules.png               the same figure at 300 dpi
  DGRules_source_data.csv   FIPS, RGU and DG rule of each drawn county

Run:
  uv run --no-project --python 3.11 --with plotly==5.24.1 --with kaleido==0.1.0.post1 --with pandas==2.2.3
      --with numpy==2.4.6 python make_fig_DGRules.py
Add --from-source-data to draw the figure from DGRules_source_data.csv instead of the utility-matching and
RGU tables; the source-data file is then read, not written.
"""
import json
import sys
from pathlib import Path
from urllib.request import urlopen

import numpy as np
import pandas as pd
import plotly.express as px

OUT = Path(__file__).resolve().parent
STEM = "DGRules"
basedir = r'F:\University of Michigan Dropbox\Jiahui Chen'
SRC = OUT / f"{STEM}_source_data.csv"
FROM_SOURCE = '--from-source-data' in sys.argv[1:]

# ---------------- counties to draw ----------------
with urlopen('https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json') as response:
    counties = json.load(response)
if FROM_SOURCE:
    print('Reading', SRC)
    src = pd.read_csv(SRC, dtype={'fips': str})
    ctdf = pd.DataFrame({'fips': src['fips'], 'tempreg': src['tempreg'], 'DG Rules': src['dg_rules']})
else:
    ctdf = pd.read_csv(basedir + r'\\PVEV\\utility_matching\Rates_dgrules.csv')
    # zero-pad 4-digit FIPS codes to match the GeoJSON ids
    ctdf['fips'] =ctdf.apply(lambda row: '0' + str(row['fips']) if len(str(row['fips'])) == 4 else row['fips'], axis=1)
    # The table has no entry for Oglala Lakota County, SD, which the plotly GeoJSON lists under its former
    # code 46113 (Shannon County): copy a row, set its FIPS to 46113, and look up its RGU and DG rule below.
    ctdf = pd.concat([ctdf, ctdf.loc[ctdf[:].index[2330:2331]]])
    ctdf['index'] = np.arange(ctdf.shape[0])
    ctdf.set_index('index', inplace=True)
    ctdf.loc[ctdf.index[-1], 'fips'] = '46113'

    # ---------------- DG rule of each county's RGU ----------------
    # As in analysis_UC_fullyear_125PVhhec.py: RGU uqlst[ci] takes the first 'DG Rules' value of its
    # rows in Rates_dgrules_tou.csv. County -> RGU also comes from Rates_dgrules_tou.csv, which lists
    # every drawn FIPS code (46113 -> RGU 200).
    ctydf = pd.read_csv(basedir + r'\\Ford_CC\\2020_Gaz_counties_national_0728_tempreg.csv')
    ctdf_urdb = pd.read_csv(basedir + r'\\PVEV\\utility_matching\Rates_dgrules_tou.csv')
    uqlst = np.unique(ctydf['tempreg'])
    rgu_cls = {int(uqlst[ci]): ctdf_urdb[ctdf_urdb['tempreg'] == uqlst[ci]]['DG Rules'].unique().tolist()[0]
               for ci in range(len(uqlst))}
    fips2rgu = dict(zip(ctdf_urdb['fips'].map(lambda v: str(int(v)).zfill(5)), ctdf_urdb['tempreg'].astype(int)))
    rgu = ctdf['fips'].map(lambda f: fips2rgu[str(f)])
    assert len(rgu_cls) == 432 and rgu.notna().all()
    ctdf['tempreg'] = rgu
    ctdf['DG Rules'] = rgu.map(rgu_cls)
    assert ctdf['DG Rules'].notna().all()

# ---------------- print-size layout ----------------
WIDTH_IN = 5.95
W = round(WIDTH_IN * 96)                        # 571 px; PDF exported at scale 1 -> 5.95 in
H = 280                                         # 2.92 in: the map fills the width left of the legend
FONT = "Arial"
PT = 96 / 72                                    # px per pt
FS_ITEM = 8.5 * PT                              # legend entries 8.5 pt
FS_TITLE = 9.0 * PT                             # legend title 9 pt, not bold
TXT = "#2a3f5f"                                 # text color of the plotly default template
MT = 8                                          # top margin (px) keeps the northern border and legend title off the edge


def _walk(c, pts):
    """Collect the [lon, lat] points of a (nested) GeoJSON coordinate list."""
    if isinstance(c[0], (int, float)):
        pts.append(c[:2])
    else:
        for x in c:
            _walk(x, pts)


# geo frame = lon/lat extent of the drawn counties; the view itself is set by fitbounds='locations'
keep = {str(v) for v in ctdf['fips']}
pts = []
for f in counties["features"]:
    if f["id"] in keep:
        _walk(f["geometry"]["coordinates"], pts)
pts = np.array(pts)
LON = [round(float(pts[:, 0].min()), 2), round(float(pts[:, 0].max()), 2)]
LAT = [round(float(pts[:, 1].min()), 2), round(float(pts[:, 1].max()), 2)]

fig = px.choropleth(ctdf, geojson=counties, locations='fips', color='DG Rules', width=W, height=H,
                    projection='mercator')
fig.update_geos(fitbounds='locations', visible=False, lataxis_range=LAT, lonaxis_range=LON)
fig.update_layout(
    autosize=False,
    margin=dict(l=0, r=0, b=0, t=MT, pad=0),
    font=dict(family=FONT, size=FS_ITEM, color=TXT),
    legend=dict(font=dict(family=FONT, size=FS_ITEM, color=TXT),
                title=dict(font=dict(family=FONT, size=FS_TITLE, color=TXT))),
)
fig.update_traces(marker_line_width=0)

fig.write_image(str(OUT / f"{STEM}.pdf"), format="pdf", width=W, height=H, scale=1)
fig.write_image(str(OUT / f"{STEM}.png"), format="png", width=W, height=H, scale=300 / 96)   # 300 dpi at 5.95 in

# ---------------- source data: the rows passed to px.choropleth (locations='fips', color='DG Rules') ----------------
if not FROM_SOURCE:
    pd.DataFrame({
        "fips": ctdf['fips'].astype(str).to_numpy(),
        "tempreg": ctdf['tempreg'].astype(int).to_numpy(),
        "dg_rules": ctdf['DG Rules'].to_numpy(),
    }).to_csv(SRC, index=False, encoding="utf-8")
