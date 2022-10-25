************************
Converting to SCC Format
************************

PollyXT netCDF files can be converted to SCC netCDF files using the :code:`create-scc`
command. It can operate on single files or whole directories.


Usage
=====

.. code-block:: sh

  pollyxt_pipelines create-scc [--interval <...>] [--round] [--no-calibration] [--start-time <...>] <input> <location> <output-path>

* :code:`input` :badge-blue:`required`: Path to PollyXT NetCDF files. Can either be a single file or a directory
* :code:`--recursive`: If :code:`input` is a directory and this option is set, it will be searched recursively.
* :code:`location` :badge-blue:`required`: Where did the Polly measurement take place (i.e. station name)
* :code:`output-path` :badge-blue:`required`: **Directory** to write the output files. It will be created if it does not exist
* :code:`--interval=`: Set the interval (in minutes), in which to split PollyXT files.
* :code:`--atmosphere=`: Select what kind of atmosphere to use: standard (default), radiosonde, cloudnet, automatic
* :code:`--no-calibration`: Do not create calibration files
* :code:`--start-time`: When to start the first file (see below for format). If `end-hour` is defined, a file of the chosen length will be created. Otherwise the intervals will start from this time.
* :code:`--end-time`: In combination with :code:`--start-time`, you can also set the end time. For example, you could generate a file from
  09:42 up until 10:11. Cannot be used without :code:`--start-time`.
* :code:`--system-id-day=`: Optionally, override the system configuration ID used for morning measurements.
* :code:`--system-id-night=`: Optionally, override the system configuration ID used for night measurements.


The files are by default split in 1 hour files when they are converted to SCC files.
This interval can be changed with the :code:`--interval=` option.

The location is required to determine the measurement ID, as well as the SCC system ID.


Merging of raw files
====================

When passing a directory path to :code:`input`, the input files are automatically
merged if required by the output. Consider the following example:

- Two input files, one from 00:00 up until 05:45, and one from 05:45 up until 12:00.
- We want to generate hourly output files from 00:00 until 12:00.

The program will generate files as normal from 00:00 until 05:00. The file
corresponding to 05:00-06:00 will automatically use data from *both* input files.
The rest will continue normally, using data only from the second input file.


Selecting time range for output files
=====================================

By default, the first output file will start at the first available measurement of
the raw files and will end one interval (:code:`--interval=`) length afterwards. This will be repeated
until the application runs out of raw data. You can configure the time of the first output file using
:code:`--start-time=` with the following time formats:

* :code:`--start-time=XX:MM`: Start at the first hour which has :MM available. (e.g. XX:30)
* :code:`--start-time=HH:MM`: Start at the first available day, exactly at HH:MM (24-hour time, e.g. 14:30)
* :code:`--start-time=YYYY-mm-DD_HH:MM`: Start exactly at the given date and time, useful for when the input directory contains many days of measurements (e.g. 2019-12-04_14:30).

When using :code:`--start-time=`, instead of generating until you run out of intervals,
you can optionally use :code:`--end-time=` to set exactly where the output file should
start and end. When using both :code:`--start-time=` and :code:`--end-time=`, the
application will create only one file. The datetime formats are the same for both options.

Atmosphere
========

By default, when a file is being converted to SCC format, the generated file will have
:code:`Molecular_Calc` set to 4 in order to use standard atmosphere. You can select which
atmosphere you want to use using the :code:`--atmosphere=` option:

* :code:`standard` :badge-blue:`default`: Use standard atmosphere
* :code:`radiosonde`: Create and use a collocated sounding file
* :code:`cloudnet`: Use Cloudnet NWP
* :code:`automatic`: Let SCC decide

If radiosonde is picked, the application will also create the corresponding Sounding file by reading
WRF profiles. You can set the directory where the WRF files are:

.. code-block:: sh

  pollyxt_pipelines config wrf.path /path/to/wrf/data

The WRF files should be named :code:`LOCATION_DDMMYYYY`, for example,
:code:`ANTIKYTHERA_02102020`.

.. caution::
  If you do not set the path to the WRF files using :code:`pollyxt_pipelines config`
  the command will fail! If you do not have access to profile files and want to skip
  the creation of sounding files, use another atmosphere!

One sounding file will be created for each SCC file. For example, with
:code:`20201001aky01.nc`, a corresponding :code:`rs_20201001aky01.nc` will
be created.

