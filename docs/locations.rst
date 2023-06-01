*********
Locations
*********

In PollyXT-Pipelines, a :code:`Location` represents a station where PollyXT is, or was, hosted. It
contains the station's coordinates and the related IDs for SCC. Specifically, for each station we know:

.. caution::
  All variables are **required**.

* **Name**: Station Name
* **Profile name** (:code:`profile_name`): The name used by WRF for this location
* **SCC Station ID** (:code:`scc_code`): The station ID registered with SCC, it's used in measurement
  IDs (e.g. :code:`aky`).
* **Latitude/Longitude** (:code:`lat`, code:`lon`): The station coordinates
* **Altitude** (:code:`altitude_asl`): The station's altitude
* **System ID** (:code:`daytime_configuration`, :code:`nighttime_configuration`): The SCC Lidar configuration ID for
  daytime and nightime
* **Channel ID** (Array, :code:`channel_id`): Value for the :code:`channel_ID` SCC variable.
* **Background** (Array, :code:`background_low`, :code:`background_high`): Values for the
  :code:`Background_Low` and :code:`Background_High` SCC variables.
* **LR Input** (Array, :code:`lr_input`): Value for the :code:`LR_Input` SCC variable.
* **Temperature** (:code:`temperature`): Value for the :code:`Temperature_at_Lidar_Station` SCC variable
* **Pressure** (:code:`pressure`): Value for the :code:`Pressure_at_Lidar_Station` SCC variable
* **Zero state for depol_cal_angle** (:code:`depol_calibration_zero_state`): Value that is used to signify a normal measurement in the
  :code:`depol_cal_angle` PollyXT variable. This is used to distinguish between normal measurements and
  measurements that are used to calibrate the depolarization angle. If :code:`depol_cal_angle` is not
  equal to :code:`zero_state_depol_cal_angle`, the corresponding time period is assumed
  to be a calibration period.
* **Total/Cross channels**: Four variables are available for setting the total/cross channel indices in the PollyXT file for 355nm, 532nm and 1064nm:
    #. For 355nm: :code:`total_channel_355_nm_idx` and :code:`cross_channel_355_nm_idx`.
    #. For 532nm: :code:`total_channel_532_nm_idx` and :code:`cross_channel_532_nm_idx`.
    #. For 1064nm: :code:`total_channel_1064_nm_idx` and :code:`cross_channel_1064_nm_idx`.
* **Calibration channels**: For both wavelengths, the SCC channel IDs must be provided in the following order in :code:`calibration_355nm_total_channel_ids` and :code:`calibration_355nm_cross_channel_ids` (same for 532nm and/or 1064nm) for each wavelength:
    #. :code:`plus_45_transmitted`
    #. :code:`plus_45_reflected`
    #. :code:`minus_45_transmitted`
    #. :code:`minus_45_reflected`
* **Sounding provider** (:code:`sounding_provider`): Which provider to use for radiosonde files.
* **Sunrise time** (:code:`sunrise_time`): Adjustments for the sunrise time. Can either be a fixed time (:code:`HH:MM` format) or an offset from the astronomical (calculated) sunrise in either +MM (e.g., +17 for +17 minutes) or -MM.
* **Sunset time** (:code:`sunset_time`): Adjustments for the sunset time. Same format as sunrise time.

For the arrays, you can input values separated by commas (see example below). Currently, the application
has a built-in registry containing information about two stations, *Antikythera* and *Finokalia*.

For depolarization channels, any channel (e.g., 355nm) that is missing one of the required fields (e.g., :code:`total_channel_355_nm_idx`) will be ignored. That means, any channel without a complete description will be skipped during the creation of depolarization calibration files. If you find one channel is missing from your generated files, make sure all required variables are present here.


Printing known locations
------------------------

To print all locations the application knows about, you can use the :code:`locations-show` command. Adding the
:code:`--details` option will print all variables for each location, instead of just the names.

.. code-block:: sh

  pollyxt_pipelines locations-show
  pollyxt_pipelines locations-show --detail



Adding new locations
--------------------

A config file is used to add new locations to the application. It is stored in different locations, depending on the
operating system you are on:

* **Linux**: :code:`/etc/pollyxt_pipelines/locations.ini` (system-wide) and :code:`~/.config/pollyxt_pipelines/locations.ini` (user)
* **Windows**: :code:`%APPDATA%/PollyXT_Pipelines/pollyxt_pipelines.ini`

To print the path for your system, use the :code:`locations-path` command:

.. code-block:: sh

  pollyxt_pipelines locations-path
  pollyxt_pipelines locations-path --user # Print only the user's path

The file is ini-formatted, where each section is a station name. For example:

.. code-block:: ini

  [Antikythera]
  scc_code = aky
  lat = 23.3100
  lon = 35.8600
  altitude_asl = 0.1
  daytime_configuration = 437
  nighttime_configuration = 438
  channel_id = 493, 500, 497, 499, 494, 496, 498, 495, 501, 941, 940, 502
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
  calibration_355nm_total_channel_ids = 1266, 1268
  calibration_355nm_cross_channel_ids = 1236, 1267
  calibration_532nm_total_channel_ids = 1270, 1272
  calibration_532nm_cross_channel_ids = 1269, 1271
  profile_name = ANTIKYTHERA
  sounding_provider = noa_wrf

You can add more than one location in the same file. Verify that it worked by running :code:`pollyxt_pipelines locations-show --detail`
when you are done.

API
---

Locations are represented using :code:`NamedTuple` objects, you can add more in
:code:`pollyxt_pipelines.locations`. All known locations should be added in
the :code:`LOCATIONS` tuple. Some helper functions are also defined
to search stations by their name/IDs.

.. automodule:: pollyxt_pipelines.locations
   :members:
   :show-inheritance: