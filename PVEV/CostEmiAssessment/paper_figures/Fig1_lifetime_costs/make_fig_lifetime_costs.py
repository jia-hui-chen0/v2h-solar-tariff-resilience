"""County maps of the 15-year bill change with rooftop PV, with and without an EV (Fig 1 lifetime costs).

Eight panels; each RGU's value is drawn on all counties of that RGU:
  a PV only | b UC | c CC | d V2H        current export rates
  e PV only | f UC | g CC | h V2H        LMP export rates
UC, CC and V2H are uncontrolled charging, controlled charging and vehicle-to-home.
Value: 15-year household bill change relative to the home with neither EV nor PV, thousand USD:
  PV only = S = 5 x sum over 2024, 2030, 2040 of the median of BaselineCost across the RGU's homes
  EV + PV = S + C, with C = 5 x sum over the same years of the median of Cost
(the per-RGU medians of _paper_numbers.py load_medians). All panels share one diverging color
scale, symmetric about 0, whose limit is the 99.5th percentile of |value| over all panels rounded
up to a multiple of 5 (35k). The mean (5th-95th percentile) across RGUs of each panel is printed.

Inputs (relative to the project root):
  PVEV/CostEmiAssessment/csv_trb_detailed/{uc,cc,v2h}_125PVhhec_fullyear[_lmpdg]/
      {ci}_{year}__5homes_percentile__70roofcover__noelec.csv
  Ford_CC/2020_Gaz_counties_national_0728_tempreg.csv   county -> RGU
  plotly county GeoJSON, downloaded at run time

Outputs (next to this script):
  Fig 1 lifetime costs.pdf               5.95 in wide, Arial, text >= 8 pt
  Fig 1 lifetime costs.png               the same figure at 300 dpi
  Fig 1 lifetime costs_source_data.csv   value of each panel and county

Run (kaleido 1.0.0 renders with a local Chrome):
  uv run --no-project --python 3.12 --with plotly==6.3.0 --with kaleido==1.0.0 --with pandas==3.1.1
      --with numpy==2.5.4 python make_fig_lifetime_costs.py
Add --from-source-data to draw the figure from "Fig 1 lifetime costs_source_data.csv" instead of the model
results; the source-data file is then read, not written.
"""
import json
import sys
from pathlib import Path
from urllib.request import urlopen

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

OUT = Path(__file__).resolve().parent
CSV = Path(r"F:/University of Michigan Dropbox/Jiahui Chen/PVEV/CostEmiAssessment/csv_trb_detailed")
CTDF = Path(r"F:/University of Michigan Dropbox/Jiahui Chen/Ford_CC/2020_Gaz_counties_national_0728_tempreg.csv")
YEARS = [2024, 2030, 2040]
STEM = "Fig 1 lifetime costs"
SRC = OUT / f"{STEM}_source_data.csv"
FROM_SOURCE = "--from-source-data" in sys.argv[1:]
VAL = "bill_change_15yr_vs_no_ev_no_pv_thousand_usd"


def lca(folder, col):
    """Per-RGU 15-year value: 5 x sum over YEARS of the median of `col` across homes (thousand USD)."""
    out = np.full(N, np.nan)
    for ci in range(N):
        v = []
        for yr in YEARS:
            p = CSV / folder / f"{ci}_{yr}__5homes_percentile__70roofcover__noelec.csv"
            v.append(pd.read_csv(p)[col].median())
        out[ci] = 5 * np.sum(v)
    return out / 1000.0   # thousand USD


