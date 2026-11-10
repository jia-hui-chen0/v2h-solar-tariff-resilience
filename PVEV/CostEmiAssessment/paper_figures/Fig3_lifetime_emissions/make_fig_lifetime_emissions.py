"""County maps of EV-attributable 15-year charging emissions (Fig 3 lifetime emissions).

Use-phase charging emissions only, without a vehicle-cycle term. Six panels; each RGU's value is
drawn on all counties of that RGU:
  a UC | b CC | c V2H        current export policy
  d UC | e CC | f V2H        LMP export
UC, CC and V2H are uncontrolled charging, controlled charging and vehicle-to-home.
Value per RGU, t CO2e (the per-RGU medians of _paper_numbers.py load_medians):
  5 x sum over 2024, 2030, 2040 of the median of Emissions across the RGU's homes.
Colors: RdBu_r on a fixed -20 to 40 t range, white at 0 and the same color step per tonne on both
sides of 0. The mean (5th-95th percentile) across RGUs of each panel is printed.

Inputs (relative to the project root):
  PVEV/CostEmiAssessment/csv_trb_detailed/{uc,cc,v2h}_125PVhhec_fullyear[_lmpdg]/
      {ci}_{year}__5homes_percentile__70roofcover__noelec.csv
  Ford_CC/2020_Gaz_counties_national_0728_tempreg.csv   county -> RGU
  plotly county GeoJSON, downloaded at run time

Outputs (next to this script):
  Fig 3 lifetime emissions.pdf               5.95 in wide, Arial 8.25 pt
  Fig 3 lifetime emissions.png               the same figure at 600 dpi
  Fig 3 lifetime emissions_source_data.csv   value of each panel and county

Run:
  uv run --no-project --python 3.14 --with plotly==5.24.1 --with kaleido==0.1.0.post1 --with pandas==3.1.1
      --with numpy==2.5.4 python make_fig_lifetime_emissions.py
Add --from-source-data to draw the figure from "Fig 3 lifetime emissions_source_data.csv" instead of the
model results; the source-data file is then read, not written.
"""
import json
import os
import sys
from urllib.request import urlopen

import numpy as np
import pandas as pd
import plotly.colors as pc
import plotly.graph_objects as go

# -- Paths -----------------------------------------------------------------
CSV = r'F:/University of Michigan Dropbox/Jiahui Chen/PVEV/CostEmiAssessment/csv_trb_detailed'
CT = r'F:/University of Michigan Dropbox/Jiahui Chen/Ford_CC/2020_Gaz_counties_national_0728_tempreg.csv'
OUT = os.path.dirname(os.path.abspath(__file__))
STEM = 'Fig 3 lifetime emissions'

YEARS = [2024, 2030, 2040]
LCA = 5
SUFFIX = '__5homes_percentile__70roofcover__noelec.csv'

ROWS = [('Current export policy', ''), ('LMP export', '_lmpdg')]
COLS = [('uc', 'Uncontrolled charging (UC)'), ('cc', 'Controlled charging (CC)'), ('v2h', 'V2H')]

SRC = os.path.join(OUT, STEM + '_source_data.csv')
FROM_SOURCE = '--from-source-data' in sys.argv[1:]

if FROM_SOURCE:
    print('Reading', SRC)
    src = pd.read_csv(SRC, dtype={'fips': str})
    fips_all = list(src.loc[src['panel'] == 'a', 'fips'])
    panels = []
    for i in range(len(ROWS) * len(COLS)):
        sel = src[src['panel'] == chr(97 + i)]
        assert list(sel['fips']) == fips_all
        panels.append(sel['ev_charging_emissions_15yr_tco2e'].to_numpy())
