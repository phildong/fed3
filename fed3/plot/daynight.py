import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scipy.ndimage import label

from fed3.core.fedfuncs import screen_mixed_alignment
from fed3.plot.helpers import _get_return_value, _parse_feds


def daynight_bar(
    feds,
    event: str = "Pellet",
    bin_width: str = "30min",
    day_start: str = "8:00:00",
    day_end: str = "20:00:00",
    mixed_align: str = "raise",
    output="plot",
):
    # parse inputs
    feds_dict = _parse_feds(feds)
    feds_all = list(*feds_dict.values())
    # screen issues alignment
    alignment = screen_mixed_alignment(feds_all, option=mixed_align)
    # TODO: figure out the multi-dataframe dict scheme
    dat = feds_all[0]
    # agg data
    yname = event + " Count"
    dat_out = (
        dat[dat["Event"] == event]
        .groupby(pd.Grouper(freq=bin_width))["Event"]
        .count()
        .rename(yname)
    )
    day_idx = dat_out.index.indexer_between_time(day_start, day_end)
    dat_out = dat_out.reset_index().rename(columns={"index": "time"})
    dat_out["isDay"] = False
    dat_out.loc[day_idx, "isDay"] = True
    # plotting
    fig = px.bar(dat_out, x="time", y=yname)
    night_lab, nlab = label(~dat_out["isDay"])
    for ilab in range(1, nlab + 1):
        loc = np.where(night_lab == ilab)[0]
        t_start, t_end = dat_out.loc[loc[0], "time"], dat_out.loc[loc[-1], "time"]
        fig.add_vrect(x0=t_start, x1=t_end, line_width=0, fillcolor="grey", opacity=0.3)
    return _get_return_value(fig, dat_out, output)
