# filename schematics of the time series file(s)
# if {station}, {sys_id}, {prod_id}, {wl} are in the schematics, they are automatically
# replaced with actual values. Those placeholders can be omitted if not necessary.
DPCAL_TIME_SERIES_NAME = "dpcal_timeseries_{station}_sys{sys_id}_prod{prod_id}_{wl}.nc"

# minimum number of points for outlier detection in the calibration time series file
DPCAL_MIN_NB_OF_POINTS = 3

# a calibration is considered as outlier if it is outside timeseries.mean +/- timeseries.stddev * DPCAL_STD_OUTLIER_FACTOR
DPCAL_STD_OUTLIER_FACTOR = 2

# calibrations with a relative uncertainty larger than MAX_DPCAL_ERR are considered not valid
MAX_DPCAL_ERR = 0.1

# a calibration is considered not valid if vertical relative stddev of the ratio profiles is > MAX_RATIO_STDDEV
MAX_RATIO_STDDEV = 0.3

# plot the calibration measurement or not
PLOT_DPCAL = True

# path where to save the plot
DPCAL_PLOT_PATH = ""

# scale plot axes (calibration value axes) automatically or not
AUTO_SCALE = True

# if not automatic scaling, which axes limits to use
AXES_LIMITS = {
    355: (-0.01, 0.3),
    532: (-0.01, 0.3),
}

# if auto scaling -> minimum bin for retrieval of axis limits of ratio profile plot
DPCAL_MIN_BIN = 5

# how many days time axis shall span above and below actual date
TIME_AXIS_SPAN = 60  # days


COLORS = {
    532: {
        0: "g",  # ratio profile 1
        1: "olive",  # ratio profile 2
        "actual": "lime",
        "invalid": "red",
        "previous": "0.7",
    },
    355: {
        0: "darkblue",
        1: "darkcyan",
        "actual": "dodgerblue",
        "invalid": "red",
        "previous": "0.7",
    },
}
