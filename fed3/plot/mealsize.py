import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scipy.ndimage import label

from fed3.core.fedfuncs import screen_mixed_alignment
from fed3.plot.helpers import _get_return_value, _parse_feds


def mealsize_hist(
    fed_df,
    event: str = "Pellet",
    tcol: str = "MM:DD:YYYY hh:mm:ss",
    meal_break: str = "30min",
    mixed_align: str = "raise",
    output="plot",
):
    # agg data
    fed_df = fed_df.sort_values(tcol).set_index(tcol)
    dat_out = (
        fed_df.groupby("group")
        .apply(label_meal, event=event, meal_break=meal_break)
        .reset_index()
    )
    # plotting
    fig = px.histogram(dat_out, x="pellet_count", color="group", barmode="group")
    return _get_return_value(fig, dat_out, output)


def label_meal(fed_df: pd.DataFrame, event: str, meal_break: str):
    meal_df = fed_df[fed_df["Event"] == event].rename_axis(index="time").reset_index()
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
