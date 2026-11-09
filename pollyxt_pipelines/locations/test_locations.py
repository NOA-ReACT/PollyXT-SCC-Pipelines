from pathlib import Path

import pytest

from pollyxt_pipelines import config
from pollyxt_pipelines.conftest import TEST_LOCATIONS_INI
from pollyxt_pipelines.locations import (
    InvalidLocationError,
    read_locations,
    read_locations_file,
)


def test_read_locations_file_reads_only_that_file(tmp_path):
    ini = tmp_path / "locations.ini"
    ini.write_text(TEST_LOCATIONS_INI)

    locations = read_locations_file(ini)

    assert list(locations) == ["Testland"]
    loc = locations["Testland"]
    assert loc.scc_code == "tst"
    assert loc.depol_calibration_zero_state == 0
    assert loc.channel_id == list(range(1, 13))
    assert loc.calibration_configuration_1064nm is None


def test_read_locations_file_missing_key_raises(tmp_path):
    ini = tmp_path / "locations.ini"
    ini.write_text(TEST_LOCATIONS_INI.replace("pressure = 1008\n", ""))

    with pytest.raises(InvalidLocationError) as ex:
        read_locations_file(ini)

    assert ex.value.section == "Testland"
    assert ex.value.path == ini
    assert "pressure" in str(ex.value)


def test_read_locations_file_bad_value_raises(tmp_path):
    ini = tmp_path / "locations.ini"
    ini.write_text(TEST_LOCATIONS_INI.replace("lat = 35.86", "lat = north"))

    with pytest.raises(InvalidLocationError):
        read_locations_file(ini)


def test_read_locations_file_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_locations_file(tmp_path / "nope.ini")


def test_read_locations_later_file_wins(tmp_path, monkeypatch):
    monkeypatch.setenv(config.CONFIG_DIR_ENV_VAR, str(tmp_path / "empty-config"))

    first = tmp_path / "first.ini"
    first.write_text(TEST_LOCATIONS_INI)
    second = tmp_path / "second.ini"
    second.write_text(
        TEST_LOCATIONS_INI.replace("[Testland]", "[Antikythera]").replace(
            "depol_calibration_zero_state = 0", "depol_calibration_zero_state = 330"
        )
    )

    locations = read_locations([first, second])

    # Built-in locations are still there
    assert "Finokalia" in locations
    # The extra file replaced the built-in Antikythera
    assert locations["Antikythera"].depol_calibration_zero_state == 330
    assert locations["Antikythera"].scc_code == "tst"
    assert "Testland" in locations


def test_read_locations_reads_config_dir(tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "locations.ini").write_text(TEST_LOCATIONS_INI)
    monkeypatch.setenv(config.CONFIG_DIR_ENV_VAR, str(config_dir))

    assert config.config_paths() == [config_dir]
    assert "Testland" in read_locations()


def test_config_paths_without_override(monkeypatch):
    monkeypatch.delenv(config.CONFIG_DIR_ENV_VAR, raising=False)
    paths = config.config_paths()
    assert all(isinstance(p, Path) for p in paths)
    assert len(paths) >= 1
