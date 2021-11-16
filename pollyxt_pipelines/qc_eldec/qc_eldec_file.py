"""
Algorithm for checking the calibration quality from SCC products.

Original code by Ina Mattis (@imattis on GitLab): https://gitlab.com/imattis/qc_eldec_file
Original code unlicensed but used with permission
"""

from datetime import datetime, timedelta
import os
from pathlib import Path
from pollyxt_pipelines import config

from pollyxt_pipelines.qc_eldec import constants
from pollyxt_pipelines.locations import Location

import numpy as np
from netCDF4 import Dataset, date2num, num2date
from matplotlib import pyplot as plt
from matplotlib.ticker import FuncFormatter
import matplotlib.dates as mdates


class ELDECfile:
    """
    class represents an ELDEC file.
    When initiated, it reads an ELDEC file and the local file with time series of previous calibrations.
    if the time series file does not exists, it is created.
    Next, the quality of the calibration is tested.
    the following criteria are checked:
        * is relative error of the gain factor below threshold?
        * is relative standard deviation of ratio profiles below threshold?
        * is there an overlap between uncertainty range of gain factor and standard deviation of time series * factor ?
         this test is only done if there already enough data points in the time series.
    If quality is ok, the information of the ELDEC file is added to the time series.
    finally, a plot is created.
    the result of the quality check can be asked with function calibration_ok()
    """

    timeseries = None
    axes_limits = (10, 0)
    max_alt = 0
    T0 = datetime(1970, 1, 1)

    def km_label(self, x, pos):
        "The two args are the value and tick position"
        #    return '%d' % (x*1e-3)
        return "%g" % (x * 1e-3)

    def __init__(self, filename, location: Location, plot_path=None):
        """
        read an ELDEC file

        Parameters
            filename: complete filename (incl. path) of ELDEC file
        """

        self.path = filename
        self.plot_path = plot_path

        # Read the file
        nc = Dataset(self.path, "r")
        nc.set_auto_mask(False)

        if nc.dimensions["time"].size > 1:
            print("cannot read ELDEC file with more than 1 calibration")
            return

        time_idx = 0  # read only first calibration

        self.altitude = nc["altitude"][:]
        self.height = self.altitude - nc["station_altitude"][0]

        time_bounds = nc["time_bounds"][time_idx]
        self.start_time = self.T0 + timedelta(seconds=int(time_bounds[0]))
        self.stop_time = self.T0 + timedelta(seconds=int(time_bounds[1]))

        self.station_id = nc.station_ID
        self.conf_id = nc.hoi_configuration_ID
        self.sys_id = nc.hoi_system_ID
        self.system = nc.system
        self.measurement_ID = nc.measurement_ID
        self.wavelength = round(
            nc["polarization_calibration_ratio_emission_wavelength"][0]
        )
        self.ELDEC_version = nc.processor_version
        self.SCC_version = nc.scc_version

        self.polcal_range_min = np.nanmin(
            nc["polarization_calibration_minimum_range"][:]
        )
        self.polcal_range_max = np.nanmax(
            nc["polarization_calibration_maximum_range"][:]
        )
        self.polcal_max_idx = np.where(self.height > self.polcal_range_max)[0][0]
        self.polcal_min_idx = np.where(self.height > self.polcal_range_min)[0][0]
        self.max_alt = max(self.max_alt, self.polcal_range_max * 1.2)

        self.ratio_profiles = self.mask(
            nc["polarization_calibration_ratio"][:, time_idx, :]
        )
        self.ratio_profile_errors = self.mask(
            nc["polarization_calibration_ratio_statistical_error"][:, time_idx, :]
        )

        self.profile_stddev = np.nanmean(
            np.nanstd(
                self.ratio_profiles[:, self.polcal_min_idx : self.polcal_max_idx],
                axis=1,
            )
        )

        if nc.getncattr("__file_format_version") <= "1.0":
            self.read_eldec_file_v10(nc)
        else:
            self.read_eldec_file_v11(nc)

        nc.close()

        # Determine config path to store timeseries
        config_path = config.config_paths()[-1] / "qc_eldec"
        config_path.mkdir(parents=True, exist_ok=True)
        self.timeseries_path = config_path / f"{location.name}_{self.wavelength}nm.nc"

        self.is_ok = False
        self.analyze()

    def read_eldec_file_v10(self, nc):
        """
        read eldec file with format version 1.0
        args: nc: netCDF4.Dataset
        """
        if os.path.basename(self.path).count("_") > 2:
            self.prod_id = int(os.path.basename(self.path).split("_")[2])
        else:
            self.prod_id = "nnn"

        time_idx = 0  # read only first calibration

        cal_values = nc["polarization_calibration_ratio_average"][:, time_idx]
        cal_errors = nc["polarization_calibration_ratio_average_statistical_error"][
            :, time_idx
        ]
        self.calvalue = np.nanmean(cal_values)
        self.calvalue_error = np.nanmean(cal_errors)

    def read_eldec_file_v11(self, nc):
        """
        read eldec file with format version > 1.0
        args: nc: netCDF4.Dataset
        """
        if nc.dimensions["calibration"].size > 1:
            print("cannot read ELDEC file with more than 1 calibration")
            return

        self.prod_id = nc.scc_product_ID
        time_idx = 0  # read only first calibration
        cal_idx = 0  # read only first calibration

        self.calvalue = nc["polarization_gain_factor"][cal_idx, time_idx]
        self.calvalue_error = nc["polarization_gain_factor_statistical_error"][
            cal_idx, time_idx
        ]

    def mask(self, a_array):
        """
        replaces invalid values of  an array by np.nan
        :param a_array: ndarray with values > 1E20 (invalid values)
        :return: ndarray with np.nan values
        """
        if np.any(a_array > 1e20):
            mask = np.where(a_array > 1e20)
            a_array[mask] = np.nan
            return a_array
        else:
            return a_array

    def check_calibration(self):
        """
        The quality of the calibration is tested.
        the following criteria are checked:
        * is relative error of the gain factor below threshold?
        * is relative standard deviation of ratio profiles below threshold?
        * is there an overlap between uncertainty range of gain factor and standard deviation of time series * factor ?
        """
        if self.error_ok() and self.profiles_ok() and not self.is_outlier():
            self.is_ok = True

    def analyze(self):
        """
        the following steps are done:
        * read time series
        * check calibration
        * add to time series (if calibration is ok)
        * plot
        """
        self.read_time_series()
        self.check_calibration()

        if self.is_ok:
            self.add_to_time_series()

        self.timeseries.close()

        if self.plot_path is not None:
            self.plot()

    def create_timeseries(self, filename):
        """
        if a time series file does not yet exists, a new empty file is created
        """
        ts_file = Dataset(filename, "w", format="NETCDF4")
        dim = ts_file.createDimension("time", 0)

        crmax_var = ts_file.createVariable("calibration_range_max", "f8", ("time",))
        crmin_var = ts_file.createVariable("calibration_range_min", "f8", ("time",))
        date_var = ts_file.createVariable("date", "i8", ("time",))
        mid_var = ts_file.createVariable("Measurement_ID", str, ("time",))
        pcal_var = ts_file.createVariable("polarization_calibration", "f8", ("time",))
        pcale_var = ts_file.createVariable(
            "polarization_calibration_error", "f8", ("time",)
        )
        calver_var = ts_file.createVariable("ELDECVersion", str, ("time",))
        scc_var = ts_file.createVariable("SCCVersion", str, ("time",))

        ts_file.close()

    def read_time_series(self):
        """
        read the existing time series of previous calibrations from local file
        """

        if not self.timeseries_path.exists():
            print(
                f"Timeseries of path calibrations not found at {self.timeseries_path}. Creating a new file..."
            )
            self.create_timeseries(self.timeseries_path)

        self.timeseries = Dataset(self.timeseries_path, "a")

        self.ts_values = self.timeseries["polarization_calibration"][:]
        self.ts_errors = self.timeseries["polarization_calibration_error"][:]
        dates = []
        for d in range(self.ts_values.size):
            dates.append(
                num2date(
                    self.timeseries["date"][d],
                    "seconds since 1970-01-01 00:00",
                    only_use_cftime_datetimes=False,
                )
            )
        self.ts_dates = np.array(dates)

    def add_to_time_series(self):
        """
        add or update current calibration value to time series file

        """
        ts = self.timeseries

        if ts.dimensions["time"].size > 0:
            if self.measurement_ID in ts.variables["Measurement_ID"]:
                idx = int(
                    np.where(ts.variables["Measurement_ID"][:] == self.measurement_ID)[
                        0
                    ][0]
                )
            else:
                ts.variables["Measurement_ID"][:] = np.ma.append(
                    ts.variables["Measurement_ID"], self.measurement_ID
                )
                idx = ts.dimensions["time"].size - 1

        else:
            ts.variables["Measurement_ID"][0] = self.measurement_ID
            idx = ts.dimensions["time"].size - 1

        ts.variables["polarization_calibration"][idx] = self.calvalue
        ts.variables["polarization_calibration_error"][idx] = self.calvalue_error
        ts.variables["calibration_range_min"][idx] = self.polcal_range_min
        ts.variables["calibration_range_max"][idx] = self.polcal_range_max
        ts.variables["date"][idx] = date2num(
            self.start_time, "seconds since 1970-01-01 00:00"
        )
        ts.variables["ELDECVersion"][idx] = self.ELDEC_version
        ts.variables["SCCVersion"][idx] = self.SCC_version

    def is_outlier(self):
        """
        a calibration value is considered an outlier if its uncertainty range (value +/-error)
        is completely outside the range
        timeseries.mean +/- timeseries.stddev * DPCAL_STD_OUTLIER_FACTOR
        if there are not enough points in the file (< DPCAL_MIN_NB_OF_POINTS), the check
        is not performed and False is returned
        """
        ts = self.timeseries
        if ts.dimensions["time"].size > constants.DPCAL_MIN_NB_OF_POINTS:
            mean = np.mean(ts["polarization_calibration"][:])
            stddev = np.std(ts["polarization_calibration"][:])
            min = mean - constants.DPCAL_STD_OUTLIER_FACTOR * stddev
            max = mean + constants.DPCAL_STD_OUTLIER_FACTOR * stddev

            if ((self.calvalue + self.calvalue_error) > min) and (
                (self.calvalue - self.calvalue_error) < max
            ):
                return False
            else:
                print(
                    "calibration {} is an outlier of the time series".format(
                        os.path.basename(self.path)
                    )
                )
                return True
        else:
            return False

    def profiles_ok(self):
        """
        a profile is considered ok if the standard deviation of both ratio profiles is below
        the threshold constants.MAX_RATIO_STDDEV
        """
        profile_rel_stddev = self.profile_stddev / self.calvalue
        if profile_rel_stddev < constants.MAX_RATIO_STDDEV:
            return True
        else:
            print(
                "calibration {}: relative standard deviation of ratio profiles too large".format(
                    os.path.basename(self.path)
                )
            )
            return False

    def error_ok(self):
        """
        a calibration (gain factor) is considered ok if its relative error is below
        the threshold constants.MAX_DPCAL_ERR
        """
        rel_err = self.calvalue_error / self.calvalue
        if rel_err < constants.MAX_DPCAL_ERR:
            return True
        else:
            print(
                "calibration {}: relative error of uncertainty too large".format(
                    os.path.basename(self.path)
                )
            )
            return False

    def plot(self):
        """
        if constants.PLOT_DPCAL, the contents of the ELDEC file and the time series file are plotted
        """
        # =====================================================================
        # create plot
        fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(8, 6), dpi=100)
        colors = constants.COLORS[self.wavelength]

        title_1 = "{} {}nm".format(self.measurement_ID, self.wavelength)
        title_2 = "{}, {}".format(
            self.station_id, self.start_time.strftime("%Y-%m-%d %H:%M")
        )
        axes[0].set_title(title_1 + "\n" + title_2)

        # ----------------------------------------------------------------------
        # plot left panel (vertical profiles)
        # ----------------------------------------------------------------------
        # create vertical profiles from the current gain factor and its error
        cal_range = (
            self.polcal_range_min
            + np.array(range(5)) * (self.polcal_range_max - self.polcal_range_min) / 4
        )
        cal_min = np.ones(5) * (self.calvalue - self.calvalue_error)
        cal_max = np.ones(5) * (self.calvalue + self.calvalue_error)
        cal_value = np.ones(5) * self.calvalue

        # plot the two ratio profiles
        for idx in range(2):
            profile = self.ratio_profiles[idx]
            error = self.ratio_profile_errors[idx]

            last_bin = np.where(self.height > self.max_alt)[0][0]

            if constants.AUTO_SCALE:
                self.axes_limits = (
                    min(
                        self.axes_limits[0],
                        np.nanmin(
                            profile[constants.DPCAL_MIN_BIN : last_bin]
                            - error[constants.DPCAL_MIN_BIN : last_bin]
                        ),
                    ),
                    max(
                        self.axes_limits[1],
                        np.nanmax(
                            profile[constants.DPCAL_MIN_BIN : last_bin]
                            + error[constants.DPCAL_MIN_BIN : last_bin]
                        ),
                    ),
                )
            else:
                self.axes_limits = constants.AXES_LIMITS[self.wavelength]

            axes[0].plot(profile, self.height, color=colors[idx], linewidth=1.5)
            axes[0].plot(profile + error, self.height, color=colors[idx], linewidth=0.5)
            axes[0].plot(profile - error, self.height, color=colors[idx], linewidth=0.5)

        if self.is_ok:
            actual_color = colors["actual"]
        else:
            actual_color = colors["invalid"]

        axes[0].plot(cal_value, cal_range, color=actual_color, linewidth=1.5)
        axes[0].plot(cal_min, cal_range, color=actual_color, linewidth=0.5)
        axes[0].plot(cal_max, cal_range, color=actual_color, linewidth=0.5)

        axes[0].set_xlim(self.axes_limits)
        axes[0].set_xlabel("DEPOL_CALIBR.")

        # label altitude axis
        axes[0].set_ylim((0, self.max_alt))
        axes[0].set_ylabel("HEIGHT, km a.g.")
        y0_formatter = FuncFormatter(self.km_label)
        axes[0].yaxis.set_major_formatter(y0_formatter)

        # ----------------------------------------------------------------------
        # plot right panel (time series)
        # ----------------------------------------------------------------------

        # plot previous and current gain factors
        axes[1].errorbar(
            self.ts_values,
            self.ts_dates,
            xerr=self.ts_errors,
            fmt="o",
            color=colors["previous"],
        )
        axes[1].errorbar(
            np.array([self.calvalue]),
            np.array([self.start_time]),
            xerr=np.array([self.calvalue_error]),
            fmt="o",
            color=actual_color,
        )

        # append current value to time series (whether self.is_ok or not). Just for plotting
        all_times = np.append(self.ts_dates, self.start_time)
        all_values = np.append(self.ts_values, self.calvalue)
        all_error = np.append(self.ts_errors, self.calvalue_error)

        # calculate min and max of time axis
        y_min = max(
            min(all_times) - timedelta(days=5),
            self.start_time - timedelta(days=constants.TIME_AXIS_SPAN),
        )
        y_max = min(
            max(all_times) + timedelta(days=5),
            self.start_time + timedelta(days=constants.TIME_AXIS_SPAN),
        )
        try:
            min_idx = np.where(all_times > y_min)[0][0]
        except:
            min_idx = 0
        try:
            max_idx = np.where(all_times > y_max)[0][0]
        except:
            max_idx = all_times.size

        if constants.AUTO_SCALE:
            x_min = (
                min(all_values[min_idx:max_idx]) - max(all_error[min_idx:max_idx]) * 0.8
            )
            x_max = (
                max(all_values[min_idx:max_idx]) + max(all_error[min_idx:max_idx]) * 1.2
            )
        else:
            x_min = constants.AXES_LIMITS[self.wavelength][0]
            x_max = constants.AXES_LIMITS[self.wavelength][1]

        axes[1].set_ylim((y_min, y_max))
        axes[1].set_ylabel("Date")
        axes[1].yaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))

        axes[1].set_xlim((x_min, x_max))
        axes[1].set_xlabel("DEPOL_CALIBR.")

        # ----------------------------------------------------------------------
        # adjust subplots and save to file
        # ----------------------------------------------------------------------

        plt.subplots_adjust(
            hspace=0.0, wspace=0.5, bottom=0.13, left=0.08, top=0.9, right=0.97
        )

        plt.savefig(self.plot_path)

        plt.close()

    def calibration_ok(self):
        """
        call this function to get information whether the calibration is ok or not ok
        """
        return self.is_ok
