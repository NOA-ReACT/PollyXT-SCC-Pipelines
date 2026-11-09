"""
Calibration QC on ELDEC products, without any state on disk.

Reading, checking and recording are separate steps, and the caller supplies the history of
earlier good calibrations:

    eldecs = [read_eldec(path) for path in eldec_paths]
    results = check_calibrations(eldecs, history)
    if all(r.ok for r in results):
        history.extend(r.point for r in results)   # the caller stores these

Nothing here reads or writes files except `read_eldec` (its argument), `plot_calibration`
(its output) and the history-file helpers used by the CLI.

Original algorithm by Ina Mattis (@imattis on GitLab): https://gitlab.com/imattis/qc_eldec_file
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Sequence

import numpy as np
from netCDF4 import Dataset

from pollyxt_pipelines.qc_eldec import constants

logger = logging.getLogger(__name__)

EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None or dt.utcoffset() is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dataclass(frozen=True)
class CalibrationPoint:
    """One calibration in the history. Plain values, so it can be stored as JSON."""

    measurement_id: str
    wavelength: int
    """nm"""
    start_time: datetime
    """UTC, timezone-aware"""
    value: float
    """Polarization gain factor"""
    error: float
    """Statistical error of `value`"""
    range_min: float
    """Calibration range, m"""
    range_max: float
    eldec_version: str
    scc_version: str

    def to_dict(self) -> dict:
        """JSON-safe dictionary, with the time in ISO 8601"""
        return {
            "measurement_id": self.measurement_id,
            "wavelength": int(self.wavelength),
            "start_time": _utc(self.start_time).isoformat(),
            "value": float(self.value),
            "error": float(self.error),
            "range_min": float(self.range_min),
            "range_max": float(self.range_max),
            "eldec_version": str(self.eldec_version),
            "scc_version": str(self.scc_version),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CalibrationPoint":
        """Inverse of `to_dict`. A time without a timezone is taken as UTC."""
        start_time = d["start_time"]
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time)
        return cls(
            measurement_id=str(d["measurement_id"]),
            wavelength=int(d["wavelength"]),
            start_time=_utc(start_time),
            value=float(d["value"]),
            error=float(d["error"]),
            range_min=float(d["range_min"]),
            range_max=float(d["range_max"]),
            eldec_version=str(d["eldec_version"]),
            scc_version=str(d["scc_version"]),
        )


@dataclass(frozen=True)
class Thresholds:
    """Limits used by `check_calibration`"""

    max_relative_error: float = constants.MAX_DPCAL_ERR
    """Maximum relative error of the gain factor"""
    max_ratio_stddev: float = constants.MAX_RATIO_STDDEV
    """Maximum relative standard deviation of the ratio profiles"""
    min_history_points: int = constants.DPCAL_MIN_NB_OF_POINTS
    """The outlier check runs only with more history points than this"""
    outlier_factor: float = constants.DPCAL_STD_OUTLIER_FACTOR
    """Value ± error must overlap mean ± `outlier_factor` × σ of the history"""


@dataclass
class Eldec:
    """A parsed ELDEC file (one calibration, one wavelength)"""

    path: Path
    measurement_id: str
    wavelength: int
    start_time: datetime
    """UTC, timezone-aware"""
    stop_time: datetime
    station_id: str
    configuration_id: int
    system_id: int
    system: str
    product_id: object
    eldec_version: str
    scc_version: str

    value: float
    """Polarization gain factor"""
    error: float
    """Statistical error of the gain factor"""
    range_min: float
    """Calibration range, m above the station"""
    range_max: float

    height: np.ndarray = field(repr=False)
    """m above the station"""
    ratio_profiles: np.ndarray = field(repr=False)
    """Two ratio profiles, shape (2, height). Invalid values are NaN."""
    ratio_profile_errors: np.ndarray = field(repr=False)
    profile_stddev: float = float("nan")
    """Mean standard deviation of the two ratio profiles inside the calibration range"""

    def to_point(self) -> CalibrationPoint:
        """This calibration as a history point"""
        return CalibrationPoint(
            measurement_id=self.measurement_id,
            wavelength=int(self.wavelength),
            start_time=self.start_time,
            value=float(self.value),
            error=float(self.error),
            range_min=float(self.range_min),
            range_max=float(self.range_max),
            eldec_version=str(self.eldec_version),
            scc_version=str(self.scc_version),
        )


@dataclass
class QCResult:
    """The outcome of `check_calibration`"""

    ok: bool
    """True if all checks passed"""
    point: CalibrationPoint
    """What to store in the history if the caller accepts the calibration"""
    error_ok: bool
    """The relative error of the gain factor is below the threshold"""
    profiles_ok: bool
    """The relative standard deviation of the ratio profiles is below the threshold"""
    outlier: Optional[bool]
    """True if the value is an outlier of the history; None if there was too little
    history to tell"""
    history_points: int
    """How many history points were comparable (same wavelength, other measurements)"""
    reasons: List[str] = field(default_factory=list)
    """Why it failed, readable. Empty when `ok`."""


def _mask_invalid(a: np.ndarray) -> np.ndarray:
    a = np.array(a, dtype=np.float64)
    a[a > 1e20] = np.nan
    return a


def read_eldec(path: Path) -> Eldec:
    """
    Read an ELDEC file. Only files with a single calibration are supported.

    Raises:
        ValueError: The file contains more than one calibration
    """

    path = Path(path)
    with Dataset(path, "r") as nc:
        nc.set_auto_mask(False)

        if nc.dimensions["time"].size > 1:
            raise ValueError(
                f"{path}: cannot read ELDEC file with more than 1 calibration"
            )
        time_idx = 0

        altitude = np.array(nc["altitude"][:], dtype=np.float64)
        height = altitude - float(nc["station_altitude"][0])

        time_bounds = nc["time_bounds"][time_idx]
        start_time = EPOCH + timedelta(seconds=int(time_bounds[0]))
        stop_time = EPOCH + timedelta(seconds=int(time_bounds[1]))

        range_min = float(np.nanmin(nc["polarization_calibration_minimum_range"][:]))
        range_max = float(np.nanmax(nc["polarization_calibration_maximum_range"][:]))

        ratio_profiles = _mask_invalid(
            nc["polarization_calibration_ratio"][:, time_idx, :]
        )
        ratio_profile_errors = _mask_invalid(
            nc["polarization_calibration_ratio_statistical_error"][:, time_idx, :]
        )

        above_min = np.where(height > range_min)[0]
        above_max = np.where(height > range_max)[0]
        min_idx = above_min[0] if above_min.size else 0
        max_idx = above_max[0] if above_max.size else height.size
        profile_stddev = float(
            np.nanmean(np.nanstd(ratio_profiles[:, min_idx:max_idx], axis=1))
        )

        if nc.getncattr("__file_format_version") <= "1.0":
            if path.name.count("_") > 2:
                product_id = int(path.name.split("_")[2])
            else:
                product_id = "nnn"
            value = float(
                np.nanmean(nc["polarization_calibration_ratio_average"][:, time_idx])
            )
            error = float(
                np.nanmean(
                    nc["polarization_calibration_ratio_average_statistical_error"][
                        :, time_idx
                    ]
                )
            )
        else:
            if nc.dimensions["calibration"].size > 1:
                raise ValueError(
                    f"{path}: cannot read ELDEC file with more than 1 calibration"
                )
            product_id = nc.scc_product_ID
            value = float(nc["polarization_gain_factor"][0, time_idx])
            error = float(nc["polarization_gain_factor_statistical_error"][0, time_idx])

        return Eldec(
            path=path,
            measurement_id=str(nc.measurement_ID),
            wavelength=int(
                round(
                    float(nc["polarization_calibration_ratio_emission_wavelength"][0])
                )
            ),
            start_time=start_time,
            stop_time=stop_time,
            station_id=nc.station_ID,
            configuration_id=nc.hoi_configuration_ID,
            system_id=nc.hoi_system_ID,
            system=nc.system,
            product_id=product_id,
            eldec_version=str(nc.processor_version),
            scc_version=str(nc.scc_version),
            value=value,
            error=error,
            range_min=range_min,
            range_max=range_max,
            height=height,
            ratio_profiles=ratio_profiles,
            ratio_profile_errors=ratio_profile_errors,
            profile_stddev=profile_stddev,
        )


def comparable_history(
    eldec: Eldec,
    history: Sequence[CalibrationPoint],
    only_before: bool = False,
) -> List[CalibrationPoint]:
    """
    The history points that `eldec` is compared with: same wavelength, not the same
    measurement, and (if `only_before`) starting before it.
    """
    start = _utc(eldec.start_time)
    return [
        p
        for p in history
        if int(p.wavelength) == int(eldec.wavelength)
        and p.measurement_id != eldec.measurement_id
        and (not only_before or _utc(p.start_time) < start)
    ]


def check_calibration(
    eldec: Eldec,
    history: Sequence[CalibrationPoint],
    thresholds: Thresholds = Thresholds(),
    only_before: bool = False,
) -> QCResult:
    """
    Check the quality of one calibration. Nothing is recorded: if the caller accepts it,
    it stores `result.point` in its history.

    The checks:

    * relative error of the gain factor below `thresholds.max_relative_error`;
    * relative standard deviation of the ratio profiles below `thresholds.max_ratio_stddev`;
    * not an outlier: with more than `thresholds.min_history_points` comparable history
      points, value ± error must overlap mean ± `thresholds.outlier_factor` × σ.

    Parameters:
        eldec: The calibration to check
        history: Earlier good calibrations, of the same station. Only points with the same
            wavelength are used, and any with the same measurement ID are left out, so a
            calibration that is checked again doesn't count itself.
        thresholds: Limits for the checks
        only_before: If True, use only history from before `eldec.start_time`. By default
            all of it is used.
    """

    reasons = []
    name = f"{eldec.measurement_id} ({eldec.wavelength} nm)"

    rel_err = eldec.error / eldec.value
    error_ok = bool(rel_err < thresholds.max_relative_error)
    if not error_ok:
        reasons.append(
            f"{name}: relative error of gain factor {rel_err:.3g} is not below {thresholds.max_relative_error}"
        )

    rel_stddev = eldec.profile_stddev / eldec.value
    profiles_ok = bool(rel_stddev < thresholds.max_ratio_stddev)
    if not profiles_ok:
        reasons.append(
            f"{name}: relative standard deviation of ratio profiles {rel_stddev:.3g} is not below {thresholds.max_ratio_stddev}"
        )

    points = comparable_history(eldec, history, only_before=only_before)
    outlier: Optional[bool] = None
    if len(points) > thresholds.min_history_points:
        values = np.array([p.value for p in points], dtype=np.float64)
        mean = np.mean(values)
        stddev = np.std(values)
        low = mean - thresholds.outlier_factor * stddev
        high = mean + thresholds.outlier_factor * stddev
        overlaps = (eldec.value + eldec.error) > low and (
            eldec.value - eldec.error
        ) < high
        outlier = not bool(overlaps)
        if outlier:
            reasons.append(
                f"{name}: gain factor {eldec.value:.4g} ± {eldec.error:.2g} is an outlier of the history ({low:.4g} to {high:.4g}, {len(points)} points)"
            )

    ok = error_ok and profiles_ok and outlier is not True
    for reason in reasons:
        logger.debug("Calibration QC failed: %s", reason)

    return QCResult(
        ok=ok,
        point=eldec.to_point(),
        error_ok=error_ok,
        profiles_ok=profiles_ok,
        outlier=outlier,
        history_points=len(points),
        reasons=reasons,
    )


def check_calibrations(
    eldecs: Sequence[Eldec],
    history: Sequence[CalibrationPoint],
    thresholds: Thresholds = Thresholds(),
    only_before: bool = False,
) -> List[QCResult]:
    """
    Check all wavelengths of one calibration against the same history.

    The calibration should be kept only if every result is ok
    (`all(r.ok for r in results)`); only then should the caller add the points to its
    history. Nothing is recorded here.
    """
    return [
        check_calibration(e, history, thresholds=thresholds, only_before=only_before)
        for e in eldecs
    ]


def plot_calibration(
    eldec: Eldec,
    history: Sequence[CalibrationPoint],
    result: QCResult,
    path: Path,
    only_before: bool = False,
) -> None:
    """
    Plot the ratio profiles and gain factor of `eldec` next to the history.

    Uses matplotlib's Agg backend directly, so no display is needed and the global backend
    is not changed.
    """

    import matplotlib.dates as mdates
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    from matplotlib.ticker import FuncFormatter

    colors = constants.COLORS.get(eldec.wavelength, constants.DEFAULT_COLORS)
    points = sorted(
        comparable_history(eldec, history, only_before=only_before),
        key=lambda p: p.start_time,
    )
    # Plot in naive UTC
    start_time = _utc(eldec.start_time).replace(tzinfo=None)
    ts_dates = np.array(
        [_utc(p.start_time).replace(tzinfo=None) for p in points], dtype=object
    )
    ts_values = np.array([p.value for p in points], dtype=np.float64)
    ts_errors = np.array([p.error for p in points], dtype=np.float64)

    fig = Figure(figsize=(8, 6), dpi=100)
    FigureCanvasAgg(fig)
    axes = fig.subplots(nrows=1, ncols=2)

    axes[0].set_title(
        f"{eldec.measurement_id} {eldec.wavelength}nm\n"
        f"{eldec.station_id}, {start_time:%Y-%m-%d %H:%M}"
    )

    # Left panel: vertical profiles
    max_alt = eldec.range_max * 1.2
    cal_range = eldec.range_min + np.arange(5) * (eldec.range_max - eldec.range_min) / 4
    above = np.where(eldec.height > max_alt)[0]
    last_bin = above[0] if above.size else eldec.height.size

    axes_limits = (10, 0)
    for idx in range(2):
        profile = eldec.ratio_profiles[idx]
        error = eldec.ratio_profile_errors[idx]

        if constants.AUTO_SCALE:
            window = slice(constants.DPCAL_MIN_BIN, last_bin)
            with np.errstate(invalid="ignore"):
                low = np.nanmin(profile[window] - error[window])
                high = np.nanmax(profile[window] + error[window])
            axes_limits = (min(axes_limits[0], low), max(axes_limits[1], high))
        else:
            axes_limits = constants.AXES_LIMITS.get(eldec.wavelength, (-0.01, 0.3))

        axes[0].plot(profile, eldec.height, color=colors[idx], linewidth=1.5)
        axes[0].plot(profile + error, eldec.height, color=colors[idx], linewidth=0.5)
        axes[0].plot(profile - error, eldec.height, color=colors[idx], linewidth=0.5)

    actual_color = colors["actual"] if result.ok else colors["invalid"]
    axes[0].plot(np.full(5, eldec.value), cal_range, color=actual_color, linewidth=1.5)
    axes[0].plot(
        np.full(5, eldec.value - eldec.error),
        cal_range,
        color=actual_color,
        linewidth=0.5,
    )
    axes[0].plot(
        np.full(5, eldec.value + eldec.error),
        cal_range,
        color=actual_color,
        linewidth=0.5,
    )

    if np.all(np.isfinite(axes_limits)) and axes_limits[0] < axes_limits[1]:
        axes[0].set_xlim(axes_limits)
    axes[0].set_xlabel("DEPOL_CALIBR.")
    axes[0].set_ylim((0, max_alt))
    axes[0].set_ylabel("HEIGHT, km a.g.")
    axes[0].yaxis.set_major_formatter(FuncFormatter(lambda x, pos: "%g" % (x * 1e-3)))

    # Right panel: time series
    if points:
        axes[1].errorbar(
            ts_values, ts_dates, xerr=ts_errors, fmt="o", color=colors["previous"]
        )
    axes[1].errorbar(
        np.array([eldec.value]),
        np.array([start_time], dtype=object),
        xerr=np.array([eldec.error]),
        fmt="o",
        color=actual_color,
    )

    all_times = np.append(ts_dates, start_time)
    all_values = np.append(ts_values, eldec.value)
    all_errors = np.append(ts_errors, eldec.error)

    y_min = max(
        min(all_times) - timedelta(days=5),
        start_time - timedelta(days=constants.TIME_AXIS_SPAN),
    )
    y_max = min(
        max(all_times) + timedelta(days=5),
        start_time + timedelta(days=constants.TIME_AXIS_SPAN),
    )
    visible = np.array([y_min <= t <= y_max for t in all_times])

    if constants.AUTO_SCALE:
        x_min = np.min(all_values[visible]) - np.max(all_errors[visible]) * 0.8
        x_max = np.max(all_values[visible]) + np.max(all_errors[visible]) * 1.2
    else:
        x_min, x_max = constants.AXES_LIMITS.get(eldec.wavelength, (-0.01, 0.3))

    axes[1].set_ylim((y_min, y_max))
    axes[1].set_ylabel("Date")
    axes[1].yaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    if np.isfinite(x_min) and np.isfinite(x_max) and x_min < x_max:
        axes[1].set_xlim((x_min, x_max))
    axes[1].set_xlabel("DEPOL_CALIBR.")

    fig.subplots_adjust(
        hspace=0.0, wspace=0.5, bottom=0.13, left=0.08, top=0.9, right=0.97
    )
    fig.savefig(path)


# History files (used by the CLI)

_HISTORY_WAVELENGTH_RE = re.compile(r"_(\d+)nm\.nc$")


def read_history_file(
    path: Path, wavelength: Optional[int] = None
) -> List[CalibrationPoint]:
    """
    Read a QC history file (`<location>_<wavelength>nm.nc`, as made by the `qc-eldec`
    command) into history points.

    Parameters:
        path: The history file
        wavelength: The wavelength of the points. If not given, it is taken from the
            filename.

    Raises:
        ValueError: No wavelength given and none in the filename
    """

    path = Path(path)
    if wavelength is None:
        match = _HISTORY_WAVELENGTH_RE.search(path.name)
        if match is None:
            raise ValueError(
                f"Cannot tell the wavelength from {path.name}; pass `wavelength`"
            )
        wavelength = int(match.group(1))

    points = []
    with Dataset(path, "r") as nc:
        nc.set_auto_mask(False)
        n = nc.dimensions["time"].size
        ids = nc["Measurement_ID"][:]
        values = nc["polarization_calibration"][:]
        errors = nc["polarization_calibration_error"][:]
        range_min = nc["calibration_range_min"][:]
        range_max = nc["calibration_range_max"][:]
        dates = nc["date"][:]
        eldec_versions = nc["ELDECVersion"][:]
        scc_versions = nc["SCCVersion"][:]

        for i in range(n):
            points.append(
                CalibrationPoint(
                    measurement_id=str(ids[i]),
                    wavelength=int(wavelength),
                    start_time=EPOCH + timedelta(seconds=int(dates[i])),
                    value=float(values[i]),
                    error=float(errors[i]),
                    range_min=float(range_min[i]),
                    range_max=float(range_max[i]),
                    eldec_version=str(eldec_versions[i]),
                    scc_version=str(scc_versions[i]),
                )
            )

    return points


def create_history_file(path: Path) -> None:
    """Create an empty QC history file"""
    with Dataset(path, "w", format="NETCDF4") as ts:
        ts.createDimension("time", 0)
        ts.createVariable("calibration_range_max", "f8", ("time",))
        ts.createVariable("calibration_range_min", "f8", ("time",))
        ts.createVariable("date", "i8", ("time",))
        ts.createVariable("Measurement_ID", str, ("time",))
        ts.createVariable("polarization_calibration", "f8", ("time",))
        ts.createVariable("polarization_calibration_error", "f8", ("time",))
        ts.createVariable("ELDECVersion", str, ("time",))
        ts.createVariable("SCCVersion", str, ("time",))


def append_to_history_file(path: Path, point: CalibrationPoint) -> None:
    """
    Add a point to a QC history file, creating the file if needed. A point with the same
    measurement ID is replaced.
    """

    path = Path(path)
    if not path.exists():
        create_history_file(path)

    with Dataset(path, "a") as ts:
        ids = [str(x) for x in ts["Measurement_ID"][:]]
        idx = (
            ids.index(point.measurement_id) if point.measurement_id in ids else len(ids)
        )

        ts["Measurement_ID"][idx] = point.measurement_id
        ts["polarization_calibration"][idx] = point.value
        ts["polarization_calibration_error"][idx] = point.error
        ts["calibration_range_min"][idx] = point.range_min
        ts["calibration_range_max"][idx] = point.range_max
        ts["date"][idx] = int((_utc(point.start_time) - EPOCH).total_seconds())
        ts["ELDECVersion"][idx] = point.eldec_version
        ts["SCCVersion"][idx] = point.scc_version
