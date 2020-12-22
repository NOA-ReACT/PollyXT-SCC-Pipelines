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
* **Total/Cross channels**: Four variables are available for setting the total/cross channel indices for 355nm and 532nm:
    #. For 355nm: :code:`total_channel_355_nm` and :code:`cross_channel_355_nm`.
    #. For 532nm: :code:`total_channel_532_nm` and :code:`cross_channel_532_nm`.
* **Calibration channels**: For both wavelengths, the channel IDs must be provided in the following order in :code:`calibration_355nm_channel_ids` and :code:`calibration_532nm_channel_ids` for each wavelength:
    #. :code:`plus_45_transmitted`
    #. :code:`plus_45_reflected`
    #. :code:`minus_45_transmitted`
    #. :code:`minus_45_reflected`

For the arrays, you can input values separated by commas (see example below). Currently, the application
has a built-in registry containing information about two stations, *Antikythera* and *Finokalia*.


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
  profile_name = ANTIKYTHERA
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
  total_channel_355_nm = 0
  cross_channel_355_nm = 1
  total_channel_532_nm = 4
  cross_channel_532_nm = 5
  calibration_355nm_channel_ids = 1236, 1266, 1267, 1268
  calibration_532nm_channel_ids = 1269, 1270, 1271, 1272

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