if FROM_SOURCE:
    # rebuild plot_df (one column per panel, rows in drawing order) and the per-RGU panel values
    print("Reading", SRC)
    long = pd.read_csv(SRC, dtype={"fips": str})
    plot_df = long.loc[long["panel"] == "a", ["fips", "tempreg"]].reset_index(drop=True)
    uqlst = np.unique(plot_df["tempreg"])
    N = len(uqlst)
    panels = []
    for L in "abcdefgh":
        sel = long[long["panel"] == L]
        assert (sel["fips"].to_numpy() == plot_df["fips"].to_numpy()).all()
        assert (sel.groupby("tempreg")[VAL].nunique() == 1).all()       # one value per RGU
        name = sel["panel_title"].iloc[0]
        pol = {"Current export rates": "cur", "LMP export rates": "lmp"}[sel["export_rates"].iloc[0]]
        plot_df[f"{L}_{name.replace(' ', '_')}_{pol}"] = sel[VAL].to_numpy()
        panels.append((name, pol, sel.drop_duplicates("tempreg").set_index("tempreg")[VAL].loc[uqlst].to_numpy()))
    src = plot_df.iloc[:-1]
else:
    ctdf = pd.read_csv(CTDF)
    ctdf["fips"] = ctdf["fips"].astype(str).str.zfill(5)
    uqlst = np.unique(ctdf["tempreg"])
    N = len(uqlst)
    ci_of_county = np.searchsorted(uqlst, ctdf["tempreg"].to_numpy())   # RGU index ci of each county

    panels = []
    for pol, suf in [("cur", ""), ("lmp", "_lmpdg")]:
        S = lca(f"uc_125PVhhec_fullyear{suf}", "BaselineCost")
        panels.append(("PV only", pol, S))
        for name, scen in [("Uncontrolled charging", "uc"), ("Controlled charging", "cc"), ("V2H", "v2h")]:
            panels.append((name, pol, S + lca(f"{scen}_125PVhhec_fullyear{suf}", "Cost")))
letters = "abcdefgh"

allv = np.concatenate([v for _, _, v in panels])
R = float(np.ceil(np.percentile(np.abs(allv), 99.5) / 5) * 5)   # shared color limit, thousand USD
print(f"color range +/-{R:.0f}k; values span {allv.min():.1f}k to {allv.max():.1f}k; "
      f"RGU values beyond the range: {int((np.abs(allv) > R).sum())}")
for L, (name, pol, v) in zip(letters, panels):
    print(f"{L} {name:22s} {pol}: {v.mean():.1f}k ({np.percentile(v, 5):.1f}k to {np.percentile(v, 95):.1f}k) n={v.size}")

if not FROM_SOURCE:
    # per-county table: one column per panel
    src = ctdf[["fips", "tempreg"]].copy()
    for L, (name, pol, v) in zip(letters, panels):
        src[f"{L}_{name.replace(' ', '_')}_{pol}"] = v[ci_of_county]
    # The county table has no entry for Oglala Lakota County, SD, which the plotly GeoJSON lists under its
    # former code 46113 (Shannon County); draw it with the values of neighboring Bennett County (46007, row 2330).
    plot_df = pd.concat([src, src.iloc[2330:2331]], ignore_index=True)
    plot_df.loc[plot_df.index[-1], "fips"] = "46113"

with urlopen("https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json", timeout=60) as r:
    counties = json.load(r)
keep = set(plot_df["fips"])


def _round(c):
    return [_round(x) for x in c] if isinstance(c[0], list) else [round(c[0], 4), round(c[1], 4)]


# keep only the drawn counties and round coordinates to 4 decimals (smaller PDF)
feats = [f for f in counties["features"] if f["id"] in keep]
for f in feats:
    f["geometry"]["coordinates"] = _round(f["geometry"]["coordinates"])
counties = {"type": "FeatureCollection", "features": feats}

# ---------------- layout (px; PDF exported at scale 1, 571 px = 5.95 in) ----------------
WIDTH_IN = 5.95
W = round(WIDTH_IN * 96)
H = 249
FS = 11.5
FONT = "Arial"
M = dict(l=36, r=2, t=5, b=12)
HP = H - M["t"] - M["b"]
CB_H, TITLE_H = 46, 16
MAP_H = (HP - CB_H - 2 * TITLE_H) / 2
px = lambda v: v / HP
ROW_Y = {1: (1 - px(CB_H + TITLE_H + MAP_H), 1 - px(CB_H + TITLE_H)), 2: (0.0, px(MAP_H))}

