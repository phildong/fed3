import numpy as np
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


def agg_events(fed_df, tcol: str = "elps_time", anmcol: str = "animal", trange=None):
    if trange is not None:
        t0, t1 = pd.Timedelta(trange[0]), pd.Timedelta(trange[1])
        fed_df = fed_df[(fed_df[tcol] >= t0) & (fed_df[tcol] <= t1)].copy()
    if anmcol is not None:
        grp_cols = ["Event", "group", "animal"]
    else:
        grp_cols["Event", "group"]
    return fed_df.groupby(grp_cols).size().rename("count").reset_index()


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
        self.meta_dict = None
        self.data_combined = None

    def select_data(self, dpaths=None):
        if dpaths is None:
            fs = pn.widgets.FileSelector(
                directory=".",
                root_directory="/",
                only_files=True,
                name="Select FED Data Files",
            )
            fs.param.watch(self._on_sel_data, ["value"], onlychanged=True)
            display(fs)
        else:
            self.dpaths = dpaths
            print("Selected {} files".format(len(dpaths)))

    def _on_sel_data(self, event) -> None:
        for dp in event.new:
            self.dpaths.add(dp)

    def assign_metadata(self, meta_dict=None, rel_start=False):
        assert len(self.dpaths) > 0, "Please add data files first!"
        if meta_dict is None:
            self.meta_dict = {dp: dict() for dp in self.dpaths}
            wgts = []
            self._wgt_grps = []
            self._wgt_anms = []
            for idp, dp in enumerate(self.dpaths):
                w_dp = pn.pane.Markdown("## {}".format(dp))
                w_grp = pn.widgets.AutocompleteInput(
                    name="group",
                    placeholder="default",
                    restrict=False,
                    search_strategy="includes",
                    min_characters=1,
                    sizing_mode="stretch_width",
                )
                w_anm = pn.widgets.AutocompleteInput(
                    name="animal",
                    placeholder="animal{}".format(idp),
                    restrict=False,
                    search_strategy="includes",
                    min_characters=1,
                    sizing_mode="stretch_width",
                )
                w_st = pn.widgets.DatetimePicker(
                    name="start time", sizing_mode="stretch_width"
                )
                w_grp._dpath = dp
                w_anm._dpath = dp
                w_st._dpath = dp
                w_grp.param.watch(self._on_updt_grp, ["value"], onlychanged=True)
                w_anm.param.watch(self._on_updt_anm, ["value"], onlychanged=True)
                w_st.param.watch(self._on_updt_st, ["value"], onlychanged=True)
                w_row = pn.Column(pn.layout.Divider(), w_dp, pn.Row(w_grp, w_anm, w_st))
                wgts.append(w_row)
                self._wgt_grps.append(w_grp)
                self._wgt_anms.append(w_anm)
                self.meta_dict[dp]["group"] = "default"
                self.meta_dict[dp]["animal"] = "animal{}".format(idp)
                if rel_start:
                    self.meta_dict[dp]["start_time"] = "start"
            wbox = pn.Column(*wgts)
            display(wbox)
        else:
            self.meta_dict = meta_dict

    def _on_updt_grp(self, event) -> None:
        dp = event.obj._dpath
        self.meta_dict[dp]["group"] = event.new
        self._refresh_grp_opts()

    def _on_updt_anm(self, event) -> None:
        dp = event.obj._dpath
        self.meta_dict[dp]["animal"] = event.new
        self._refresh_anm_opts()

    def _on_updt_st(self, event) -> None:
        dp = event.obj._dpath
        self.meta_dict[dp]["start_time"] = event.new

    def _refresh_grp_opts(self) -> None:
        opts = list(set([w.value for w in self._wgt_grps]))
        for w in self._wgt_grps:
            w.options = opts

    def _refresh_anm_opts(self) -> None:
        opts = list(set([w.value for w in self._wgt_anms]))
        for w in self._wgt_anms:
            w.options = opts

    def load_data(self, t_col="MM:DD:YYYY hh:mm:ss", **kwargs) -> None:
        assert len(self.dpaths) > 0, "Please add data files first!"
        if self.meta_dict is None:
            self.meta_dict = {dp: dict() for dp in self.dpaths}
        grps = set([m.get("group", "default") for m in self.meta_dict.values()])
        self.grouped = {g: [] for g in grps}
        dfs = []
        for dp, mdict in self.meta_dict.items():
            df = load(dp, **kwargs).reset_index()
            df["dpath"] = dp
            grp = mdict.get("group", "default")
            anm = mdict.get("animal", np.nan)
            st = mdict.get("start_time", None)
            df["group"] = grp
            df["animal"] = anm
            if st == "start":
                st = df.loc[0, t_col]
            if st is not None:
                df["elps_time"] = df[t_col] - st
            else:
                df["elps_time"] = np.nan
            dfs.append(df)
            self.grouped[grp].append(df)
        self.data_combined = pd.concat(dfs, ignore_index=True)
        print(
            "Loaded {} data with {} groups: {}".format(
                len(self.meta_dict), len(self.grouped), list(self.grouped.keys())
            )
        )
