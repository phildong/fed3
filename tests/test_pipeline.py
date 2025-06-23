# %% import and definition
import os

import panel as pn

import fed3
import fed3.plot as fplot
from fed3.utilities import FED3DATA, export_summary

pn.extension()

IN_DPATH = "./data/20250606/"
OUT_PATH = "./output/"

os.makedirs(OUT_PATH, exist_ok=True)

# %% select data
dpaths = []
for root, dirs, files in os.walk(IN_DPATH):
    csvf = list(filter(lambda fn: fn.lower().endswith(".csv"), files))
    dpaths.extend([os.path.join(root, cf) for cf in csvf])
fed_data = FED3DATA()
fed_data.select_data(dpaths)
fed_data.assign_metadata(rel_start=True)

# %% load data and process
fed_data.load_data()
fig_daynight = fplot.daynight_bar(
    fed_data.data_combined, agg_grp="sum", tcol="elps_time"
)
fig_msize = fplot.mealsize_hist(fed_data.data_combined)
summary = export_summary(fed_data.data_combined)
summary.to_csv(os.path.join(OUT_PATH, "summary.csv"))
