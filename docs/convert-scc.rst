************************
Converting to SCC Format
************************

PollyXT netCDF files can be converted to SCC netCDF files using the :code:`create-scc`
command. It's sibling command, :code:`create-scc-batch`, has all the same functionality
but can work with whole directories of files.


Usage
=====

.. code-block:: sh

  pollyxt_pipelines create-scc [--interval <...>] [--round] [--no-radiosonde] [--no-calibration] <input> <location> <output-path>

* :code:`input` :badge-blue:`required`: Which PollyXT file to convert into SCC format. Must be in netCDF format.
* :code:`location` :badge-blue:`required`: Where did the Polly measurement take place (i.e. station name)
* :code:`output-path` :badge-blue:`required`: Directory to write the output files. It will be created if it does not exist
* :code:`--interval=`: Set the interval (in minutes), in which to split PollyXT files.
* :code:`--no-radiosonde`: Do not create sounding files
* :code:`--no-calibration`: Do not create calibration files


The files are by default split in 1 hour files when they are converted to SCC files.
This interval can be changed with the :code:`--interval=` option.

The location is required to determine the measurement ID, as well as the SCC system ID.



Sounding
========

By default, when a file is being converted to SCC format, the application will
also create the corresponding Sounding file by reading WRF profiles. You can set
the directory where the WRF files are:

.. code-block:: sh

  pollyxt_pipelines config wrf.path /path/to/wrf/data

The WRF files should be named :code:`LOCATION_DDMMYYYY`, for example,
:code:`ANTIKYTHERA_02102020`.

.. caution::
  If you do not set the path to the WRF files using :code:`pollyxt_pipelines config`
  the command will fail! If you do not have access to profile files and want to skip
  the creation of sounding files, use the :code:`--no-radiosonde` option.

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

If the PollyXT file contains data in one of the following periods, a calibration file
will be created:

- 02:31 to 02:41
- 17:31 to 17:41
- 21:31 to 21:41

During these time periods, the corresponding points in the output SCC file will
be set to :code:`NaN`. To disable the generation of calibration files (and :code:`NaN`),
use the :code:`--no-calibration` option.



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

  pollyxt_pipelines create-scc 2019_06_02_Sun_NOA_06_00_01.nc Antikythera ./scc_data --no-calibration --no-radiosonde


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