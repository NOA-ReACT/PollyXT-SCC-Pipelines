"""
Routines for converting PollyXT files to SCC files
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Literal, Optional, Tuple
import logging
import re

import numpy as np
from netCDF4 import Dataset

from pollyxt_pipelines import sun, utils
from pollyxt_pipelines.locations import Location
from pollyxt_pipelines.enums import Atmosphere, Wavelength
from pollyxt_pipelines.polly_to_scc import pollyxt
from pollyxt_pipelines.polly_to_scc.exceptions import (
    NoMeasurementsInTimePeriod,
    TimeOutsideFile,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SCCFile:
    """
    One SCC netCDF file produced by a conversion.
    """

    kind: Literal["data", "calibration"]
    """Whether this is a measurement (data) file or a depolarization calibration file"""

    measurement_id: str
    """SCC measurement ID, as written in the file's `Measurement_ID` attribute"""

    path: Path
    """Where the file was written"""

    start: datetime
    """Time of the first measurement in the file (timezone-aware, UTC)"""

    end: datetime
    """Time of the last measurement in the file (timezone-aware, UTC). This is the start
    of the last 30 s profile, so a full hour of data spans 59.5 minutes."""

    configuration_id: int
    """SCC lidar configuration (system) ID to upload the file with"""

    wavelength: Optional[Wavelength] = None
    """Calibration files only: the calibrated wavelength"""


@dataclass
class WindowConversion:
    """
    The result of converting one time window with `convert_window`.
    """

    data: Optional[SCCFile]
    """The data file, or None if the window has no (non-calibration) measurements"""

    calibrations: List[SCCFile] = field(default_factory=list)
    """Calibration files for the calibration periods that start in the window"""

    skipped: List[str] = field(default_factory=list)
    """Human-readable reasons for calibration files that were not made"""


CALIBRATION_ID_SUFFIX = {
    Wavelength.NM_355: "35",
    Wavelength.NM_532: "53",
    Wavelength.NM_1064: "10",
}
"""Suffix appended to the calibration measurement ID, per wavelength"""


def data_measurement_id(location: Location, start_date: datetime) -> str:
    """
    Measurement ID of a data file: `YYYYMMDD{scc_code}HHMM`, from the time of its first
    measurement.
    """
    return start_date.strftime(f"%Y%m%d{location.scc_code}%H%M")


def calibration_measurement_id(
    location: Location, start_date: datetime, wavelength: Wavelength
) -> str:
    """
    Measurement ID of a calibration file: `YYYYMMDD{scc_code}HH` followed by `35`, `53` or
    `10` for 355, 532 or 1064 nm, from the start of the calibration period.

    Note that this can coincide with a data file's ID (e.g. a data file starting at HH:35).
    The scheme is kept as it is on purpose.
    """
    if wavelength not in CALIBRATION_ID_SUFFIX:
        raise ValueError(f"Unknown wavelength {wavelength}")
    return (
        start_date.strftime(f"%Y%m%d{location.scc_code}%H")
        + CALIBRATION_ID_SUFFIX[wavelength]
    )


def calibration_configuration_id(
    location: Location, wavelength: Wavelength
) -> Optional[int]:
    """SCC configuration ID for calibration files of the given wavelength"""
    if wavelength == Wavelength.NM_355:
        return location.calibration_configuration_355nm
    if wavelength == Wavelength.NM_532:
        return location.calibration_configuration_532nm
    if wavelength == Wavelength.NM_1064:
        return location.calibration_configuration_1064nm
    raise ValueError(f"Unknown wavelength {wavelength}")


