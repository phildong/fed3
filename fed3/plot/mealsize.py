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
    dat_out = label_meal(dat, event, meal_break)
    # plotting
    fig = px.histogram(dat_out, x="pellet_count")
    return _get_return_value(fig, dat_out, output)


def label_meal(fed_df: pd.DataFrame, event: str, meal_break: str):
    meal_df = (
        fed_df[fed_df["Event"] == event].reset_index().rename(columns={"index": "time"})
    )
    meal_df["same_meal"] = meal_df["time"].diff() < pd.Timedelta(meal_break)
    meal_ct, nmeal = label(meal_df["same_meal"])
    meal_df["meal_ct"] = np.where(meal_ct > 0, meal_ct, np.nan)
    meal_df["meal_ct"] = meal_df["meal_ct"].bfill().fillna(nmeal + 1)
    meal_df = meal_df.groupby("meal_ct").apply(agg_meal).reset_index()
    return meal_df


def agg_meal(meal_df: pd.DataFrame, t_col="time"):
    meta_cols = set(meal_df.columns).intersection(["Session_Type", "isDay"])
    return pd.Series(
        {
            "start_time": meal_df[t_col].iloc[0],
            "end_time": meal_df[t_col].iloc[-1],
            "pellet_count": len(meal_df),
        }
        | {m: meal_df[m].iloc[0] for m in meta_cols}
    )
