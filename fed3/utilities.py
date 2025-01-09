import pandas as pd

from fed3.metrics.core import get_metric
from fed3.plot.daynight import label_daynight
from fed3.plot.mealsize import label_meal


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
