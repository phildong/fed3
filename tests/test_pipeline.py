# %% import and definition
import os

import panel as pn

import fed3
import fed3.plot as fplot
from fed3.utilities import FED3DATA, export_summary

pn.extension()

IN_DPATH = "./data/20250606/"

# %% run pipeline
dpaths = []
for root, dirs, files in os.walk(IN_DPATH):
    csvf = list(filter(lambda fn: fn.lower().endswith(".csv"), files))
    dpaths.extend([os.path.join(root, cf) for cf in csvf])
fed_data = FED3DATA()
fed_data.select_data(dpaths)
fed_data.assign_metadata()
fed_data.load_data()
