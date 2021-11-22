**************
Calibration QC
**************

PollyXT-Pipelines contains routines for checking the quality of the system calibration by looking at the ELDEC output files. Specifically, the :code:`qc-eldec` command can read such ELDEC files and check whether the calibration is OK by the following criteria:

* is relative error of the gain factor below threshold?
* is relative standard deviation of ratio profiles below threshold?
* is there an overlap between uncertainty range of gain factor and standard deviation of time series * factor ?

The command stores previous calibrations (per-location) so they can be compared and used for the last criteria. The results are optionally plotted.

The history files are stored at the config directory. For Linux, that should be `~/.config/pollyxt_pipelines/` and for Windows `%APPDATA%/PollyXT_Pipelines/`.


Usage
=====

.. code-block:: sh

  pollyxt_pipelines qc-eldec <input> <location> [<plot>]

* :code:`input` :badge-blue:`required`: Path to the ELDEC NetCDF file
* :code:`location` :badge-blue:`required`: Station name. Used to store past calibrations.
* :code:`plot`: Optionally, a path to store the depol. calibration plot.


To delete the history of calibrations, the following command can be used:

.. code-block:: sh

    pollyxt_pipelines qc-eldec-delete-history