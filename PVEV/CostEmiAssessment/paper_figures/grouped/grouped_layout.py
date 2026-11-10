"""Shared page geometry, type scale and legend for Fig_Bill_grouped and Fig_Emissions_grouped.

Both figure scripts import this module, so the two figures have the same page size, panel positions
and font sizes. Sizes are in inches and points at the printed size (5.95 in wide, included at 100%).
Importing the module sets the matplotlib fonts: Arial, embedded as TrueType (pdf.fonttype 42).
"""
import matplotlib
from matplotlib.patches import Patch
from matplotlib.transforms import ScaledTranslation

matplotlib.rcParams["axes.unicode_minus"] = False   # ASCII hyphen-minus on negative tick labels
matplotlib.rcParams["pdf.fonttype"] = 42             # embed Arial as TrueType (text stays text)
matplotlib.rcParams["ps.fonttype"] = 42
matplotlib.rcParams["font.family"] = "Arial"
matplotlib.rcParams["mathtext.fontset"] = "custom"
matplotlib.rcParams["mathtext.rm"] = "Arial"
matplotlib.rcParams["mathtext.it"] = "Arial:italic"
matplotlib.rcParams["mathtext.bf"] = "Arial:bold"

FONTFAMILY = "Arial"

# ── Type scale (points) ──────────────────────────────────────────────
FS_PANEL_TITLE = 9.0    # panel titles "(a) ...", "(b) ...", bold
FS_AXIS_LABEL = 9.0     # y-axis titles
FS_TICK = 8.5           # tick labels and bold cluster labels
FS_SMALL = 8.5          # legend entries and the "n=432" note

# ── Page geometry (inches) ───────────────────────────────────────────
W = 5.95                # page width
AX_H = 2.30             # height of each panel's axes (166 pt: the 9-pt y titles fit within it)
LEFT = 0.82             # left edge of axes: room for the 3-line emissions (b) y title + tick labels
RIGHT = 0.06            # right margin
TOP = 0.26              # page top to top of panel (a) axes: room for panel title
MID = 0.92              # bottom of (a) axes to top of (b) axes: ticks, cluster labels, gap, title (b)
BOTTOM = 1.06           # bottom of (b) axes to page bottom: ticks, cluster labels, legend
H = TOP + AX_H + MID + AX_H + BOTTOM
AX_W = W - LEFT - RIGHT

TITLE_PAD = 6.0         # pt between axes top and panel title
YLABEL_PAD = 5.0        # pt between y tick labels and y title
CLUSTER_OFFSET_PT = 21.0  # pt from the x axis down to the top of the bold cluster labels


def set_y_major_locator(ax):
    """Y major ticks at 'nice' steps (1, 2, 2.5, 5 or 10 x a power of ten), about 8 intervals.

    This is matplotlib's default AutoLocator with nbins fixed at 8 instead of 'auto', which would derive
    the number of intervals from the axes height; the tick step therefore does not depend on the panel height."""
    from matplotlib.ticker import MaxNLocator
    ax.yaxis.set_major_locator(MaxNLocator(nbins=8, steps=[1, 2, 2.5, 5, 10]))


def make_figure(plt):
    """Two stacked panels at fixed positions (no bbox_inches='tight': page stays exactly W x H)."""
    fig = plt.figure(figsize=(W, H))
    ax1 = fig.add_axes([LEFT / W, (BOTTOM + AX_H + MID) / H, AX_W / W, AX_H / H])
    ax2 = fig.add_axes([LEFT / W, BOTTOM / H, AX_W / W, AX_H / H])
    return fig, ax1, ax2


def cluster_label_transform(ax, fig):
    """x in data units, y = x-axis line, then shifted down by CLUSTER_OFFSET_PT points."""
    return ax.get_xaxis_transform() + ScaledTranslation(0, -CLUSTER_OFFSET_PT / 72, fig.dpi_scale_trans)


def add_legend(fig, C_UC, C_CC, C_V2H, C_PV):
    """Four entries in 2 x 2 (one row of four is 445 pt wide at 8.5 pt, wider than the 428 pt page).
    Handles are passed column-major so the rows read UC, CC / V2H, PV left to right."""
    uc = Patch(facecolor=C_UC, edgecolor="black", label="Uncontrolled charging (UC)")
    cc = Patch(facecolor=C_CC, edgecolor="black", label="Controlled charging (CC)")
    v2h = Patch(facecolor=C_V2H, edgecolor="black", label="Vehicle-to-Home (V2H)")
    pv = Patch(facecolor=C_PV, edgecolor="black", label="PV-only (no EV)")
    x_center = (LEFT + AX_W / 2) / W     # centered under the axes
    return fig.legend(handles=[uc, v2h, cc, pv], loc="lower center", bbox_to_anchor=(x_center, 0.03 / H),
                      ncol=2, prop={"family": FONTFAMILY, "size": FS_SMALL},
                      framealpha=0.92, edgecolor="gray", handlelength=1.2, handleheight=0.7,
                      columnspacing=1.5, borderaxespad=0.0)
