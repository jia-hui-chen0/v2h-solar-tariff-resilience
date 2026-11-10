"""SI Fig_SI_degradation_grid: county maps of 15-year EV battery capacity loss, 4 chemistries x 3 strategies.

Rows NMC 75Ah, NMC B1, NMC B2, LFP 250Ah; columns UC, CC, V2H (current export tariffs); panels (a)-(l).
The value of an RGU is the second-highest total capacity loss (calendar + cycle) among the RGU's simulated
cases, in percent, drawn on every county of that RGU. All panels share one "Reds" color scale from 0 to
the largest value rounded up to the next 0.5 %, shown as a horizontal colorbar on top.

Inputs (relative to the project root):
    Ford_CC/DegradationAssessment_revision/Deginterm_pvev/   degradation results (scc and lmpdg runs skipped)
    Ford_CC/2020_Gaz_counties_national_0728_tempreg.csv      county FIPS -> RGU (tempreg)
    geo/geojson-counties-fips.json (next to this script)     plotly's county GeoJSON, downloaded from
        https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json
Outputs, next to this script:
    Fig_SI_degradation_grid.pdf        571 px (5.94 in) wide, Arial, text 8.5-9 pt
    Fig_SI_degradation_grid.png        300 dpi, rendered from the PDF
    Fig_SI_degradation_grid_source_data.csv   one row per county per panel

Run: PYTHONIOENCODING=utf-8 uv run --no-project --python 3.12 --with plotly==6.3.0 --with kaleido==1.0.0
     --with pymupdf==2.1 --with pandas==3.1.1 --with numpy==2.5.4 --with pillow==13.0.0
     python make_fig_si_degradation_grid.py
(kaleido 1.0 needs Google Chrome on the machine to export.)
Add --from-source-data to draw the figure from Fig_SI_degradation_grid_source_data.csv instead of the
degradation results; the source-data file is then read, not written.
"""
import os, sys, json, math, numpy as np, pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pymupdf
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))

DEG_D = r'F:\University of Michigan Dropbox\Jiahui Chen\Ford_CC\DegradationAssessment_revision\Deginterm_pvev'
FORD = r'F:\University of Michigan Dropbox\Jiahui Chen\Ford_CC'
GEOJSON = os.path.join(HERE, 'geo', 'geojson-counties-fips.json')
OUT = HERE
STEM = 'Fig_SI_degradation_grid'
SRC = os.path.join(OUT, STEM + '_source_data.csv')
FROM_SOURCE = '--from-source-data' in sys.argv[1:]

# ----------------------------------------------------------------------------------------------
# DATA
# ----------------------------------------------------------------------------------------------
if not FROM_SOURCE:
    print('Loading data...')
    ctdf = pd.read_csv(os.path.join(FORD, '2020_Gaz_counties_national_0728_tempreg.csv'))
    ctdf['fips'] = ctdf['fips'].astype(str).str.zfill(5)
    uqlst = np.unique(ctdf['tempreg'])
    N_RGU = len(uqlst)

    # Shannon County, SD (FIPS 46113 in the GeoJSON) is not in the county table: give it the row of
    # neighboring Bennett County (row 2330)
    ctdf = pd.concat([ctdf, ctdf.iloc[2330:2331]], ignore_index=True)
    ctdf.loc[ctdf.index[-1], 'fips'] = '46113'

with open(GEOJSON, encoding='utf-8') as r:
    counties_full = json.load(r)
excluded = {'02', '15', '60', '66', '69', '72', '78'}
features = [f for f in counties_full['features'] if f['id'][:2] not in excluded]
counties = {"type": "FeatureCollection", "features": features}


def load_deg(scen_tag, batt_tag):
    """Load 2nd-worst degradation per RGU. Returns {rgu_idx: percent_loss}.
    CSV format (3 rows): row0=lifecty_years, row1=qcallst(calendar), row2=qcyclst(cycle).
    Total capacity loss = qcallst + qcyclst = row1 + row2."""
    data = {}
    for f in os.listdir(DEG_D):
        if f'{scen_tag}' in f and f'{batt_tag}' in f and 'scc' not in f and 'lmpdg' not in f:
            ci = int(f.split('_')[0])
            try:
                df = pd.read_csv(os.path.join(DEG_D, f))
                total = df.iloc[1].to_numpy() + df.iloc[2].to_numpy()
                valid = total[~np.isnan(total)]
                if len(valid) >= 2:
                    data[ci] = np.sort(valid)[-2] * 100  # percent
            except:
                pass
    return data