def day_night_configuration(
    location: Location, start_date: datetime
) -> Tuple[int, bool, Optional[datetime], Optional[datetime]]:
    """
    Decide whether a data file starting at `start_date` uses the day or night configuration.

    Returns:
        A tuple of (configuration ID, is daytime, sunrise time, sunset time). The sunrise and
        sunset times are None when the sun doesn't rise or set that day.
    """

    suninfo = sun.get_sun_times(location, start_date)

    if re.match(r"[0-2]\d:[0-5]\d", location.sunrise_time):
        hh, mm = location.sunrise_time.split(":")
        sunrise_time = start_date.replace(hour=int(hh), minute=int(mm))
    elif suninfo.sunrise_time is not None:
        sunrise_time = suninfo.sunrise_time.replace(tzinfo=None)
        if re.match(r"[+-]\d+", location.sunrise_time):
            sunrise_time += timedelta(minutes=int(location.sunrise_time))
    else:
        sunrise_time = None

    if re.match(r"[0-2]\d:[0-5]\d", location.sunset_time):
        hh, mm = location.sunset_time.split(":")
        sunset_time = start_date.replace(hour=int(hh), minute=int(mm))
    elif suninfo.sunset_time is not None:
        sunset_time = suninfo.sunset_time.replace(tzinfo=None)
        if re.match(r"[+-]\d+", location.sunset_time):
            sunset_time += timedelta(minutes=int(location.sunset_time))
    else:
        sunset_time = None

    is_daytime = suninfo.always_up or (
        sunrise_time is not None
        and sunset_time is not None
        and sunrise_time < start_date < sunset_time
    )
    if is_daytime:
        return location.daytime_configuration, True, sunrise_time, sunset_time
    return location.nighttime_configuration, False, sunrise_time, sunset_time


