import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest
from netCDF4 import Dataset

from pollyxt_pipelines import config
from pollyxt_pipelines.qc_eldec import qc
from pollyxt_pipelines.qc_eldec.qc import CalibrationPoint, Thresholds

UTC = timezone.utc
START = datetime(2026, 1, 1, 2, 31, tzinfo=UTC)


def write_eldec_file(
    path,
    measurement_id="20260101tst0235",
    wavelength=355.0,
    value=0.1,
    error=0.002,
    start=START,
    noise=0.001,
):
    """A minimal ELDEC file (format 1.1) with one calibration"""
    altitude = np.arange(0, 6000, 7.5) + 100.0
    rng = np.random.default_rng(0)
    ratio = value + rng.normal(0, noise, size=(2, 1, altitude.size))
    t0 = int((start - datetime(1970, 1, 1, tzinfo=UTC)).total_seconds())

    with Dataset(path, "w") as nc:
        nc.createDimension("time", 1)
        nc.createDimension("nv", 2)
        nc.createDimension("altitude", altitude.size)
        nc.createDimension("calibration", 1)
        nc.createDimension("ratio", 2)

        nc.createVariable("altitude", "f8", ("altitude",))[:] = altitude
        nc.createVariable("station_altitude", "f8", ("calibration",))[:] = 100.0
        nc.createVariable("time_bounds", "i8", ("time", "nv"))[:] = [[t0, t0 + 600]]
        nc.createVariable(
            "polarization_calibration_ratio_emission_wavelength", "f8", ("calibration",)
        )[:] = wavelength
        nc.createVariable(
            "polarization_calibration_minimum_range", "f8", ("calibration",)
        )[:] = 1200.0
        nc.createVariable(
            "polarization_calibration_maximum_range", "f8", ("calibration",)
        )[:] = 2500.0
        nc.createVariable(
            "polarization_calibration_ratio", "f8", ("ratio", "time", "altitude")
        )[:] = ratio
        nc.createVariable(
            "polarization_calibration_ratio_statistical_error",
            "f8",
            ("ratio", "time", "altitude"),
        )[:] = np.full_like(ratio, error)
        nc.createVariable("polarization_gain_factor", "f8", ("calibration", "time"))[
            :
        ] = value
        nc.createVariable(
            "polarization_gain_factor_statistical_error", "f8", ("calibration", "time")
        )[:] = error

        nc.station_ID = "tst"
        nc.hoi_configuration_ID = 1003
        nc.hoi_system_ID = 1003
        nc.system = "Test PollyXT"
        nc.measurement_ID = measurement_id
        nc.processor_version = "eldec 1.0"
        nc.scc_version = "scc 5.2"
        nc.scc_product_ID = 42
        nc.setncattr("__file_format_version", "1.1")

    return path


def point(measurement_id, value, wavelength=355, days_before=10, error=0.002):
    return CalibrationPoint(
        measurement_id=measurement_id,
        wavelength=wavelength,
        start_time=START - timedelta(days=days_before),
        value=value,
        error=error,
        range_min=1200.0,
        range_max=2500.0,
        eldec_version="eldec 1.0",
        scc_version="scc 5.2",
    )


GOOD_HISTORY = [
    point("h1", 0.100),
    point("h2", 0.101),
    point("h3", 0.099),
    point("h4", 0.1005),
]


@pytest.fixture
def eldec(tmp_path):
    return qc.read_eldec(write_eldec_file(tmp_path / "eldec.nc"))


def test_read_eldec(eldec):
    assert eldec.measurement_id == "20260101tst0235"
    assert eldec.wavelength == 355
    assert eldec.start_time == START
    assert eldec.value == pytest.approx(0.1)
    assert eldec.error == pytest.approx(0.002)
    assert eldec.range_min == 1200.0
    assert eldec.range_max == 2500.0
    assert eldec.ratio_profiles.shape == (2, eldec.height.size)
    assert eldec.profile_stddev == pytest.approx(0.001, rel=0.2)


def test_no_history(eldec):
    result = qc.check_calibration(eldec, [])

    assert result.ok
    assert result.error_ok and result.profiles_ok
    assert result.outlier is None
    assert result.history_points == 0
    assert result.reasons == []
    assert result.point == eldec.to_point()


def test_short_history_skips_outlier_check(eldec):
    # Not more than DPCAL_MIN_NB_OF_POINTS (3): no outlier check, even for a far value
    far = replace(eldec, value=0.5, error=0.01)
    result = qc.check_calibration(far, GOOD_HISTORY[:3])

    assert result.outlier is None
    assert result.history_points == 3
    assert result.ok


def test_enough_history_not_outlier(eldec):
    result = qc.check_calibration(eldec, GOOD_HISTORY)

    assert result.outlier is False
    assert result.history_points == 4
    assert result.ok


def test_enough_history_outlier(eldec):
    far = replace(eldec, value=0.15, error=0.001, profile_stddev=0.001)
    result = qc.check_calibration(far, GOOD_HISTORY)

    assert result.outlier is True
    assert not result.ok
    assert len(result.reasons) == 1
    assert "outlier" in result.reasons[0]


def test_same_measurement_id_is_left_out(eldec):
    # The calibration itself is in the history (checked again): it must not count
    history = GOOD_HISTORY[:3] + [point(eldec.measurement_id, eldec.value)]
    result = qc.check_calibration(eldec, history)

    assert result.history_points == 3
    assert result.outlier is None