def assign_to_counties(rgu_dict, col_name):
    """Assign RGU-level data to ALL counties sharing each RGU's tempreg."""
    ctdf[col_name] = np.nan
    for ci, val in rgu_dict.items():
        if ci < N_RGU:
            tempreg = int(uqlst[ci])
            mask = ctdf['tempreg'] == tempreg
            ctdf.loc[mask, col_name] = val


batteries = ['75AhA', 'B1', 'B2', 'LFP']
batt_names = ['NMC 75Ah', 'NMC B1', 'NMC B2', 'LFP 250Ah']
scen_tags = ['UC', 'CC', 'V2H']

if FROM_SOURCE:
    # one column per panel; counties are drawn in the row order of the county table in this repository
    # (Ford_CC/2020_Gaz_counties_national_0728_tempreg.csv), with Shannon County, SD (46113) last
    print('Reading', SRC)
    src = pd.read_csv(SRC, dtype={'fips': str})
    REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
    order = pd.read_csv(os.path.join(REPO, 'Ford_CC', '2020_Gaz_counties_national_0728_tempreg.csv'),
                        usecols=['fips'])['fips'].astype(str).str.zfill(5).tolist() + ['46113']
    ctdf = None
    for bi, bt in enumerate(batteries):
        for si, st in enumerate(scen_tags):
            sel = src[(src['battery_file_tag'] == bt) & (src['strategy'] == st)]
            sel = sel.set_index('fips').loc[order].reset_index()
            if ctdf is None:
                ctdf = sel[['fips']].copy()
            assert (sel['fips'] == ctdf['fips']).all()
            ctdf[f'deg_{bt}_{st}'] = sel['capacity_loss_pct']
else:
    print('Loading degradation data and assigning to counties...')
    for bi, bt in enumerate(batteries):
        for si, st in enumerate(scen_tags):
            d = load_deg(st, bt)
            assign_to_counties(d, f'deg_{bt}_{st}')
            vals = ctdf[f'deg_{bt}_{st}'].dropna()
            print(f'  {batt_names[bi]} / {st}: {len(d)} RGUs -> {len(vals)} counties, max={vals.max():.2f}%')

global_zmax = 0.0
for bi, bt in enumerate(batteries):
    for si, st in enumerate(scen_tags):
        vals = ctdf[f'deg_{bt}_{st}'].dropna()
        if len(vals):
            global_zmax = max(global_zmax, vals.max())
if global_zmax < 1:
    global_zmax = math.ceil(global_zmax * 10) / 10
else:
    global_zmax = math.ceil(global_zmax * 2) / 2
print(f'Global zmax across all panels: {global_zmax:.2f}%')

# ----------------------------------------------------------------------------------------------
# LAYOUT at print size
# ----------------------------------------------------------------------------------------------
FONT = 'Arial'
PX_PER_PT = 1 / (0.72636 * 1.00113)      # kaleido 1.0 / Chrome: span size = 0.72636 * px; page 571 px = 5.9433 in
FS_TICK = round(8.5 * PX_PER_PT, 2)       # 8.5 pt printed
FS_TITLE = round(9.0 * PX_PER_PT, 2)      # 9 pt printed
W = 571                                   # px -> 5.943 in PDF page
M = dict(l=0, r=0, t=2, b=3)
NR, NC = 4, 3
CB_H = 50       # px reserved on top for the horizontal colorbar (title + bar + tick labels)
TITLE_H = 16    # px reserved above each map for its panel title
MAP_H = 100     # geo domain height: holds the 150 x 94.5 px CONUS of a 190 px-wide column without shrinking
ROW_GAP = 2
HP = CB_H + NR * (TITLE_H + MAP_H) + (NR - 1) * ROW_GAP
H = HP + M['t'] + M['b']
f = lambda px: 1 - px / HP                # px from top of plot area -> paper y


def row_dom(r):
    top = CB_H + r * (TITLE_H + MAP_H + ROW_GAP) + TITLE_H
    return (f(top + MAP_H), f(top))