def create_scc_netcdf(
    pf: pollyxt.PollyXTFile,
    output_path: Path,
    location: Location,
    atmosphere=Atmosphere.STANDARD_ATMOSPHERE,
) -> Tuple[str, Path]:
    """
    Convert a PollyXT netCDF file to a SCC file.

    Parameters:
        pf: An opened PollyXT file. When you create this, you can specify the time period of interest.
        output_path: Where to store the produced netCDF file
        location: Where did this measurement take place
        atmosphere: What kind of atmosphere to use.

    Note:
        If atmosphere is set to Atmosphere.SOUNDING, the `Sounding_File_Name` attribute will be set to
        `rs_{MEASUREMENT_ID}.rs`, ie the filename of the accompaning radiosonde. This file is *not* created
        by this function.

    Returns:
        A tuple containing  the measurement ID and the output path
    """

    # Calculate measurement ID
    measurement_id = data_measurement_id(location, pf.start_date)

    # Create SCC file
    # Output filename is always the measurement ID
    output_filename = output_path / f"{measurement_id}.nc"
    nc = Dataset(output_filename, "w")

    # Create dimensions (mandatory!)
    nc.createDimension("points", np.size(pf.raw_signal, axis=1))
    nc.createDimension("channels", np.size(pf.raw_signal, axis=2))
    nc.createDimension("time", None)
    nc.createDimension("nb_of_time_scales", 1)
    nc.createDimension("scan_angles", 1)

    # Create Global Attributes (mandatory!)
    nc.Measurement_ID = measurement_id
    nc.RawData_Start_Date = pf.start_date.strftime("%Y%m%d")
    nc.RawData_Start_Time_UT = pf.start_date.strftime("%H%M%S")
    nc.RawData_Stop_Time_UT = pf.end_date.strftime("%H%M%S")

    # Create Global Attributes (optional)
    nc.RawBck_Start_Date = nc.RawData_Start_Date
    nc.RawBck_Start_Time_UT = nc.RawData_Start_Time_UT
    nc.RawBck_Stop_Time_UT = nc.RawData_Stop_Time_UT
    if atmosphere == Atmosphere.RADIOSONDE:
        nc.Sounding_File_Name = f"rs_{measurement_id[:-2]}.nc"
    # nc.Overlap_File_Name = 'ov_' + selected_start.strftime('%Y%m%daky%H') + '.nc'

    # Day or night configuration, from sunset and sunrise times for the current station
    configuration_id, is_daytime, sunrise_time, sunset_time = day_night_configuration(
        location, pf.start_date
    )
    nc.X_PollyXTPipelines_Configuration_ID = configuration_id
    nc.X_PollyXTPipelines_Is_Daytime = "yes" if is_daytime else "no"

    nc.X_PollyXTPipelines_Sunrise_time = (
        sunrise_time.strftime("%H:%M") if sunrise_time is not None else "NA"
    )
    nc.X_PollyXTPipelines_Sunset_time = (
        sunset_time.strftime("%H:%M") if sunset_time is not None else "NA"
    )

    # Create Variables. (mandatory)
    raw_data_start_time = nc.createVariable(
        "Raw_Data_Start_Time", "i4", dimensions=("time", "nb_of_time_scales"), zlib=True
    )
    raw_data_stop_time = nc.createVariable(
        "Raw_Data_Stop_Time", "i4", dimensions=("time", "nb_of_time_scales"), zlib=True
    )
    raw_lidar_data = nc.createVariable(
        "Raw_Lidar_Data", "f8", dimensions=("time", "channels", "points"), zlib=True
    )
    channel_id = nc.createVariable(
        "channel_ID", "i4", dimensions=("channels"), zlib=True
    )
    channel_id[:] = -1
    if isinstance(location.channel_id[0], int):
        channel_id[:] = np.array(location.channel_id)
    else:
        str_len = np.max([len(x) for x in location.channel_id])
        channel_id = nc.createVariable(
            "channel_string_ID",
            f"S{str_len}",
            dimensions=("channels"),
        )
        channel_id[:] = np.array(location.channel_id, f"S{str_len}")

    id_timescale = nc.createVariable(
        "id_timescale", "i4", dimensions=("channels"), zlib=True
    )
    laser_pointing_angle = nc.createVariable(
        "Laser_Pointing_Angle", "f8", dimensions=("scan_angles"), zlib=True
    )
    laser_pointing_angle_of_profiles = nc.createVariable(
        "Laser_Pointing_Angle_of_Profiles",
        "i4",
        dimensions=("time", "nb_of_time_scales"),
        zlib=True,
    )
    laser_shots = nc.createVariable(
        "Laser_Shots", "i4", dimensions=("time", "channels"), zlib=True
    )
    background_low = nc.createVariable(
        "Background_Low", "f8", dimensions=("channels"), zlib=True
    )
    background_high = nc.createVariable(
        "Background_High", "f8", dimensions=("channels"), zlib=True
    )
    molecular_calc = nc.createVariable("Molecular_Calc", "i4", dimensions=(), zlib=True)
    nc.createVariable("Pol_Calib_Range_Min", "f8", dimensions=("channels"), zlib=True)
    nc.createVariable("Pol_Calib_Range_Max", "f8", dimensions=("channels"), zlib=True)
    pressure_at_lidar_station = nc.createVariable(
        "Pressure_at_Lidar_Station", "f8", dimensions=(), zlib=True
    )
    temperature_at_lidar_station = nc.createVariable(
        "Temperature_at_Lidar_Station", "f8", dimensions=(), zlib=True
    )
    lr_input = nc.createVariable("LR_Input", "i4", dimensions=("channels"), zlib=True)

    # Fill Variables with Data. (mandatory)
    raw_data_start_time[:] = pf.measurement_time[~pf.calibration_mask]
    raw_data_stop_time[:] = (pf.measurement_time[~pf.calibration_mask]) + 30
    raw_lidar_data[:] = pf.raw_signal_swap[~pf.calibration_mask]
    id_timescale[:] = np.zeros(np.size(pf.raw_signal[~pf.calibration_mask], axis=2))
    laser_pointing_angle[:] = int(pf.zenith_angle.item(0))
    laser_pointing_angle_of_profiles[:] = np.zeros(
        np.size(pf.raw_signal[~pf.calibration_mask], axis=0)
    )
    laser_shots[:] = pf.measurement_shots[~pf.calibration_mask]
    background_low[:] = np.array(location.background_low)
    background_high[:] = np.array(location.background_high)
    molecular_calc[:] = int(atmosphere)
    pressure_at_lidar_station[:] = location.pressure
    temperature_at_lidar_station[:] = location.temperature
    lr_input[:] = np.array(location.lr_input)

    # Close the netCDF file.
    nc.close()

    return measurement_id, output_filename


