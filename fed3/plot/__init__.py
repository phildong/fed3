# -*- coding: utf-8 -*-

"""
.. include:: ../../docs/plots_getting_started.md
"""

# define options
OPTIONS = {"default_shadedark": True, "default_legend": True}

# imports for package namespace

from .barchart import bar
from .chronogram import chronogram_circle, chronogram_line, chronogram_spiny
from .daynight import daynight_bar
from .helpers import argh, legend
from .ipi import ipi
from .mealsize import mealsize_hist
from .shadedark import shade_darkness
from .simple import line, scatter

__all__ = [
    "argh",
    "bar",
    "chronogram_circle",
    "chronogram_line",
    "chronogram_spiny",
    "daynight_bar",
    "ipi",
    "legend",
    "line",
    "mealsize_hist",
    "scatter",
    "shade_darkness",
]