def test_other_wavelengths_are_left_out(eldec):
    history = GOOD_HISTORY[:3] + [point("x532", 0.1, wavelength=532)]
    result = qc.check_calibration(eldec, history)

    assert result.history_points == 3
    assert result.outlier is None


def test_only_before(eldec):
    history = GOOD_HISTORY[:3] + [point("future", 0.1, days_before=-5)]

    assert qc.check_calibration(eldec, history).history_points == 4
    assert qc.check_calibration(eldec, history, only_before=True).history_points == 3


def test_error_too_large(eldec):
    bad = replace(eldec, error=0.02)
    result = qc.check_calibration(bad, [])

    assert not result.error_ok
    assert not result.ok
    assert "relative error" in result.reasons[0]


def test_profiles_too_noisy(eldec):
    bad = replace(eldec, profile_stddev=0.05)
    result = qc.check_calibration(bad, [])

    assert not result.profiles_ok
    assert not result.ok


def test_custom_thresholds(eldec):
    result = qc.check_calibration(eldec, [], Thresholds(max_relative_error=0.01))
    assert not result.error_ok


def test_check_calibrations_records_nothing(tmp_path, eldec):
    e532 = qc.read_eldec(
        write_eldec_file(
            tmp_path / "eldec532.nc",
            measurement_id="20260101tst0253",
            wavelength=532,
            error=0.05,
        )
    )
    history = list(GOOD_HISTORY)

    results = qc.check_calibrations([eldec, e532], history)

    assert [r.ok for r in results] == [True, False]
    assert not all(r.ok for r in results)
    assert history == GOOD_HISTORY


def test_calibration_point_json_round_trip():
    p = point("20260101tst0235", 0.1234)
    d = json.loads(json.dumps(p.to_dict()))

    assert d["start_time"] == "2025-12-22T02:31:00+00:00"
    assert CalibrationPoint.from_dict(d) == p


def test_calibration_point_naive_time_is_utc():
    d = point("a", 0.1).to_dict()
    d["start_time"] = "2025-12-22T02:31:00"
    assert CalibrationPoint.from_dict(d).start_time == START - timedelta(days=10)


def test_history_file_round_trip(tmp_path):
    path = tmp_path / "Testland_355nm.nc"
    for p in GOOD_HISTORY:
        qc.append_to_history_file(path, p)
    # Same ID again replaces the earlier point
    updated = replace(GOOD_HISTORY[1], value=0.111)
    qc.append_to_history_file(path, updated)

    points = qc.read_history_file(path)

    assert points == [GOOD_HISTORY[0], updated, GOOD_HISTORY[2], GOOD_HISTORY[3]]


def test_history_file_wavelength(tmp_path):
    path = tmp_path / "history.nc"
    qc.append_to_history_file(path, GOOD_HISTORY[0])

    with pytest.raises(ValueError):
        qc.read_history_file(path)
    assert qc.read_history_file(path, wavelength=355) == [GOOD_HISTORY[0]]


@pytest.mark.parametrize("wavelength", [355, 532, 1064])
def test_plot_calibration(tmp_path, wavelength):
    e = qc.read_eldec(
        write_eldec_file(tmp_path / f"eldec{wavelength}.nc", wavelength=wavelength)
    )
    history = [replace(p, wavelength=wavelength) for p in GOOD_HISTORY]
    result = qc.check_calibration(e, history)

    out = tmp_path / f"plot{wavelength}.png"
    qc.plot_calibration(e, history, result, out)

    assert out.stat().st_size > 0


def test_plot_without_history(tmp_path, eldec):
    out = tmp_path / "plot.png"
    qc.plot_calibration(eldec, [], qc.check_calibration(eldec, []), out)
    assert out.exists()


def test_cli_wrapper_uses_history_file(tmp_path, monkeypatch, test_location):
    from pollyxt_pipelines.qc_eldec.qc_eldec_file import ELDECfile, history_path

    monkeypatch.setenv(config.CONFIG_DIR_ENV_VAR, str(tmp_path / "config"))
    path = write_eldec_file(tmp_path / "eldec.nc")

    first = ELDECfile(path, test_location, plot_path=tmp_path / "plot.png")
    assert first.calibration_ok()
    assert (tmp_path / "plot.png").exists()

    hist = history_path(test_location, 355)
    assert hist == tmp_path / "config" / "qc_eldec" / "Testland_355nm.nc"
    assert [p.measurement_id for p in qc.read_history_file(hist)] == ["20260101tst0235"]

    # Checking again doesn't count itself or add a second point
    second = ELDECfile(path, test_location)
    assert second.calibration_ok()
    assert second.result.history_points == 0
    assert len(qc.read_history_file(hist)) == 1


def test_cli_wrapper_failing_calibration_not_recorded(
    tmp_path, monkeypatch, test_location
):
    from pollyxt_pipelines.qc_eldec.qc_eldec_file import ELDECfile, history_path

    monkeypatch.setenv(config.CONFIG_DIR_ENV_VAR, str(tmp_path / "config"))
    path = write_eldec_file(tmp_path / "eldec.nc", error=0.05)

    assert not ELDECfile(path, test_location).calibration_ok()
    assert qc.read_history_file(history_path(test_location, 355)) == []
