import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scipy.ndimage import label

from fed3.core.fedfuncs import screen_mixed_alignment
from fed3.plot.helpers import _get_return_value, _parse_feds


def label_daynight(fed_df: pd.DataFrame, day_start: str, day_end: str):
    day_idx = fed_df.index.indexer_between_time(day_start, day_end)
    fed_df = fed_df.reset_index().rename(columns={"index": "time"})
    fed_df["isDay"] = False
    fed_df.loc[day_idx, "isDay"] = True
    day_lab, nlab = label(fed_df["isDay"])
    day_lab = np.where(day_lab > 0, day_lab, np.nan)
    fed_df["day_ct"] = day_lab
    fed_df["day_ct"] = fed_df["day_ct"].bfill().fillna(nlab + 1).astype(int)
    return fed_df


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
    dat_out = label_daynight(dat_out, day_start, day_end)
    # plotting
    fig = px.bar(dat_out, x="time", y=yname)
    night_lab, nlab = label(~dat_out["isDay"])
    for ilab in range(1, nlab + 1):
        loc = np.where(night_lab == ilab)[0]
        t_start, t_end = dat_out.loc[loc[0], "time"], dat_out.loc[loc[-1], "time"]
        fig.add_vrect(x0=t_start, x1=t_end, line_width=0, fillcolor="grey", opacity=0.3)
    return _get_return_value(fig, dat_out, output)