titles = [f"<b>{L}</b>  {name}" for L, (name, pol, v) in zip(letters, panels)]
fig = make_subplots(rows=2, cols=4, specs=[[{"type": "geo"}] * 4] * 2,
                    horizontal_spacing=0.004, vertical_spacing=0.1, subplot_titles=titles)
for k in range(1, 9):
    fig.layout["geo" if k == 1 else f"geo{k}"].domain.y = ROW_Y[1 if k <= 4 else 2]
for k, ann in enumerate(fig.layout.annotations):
    ann.y = ROW_Y[1 if k < 4 else 2][1]
    ann.yanchor = "bottom"

step = 10 if R > 30 else 5
ticks = [t for t in range(-int(R) // step * step, int(R) + 1, step)]
cols = [c for c in src.columns if c not in ("fips", "tempreg")]
for i, col in enumerate(cols):
    fig.add_trace(go.Choropleth(
        geojson=counties, locations=plot_df["fips"], z=plot_df[col], featureidkey="id",
        colorscale="RdBu_r", zmin=-R, zmax=R, showscale=(i == 0), marker=dict(line=dict(width=0)),
        colorbar=dict(
            orientation="h", x=0.5, xanchor="center", y=1, yanchor="top", ypad=0, xpad=0,
            thickness=12, len=0.35, outlinewidth=0.5, outlinecolor="black",
            tickmode="array", tickvals=ticks, ticktext=[f"{t:g}" for t in ticks],
            ticks="outside", ticklen=3, tickwidth=0.5, tickcolor="black",
            tickfont=dict(family=FONT, size=FS, color="black"),
            title=dict(text="15-year bill change vs. home without EV or PV (thousand USD)", side="top",
                       font=dict(family=FONT, size=FS, color="black")),
        ),
    ), row=i // 4 + 1, col=i % 4 + 1)

# source data: the locations and z passed to each go.Choropleth above, long format (one row per panel and location)
if not FROM_SOURCE:
    pd.concat([pd.DataFrame({"panel": L, "panel_title": name,
                             "export_rates": {"cur": "Current export rates", "lmp": "LMP export rates"}[pol],
                             "fips": plot_df["fips"], "tempreg": plot_df["tempreg"],
                             "bill_change_15yr_vs_no_ev_no_pv_thousand_usd": plot_df[col]})
               for L, (name, pol, _), col in zip(letters, panels, cols)], ignore_index=True
              ).to_csv(SRC, index=False, encoding="utf-8")

fig.update_geos(visible=False, scope="usa", fitbounds="locations", bgcolor="white")
for ann in fig.layout.annotations:
    ann.font = dict(family=FONT, size=FS, color="black")
for r, lab in [(1, "Current<br>export rates"), (2, "LMP<br>export rates")]:
    geo = fig.layout["geo" if r == 1 else "geo5"]
    y0, y1 = geo.domain.y
    fig.add_annotation(text=lab, xref="paper", yref="paper", x=0, xshift=-6, y=(y0 + y1) / 2,
                       xanchor="right", yanchor="middle", textangle=-90, showarrow=False,
                       font=dict(family=FONT, size=FS, color="black"))
fig.update_layout(width=W, height=H, margin=M, paper_bgcolor="white", plot_bgcolor="white",
                  font=dict(family=FONT, size=FS, color="black"), showlegend=False)

fig.write_image(str(OUT / f"{STEM}.pdf"), format="pdf", width=W, height=H, scale=1)
fig.write_image(str(OUT / f"{STEM}.png"), format="png", width=W, height=H, scale=300 / 96)   # 300 dpi at 5.95 in
