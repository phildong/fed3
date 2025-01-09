#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module defines functions for working with `fed3.FEDFrame` objects.
Key operations include concatenating/splitting data, filtering, and
temporal alignment.
"""

__all__ = [
    "as_aligned",
    "can_concat",
    "concat",
    "load",
    "screen_mixed_alignment",
    "split",
    "timecrop",
]

import os
import warnings
from collections.abc import Iterable

import pandas as pd

from fed3.core import FEDFrame
from fed3.metrics.core import get_metric
from fed3.plot.daynight import label_daynight
from fed3.plot.mealsize import label_meal

"""Date to use when aligning data based on elapsed time or time of day."""


def _split_handle_dates(dates):
    """Helper function for parsing the `dates` parameter within `split()."""
    old = pd.Timestamp("01-01-1970")
    future = pd.Timestamp("12-31-2200")
    if not isinstance(dates, Iterable) or isinstance(dates, str):
        dates = [old, pd.to_datetime(dates), future]
    else:
        dates = [pd.to_datetime(date) for date in dates]
        dates = [old] + dates + [future]

    return dates


def as_aligned(feds, alignment, inplace=False):
    """
    Helper function for setting the alignment of one or more FEDFrames.
    See `fed3.core.fedframe.FEDFrame.set_alignment()` for more information.

    Parameters
    ----------
    feds : FEDFrame or collection of FEDFrames
        FEDFrames to set alignment for
    alignment: 'str':
        Alignment string.
    inplace : bool
        When True, the FEDFrames are modified in place; otherwise,
        new copies are created.

    Returns
    -------
    aligned or None
        Either one FEDFrame or a list of FEDFrames with new alignment..

    """
    if isinstance(feds, FEDFrame):
        aligned = feds.set_alignment(alignment, inplace=inplace)
    else:
        aligned = [f.set_alignment(alignment) for f in feds]

    return aligned


def can_concat(feds):
    """
    Determines whether or not FEDFrames can be concatenated, (based on whether
    their start and end times overlap).

    Parameters
    ----------
    feds : array
        an array of FEDFrames

    Returns
    -------
    bool

    """
    sorted_feds = sorted(feds, key=lambda x: x.start_time)
    for i, file in enumerate(sorted_feds[1:], start=1):
        if file.start_time <= sorted_feds[i - 1].end_time:
            return False
    return True


def concat(
    feds,
    name=None,
    add_concat_number=True,
    reset_columns=("Pellet_Count", "Left_Poke_Count", "Right_Poke_Count"),
):
    """
    Concatenated FED3 data in time.

    Parameters
    ----------
    feds : collection of FEDFrame objects
        List or other collection of FEDFrame
    name : str, optional
        Name to give the new FEDFrame with concatenated data.
        The default is None, in which case the name of the first FEDFrame
        is used.
    add_concat_number : bool, optional
        Adds a column keeping record of the concatenation. The default is True.
    reset_columns : list-like, optional
        Columns whose counts should be modified in order to preserve counts
        across the concatenated data.  The default is
        `('Pellet_Count', 'Left_Poke_Count','Right_Poke_Count')`.

    Raises
    ------
    ValueError
        Cannot concatenated FED data when the timestamps are overlapping.

    Returns
    -------
    newfed : fed3.FEDFrame
        New FEDFrame object with concatenated data.

    """

    if name is None:
        name = feds[0].name

    if not can_concat(feds):
        raise ValueError("FEDFrame dates overlap, cannot concat.")

    output = []
    offsets = {}

    sorted_feds = sorted(feds, key=lambda x: x.start_time)

    for i, fed in enumerate(sorted_feds):
        df = fed.copy()
        if add_concat_number:
            df["Concat_#"] = i

        if i == 0:
            for col in reset_columns:
                if col in df.columns:
                    offsets[col] = df[col].max()

        else:
            for col, offset in offsets.items():
                df[col] += offset
                offsets[col] = df[col].max()

        output.append(df)

    newfed = pd.concat(output)
    newfed._load_init(name=name)

    return newfed


def determine_alignment(feds):
    """
    Return the temporal alignment for a FEDFrame or group of FEDFrames.
    See `align()` for more information.

    Parameters
    ----------
    feds : fed3.FEDFrame or list of such
        FED3 data to determine alignment for.

    Returns
    -------
    str
        'datetime', 'time', 'elapsed', or 'mixed' (the latter when
        there are multiple alignment types).

    """
    alignments = set(f._alignment for f in feds)
    return "mixed" if len(alignments) > 1 else list(alignments)[0]


def load(
    path,
    index_col="MM:DD:YYYY hh:mm:ss",
    dropna=True,
    deduplicate_index=None,
    offset="1S",
    reset_counts=False,
    reset_columns=("Pellet_Count", "Left_Poke_Count", "Right_Poke_Count"),
):
    """
    Load FED3 data from a CSV/Excel file.  This is the typical
    recommended way for importing FED3 data.  Relies mostly
    on `pandas.read_csv()` and `pandas.read_excel()` for the parsing.

    Parameters
    ----------
    path : str
        System path to FED3 data file.
    index_col : str, optional
        Timestamp column to use as index. The default is 'MM:DD:YYYY hh:mm:ss'.
    dropna : bool, optional
        Remove all empty rows. The default is True.
    deduplicate_index, offset, reset_counts, reset_columns: optional
        Arguments passed to `fed3.FEDFrame.deduplicate_index()`, used
        to remove duplicate timestamps as the data are loaded.

    Returns
    -------
    f : fed3.FEDFrame
        New FEDFrame object.

    """
    # read the path
    name, ext = os.path.splitext(path)
    ext = ext.lower()

    read_opts = {".csv": pd.read_csv, ".xlsx": pd.read_excel}
    func = read_opts[ext]
    feddata = func(path, parse_dates=True, index_col=index_col)
    if dropna:
        feddata = feddata.dropna(how="all")

    name = os.path.basename(name)
    f = FEDFrame(feddata)
    f._load_init(
        name=name,
        path=path,
        deduplicate_index=deduplicate_index,
        offset=offset,
        reset_counts=reset_counts,
        reset_columns=reset_columns,
    )

    return f


def screen_mixed_alignment(feds, option="raise"):
    """
    Check FEDFrames for having mixed alignment styles (see `align()`).
    This is called by most plots witin `fed3.plot` for the `mixed_align`
    parameter.

    Parameters
    ----------
    feds : FEDFrame or list of such.
        FED3 data to screen.
    option : str, optional
        Method for screening data. The default is 'raise', which will raise
        an error for mixed alignment.  'warn' will only show a warning, while
        'ignore' will pass silently.

    Raises
    ------
    ValueError
        Screening method not recognized, or 'raise' option being used.

    Returns
    -------
    alignment : str
        Alignment string returned by `determine_alignment()`.

    """

    alignment = determine_alignment(feds)

    if alignment != "mixed":
        return alignment

    if option == "raise":
        raise ValueError("The passed FEDFrames have mixed alignment.")

    elif option == "warn":
        warnings.warn("The passed FEDFrames have mixed alignment.")

    elif option != "ignore":
        raise ValueError('Mixed alignment option must be "ignore", "warn", or "raise"')

    return alignment


def split(
    fed,
    dates,
    reset_columns=("Pellet_Count", "Left_Poke_Count", "Right_Poke_Count"),
    return_empty=False,
    tag_name=True,
):
    """
    Split one FEDFrame into a multiple based on one or more dates.

    Parameters
    ----------
    fed : fed3.FEDFrame
        FED3 data.
    dates : datetime string or datetime object, or list-like of such
        Timestamp(s) to split the data on.
    reset_columns : list-like, optional
        Columns whose cumulative totals should be reset when splitting the data.
        The default is ('Pellet_Count', 'Left_Poke_Count', 'Right_Poke_Count').
    return_empty : bool, optional
        Return empty FEDFrames created from splitting. The default is False.
    tag_name : bool, optional
        Add a `'_#'` tag to the name of each new FEDFrame. The default is True.

    Returns
    -------
    output : list
        List of FED3 objects created by split.

    """
    dates = _split_handle_dates(dates)
    output = []
    offsets = {col: 0 for col in reset_columns}
    og_name = fed.name
    for i in range(len(dates[:-1])):
        start = dates[i]
        end = dates[i + 1]
        subset = fed[(fed.index >= start) & (fed.index < end)].copy()
        if tag_name:
            subset.name = f"{og_name}_{i}"
        if not return_empty and subset.empty:
            continue
        if offsets:
            for col in reset_columns:
                subset[col] -= offsets[col]
                offsets[col] = subset[col].max()
        output.append(subset)
    return output


def timecrop(
    fed,
    start,
    end,
    reset_columns=("Pellet_Count", "Left_Poke_Count", "Right_Poke_Count"),
    name=None,
):
    """
    Return a new FEDFrame cropped in time to only include data between two
    dates.

    Parameters
    ----------
    fed : fed3.FEDFrame
        FED3 data.
    start : datetime str or object
        Time to start including data (inclusive).
    end : datetime str or object
        Time to stop including data (exclusive).
    reset_columns : list-like, optional
        Columns whose cumulative totals should be reset when cropping the data.
        The default is ('Pellet_Count', 'Left_Poke_Count', 'Right_Poke_Count').
    name : str, optional
        Name for the new FEDFrame produced. The default is None.

    Returns
    -------
    newfed : fed3.FEDFrame
        New FEDFrame object after filtering.

    """

    prior = fed[(fed.index < start)]
    newfed = fed[(fed.index >= start) & (fed.index < end)].copy()
    for col in reset_columns:
        if not prior.empty:
            newfed[col] -= prior[col].max()

    if name is not None:
        newfed.name = name

    return newfed


def agg_duration(df, tcol="time", unit="1 hour"):
    return (df[tcol].max() - df[tcol].min()) / pd.Timedelta(unit)


def export_summary(
    fed, day_start: str = "8:00:00", day_end: str = "20:00:00", meal_break: str = "5min"
):
    f = fed  # TODO: add support for multiple datasets
    f = label_daynight(f, day_start, day_end)
    dur = agg_duration(f)
    dur_dn = (
        f.groupby(["isDay", "day_ct"])
        .apply(agg_duration)
        .rename("duration")
        .reset_index()
        .groupby("isDay")["duration"]
        .sum()
    )
    agg_res = {
        "duration": dur,
        "duration-day": dur_dn.loc[True],
        "duration-night": dur_dn.loc[False],
    }
    for agg_var in ["pellets", "meals", "pokes", "correct_pokes"]:
        if agg_var == "meals":
            meal_df = label_meal(f.set_index("time"), "Pellet", meal_break)
            meal_df_agg = meal_df.groupby("isDay").apply(
                lambda df: df["pellet_count"].sum() / len(df)
            )
            agg_res["pellets/meal"] = meal_df["pellet_count"].sum() / len(meal_df)
            # TODO: confirm this is inconsistent with pellet / nmeal due to timing of meal
            agg_res["pellets/meal-day"] = meal_df_agg.loc[True]
            agg_res["pellets/meal-night"] = meal_df_agg.loc[False]

            meal_df["value"] = 1
            dat = meal_df[["isDay", "value"]]
        else:
            agg_func = get_metric("binary_{}".format(agg_var))[0]
            agg_df = f.copy()
            agg_df["value"] = agg_func(f)
            dat = agg_df[["isDay", "value"]].fillna(0)
        dat_tt = dat["value"].sum()
        dat_tt_dn = dat.groupby("isDay")["value"].sum()
        dat_perh = dat_tt / dur
        dat_perh_dn = dat_tt_dn / dur_dn
        agg_res[agg_var] = dat_tt
        agg_res["{}-day".format(agg_var)] = dat_tt_dn.loc[True]
        agg_res["{}-night".format(agg_var)] = dat_tt_dn.loc[False]
        agg_res["{}/hr".format(agg_var)] = dat_perh
        agg_res["{}/hr-day".format(agg_var)] = dat_perh_dn.loc[True]
        agg_res["{}/hr-night".format(agg_var)] = dat_perh_dn.loc[False]
    bat = get_metric("battery")[0](f.copy())
    agg_res["min_battery"] = bat.min()
    mot = get_metric("motor")[0](f.copy())
    agg_res["motor_count"] = (mot > 10).sum()
    return pd.Series(agg_res).rename("value").to_frame()