else:
    # -- County table / RGU index ----------------------------------------------
    ctdf = pd.read_csv(CT)
    ctdf['fips'] = ctdf['fips'].astype(int).astype(str).str.zfill(5)
    uqlst = np.unique(ctdf['tempreg'])
    N_RGU = len(uqlst)
    ci_of_county = np.searchsorted(uqlst, ctdf['tempreg'].values)  # ci = position in np.unique
    # Counties the plotly GeoJSON lists under former FIPS codes: Oglala Lakota SD as Shannon 46113 takes the
    # RGU of neighboring Bennett 46007; Bedford city VA 51515 takes the RGU of Bedford County 51019.
    former = []
    for code, donor in [('46113', '46007'), ('51515', '51019')]:
        m = ctdf['fips'] == donor
        if m.any():
            former.append((code, int(ci_of_county[np.flatnonzero(m.values)[0]])))
    fips_all = list(ctdf['fips']) + [o for o, _ in former]
    ci_all = np.concatenate([ci_of_county, np.array([c for _, c in former], dtype=int)])


    # -- Data --------------------------------------------------------------------
    def load_rgu_15yr_emissions_t(scen_dir):
        """Per-RGU 15-yr EV-attributable charging emissions (t): 5 x sum over YEARS of the median across homes."""
        out = np.full(N_RGU, np.nan)
        for ci in range(N_RGU):
            meds = []
            for yr in YEARS:
                p = os.path.join(CSV, scen_dir, f'{ci}_{yr}{SUFFIX}')
                if os.path.exists(p):
                    meds.append(pd.read_csv(p, usecols=['Emissions'])['Emissions'].median())
            if len(meds) == len(YEARS):
                out[ci] = sum(meds) * LCA / 1000.0
        return out


    panels = []
    print('EV-attributable 15-yr charging emissions, t CO2e: mean (p5-p95) across RGU medians')
    for rlab, sfx in ROWS:
        for s, clab in COLS:
            v = load_rgu_15yr_emissions_t(f'{s}_125PVhhec_fullyear{sfx}')
            ok = v[~np.isnan(v)]
            print(f'  {rlab:22s} {s.upper():4s} n={ok.size:3d} mean={ok.mean():6.2f} '
                  f'p5={np.percentile(ok, 5):6.2f} p95={np.percentile(ok, 95):6.2f} '
                  f'min={ok.min():7.2f} max={ok.max():6.2f} RGUs<0={int((ok < 0).sum())}')
            panels.append(v[ci_all])

allv = np.concatenate([p[~np.isnan(p)] for p in panels])

# -- One shared diverging color range, white at exactly 0 ---------------------
ZMIN, ZMAX = -20.0, 40.0
assert allv.min() >= ZMIN and allv.max() <= ZMAX, (allv.min(), allv.max())
HALF = max(abs(ZMIN), abs(ZMAX))   # same color per tonne on both sides of 0
base = pc.get_colorscale('RdBu_r')


def sample(x):  # x in [0,1] on the symmetric -HALF..HALF scale
    return pc.sample_colorscale(base, [float(np.clip(x, 0, 1))])[0]


stops = np.linspace(0, 1, 31)
cscale = [[float(t), sample((ZMIN + t * (ZMAX - ZMIN) + HALF) / (2 * HALF))] for t in stops]
TICKS = list(range(int(ZMIN), int(ZMAX) + 1, 10))

# -- County GeoJSON, contiguous U.S. only ------------------------------------
with urlopen('https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json') as r:
    gj = json.load(r)
excluded = {'02', '15', '60', '66', '69', '72', '78'}   # AK, HI and territories
feats = [f for f in gj['features'] if f['id'][:2] not in excluded]
counties = {'type': 'FeatureCollection', 'features': feats}

# -- Layout in px. Plotly PDF: 1 px = 0.75 pt, so 571 px = 428 pt = 5.95 in ---
W, FS, FONT = 571, 11, 'Arial'      # 11 px -> 8.25 pt printed at \columnwidth
LBL = 22                            # left strip for the row labels
CB_BOTTOM, CB_THICK = 49, 12        # colorbar block (title, bar, ticks, labels) ends at 49 px;
                                    # yanchor='bottom' anchors the tick labels' bottom
TITLE_H, MAP_H, GAP = 15, 98, 4     # albers-usa frame is ~1.9:1, so 98 px fills a 183 px cell
row1_top = CB_BOTTOM + 4
H = row1_top + 2 * (TITLE_H + MAP_H) + GAP + 3
cell_w = (W - LBL) / 3


