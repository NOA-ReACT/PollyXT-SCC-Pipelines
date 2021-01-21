from datetime import datetime

import pytest

from pollyxt_pipelines.utils import date_option_to_datetime


class TestDateOptionToDatetime:
    """
    Tests for the utils.date_option_to_datetime() function
    """

    def test_full_date(self):
        measurement_start = datetime.strptime("2020-01-01_01:23", "%Y-%m-%d_%H:%M")
        string = "2022-02-10_10:34"

        result = date_option_to_datetime(measurement_start, string)

        assert result == datetime.strptime(string, "%Y-%m-%d_%H:%M")

    def test_hour(self):
        measurement_start = datetime.strptime("2020-01-01_01:23", "%Y-%m-%d_%H:%M")
        string = "12:00"

        result = date_option_to_datetime(measurement_start, string)

        assert result == measurement_start.replace(hour=12, minute=00)

    def test_minute(self):
        # Minutes not available in first hour
        measurement_start = datetime.strptime("2020-01-01_01:23", "%Y-%m-%d_%H:%M")
        string = "XX:02"

        result = date_option_to_datetime(measurement_start, string)

        assert result == measurement_start.replace(hour=2, minute=2)

        # Minutes available in first hour
        measurement_start = datetime.strptime("2020-01-01_01:23", "%Y-%m-%d_%H:%M")
        string = "XX:31"

        result = date_option_to_datetime(measurement_start, string)

        assert result == measurement_start.replace(minute=31)

    def test_invalid_input(self):
        measurement_start = datetime.today()  # This doesn't matter much

        # Bad month (13)
        with pytest.raises(ValueError):
            date_option_to_datetime(measurement_start, "1996-13-14_00:01")

        # Bad ISO formatting
        with pytest.raises(ValueError):
            date_option_to_datetime(measurement_start, "1996/13/14 00:01")

        # Bad hour format
        with pytest.raises(ValueError):
            date_option_to_datetime(measurement_start, "00-01")

        # Bad hour value (26)
        with pytest.raises(ValueError):
            date_option_to_datetime(measurement_start, "26:00")

        # Bad minute value (:70)
        with pytest.raises(ValueError):
            date_option_to_datetime(measurement_start, "XX:70")
