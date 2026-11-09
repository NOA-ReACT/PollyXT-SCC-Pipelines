"""
Shared pytest fixtures: synthetic PollyXT files and a test location.
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Sequence

import numpy as np
import pytest
from netCDF4 import Dataset

PROFILE_SECONDS = 30
N_CHANNELS = 12
N_POINTS = 300
CALIBRATION_LENGTH = 20  # profiles: 10 at +45°, 10 at -45°

TEST_LOCATIONS_INI = """
[Testland]
scc_code = tst
lat = 35.86
lon = 23.31
altitude_asl = 0.1
daytime_configuration = 1001
nighttime_configuration = 1002
calibration_configuration_355nm = 1003
calibration_configuration_532nm = 1004
channel_id = 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12
background_low = 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
background_high = 249, 249, 249, 249, 249, 249, 249, 249, 249, 249, 249, 249
lr_input = 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1
temperature = 20
pressure = 1008
depol_calibration_zero_state = 0
total_channel_355_nm_idx = 0
cross_channel_355_nm_idx = 1
total_channel_532_nm_idx = 4
cross_channel_532_nm_idx = 5
calibration_355nm_total_channel_ids = 21, 22
calibration_355nm_cross_channel_ids = 23, 24
calibration_532nm_total_channel_ids = 25, 26
calibration_532nm_cross_channel_ids = 27, 28
profile_name = TEST
sounding_provider = noa_wrf
sunrise_time = 04:00
sunset_time = 16:00
"""


def write_polly_file(
    path: Path,
    start: datetime,
    n_profiles: int,
    calibrations: Sequence[int] = (),
    calibration_length: int = CALIBRATION_LENGTH,
) -> Path:
    """
    Write a minimal synthetic PollyXT netCDF file.

    Parameters:
        path: Output file
        start: Time of the first profile (naive UTC)
        n_profiles: Number of 30 s profiles
        calibrations: Profile indices where calibration periods start. Each period is
            `calibration_length` profiles: half at +45°, half at -45°. It is cut short if
            the file ends first.
    """

    times = [start + timedelta(seconds=PROFILE_SECONDS * i) for i in range(n_profiles)]
    measurement_time = np.array(
        [
            [int(t.strftime("%Y%m%d")), t.hour * 3600 + t.minute * 60 + t.second]
            for t in times
        ],
        dtype=np.int32,
    )

    depol_cal_angle = np.zeros(n_profiles, dtype=np.float64)
    half = calibration_length // 2
    for c in calibrations:
        depol_cal_angle[c : c + half] = 45.0
        depol_cal_angle[c + half : c + calibration_length] = -45.0

    rng = np.random.default_rng(int(start.timestamp()))
    raw_signal = rng.integers(0, 1000, size=(n_profiles, N_POINTS, N_CHANNELS))

    with Dataset(path, "w") as nc:
        nc.createDimension("time", n_profiles)
        nc.createDimension("height", N_POINTS)
        nc.createDimension("channel", N_CHANNELS)
        nc.createDimension("date_time", 2)
        nc.createDimension("one", 1)
        nc.createDimension("coordinates", 2)

        nc.createVariable("measurement_time", "i4", ("time", "date_time"))[
            :
        ] = measurement_time
        nc.createVariable("raw_signal", "i4", ("time", "height", "channel"))[
            :
        ] = raw_signal
        nc.createVariable("measurement_shots", "i4", ("time", "channel"))[:] = 600
        nc.createVariable("zenithangle", "f4", ("one",))[:] = 5.0
        nc.createVariable("location_coordinates", "f4", ("coordinates",))[:] = [
            35.86,
            23.31,
        ]
        nc.createVariable("depol_cal_angle", "f8", ("time",))[:] = depol_cal_angle

    return path


@pytest.fixture
def test_location(tmp_path):
    """The `Testland` location, read from its own file."""
    from pollyxt_pipelines.locations import read_locations_file

    ini = tmp_path / "test_locations.ini"
    ini.write_text(TEST_LOCATIONS_INI)
    return read_locations_file(ini)["Testland"]


@pytest.fixture
def polly_dir(tmp_path):
    """An empty directory for synthetic PollyXT files."""
    path = tmp_path / "polly"
    path.mkdir()
    return path


@pytest.fixture
def output_dir(tmp_path):
    """An empty directory for SCC output files."""
    path = tmp_path / "out"
    path.mkdir()
    return path
