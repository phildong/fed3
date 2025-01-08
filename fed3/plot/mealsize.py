import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scipy.ndimage import label

from fed3.core.fedfuncs import screen_mixed_alignment
from fed3.plot.helpers import _get_return_value, _parse_feds


def mealsize_hist(
    feds,
    event: str = "Pellet",
    meal_break: str = "30min",
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
    dat_sub = dat[dat["Event"] == event].reset_index().rename(columns={"index": "time"})
    dat_sub["same_meal"] = dat_sub["time"].diff() < pd.Timedelta(meal_break)
    dat_sub["meal_ct"] = label(dat_sub["same_meal"])[0]
    dat_out = (
        dat_sub[dat_sub["meal_ct"] > 0].groupby("meal_ct").apply(agg_meal).reset_index()
    )
    # plotting
    fig = px.histogram(dat_out, x="pellet_count")
    return _get_return_value(fig, dat_out, output)


def agg_meal(meal_df: pd.DataFrame, t_col="time"):
    return pd.Series(
        {
            "start_time": meal_df[t_col].iloc[0],
            "end_time": meal_df[t_col].iloc[-1],
            "pellet_count": len(meal_df),
        }
    )