def create_scc_calibration_netcdf(
    pf: pollyxt.PollyXTFile,
    output_path: Path,
    location: Location,
    wavelength: Wavelength,
    pol_calib_range_min: int = 1200,
    pol_calib_range_max: int = 2500,
) -> Tuple[str, Path]:
    """
    From a PollyXT netCDF file, create the corresponding calibration SCC file.
    Calibration only occures when `depol_cal_angle` is not equal to the default state value.
    Take care to create the `PollyXTFile` with these intervals.

    Parameters:
        pf: An opened PollyXT file
        output_path: Where to store the produced netCDF file
        location: Where did this measurement take place
        wavelength: Calibration for 355nm or 532nm
        pol_calib_range_min: Calibration contant calculation, minimum height
        pol_calib_range_max: Calibration contant calculation, maximum height

    Returns:
        A tuple containing the measurement ID and the output path
    """

    # Calculate measurement ID. The returned ID has no wavelength suffix, but the
    # `Measurement_ID` attribute in the file does (see `calibration_measurement_id`).
    measurement_id = pf.start_date.strftime(f"%Y%m%d{location.scc_code}%H")

    # Find start/end indices for the +45 and -45 degree calibration cycles in Polly file
    idx = list(np.where(np.diff(pf.depol_cal_angle))[0])
    start_positive = 2
    idx = list(filter(lambda x: x >= start_positive + 4, idx))
    if len(idx) == 0:
        raise ValueError(
            "no change from +45° to -45° found in the calibration period (is it complete?)"
        )
    end_positive = idx[0]
    positive_length = end_positive - start_positive

    start_negative = idx[0] + 3
    idx = list(filter(lambda x: x >= start_negative + 4, idx))
    end_negative = pf.depol_cal_angle.shape[0] - 3
    negative_length = end_negative - start_negative

    # Reduce the larger period to match
    if positive_length > negative_length:
        end_positive -= positive_length - negative_length
        positive_length = negative_length
    elif negative_length > positive_length:
        end_negative -= negative_length - positive_length
        negative_length = positive_length

    if positive_length <= 0:
        raise ValueError("calibration period is too short")

    # Define total and cross channels IDs from Polly
    if wavelength == Wavelength.NM_355:
        total_channel_idx = location.total_channel_355_nm_idx
        cross_channel_idx = location.cross_channel_355_nm_idx
        channel_ids = np.array(
            location.calibration_355nm_total_channel_ids
            + location.calibration_355nm_cross_channel_ids
        )
    elif wavelength == Wavelength.NM_532:
        total_channel_idx = location.total_channel_532_nm_idx
        cross_channel_idx = location.cross_channel_532_nm_idx
        channel_ids = np.array(
            location.calibration_532nm_total_channel_ids
            + location.calibration_532nm_cross_channel_ids
        )
    elif wavelength == Wavelength.NM_1064:
        total_channel_idx = location.total_channel_1064_nm_idx
        cross_channel_idx = location.cross_channel_1064_nm_idx
        channel_ids = np.array(
            location.calibration_1064nm_total_channel_ids
            + location.calibration_1064nm_cross_channel_ids
        )
    else:
        raise ValueError(f"Unknown wavelength {wavelength}")

    # Create SCC file
    # Output filename is always the measurement ID
    output_filename = output_path / f"calibration_{measurement_id}_{int(wavelength)}.nc"
    nc = Dataset(output_filename, "w")
    try:
        _write_calibration_netcdf(
            nc,
            pf,
            location,
            wavelength,
            channel_ids,
            total_channel_idx,
            cross_channel_idx,
            start_positive,
            end_positive,
            start_negative,
            end_negative,
            positive_length,
            pol_calib_range_min,
            pol_calib_range_max,
        )
    except BaseException:
        # Don't leave a broken file behind
        nc.close()
        output_filename.unlink(missing_ok=True)
        raise
    nc.close()

    return measurement_id, output_filename


