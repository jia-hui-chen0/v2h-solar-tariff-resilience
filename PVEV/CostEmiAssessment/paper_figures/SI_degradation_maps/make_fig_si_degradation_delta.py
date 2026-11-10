"""SI Fig_SI_degradation_delta: county maps of the change in 15-year EV battery capacity loss from V2H.

Panels (a)-(d): V2H minus UC; (e)-(h): V2H minus CC; columns NMC 75Ah, NMC B1, NMC B2, LFP 250Ah
(current export tariffs). The capacity loss of an RGU under one strategy is the second-highest total loss
(calendar + cycle) among the RGU's simulated cases, in percent; the difference is taken per RGU, in
percentage points, and drawn on every county of that RGU. All panels share one diverging "RdBu_r" color
scale centered on 0, with limits at +/- the largest absolute difference rounded up (to 1, 2.5, 5, or the
next integer up to 20), shown as a horizontal colorbar on top.

Inputs (relative to the project root):
    Ford_CC/DegradationAssessment_revision/Deginterm_pvev/   degradation results (scc and lmpdg runs skipped)
    Ford_CC/2020_Gaz_counties_national_0728_tempreg.csv      county FIPS -> RGU (tempreg)
    geo/geojson-counties-fips.json (next to this script)     plotly's county GeoJSON, downloaded from
        https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json
Outputs, next to this script:
    Fig_SI_degradation_delta.pdf       571 px (5.94 in) wide, Arial, text 8.5-9 pt
    Fig_SI_degradation_delta.png       300 dpi, rendered from the PDF
    Fig_SI_degradation_delta_source_data.csv   one row per county per panel

Run: PYTHONIOENCODING=utf-8 uv run --no-project --python 3.12 --with plotly==6.3.0 --with kaleido==1.0.0
     --with pymupdf==2.1 --with pandas==3.1.1 --with numpy==2.5.4 --with pillow==13.0.0
     python make_fig_si_degradation_delta.py
(kaleido 1.0 needs Google Chrome on the machine to export.)
Add --from-source-data to draw the figure from Fig_SI_degradation_delta_source_data.csv instead of the
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
STEM = 'Fig_SI_degradation_delta'
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
    """Load 2nd-worst degradation per RGU for one scenario+battery combo.
    Returns dict {rgu_idx: percent_loss}."""
    data = {}
    for f in os.listdir(DEG_D):
        if f'{scen_tag}' in f and f'{batt_tag}' in f and 'scc' not in f and 'lmpdg' not in f:
            ci = int(f.split('_')[0])
            try:
                df = pd.read_csv(os.path.join(DEG_D, f))
                total = df.iloc[1].to_numpy() + df.iloc[2].to_numpy()
                valid = total[~np.isnan(total)]
                if len(valid) >= 2:
                    data[ci] = np.sort(valid)[-2] * 100  # convert to percent
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

if FROM_SOURCE:
    # one column per panel; counties are drawn in the row order of the county table in this repository
    # (Ford_CC/2020_Gaz_counties_national_0728_tempreg.csv), with Shannon County, SD (46113) last
    print('Reading', SRC)
    src = pd.read_csv(SRC, dtype={'fips': str})
    REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
    order = pd.read_csv(os.path.join(REPO, 'Ford_CC', '2020_Gaz_counties_national_0728_tempreg.csv'),
                        usecols=['fips'])['fips'].astype(str).str.zfill(5).tolist() + ['46113']
    ctdf = None
    for bt in batteries:
        for prefix, ref in [('delta_uc', 'UC'), ('delta_cc', 'CC')]:
            sel = src[(src['battery_file_tag'] == bt) & (src['reference_strategy'] == ref)]
            sel = sel.set_index('fips').loc[order].reset_index()
            if ctdf is None:
                ctdf = sel[['fips']].copy()
            assert (sel['fips'] == ctdf['fips']).all()
            ctdf[f'{prefix}_{bt}'] = sel['delta_capacity_loss_pp']
else:
    print('Computing deltas and assigning to counties...')
    for bi, bt in enumerate(batteries):
        uc_d = load_deg('UC', bt)
        cc_d = load_deg('CC', bt)
        v2h_d = load_deg('V2H', bt)
        common_uc = set(uc_d) & set(v2h_d)
        delta_uc = {c: v2h_d[c] - uc_d[c] for c in common_uc}
        assign_to_counties(delta_uc, f'delta_uc_{bt}')
        common_cc = set(cc_d) & set(v2h_d)
        delta_cc = {c: v2h_d[c] - cc_d[c] for c in common_cc}
        assign_to_counties(delta_cc, f'delta_cc_{bt}')
        vals_uc = ctdf[f'delta_uc_{bt}'].dropna()
        vals_cc = ctdf[f'delta_cc_{bt}'].dropna()
        print(f'  {batt_names[bi]}: V2H-UC {len(delta_uc)} RGUs [{vals_uc.min():.2f}, {vals_uc.max():.2f}]; '
              f'V2H-CC {len(delta_cc)} RGUs [{vals_cc.min():.2f}, {vals_cc.max():.2f}]')

all_vals = []
for bt in batteries:
    for prefix in ['delta_uc', 'delta_cc']:
        v = ctdf[f'{prefix}_{bt}'].dropna()
        if len(v):
            all_vals.extend(v.tolist())
global_absmax_raw = max(abs(np.min(all_vals)), abs(np.max(all_vals)))


def round_up_clean(x):
    if x <= 0: return 1
    if x <= 1: return 1
    if x <= 2.5: return 2.5
    if x <= 5: return 5
    if x <= 20:
        return math.ceil(x)
    magnitude = 10 ** math.floor(math.log10(x))
    normalized = x / magnitude
    if normalized <= 2: result = 2
    elif normalized <= 5: result = 5
    else: result = 10
    return result * magnitude


global_absmax = round_up_clean(global_absmax_raw)
print(f'Global symmetric color range: raw_absmax={global_absmax_raw:.2f}, clean_absmax={global_absmax:.2f}')

# ----------------------------------------------------------------------------------------------
# LAYOUT at print size
# ----------------------------------------------------------------------------------------------
FONT = 'Arial'
PX_PER_PT = 1 / (0.72636 * 1.00113)      # kaleido 1.0 / Chrome: span size = 0.72636 * px; page 571 px = 5.9433 in
FS_TICK = round(8.5 * PX_PER_PT, 2)       # 8.5 pt printed
FS_TITLE = round(9.0 * PX_PER_PT, 2)      # 9 pt printed
W = 571                                   # px -> 5.943 in PDF page
# Bottom margin 12 px: kaleido's PDF export prints the W x H px page inside Chrome's 0.1 in page margins
# and scales the figure to the page width (0.72637 pt/px instead of 0.75), so about (18.1 - 0.0343 H) px
# are cut off at the bottom. A 12 px margin keeps that cut below the maps.
M = dict(l=0, r=0, t=2, b=12)
NR, NC = 2, 4
CB_H = 50       # px reserved on top for the horizontal colorbar (title + bar + tick labels)
TITLE_H = 16    # px reserved above each map for its panel title
MAP_H = 76      # geo domain height: holds the 113 x 71 px CONUS of a 143 px-wide column without shrinking
ROW_GAP = 6
HP = CB_H + NR * (TITLE_H + MAP_H) + (NR - 1) * ROW_GAP
H = HP + M['t'] + M['b']
f = lambda px: 1 - px / HP                # px from top of plot area -> paper y


def row_dom(r):
    top = CB_H + r * (TITLE_H + MAP_H + ROW_GAP) + TITLE_H
    return (f(top + MAP_H), f(top))


subplot_titles = [
    '(a) NMC 75Ah V2H−UC', '(b) NMC B1 V2H−UC', '(c) NMC B2 V2H−UC', '(d) LFP V2H−UC',
    '(e) NMC 75Ah V2H−CC', '(f) NMC B1 V2H−CC', '(g) NMC B2 V2H−CC', '(h) LFP V2H−CC',
]
fig = make_subplots(rows=NR, cols=NC, specs=[[{'type': 'geo'}] * NC] * NR,
                    horizontal_spacing=0, vertical_spacing=0.04, subplot_titles=subplot_titles)

# Row 1: V2H-UC
for bi, bt in enumerate(batteries):
    col = f'delta_uc_{bt}'
    showscale = (bi == 3)
    fig.add_trace(go.Choropleth(
        geojson=counties,
        locations=ctdf['fips'],
        z=ctdf[col],
        featureidkey="id",
        colorscale="RdBu_r",
        zmin=-global_absmax,
        zmax=global_absmax,
        zmid=0,
        showscale=showscale,
        marker=dict(line=dict(width=0)),
        colorbar=dict(
            orientation='h', x=0.5, xanchor='center', y=1, yanchor='top', xpad=0, ypad=0,
            thickness=12, len=0.35, outlinewidth=0.5, outlinecolor='black',
            title=dict(text='Percentage points', side='top', font=dict(family=FONT, size=FS_TITLE, color='black')),
            tickfont=dict(family=FONT, size=FS_TICK, color='black'),
            tickformat='.1f',
            tickmode='array',
            tickvals=[-global_absmax, -global_absmax / 2, 0, global_absmax / 2, global_absmax],
            ticktext=[t.replace('-', '−') for t in      # negative labels with U+2212, as in the panel titles
                      [f'{-global_absmax:.0f}', f'{-global_absmax / 2:.0f}', '0', f'{global_absmax / 2:.0f}',
                       f'{global_absmax:.0f}']],
            ticks='outside', tickwidth=0.5, ticklen=3, tickcolor='black')
        if showscale else None,
    ), row=1, col=bi + 1)

# Row 2: V2H-CC
for bi, bt in enumerate(batteries):
    col = f'delta_cc_{bt}'
    fig.add_trace(go.Choropleth(
        geojson=counties,
        locations=ctdf['fips'],
        z=ctdf[col],
        featureidkey="id",
        colorscale="RdBu_r",
        zmin=-global_absmax,
        zmax=global_absmax,
        zmid=0,
        showscale=False,
        marker=dict(line=dict(width=0)),
    ), row=2, col=bi + 1)

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
    font=dict(family=FONT, size=FS_TICK, color='black'),
    showlegend=False,
)

# Source data: per-county values exactly as held by each choropleth trace (trace order = panel order (a)-(h))
if not FROM_SOURCE:
    rows = []
    for k in range(NR * NC):
        tr, bi, ref = fig.data[k], k % NC, ['UC', 'CC'][k // NC]
        rows.append(pd.DataFrame({'panel': subplot_titles[k][1], 'battery': batt_names[bi],
                                  'battery_file_tag': batteries[bi], 'reference_strategy': ref,
                                  'fips': np.asarray(tr.locations).astype(str),
                                  'rgu_index': np.searchsorted(uqlst, ctdf['tempreg'].to_numpy()),
                                  'delta_capacity_loss_pp': np.asarray(tr.z, dtype=float)}).sort_values('fips', kind='stable'))
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