def py(px):  # px from the top -> paper fraction from the bottom
    return 1 - px / H


fig = go.Figure()
lay = {}
for i, z in enumerate(panels):
    r, c = divmod(i, 3)
    gid = 'geo' if i == 0 else f'geo{i + 1}'
    top = row1_top + r * (TITLE_H + MAP_H + GAP) + TITLE_H
    x0 = (LBL + c * cell_w) / W
    lay[gid] = dict(domain=dict(x=[x0, x0 + cell_w / W], y=[py(top + MAP_H), py(top)]),
                    visible=False, scope='usa', projection_type='albers usa',
                    fitbounds='locations', showland=False, bgcolor='rgba(0,0,0,0)')
    fig.add_trace(go.Choropleth(
        geo=gid, geojson=counties, locations=fips_all, z=z, featureidkey='id',
        colorscale=cscale, zmin=ZMIN, zmax=ZMAX, zauto=False,
        showscale=(i == 0),
        # stroke each county in its own fill color: removes the hairline seams that
        # PDF viewers draw between unstroked polygons
        marker=dict(line=dict(width=0.3, color=[
            'rgba(0,0,0,0)' if np.isnan(v) else sample((v + HALF) / (2 * HALF)) for v in z])),
        colorbar=dict(
            orientation='h', thickness=CB_THICK, len=0.35, lenmode='fraction',
            x=(LBL + (W - LBL) / 2) / W, xanchor='center',
            y=py(CB_BOTTOM), yanchor='bottom', ypad=0, xpad=0,
            outlinewidth=0.5, outlinecolor='black',
            title=dict(text='EV-attributable 15-year charging emissions '
                            '(tCO<sub><span style="font-size:11px">2</span></sub>e)',
                       side='top', font=dict(family=FONT, size=FS)),
            tickmode='array', tickvals=TICKS,
            ticktext=[f'{t:g}'.replace('-', '\u2212') for t in TICKS],
            tickfont=dict(family=FONT, size=FS),
            ticks='outside', ticklen=3, tickwidth=0.5, tickcolor='black'),
    ))
    _, clab = COLS[c]
    fig.add_annotation(text=f'({chr(97 + i)}) {clab}', xref='paper', yref='paper',
                       x=x0 + cell_w / W / 2, y=py(top), xanchor='center', yanchor='bottom',
                       showarrow=False, font=dict(family=FONT, size=FS, color='black'))

for r, (rlab, _) in enumerate(ROWS):
    top = row1_top + r * (TITLE_H + MAP_H + GAP)
    fig.add_annotation(text=f'<b>{rlab}</b>', xref='paper', yref='paper',
                       x=0, y=py(top + (TITLE_H + MAP_H) / 2), xanchor='left', yanchor='middle',
                       textangle=-90, showarrow=False,
                       font=dict(family=FONT, size=FS, color='black'))

fig.update_layout(**lay, width=W, height=H, margin=dict(l=0, r=0, t=0, b=0, autoexpand=False),
                  paper_bgcolor='white', plot_bgcolor='white',
                  font=dict(family=FONT, size=FS, color='black'), showlegend=False)

fig.write_image(os.path.join(OUT, STEM + '.pdf'), format='pdf', width=W, height=H, scale=1)
fig.write_image(os.path.join(OUT, STEM + '.png'), format='png', width=W, height=H,
                scale=600 * 5.95 / W)  # 600 dpi at 5.95 in

# long-format source data: the locations and z passed to each go.Choropleth above (one row per panel and location)
if not FROM_SOURCE:
    pd.concat([pd.DataFrame({'panel': chr(97 + i), 'panel_title': COLS[i % 3][1], 'export_policy': ROWS[i // 3][0],
                             'fips': fips_all, 'tempreg': uqlst[ci_all],
                             'ev_charging_emissions_15yr_tco2e': z})
               for i, z in enumerate(panels)], ignore_index=True
              ).to_csv(SRC, index=False, encoding='utf-8')
