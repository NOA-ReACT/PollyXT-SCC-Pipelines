*********************
Using as a library
*********************

Besides the command line, PollyXT-Pipelines can be used from Python. The functions on this
page are meant for programs that run in a fresh environment each time (e.g. a container),
work in time windows and keep their own state. None of them write anywhere except the paths
they are given.

All times are UTC. Functions accept naive datetimes (taken as UTC) or timezone-aware ones
(converted to UTC), and return timezone-aware UTC datetimes.


Locations
=========

.. code-block:: python

    from pathlib import Path
    from pollyxt_pipelines.locations import read_locations_file, read_locations

    # Only this file
    location = read_locations_file(Path("locations.ini"))["Antikythera"]

    # Built-in locations, then the config directories, then these files (later wins)
    locations = read_locations([Path("locations.ini")])

An invalid section raises :code:`InvalidLocationError` (a :code:`ValueError`) naming the file,
the section and the problem. Sections are never skipped.

:code:`locations.LOCATIONS` is still read at import from the built-in file and the config
directories, for the CLI.

The config directories can be replaced by a single directory with the
:code:`POLLYXT_PIPELINES_CONFIG_DIR` environment variable, e.g. to keep the config somewhere
writable in a container.


Converting one time window
==========================

.. code-block:: python

    from datetime import datetime
    from pollyxt_pipelines.enums import Atmosphere
    from pollyxt_pipelines.polly_to_scc.pollyxt import PollyXTRepository
    from pollyxt_pipelines.polly_to_scc.scc_netcdf import convert_window

    repo = PollyXTRepository(Path("raw/"), location)
    result = convert_window(
        repo,
        start=datetime(2026, 1, 1, 10),
        end=datetime(2026, 1, 1, 11),   # exclusive
        output_path=Path("out/"),
        location=location,
        atmosphere=Atmosphere.STANDARD_ATMOSPHERE,
    )

    if result.data and result.data.end - result.data.start >= timedelta(minutes=59):
        upload(result.data.path, result.data.configuration_id)
    for cal in result.calibrations:
        upload(cal.path, cal.configuration_id)   # cal.wavelength, cal.measurement_id
    for reason in result.skipped:
        log(reason)

The result is a :code:`WindowConversion` with:

* :code:`data`: an :code:`SCCFile` (kind, measurement ID, path, first and last measurement,
  configuration ID), or :code:`None` when the window has no measurements;
* :code:`calibrations`: one :code:`SCCFile` per wavelength for each calibration period that
  *starts* in the window;
* :code:`skipped`: readable reasons for calibration files that were not made.

Rules:

* The window may extend past the data on either side; it is clipped and does not raise.
* :code:`data.start`/:code:`data.end` are the first and last measurement (the start of the
  last 30 s profile), so a complete hour spans 59.5 minutes.
* A calibration period belongs to the window that contains its start, even if it ends after
  the window, and is made from the repository's data for the whole period. So each period is
  converted by exactly one window, as long as the repository has enough data after the
  window.
* A period is skipped when the repository's data ends during it, or when it begins at the
  repository's first measurement (its real start is unknown then). A wavelength that fails
  is skipped with a reason; the others are still made.
* Errors that make the whole window impossible (e.g. a corrupt input file) raise.


Measurement IDs
---------------

Measurement IDs and filenames depend only on the data and the location, never on when the
conversion ran, so converting a window again gives the same names.

* Data files: :code:`YYYYMMDD{scc_code}HHMM`, from the first measurement in the file. The
  file is :code:`{measurement_id}.nc`.
* Calibration files: :code:`YYYYMMDD{scc_code}HH` followed by :code:`35`, :code:`53` or
  :code:`10` for 355, 532 and 1064 nm, from the start of the calibration period. The file is
  :code:`calibration_YYYYMMDD{scc_code}HH_{wavelength}.nc`.

The two schemes can produce the same ID (e.g. a data file starting at HH:35 and the 355 nm
calibration of hour HH), and two calibration periods starting in the same hour share IDs.
This is how the scheme was designed and it is kept as it is.


Calibration QC
==============

The QC check is split into reading, checking and recording. The caller supplies the history
of earlier good calibrations and decides what to store:

.. code-block:: python

    from pollyxt_pipelines.qc_eldec.qc import (
        CalibrationPoint, check_calibrations, plot_calibration, read_eldec,
    )

    history = [CalibrationPoint.from_dict(d) for d in stored_metadata]
    eldecs = [read_eldec(p) for p in eldec_paths]       # one per wavelength
    results = check_calibrations(eldecs, history)

    if all(r.ok for r in results):
        store([r.point.to_dict() for r in results])      # JSON-safe
    else:
        for r in results:
            log(r.reasons)

    plot_calibration(eldecs[0], history, results[0], Path("plot.png"))

* Only history points with the same wavelength are used, and points with the same
  measurement ID are left out, so a calibration checked again does not count itself.
* All history is used by default; pass :code:`only_before=True` to use only calibrations
  before this one.
* The outlier check runs only with more than :code:`Thresholds.min_history_points` points;
  otherwise :code:`QCResult.outlier` is :code:`None`.
* :code:`check_calibrations` records nothing. Keep a calibration only if every wavelength
  passes.
* :code:`plot_calibration` uses matplotlib's Agg backend directly and needs no display.

To import the history files kept by the :code:`qc-eldec` command
(:code:`<location>_<wavelength>nm.nc` in the config directory), use
:code:`read_history_file(path)`.


SCC
===

* :code:`SCC.get_measurement(measurement_id)` returns :code:`None` when the measurement does
  not exist. Use it to check whether a file is already uploaded.
* :code:`SCC.wait_for_product(measurement_id, product="eldec", timeout=300, poll=30)` waits
  until the measurement is neither queued nor processing and returns it; check
  :code:`measurement.eldec.status`. Time spent queued or processing does not count towards
  the timeout.


Logging
=======

Library code logs through :code:`logging.getLogger(__name__)` (under the
:code:`pollyxt_pipelines` logger) and never prints. Configure logging in your program to
decide where messages go. The CLI shows them in the terminal through :code:`rich`.
