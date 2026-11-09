from datetime import datetime, timedelta, timezone

import pytest
from netCDF4 import Dataset

from pollyxt_pipelines.conftest import write_polly_file
from pollyxt_pipelines.enums import Wavelength
from pollyxt_pipelines.polly_to_scc import pollyxt, scc_netcdf
from pollyxt_pipelines.polly_to_scc.scc_netcdf import convert_window

UTC = timezone.utc
DAY = datetime(2026, 1, 1)


def at(hh, mm=0, ss=0):
    """Naive UTC time on the test day"""
    return DAY.replace(hour=hh, minute=mm, second=ss)


def idx(hh, mm):
    """Profile index of HH:MM in a file starting at 09:00"""
    return int((at(hh, mm) - at(9)).total_seconds() // 30)


@pytest.fixture
def repo(polly_dir, test_location):
    """
    09:00 to 14:59:30, with calibrations at 09:20 (inside an hour) and 10:55 (crossing
    into 11:00).
    """
    write_polly_file(
        polly_dir / "a.nc",
        at(9),
        6 * 120,
        calibrations=[idx(9, 20), idx(10, 55)],
    )
    return pollyxt.PollyXTRepository(polly_dir, test_location)


def test_data_file_for_full_hour(repo, output_dir, test_location):
    result = convert_window(
        repo, at(10), at(11), output_dir, test_location, calibration=False
    )

    assert result.data is not None
    assert result.data.kind == "data"
    assert result.data.measurement_id == "20260101tst1000"
    assert result.data.path == output_dir / "20260101tst1000.nc"
    assert result.data.start == datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
    # End is exclusive: the 11:00 profile is not included
    assert result.data.end == datetime(2026, 1, 1, 10, 59, 30, tzinfo=UTC)
    assert result.data.configuration_id == test_location.daytime_configuration
    assert result.calibrations == []
    assert result.skipped == []

    with Dataset(result.data.path) as nc:
        assert nc.Measurement_ID == result.data.measurement_id
        assert nc.X_PollyXTPipelines_Configuration_ID == result.data.configuration_id
        # 10:55-10:59:30 is calibration, so 10 profiles are left out
        assert nc["Raw_Lidar_Data"].shape[0] == 120 - 10


def test_window_clipped_at_start(repo, output_dir, test_location):
    result = convert_window(repo, at(8, 30), at(9, 30), output_dir, test_location)

    assert result.data.start == datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
    assert result.data.end == datetime(2026, 1, 1, 9, 29, 30, tzinfo=UTC)
    assert result.data.measurement_id == "20260101tst0900"


def test_window_clipped_at_end(repo, output_dir, test_location):
    result = convert_window(repo, at(14, 30), at(16), output_dir, test_location)

    assert result.data.start == datetime(2026, 1, 1, 14, 30, tzinfo=UTC)
    assert result.data.end == datetime(2026, 1, 1, 14, 59, 30, tzinfo=UTC)


def test_window_starting_mid_hour(polly_dir, output_dir, test_location):
    # The instrument started at 10:20
    write_polly_file(polly_dir / "a.nc", at(10, 20), 120)
    repo = pollyxt.PollyXTRepository(polly_dir, test_location)

    result = convert_window(repo, at(10), at(11), output_dir, test_location)

    assert result.data.measurement_id == "20260101tst1020"
    assert result.data.start == datetime(2026, 1, 1, 10, 20, tzinfo=UTC)
    assert result.data.end - result.data.start == timedelta(minutes=39, seconds=30)


def test_window_without_data(repo, output_dir, test_location):
    result = convert_window(repo, at(6), at(7), output_dir, test_location)

    assert result.data is None
    assert result.calibrations == []
    assert result.skipped == []
    assert list(output_dir.iterdir()) == []


def test_calibration_inside_hour(repo, output_dir, test_location):
    result = convert_window(repo, at(9), at(10), output_dir, test_location)

    assert result.skipped == []
    assert [c.wavelength for c in result.calibrations] == [
        Wavelength.NM_355,
        Wavelength.NM_532,
    ]
    c355, c532 = result.calibrations
    assert c355.kind == "calibration"
    assert c355.measurement_id == "20260101tst0935"
    assert c532.measurement_id == "20260101tst0953"
    assert c355.configuration_id == test_location.calibration_configuration_355nm
    assert c532.configuration_id == test_location.calibration_configuration_532nm
    assert c355.start == datetime(2026, 1, 1, 9, 20, tzinfo=UTC)
    assert c355.end == datetime(2026, 1, 1, 9, 29, 30, tzinfo=UTC)

    for c in result.calibrations:
        with Dataset(c.path) as nc:
            assert nc.Measurement_ID == c.measurement_id
            assert nc.X_PollyXTPipelines_Configuration_ID == c.configuration_id


def test_calibration_crossing_hour_belongs_to_start_window(
    repo, output_dir, test_location
):
    first = convert_window(repo, at(10), at(11), output_dir, test_location)
    second = convert_window(repo, at(11), at(12), output_dir, test_location)

    assert [c.measurement_id for c in first.calibrations] == [
        "20260101tst1035",
        "20260101tst1053",
    ]
    assert first.calibrations[0].start == datetime(2026, 1, 1, 10, 55, tzinfo=UTC)
    assert first.calibrations[0].end == datetime(2026, 1, 1, 11, 4, 30, tzinfo=UTC)
    assert first.skipped == []

    assert second.calibrations == []
    assert second.skipped == []


def test_calibration_crossing_file_boundary(polly_dir, output_dir, test_location):
    write_polly_file(polly_dir / "a.nc", at(9), idx(10, 30), calibrations=[idx(10, 25)])
    # Second file continues the calibration (last 10 profiles at -45°)
    second = write_polly_file(polly_dir / "b.nc", at(10, 30), 90)
    with Dataset(second, "a") as nc:
        nc["depol_cal_angle"][0:10] = -45.0
    repo = pollyxt.PollyXTRepository(polly_dir, test_location)

    result = convert_window(repo, at(10), at(11), output_dir, test_location)

    assert result.skipped == []
    assert len(result.calibrations) == 2
    assert result.calibrations[0].end == datetime(2026, 1, 1, 10, 34, 30, tzinfo=UTC)


def test_calibration_cut_off_by_end_of_data(polly_dir, output_dir, test_location):
    # Data ends at 11:59:30, during a calibration that started at 11:55
    write_polly_file(polly_dir / "a.nc", at(9), 3 * 120, calibrations=[idx(11, 55)])
    repo = pollyxt.PollyXTRepository(polly_dir, test_location)

    result = convert_window(repo, at(11), at(12), output_dir, test_location)

    assert result.data is not None
    assert result.calibrations == []
    assert len(result.skipped) == 1
    assert "11:55" in result.skipped[0]
    assert "ends during the calibration" in result.skipped[0]
    assert not list(output_dir.glob("calibration_*"))


def test_calibration_at_first_measurement(polly_dir, output_dir, test_location):
    write_polly_file(polly_dir / "a.nc", at(9), 120, calibrations=[0])
    repo = pollyxt.PollyXTRepository(polly_dir, test_location)

    result = convert_window(repo, at(9), at(10), output_dir, test_location)

    assert result.calibrations == []
    assert len(result.skipped) == 1
    assert "real start is unknown" in result.skipped[0]


def test_one_wavelength_failing_is_skipped(repo, output_dir, test_location):
    broken = test_location._replace(total_channel_532_nm_idx=99)

    result = convert_window(repo, at(9), at(10), output_dir, broken)

    assert [c.wavelength for c in result.calibrations] == [Wavelength.NM_355]
    assert len(result.skipped) == 1
    assert "532 nm" in result.skipped[0]
    # No partial file is left behind
    assert not (output_dir / "calibration_20260101tst09_532.nc").exists()


def test_no_calibration(repo, output_dir, test_location):
    result = convert_window(
        repo, at(9), at(10), output_dir, test_location, calibration=False
    )
    assert result.calibrations == []


def test_rerun_gives_same_names(repo, tmp_path, test_location):
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_dir.mkdir()
    second_dir.mkdir()

    first = convert_window(repo, at(10), at(11), first_dir, test_location)
    # Same window, given as an aware datetime in another timezone
    athens = timezone(timedelta(hours=2))
    second = convert_window(
        repo,
        datetime(2026, 1, 1, 12, 0, tzinfo=athens),
        datetime(2026, 1, 1, 13, 0, tzinfo=athens),
        second_dir,
        test_location,
    )

    def names(result):
        files = [result.data] + result.calibrations
        return [(f.measurement_id, f.path.name, f.start, f.end) for f in files]

    assert names(first) == names(second)
    assert sorted(p.name for p in first_dir.iterdir()) == sorted(
        p.name for p in second_dir.iterdir()
    )


def test_end_before_start_raises(repo, output_dir, test_location):
    with pytest.raises(ValueError):
        convert_window(repo, at(11), at(10), output_dir, test_location)


def test_cli_generator_still_works(repo, output_dir, test_location):
    results = list(
        scc_netcdf.convert_pollyxt_file(
            repo,
            output_dir,
            test_location,
            timedelta(hours=1),
            scc_netcdf.Atmosphere.STANDARD_ATMOSPHERE,
        )
    )

    data = [r for r in results if "calibration" not in str(r[1])]
    calibrations = [r for r in results if "calibration" in str(r[1])]

    assert [r[0] for r in data] == [f"20260101tst{h:02}00" for h in range(9, 15)]
    # Both calibrations are strictly inside the data; IDs reported without suffix
    assert [r[0] for r in calibrations] == [
        "20260101tst09",
        "20260101tst09",
        "20260101tst10",
        "20260101tst10",
    ]