def _write_calibration_netcdf(
    nc: Dataset,
    pf: pollyxt.PollyXTFile,
    location: Location,
    wavelength: Wavelength,
    channel_ids: np.ndarray,
    total_channel_idx: int,
    cross_channel_idx: int,
    start_positive: int,
    end_positive: int,
    start_negative: int,
    end_negative: int,
    positive_length: int,
    pol_calib_range_min: int,
    pol_calib_range_max: int,
):
    nc.Measurement_ID = calibration_measurement_id(location, pf.start_date, wavelength)
    nc.X_PollyXTPipelines_Configuration_ID = calibration_configuration_id(
        location, wavelength
    )

    # Create Dimensions. (mandatory)
    nc.createDimension("points", np.size(pf.raw_signal, axis=1))
    nc.createDimension("channels", 4)
    nc.createDimension("time", positive_length)
    nc.createDimension("nb_of_time_scales", 1)
    nc.createDimension("scan_angles", 1)

    # Create Global Attributes. (mandatory)
    # Move start date a couple of profiles forward to accomodate the fact that we skip
    # some profiles at the beginning of the file.
    start_date = pf.start_date + timedelta(seconds=(start_positive * 30))
    nc.RawData_Start_Date = start_date.strftime("%Y%m%d")
    nc.RawData_Start_Time_UT = start_date.strftime("%H%M%S")
    nc.RawData_Stop_Time_UT = pf.end_date.strftime("%H%M%S")

    # Create Global Attributes (optional)
    nc.RawBck_Start_Date = nc.RawData_Start_Date
    nc.RawBck_Start_Time_UT = nc.RawData_Start_Time_UT
    nc.RawBck_Stop_Time_UT = nc.RawData_Stop_Time_UT

    # Create Variables. (mandatory)
    raw_data_start_time = nc.createVariable(
        "Raw_Data_Start_Time", "i4", dimensions=("time", "nb_of_time_scales"), zlib=True
    )
    raw_data_stop_time = nc.createVariable(
        "Raw_Data_Stop_Time", "i4", dimensions=("time", "nb_of_time_scales"), zlib=True
    )
    raw_lidar_data = nc.createVariable(
        "Raw_Lidar_Data", "f8", dimensions=("time", "channels", "points"), zlib=True
    )
    channel_id = nc.createVariable(
        "channel_ID", "i4", dimensions=("channels"), zlib=True
    )
    channel_id[:] = 1
    if isinstance(location.channel_id[0], int):
        channel_id[:] = np.array(channel_ids)
    else:
        str_len = np.max([len(x) for x in channel_ids])
        channel_id = nc.createVariable(
            "channel_string_ID",
            f"S{str_len}",
            dimensions=("channels"),
        )
        channel_id[:] = np.array(channel_ids)
    id_timescale = nc.createVariable(
        "id_timescale", "i4", dimensions=("channels"), zlib=True
    )
    laser_pointing_angle = nc.createVariable(
        "Laser_Pointing_Angle", "f8", dimensions=("scan_angles"), zlib=True
    )
    laser_pointing_angle_of_profiles = nc.createVariable(
        "Laser_Pointing_Angle_of_Profiles",
        "i4",
        dimensions=("time", "nb_of_time_scales"),
        zlib=True,
    )
    laser_shots = nc.createVariable(
        "Laser_Shots", "i4", dimensions=("time", "channels"), zlib=True
    )
    background_low = nc.createVariable(
        "Background_Low", "f8", dimensions=("channels"), zlib=True
    )
    background_high = nc.createVariable(
        "Background_High", "f8", dimensions=("channels"), zlib=True
    )
    molecular_calc = nc.createVariable("Molecular_Calc", "i4", dimensions=(), zlib=True)
    pol_calib_range_min_var = nc.createVariable(
        "Pol_Calib_Range_Min", "f8", dimensions=("channels"), zlib=True
    )
    pol_calib_range_max_var = nc.createVariable(
        "Pol_Calib_Range_Max", "f8", dimensions=("channels"), zlib=True
    )
    pressure_at_lidar_station = nc.createVariable(
        "Pressure_at_Lidar_Station", "f8", dimensions=(), zlib=True
    )
    temperature_at_lidar_station = nc.createVariable(
        "Temperature_at_Lidar_Station", "f8", dimensions=(), zlib=True
    )

    # Fill Variables with Data. (mandatory)
    raw_data_start_time[:] = np.arange(0, positive_length) * 30
    raw_data_stop_time[:] = (np.arange(0, positive_length) * 30) + 30
    id_timescale[:] = np.array([0, 0, 0, 0])
    laser_pointing_angle[:] = 5
    laser_pointing_angle_of_profiles[:, :] = 0.0
    laser_shots[:] = 600
    background_low[:] = np.array([0, 0, 0, 0])
    background_high[:] = np.array([249, 249, 249, 249])
    molecular_calc[:] = 0
    pol_calib_range_min_var[:] = np.repeat(pol_calib_range_min, 4)
    pol_calib_range_max_var[:] = np.repeat(pol_calib_range_max, 4)
    pressure_at_lidar_station[:] = location.pressure
    temperature_at_lidar_station[:] = location.temperature

    raw_lidar_data[:] = 0
    # Total channel, +45°
    raw_lidar_data[:, 0, :] = pf.raw_signal_swap[
        start_positive:end_positive, total_channel_idx, :
    ]
    # Cross channel, +45°
    raw_lidar_data[:, 2, :] = pf.raw_signal_swap[
        start_positive:end_positive, cross_channel_idx, :
    ]
    # Total channel, -45°
    raw_lidar_data[:, 1, :] = pf.raw_signal_swap[
        start_negative:end_negative, total_channel_idx, :
    ]
    # Cross channel, -45°
    raw_lidar_data[:, 3, :] = pf.raw_signal_swap[
        start_negative:end_negative, cross_channel_idx, :
    ]


