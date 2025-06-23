import pandas as pd
import panel as pn
from IPython.display import display

from fed3.core.fedfuncs import load
from fed3.metrics.core import get_metric
from fed3.plot.daynight import label_daynight
from fed3.plot.mealsize import label_meal


def agg_duration(df, tcol="time", unit="1 hour"):
    return (df[tcol].max() - df[tcol].min()) / pd.Timedelta(unit)


def export_summary(fed_df, tcol: str = "MM:DD:YYYY hh:mm:ss", **kwargs):
    summary = (
        fed_df.set_index(tcol)
        .groupby("group")
        .apply(compute_summary, **kwargs)
        .reset_index()
    )
    return summary


def compute_summary(
    f: pd.DataFrame,
    day_start: str = "8:00:00",
    day_end: str = "20:00:00",
    meal_break: str = "5min",
):
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


class FED3DATA:
    def __init__(self):
        self.dpaths = set()
        self.dpath_dict = None
        self.data_combined = None

    def select_data(self):
        fs = pn.widgets.FileSelector(
            directory=".",
            root_directory="/",
            only_files=True,
            name="Select FED Data Files",
        )
        fs.param.watch(self._on_sel_data, ["value"], onlychanged=True)
        display(fs)

    def _on_sel_data(self, event) -> None:
        for dp in event.new:
            self.dpaths.add(dp)

    def assign_metadata(self):
        assert len(self.dpaths) > 0, "Please add data files first!"
        self.dpath_dict = {dp: "default" for dp in self.dpaths}
        wdps = []
        for dp in self.dpaths:
            wdp = pn.widgets.TextInput(
                name=dp,
                placeholder="default",
                value="default",
                sizing_mode="stretch_width",
            )
            wdp.param.watch(self._on_assn_grp, ["value"], onlychanged=True)
            wdps.append(wdp)
        wbox = pn.WidgetBox(*wdps)
        display(wbox)

    def _on_assn_grp(self, event) -> None:
        dp = event.obj.name
        self.dpath_dict[dp] = event.new

    def load_data(self, **kwargs) -> None:
        assert len(self.dpaths) > 0, "Please add data files first!"
        if self.dpath_dict is None:
            self.dpath_dict = {dp: "default" for dp in self.dpaths}
        self.grouped = {g: [] for g in set(self.dpath_dict.values())}
        dfs = []
        for dp, grp in self.dpath_dict.items():
            df = load(dp, **kwargs)
            df["dpath"] = dp
            df["group"] = grp
            dfs.append(df.reset_index())
            self.grouped[grp].append(df)
        self.data_combined = pd.concat(dfs, ignore_index=True)
        print(
            "Loaded {} data with {} groups: {}".format(
                len(self.dpath_dict), len(self.grouped), list(self.grouped.keys())
            )
        )
