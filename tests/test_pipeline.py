# %% import and definition
import os

import panel as pn

import fed3
import fed3.plot as fplot
from fed3.utilities import FED3DATA, export_summary

pn.extension()

IN_DPATH = "./data/20250606/"
PARAM_META_DICT = {
    "./data/20250606/mCherry/FED025_060424_00.CSV": {
        "group": "mCherry",
        "animal": "animal0",
        "start_time": "start",
    },
    "./data/20250606/mCherry/FED028_051524_00.CSV": {
        "group": "mCherry",
        "animal": "animal1",
        "start_time": "start",
    },
    "./data/20250606/mCherry/FED021_060424_00.CSV": {
        "group": "mCherry",
        "animal": "animal2",
        "start_time": "start",
    },
    "./data/20250606/mCherry/FED038_060424_00.CSV": {
        "group": "mCherry",
        "animal": "animal3",
        "start_time": "start",
    },
    "./data/20250606/mCherry/FED008_060124_00.CSV": {
        "group": "mCherry",
        "animal": "animal4",
        "start_time": "start",
    },
    "./data/20250606/mCherry/FED042_060124_00.CSV": {
        "group": "mCherry",
        "animal": "animal5",
        "start_time": "start",
    },
    "./data/20250606/mCherry/FED039_060124_00.CSV": {
        "group": "mCherry",
        "animal": "animal6",
        "start_time": "start",
    },
    "./data/20250606/mCherry/FED003_060124_00.CSV": {
        "group": "mCherry",
        "animal": "animal7",
        "start_time": "start",
    },
    "./data/20250606/hM4d/FED024_060124_00.CSV": {
        "group": "hM4d",
        "animal": "animal8",
        "start_time": "start",
    },
    "./data/20250606/hM4d/FED023_051524_00.CSV": {
        "group": "hM4d",
        "animal": "animal9",
        "start_time": "start",
    },
    "./data/20250606/hM4d/FED022_060124_00.CSV": {
        "group": "hM4d",
        "animal": "animal10",
        "start_time": "start",
    },
    "./data/20250606/hM4d/FED018_080124_00.CSV": {
        "group": "hM4d",
        "animal": "animal11",
        "start_time": "start",
    },
    "./data/20250606/hM4d/FED016_051524_00.CSV": {
        "group": "hM4d",
        "animal": "animal12",
        "start_time": "start",
    },
    "./data/20250606/hM4d/FED043_080124_00.CSV": {
        "group": "hM4d",
        "animal": "animal13",
        "start_time": "start",
    },
    "./data/20250606/hM4d/FED030_060424_00.CSV": {
        "group": "hM4d",
        "animal": "animal14",
        "start_time": "start",
    },
    "./data/20250606/hM4d/FED008_072624_01.CSV": {
        "group": "hM4d",
        "animal": "animal15",
        "start_time": "start",
    },
}
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
fig_daynight = fplot.daynight_plot(
    fed_data.data_combined, agg_grp="sum", tcol="elps_time"
)
fig_msize = fplot.mealsize_hist(fed_data.data_combined)
summary = export_summary(fed_data.data_combined)
summary.to_csv(os.path.join(OUT_PATH, "summary.csv"))