def convert_pollyxt_file(
    repo: pollyxt.PollyXTRepository,
    output_path: Path,
    location: Location,
    interval: timedelta,
    atmosphere: Atmosphere,
    should_round=False,
    calibration=True,
    start_time=None,
    end_time=None,
):
    """
    Converts a pollyXT repository into a collection of SCC files. The input files will be split/merged into intervals
    before being converted to the new format.

    This function is a generator, so you can use it in a for loop to monitor progress:

        for measurement_id, path, start_time, end_time in convert_pollyxt_file(...):
            # Do something with id/path, maybe print a message?


    Parameters:
        repo: PollyXT file to convert
        output_path: Directory to write the SCC files
        location: Geographical information, where the measurement took place
        interval: What interval to use when splitting the PollyXT file (e.g. 1 hour)
        atmosphere: Which atmosphere to use on SCC
        should_round: If true, the interval starts will be rounded down. For example, from 01:02 to 01:00.
        calibration: Set to False to disable generation of calibration files.
        start_hour: Optionally, set when the first file should start. The intervals will start from here. (HH:MM or YYYY-MM-DD_HH:MM format, string)
        end_hour: Optionally, also set the end time. Must be used with `start_hour`. If this is set, only one output file
                  is generated, for your target interval (HH:MM or YYYY-MM-DD_HH:MM format, string).
    """

    # Open input netCDF
    measurement_start, measurement_end = repo.get_time_period()

    # Handle start/end time
    if start_time is not None:
        start_time = utils.date_option_to_datetime(measurement_start, start_time)

        if start_time < measurement_start or measurement_end < start_time:
            raise TimeOutsideFile(measurement_start, measurement_end, start_time)

        measurement_start = start_time

    if start_time is None and end_time is not None:
        raise ValueError("Can't use end_hour without start_hour")

    if end_time is not None:
        end_time = utils.date_option_to_datetime(measurement_end, end_time)

        if end_time < measurement_start or measurement_end < start_time:
            raise TimeOutsideFile(measurement_start, measurement_end, end_time)

        measurement_end = end_time
        if interval is None:
            interval = timedelta(seconds=(end_time - start_time).total_seconds())

    # Create output files
    interval_start = measurement_start
    while interval_start < measurement_end:
        # If the option is set, round down hours
        if should_round:
            interval_start = interval_start.replace(microsecond=0, second=0, minute=0)

        # Interval end
        interval_end = interval_start + interval

        # Open netCDF file and convert to SCC
        try:
            pf = repo.get_pollyxt_file(
                interval_start, interval_end + timedelta(seconds=1)
            )
            id, path = create_scc_netcdf(pf, output_path, location, atmosphere)

            yield id, path, pf.start_date, pf.end_date
        except NoMeasurementsInTimePeriod as ex:
            # Go to next loop
            interval_start = interval_end
            continue

        # Set start of next interval to the end of this one
        interval_start = interval_end

    # Generate calibration files
    if calibration:
        # Only calibration periods strictly inside the converted range
        for start, end in repo.get_calibration_periods():
            if start > measurement_start and end < measurement_end:
                files, _ = _convert_calibration_period(
                    repo, start, end, output_path, location
                )
                for f in files:
                    # The CLI has always reported the ID without the wavelength suffix
                    yield f.measurement_id[:-2], f.path, start, end


def _format_period(start: datetime, end: datetime) -> str:
    return f"{start:%Y-%m-%d %H:%M}–{end:%H:%M}"


