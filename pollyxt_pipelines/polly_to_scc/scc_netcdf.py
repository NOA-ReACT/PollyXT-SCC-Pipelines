"""
Routines for converting PollyXT files to SCC files
"""

from datetime import timedelta
from pathlib import Path
from typing import Tuple
import re

import numpy as np
from netCDF4 import Dataset
from astral import LocationInfo
from astral.sun import sunrise, sunset

from pollyxt_pipelines import utils
from pollyxt_pipelines.locations import Location
from pollyxt_pipelines.enums import Atmosphere, Wavelength
from pollyxt_pipelines.polly_to_scc import pollyxt
from pollyxt_pipelines.polly_to_scc.exceptions import (
    NoMeasurementsInTimePeriod,
    TimeOutsideFile,
)


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
    measurement_id = pf.start_date.strftime(f"%Y%m%d{location.scc_code}%H%M")

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

    # Calculate sunset and sunrise times for the current station
    sun_locinfo = LocationInfo(
        location.name, "", timezone="UTC", latitude=location.lat, longitude=location.lon
    )
    if re.match(r"[0-2]\d:[0-5]\d", location.sunrise_time):
        hh, mm = location.sunrise_time.split(":")
        hh, mm = int(hh), int(mm)
        sunrise_time = pf.start_date.replace(hour=hh, minute=mm)
    else:
        sunrise_time = sunrise(sun_locinfo.observer, pf.start_date)
        sunrise_time = sunrise_time.replace(tzinfo=None)
        if re.match(r"[+-]\d+", location.sunrise_time):
            sunrise_time += timedelta(minutes=int(location.sunrise_time))

    if re.match(r"[0-2]\d:[0-5]\d", location.sunset_time):
        hh, mm = location.sunset_time.split(":")
        hh, mm = int(hh), int(mm)
        sunset_time = pf.start_date.replace(hour=hh, minute=mm)
    else:
        sunset_time = sunset(sun_locinfo.observer, pf.start_date)
        sunset_time = sunset_time.replace(tzinfo=None)
        if re.match(r"[+-]\d+", location.sunset_time):
            sunset_time += timedelta(minutes=int(location.sunset_time))

    if sunrise_time < pf.start_date and pf.start_date < sunset_time:
        nc.X_PollyXTPipelines_Configuration_ID = location.daytime_configuration
        nc.X_PollyXTPipelines_Is_Daytime = "yes"
    else:
        nc.X_PollyXTPipelines_Configuration_ID = location.nighttime_configuration
        nc.X_PollyXTPipelines_Is_Daytime = "no"

    nc.X_PollyXTPipelines_Sunrise_time = sunrise_time.strftime("%H:%M")
    nc.X_PollyXTPipelines_Sunset_time = sunset_time.strftime("%H:%M")

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
    raw_data_start_time[:] = (
        pf.measurement_time[~pf.calibration_mask, 1] - pf.measurement_time[0, 1]
    )
    raw_data_stop_time[:] = (
        pf.measurement_time[~pf.calibration_mask, 1] - pf.measurement_time[0, 1]
    ) + 30
    raw_lidar_data[:] = pf.raw_signal_swap[~pf.calibration_mask]
    channel_id[:] = np.array(location.channel_id)
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

    # Calculate measurement ID
    measurement_id = pf.start_date.strftime(f"%Y%m%d{location.scc_code}%H")

    # Create SCC file
    # Output filename is always the measurement ID
    output_filename = output_path / f"calibration_{measurement_id}_{int(wavelength)}.nc"
    nc = Dataset(output_filename, "w")

    # Find start/end indices for the +45 and -45 degree calibration cycles in Polly file
    idx = list(np.where(np.diff(pf.depol_cal_angle))[0])
    start_positive = 2
    idx = list(filter(lambda x: x >= start_positive + 4, idx))
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
    raw_data_start_time[:] = (
        pf.measurement_time[start_positive:end_positive, 1]
        - pf.measurement_time[start_positive, 1]
    )
    raw_data_stop_time[:] = (
        pf.measurement_time[start_negative:end_negative, 1]
        - pf.measurement_time[start_positive, 1]
    )
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

    # Define total and cross channels IDs from Polly
    if wavelength == Wavelength.NM_355:
        total_channel_idx = location.total_channel_355_nm_idx
        cross_channel_idx = location.cross_channel_355_nm_idx
        channel_id[:] = np.array(
            location.calibration_355nm_total_channel_ids
            + location.calibration_355nm_cross_channel_ids
        )
        nc.Measurement_ID = measurement_id + "35"
        nc.X_PollyXTPipelines_Configuration_ID = (
            location.calibration_configuration_355nm
        )
    elif wavelength == Wavelength.NM_532:
        total_channel_idx = location.total_channel_532_nm_idx
        cross_channel_idx = location.cross_channel_532_nm_idx
        channel_id[:] = np.array(
            location.calibration_532nm_total_channel_ids
            + location.calibration_532nm_cross_channel_ids
        )
        nc.Measurement_ID = measurement_id + "53"
        nc.X_PollyXTPipelines_Configuration_ID = (
            location.calibration_configuration_532nm
        )
    elif wavelength == Wavelength.NM_1064:
        total_channel_idx = location.total_channel_1064_nm_idx
        cross_channel_idx = location.cross_channel_1064_nm_idx
        channel_id[:] = np.array(
            location.calibration_1064nm_total_channel_ids
            + location.calibration_1064nm_cross_channel_ids
        )
        nc.Measurement_ID = measurement_id + "10"
        nc.X_PollyXTPipelines_Configuration_ID = (
            location.calibration_configuration_1064nm
        )
    else:
        raise ValueError(f"Unknown wavelength {wavelength}")

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

    # Close the netCDF file.
    nc.close()

    return measurement_id, output_filename


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
                interval_start, interval_end + timedelta(seconds=30)
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
        depol_channels = location.has_depol_channels()

        # Check for any valid calibration intervals
        for start, end in repo.get_calibration_periods():
            if start > measurement_start and end < measurement_end:
                pf = repo.get_pollyxt_file(start, end)

                # Generate calibration files for all channels that exist!
                for wv, channel_exists in depol_channels.items():
                    if channel_exists:
                        id, path = create_scc_calibration_netcdf(
                            pf, output_path, location, wavelength=wv
                        )
                        yield id, path, start, end
