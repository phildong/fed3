import itertools as itt

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.express.colors import qualitative
from scipy.ndimage import label

from fed3.core.fedfuncs import screen_mixed_alignment
from fed3.plot.helpers import _get_return_value, _parse_feds


def label_daynight(fed_df: pd.DataFrame, day_start: str, day_end: str):
    if isinstance(fed_df.index, pd.TimedeltaIndex):
        fed_df.index = fed_df.index + pd.Timestamp("2025")
    assert isinstance(fed_df.index, pd.DatetimeIndex)
    day_idx = fed_df.index.indexer_between_time(day_start, day_end)
    fed_df = fed_df.rename_axis(index="time").reset_index()
    fed_df["isDay"] = False
    fed_df.loc[day_idx, "isDay"] = True
    day_lab, nlab = label(fed_df["isDay"])
    day_lab = np.where(day_lab > 0, day_lab, np.nan)
    fed_df["day_ct"] = day_lab
    fed_df["day_ct"] = fed_df["day_ct"].bfill().fillna(nlab + 1).astype(int)
    return fed_df


def daynight_plot(
    fed_df,
    kind="line",
    event: str = "Pellet",
    tcol: str = "MM:DD:YYYY hh:mm:ss",
    anmcol: str = "animal",
    bin_width: str = "30min",
    day_start: str = "8:00:00",
    day_end: str = "20:00:00",
    mixed_align: str = "raise",
    agg_grp: str = None,
    output="plot",
):
    # agg data
    yname = event + " Count"
    if anmcol is not None:
        grp_cols = ["group", anmcol, "dpath", pd.Grouper(freq=bin_width)]
    else:
        grp_cols = ["group", "dpath", pd.Grouper(freq=bin_width)]
    dat_out = (
        fed_df[fed_df["Event"] == event]
        .set_index(tcol)
        .groupby(grp_cols)["Event"]
        .count()
        .rename(yname)
        .reset_index()
    )
    if agg_grp is not None:
        if anmcol is not None:
            grp_cols = ["group", anmcol, tcol]
        else:
            grp_cols = ["group", tcol]
        dat_out = dat_out.groupby(grp_cols)[yname].agg(agg_grp).reset_index()
    else:
        dat_out = dat_out.drop(columns="group").rename(columns={"dpath": "group"})
    dat_out = dat_out.sort_values(tcol).set_index(tcol)
    dat_out = label_daynight(dat_out, day_start, day_end)
    # plotting
    if kind == "line":
        fig = line_plot(dat_out, time_col="time", value_col=yname)
    elif kind == "bar":
        fig = px.bar(dat_out, x="time", y=yname, color="group", barmode="group")
    else:
        raise ValueError("Unknown plot type: {}".format(kind))
    night_lab, nlab = label(~dat_out["isDay"])
    for ilab in range(1, nlab + 1):
        loc = np.where(night_lab == ilab)[0]
        t_start, t_end = dat_out.loc[loc[0], "time"], dat_out.loc[loc[-1], "time"]
        fig.add_vrect(x0=t_start, x1=t_end, line_width=0, fillcolor="grey", opacity=0.3)
    return _get_return_value(fig, dat_out, output)


def line_plot(
    df, time_col="time", animal_col="animal", group_col="group", value_col="value"
):
    fig = go.Figure()
    cmap = {
        g: c for g, c, in zip(df[group_col].unique(), itt.cycle(qualitative.Plotly))
    }
    # Plot individual animal traces
    for animal, sub_df in df.groupby(animal_col):
        g = sub_df[group_col].unique().item()
        fig.add_trace(
            go.Scatter(
                x=sub_df[time_col],
                y=sub_df[value_col],
                mode="lines",
                name=f"{animal}",
                line=dict(width=1, color=cmap[g]),
                showlegend=False,
                hoverinfo="name+y",
            )
        )
    # Plot group means and error bands
    for grp, group_df in df.groupby(group_col):
        # Resample or group by time for aggregation (assumes all animals have same time points)
        grp_agg = (
            group_df.groupby(time_col)
            .agg(
                mean=(value_col, "mean"),
                std=(value_col, "std"),
                count=(value_col, "count"),
            )
            .reset_index()
            .dropna()
        )
        # Optional: Compute standard error (SEM)
        grp_agg["sem"] = grp_agg["std"] / grp_agg["count"] ** 0.5
        grp_agg["upper"] = grp_agg["mean"] + grp_agg["sem"]
        grp_agg["lower"] = grp_agg["mean"] - grp_agg["sem"]
        # Plot mean line
        fig.add_trace(
            go.Scatter(
                x=grp_agg[time_col],
                y=grp_agg["mean"],
                mode="lines",
                name=f"{grp} mean",
                line=dict(width=3, color=cmap[grp]),
            )
        )
        # Plot error band
        fig.add_trace(
            go.Scatter(
                x=pd.concat([grp_agg[time_col], grp_agg[time_col][::-1]]),
                y=pd.concat([grp_agg["upper"], grp_agg["lower"][::-1]]),
                fill="toself",
                fillcolor=cmap[grp],
                line=dict(color="rgba(255,255,255,0)"),
                hoverinfo="skip",
                showlegend=False,
                name=f"{grp} SEM",
                opacity=0.6,
            )
        )
    # fig.update_layout(
    #     title="Animal-level traces and Group Mean with Error Bands",
    #     xaxis_title="Time",
    #     yaxis_title="Value",
    #     template="plotly_white",
    # )
    return fig