def _convert_calibration_period(
    repo: pollyxt.PollyXTRepository,
    start: datetime,
    end: datetime,
    output_path: Path,
    location: Location,
) -> Tuple[List[SCCFile], List[str]]:
    """
    Make the calibration files of one calibration period, one per wavelength with
    depolarization channels. A wavelength that fails is logged and returned as a reason,
    and the others are still made.

    Returns:
        A tuple of the files made and the reasons for the ones skipped
    """

    files: List[SCCFile] = []
    skipped: List[str] = []

    wavelengths = [wv for wv, ok in location.has_depol_channels().items() if ok]
    if not wavelengths:
        return files, skipped

    pf = repo.get_pollyxt_file(start, end)
    for wv in wavelengths:
        try:
            _, path = create_scc_calibration_netcdf(
                pf, output_path, location, wavelength=wv
            )
        except Exception as ex:
            reason = f"calibration {_format_period(start, end)} at {int(wv)} nm: {type(ex).__name__}: {ex}"
            logger.warning("Calibration file not made: %s", reason)
            skipped.append(reason)
            continue

        files.append(
            SCCFile(
                kind="calibration",
                measurement_id=calibration_measurement_id(location, pf.start_date, wv),
                path=path,
                start=utils.to_aware_utc(start),
                end=utils.to_aware_utc(end),
                configuration_id=calibration_configuration_id(location, wv),
                wavelength=wv,
            )
        )

    return files, skipped


def convert_window(
    repo: pollyxt.PollyXTRepository,
    start: datetime,
    end: datetime,
    output_path: Path,
    location: Location,
    atmosphere: Atmosphere = Atmosphere.STANDARD_ATMOSPHERE,
    calibration: bool = True,
) -> WindowConversion:
    """
    Convert one time window of a repository to SCC files.

    Any window may be asked for, and asking again gives the same files with the same names:
    measurement IDs and filenames depend only on the data and the location.

    Parameters:
        repo: The PollyXT files to read from
        start: Window start, inclusive. UTC: naive datetimes are taken as UTC and aware ones
            are converted to UTC.
        end: Window end, exclusive. Same rules as `start`.
        output_path: Directory to write the files to. It must exist.
        location: Where the measurement took place
        atmosphere: Which atmosphere SCC should use for the data file
        calibration: Set to False to make no calibration files

    The window may extend past the repository's data on either side; it is clipped to the
    data.

    **Data file:** at most one, from the non-calibration measurements inside the window.
    `start` and `end` on it are its first and last measurement, so the caller can apply its
    own minimum duration. With no measurements, `data` is None.

    **Calibration files:** a calibration period belongs to the window that contains its
    start, even when it ends after `end`, and is made from the repository's data for the
    whole period. So each period is converted by exactly one window. A period is skipped,
    with a reason in `skipped`, when the repository's data ends during it, or when it begins
    at the repository's first measurement (its real start is then unknown). A wavelength
    whose file can't be made is also skipped with a reason; nothing is printed.

    Raises:
        ValueError: `end` is not after `start`
        Other exceptions for problems that make the whole window impossible, e.g. a corrupt
        input file.
    """

    start = utils.to_naive_utc(start)
    end = utils.to_naive_utc(end)
    if end <= start:
        raise ValueError(f"Window end ({end}) must be after its start ({start})")
    output_path = Path(output_path)

    result = WindowConversion(data=None)

    # Data file
    try:
        pf = repo.get_pollyxt_file(start, end, include_end=False)
    except NoMeasurementsInTimePeriod:
        pf = None

    if pf is not None and np.any(~pf.calibration_mask):
        measurement_id, path = create_scc_netcdf(pf, output_path, location, atmosphere)
        configuration_id, _, _, _ = day_night_configuration(location, pf.start_date)
        result.data = SCCFile(
            kind="data",
            measurement_id=measurement_id,
            path=path,
            start=utils.to_aware_utc(pf.start_date),
            end=utils.to_aware_utc(pf.end_date),
            configuration_id=configuration_id,
        )

    # Calibration files
    if calibration:
        repo_start, repo_end = repo.get_time_period()
        for cal_start, cal_end in repo.get_calibration_periods():
            if not (start <= cal_start < end):
                continue

            period = _format_period(cal_start, cal_end)
            if cal_end >= repo_end:
                reason = f"calibration {period}: the data ends during the calibration"
            elif cal_start <= repo_start:
                reason = f"calibration {period}: starts at the first measurement, so its real start is unknown"
            else:
                files, skipped = _convert_calibration_period(
                    repo, cal_start, cal_end, output_path, location
                )
                result.calibrations.extend(files)
                result.skipped.extend(skipped)
                continue

            logger.warning("Calibration files not made: %s", reason)
            result.skipped.append(reason)

    return result