.. attention::
  When an output file is longer than one hour (when using :code:`--interval=`), the
  corresponding sounding file will be created using data from the *first* hour of
  the output file. For example, a file start starts in 00:00 and ends in 03:00, will
  have a sounding file with data from 00:00.

  :badge:`todo`: Make this behaviour customizable



Calibration
===========

If the PollyXT files contain calibration data, determined by the value of :code:`depol_cal_angle`,
the application will create calibration files. The calibration filenames are prefixed
with :code:`calibration_` and are created in pairs, one for 355nm and one for 532nm.

Which channels are used from the PollyXT netCDF file and how they are mapped to
SCC channels is configured through the current :doc:`Location <location>`. The
following diagram shows how data is copied from the PollyXT file to the SCC-format
file (for 532nm, but the same procedure takes place for 355nm).

.. image:: figures/scc-calibration-rawdata.png

In the PollyXT file, :code:`depol_cal_angle` takes zero value during normal measurements
(configurable, shown as 0 in the figure) and a non-zero value during calibration.
Using the value of :code:`depol_cal_angle`, the application will determine which
data indices correspond to the +45° and -45° calibration cycles. The first two
+45° samples are discarded, as well as the last 3 -45° samples. The samples
between the +45° and -45° calibration cycles are discarded as well. Since SCC
has separate channels for the +45° and -45° calibration cycles, the data is
copied from two channels into four as shown in the figure (see colors).

The values for :code:`Raw_Data_Start_Time` and :code:`Raw_Data_Stop_Time` are
set as the start and end time of the calibration cycle. For example:

.. image:: figures/scc-calibration-times.png

During these time periods, the corresponding data points will not be copied to
the output file. To disable the generation of calibration files, use the
:code:`--no-calibration` option.


Examples
========

Convert one file from Antikythera to SCC format, hourly, and store the output inside
the :code:`scc_data` directory.

.. code-block:: sh

  pollyxt_pipelines create-scc 2019_06_02_Sun_NOA_06_00_01.nc Antikythera ./scc_data


Convert a whole directory of files from Finokalia to SCC format and store output inside
the :code:`scc_data` directory.

.. code-block:: sh

  pollyxt_pipelines create-scc-batch ./polly_data Finokalia ./scc_data


Convert one file from Antikythera to SCC format, 30-minute interval, no calibration and
no radiosonde files:

.. code-block:: sh

  pollyxt_pipelines create-scc 2019_06_02_Sun_NOA_06_00_01.nc Antikythera ./scc_data --no-calibration --no-radiosonde --interval=30


Create hourly files that start at 09:30 (assuming this time exists in the raw file):

.. code-block:: sh

  pollyxt_pipelines create-scc 2019_06_02_Sun_NOA_06_00_01.nc Antikythera ./scc_data --no-calibration --no-radiosonde --start-time=09:30


Create hourly files that start at the first available :30:

.. code-block:: sh

  pollyxt_pipelines create-scc 2019_06_02_Sun_NOA_06_00_01.nc Antikythera ./scc_data --no-calibration --no-radiosonde --start-time=XX:30


Create hourly files that start at exactly 10:30 and override configuration ID to be 123. Do not use radiosondes and do not generate calibration files.

.. code-block:: sh

  pollyxt_pipelines create-scc 2019_06_02_Sun_NOA_06_00_01.nc Antikythera ./scc_data --no-calibration --no-radiosonde --start-time=10:30 --system-id-day=123 --system-id-night=123


Create one file that start at 09:30 and ends at 12:34 (assuming this time exists in the raw file):

.. code-block:: sh

  pollyxt_pipelines create-scc 2019_06_02_Sun_NOA_06_00_01.nc Antikythera ./scc_data --start-time=09:30 --end-time=12:34


API
===

PollyXT files are read using the :code:`PollyXTFile` class from the
:code:`pollyxt_pipelines.polly_to_scc.pollyxt` module, which opens the netCDF files,
loads all the required variables into members and closes the file. Processing methods
are inside :code:`pollyxt_pipelines.polly_to_scc.scc_netcdf`, they mostly accept
:code:`PollyXTFile`.


PollyXT file related routines
-----------------------------
.. automodule:: pollyxt_pipelines.polly_to_scc.pollyxt
   :members:
   :show-inheritance:


SCC file related routines
-------------------------
.. automodule:: pollyxt_pipelines.polly_to_scc.scc_netcdf
   :members:
   :show-inheritance: