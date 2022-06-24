#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun May  9 15:26:30 2021

@author: earnestt1234
"""

__all__ = ['set_lightcycle']

import datetime as dt

import pandas as pd

LIGHTCYCLE = {'on': dt.time(hour=7, minute=0), 'off': dt.time(hour=19, minute=0)}

def time_to_float(x):
    return x.hour + (1/60) * x.minute

def set_lightcycle(on_hour, off_hour, on_minute=0, off_minute=0):
    LIGHTCYCLE['on'] = dt.time(hour=on_hour, minute=on_minute)
    LIGHTCYCLE['off'] = dt.time(hour=off_hour, minute=off_minute)

def is_at_night(datetime, lights_on, lights_off):
    ashour = time_to_float(datetime)
    lights_on = time_to_float(lights_on)
    lights_off = time_to_float(lights_off)
    if lights_on > lights_off:
        return (lights_off <= ashour < lights_on)
    else:
        return (ashour < lights_on or ashour >= lights_off)

def lightcycle_tuples(start_date, end_date, lights_on, lights_off, kind='nights',
                      pdconvert=True):

    if kind not in ['days', 'nights']:
        raise ValueError(f"`kind` must be 'nights' or 'days', not {kind}")

    result = []
    t = start_date
    day = pd.Timedelta('24H')

    lookfor = 'on' if kind == 'days' else 'off'

    if pdconvert:
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)

    while True:

        if t == end_date:
            if lookfor == 'on' and is_at_night(end_date, lights_on, lights_off):
                result.append(t)
            break

        elif lookfor == 'off':
            if is_at_night(t, lights_on, lights_off):
                result.append(t)
                new_t = t.replace(hour=lights_on.hour, minute=lights_on.minute).floor('1T')
                lookfor = 'on'
            else:
                new_t = t.replace(hour=lights_off.hour, minute=lights_off.minute).floor('1T')

        elif lookfor == 'on':
            if not is_at_night(t, lights_on, lights_off):
                result.append(t)
                new_t = t.replace(hour=lights_off.hour, minute=lights_off.minute).floor('1T')
                lookfor = 'off'
            else:
                new_t = t.replace(hour=lights_on.hour, minute=lights_on.minute).floor('1T')

        if new_t < t:
            new_t += day

        if new_t > end_date:
            new_t = end_date

        t = new_t

    result = list(zip(result[::2], result[1::2]))

    return result