subplot_titles = [
    '(a) NMC 75Ah UC', '(b) NMC 75Ah CC', '(c) NMC 75Ah V2H',
    '(d) NMC B1 UC',   '(e) NMC B1 CC',   '(f) NMC B1 V2H',
    '(g) NMC B2 UC',   '(h) NMC B2 CC',   '(i) NMC B2 V2H',
    '(j) LFP UC',      '(k) LFP CC',      '(l) LFP V2H',
]
fig = make_subplots(rows=NR, cols=NC, specs=[[{'type': 'geo'}] * NC] * NR,
                    horizontal_spacing=0, vertical_spacing=0.03, subplot_titles=subplot_titles)

for bi, bt in enumerate(batteries):
    for si, st in enumerate(scen_tags):
        col = f'deg_{bt}_{st}'
        showscale = (bi == 0 and si == 2)
        fig.add_trace(go.Choropleth(
            geojson=counties,
            locations=ctdf['fips'],
            z=ctdf[col],
            featureidkey="id",
            colorscale="Reds",
            zmin=0,
            zmax=global_zmax,
            showscale=showscale,
            marker=dict(line=dict(width=0)),
            colorbar=dict(
                orientation='h', x=0.5, xanchor='center', y=1, yanchor='top', xpad=0, ypad=0,
                thickness=12, len=0.35, outlinewidth=0.5, outlinecolor='black',
                title=dict(text='%', side='top', font=dict(family=FONT, size=FS_TITLE, color='black')),
                tickfont=dict(family=FONT, size=FS_TICK, color='black'),
                tickmode='array',
                tickvals=[0, 5, 10],
                ticktext=['0.0', '5.0', '10.0'],
                ticks='outside', tickwidth=0.5, ticklen=3, tickcolor='black')
            if showscale else None,
        ), row=bi + 1, col=si + 1)

fig.update_geos(
    visible=False,
    scope='usa',
    center=dict(lat=38.5, lon=-98),
    projection_scale=1,
    lataxis_range=[16, 60],
    lonaxis_range=[-125, -66]
)

for k in range(NR * NC):
    fig.layout['geo' if k == 0 else f'geo{k + 1}'].domain.y = row_dom(k // NC)
for k, ann in enumerate(fig.layout.annotations):
    ann.y = row_dom(k // NC)[1]
    ann.yanchor = 'bottom'
    ann.yshift = -1
    ann.font = dict(family=FONT, size=FS_TITLE, color='black')

fig.update_layout(
    width=W, height=H, margin=M,
    plot_bgcolor='white', paper_bgcolor='white',
    font=dict(family=FONT, color='black', size=FS_TICK),
    showlegend=False,
)

# Source data: per-county values exactly as held by each choropleth trace (trace order = panel order (a)-(l))
if not FROM_SOURCE:
    rows, k = [], 0
    for bi, bt in enumerate(batteries):
        for si, st in enumerate(scen_tags):
            tr = fig.data[k]
            rows.append(pd.DataFrame({'panel': subplot_titles[k][1], 'battery': batt_names[bi], 'battery_file_tag': bt,
                                      'strategy': st, 'fips': np.asarray(tr.locations).astype(str),
                                      'rgu_index': np.searchsorted(uqlst, ctdf['tempreg'].to_numpy()),
                                      'capacity_loss_pct': np.asarray(tr.z, dtype=float)}).sort_values('fips', kind='stable'))
            k += 1
    pd.concat(rows, ignore_index=True).to_csv(SRC, index=False, encoding='utf-8')

print(f'Saving {W}x{H} px ...')
pdf_path = os.path.join(OUT, STEM + '.pdf')
png_path = os.path.join(OUT, STEM + '.png')
fig.write_image(pdf_path, format='pdf', width=W, height=H, scale=1)

# PNG rendered from the PDF at 300 dpi, so both files show the same page (kaleido's own PNG export uses a
# different scale and bottom cut than its PDF export)
with pymupdf.open(pdf_path) as doc:
    pix = doc[0].get_pixmap(dpi=300, alpha=False)
    Image.frombytes('RGB', (pix.width, pix.height), pix.samples).save(png_path, dpi=(300, 300))
print('saved', pdf_path, 'and', png_path)
