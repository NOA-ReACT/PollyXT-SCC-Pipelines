*********
Locations
*********

In PollyXT-Pipelines, a :code:`Location` represents a station where PollyXT is, or was, hosted. It
contains the station's coordinates and the related IDs for SCC. Specifically, for each station we know:

* **Name**: Station Name
* **Profile name** (:code:`profile_name`): The name used by WRF for this location
* **SCC Station ID** (:code:`scc_code`): The station ID registered with SCC, it's used in measurement
  IDs (e.g. :code:`aky`).
* **Latitude/Longitude** (:code:`lat`, code:`lon`): The station coordinates
* **Altitude** (:code:`altiude`): The station's altitude
* **System ID** (:code:`system_id_day`, :code:`system_id_night`): The SCC Lidar configuration ID for
  daytime and nightime
* **Channel ID** (Array, :code:`channel_id`): Value for the :code:`channel_ID` SCC variable.
* **Background** (Array, :code:`background_low`, :code:`background_high`): Values for the
  :code:`Background_Low` and :code:`Background_High` SCC variables.
* **LR Input** (Array, :code:`lr_input`): Value for the :code:`LR_Input` SCC variable.

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
  altitude = 0.1
  system_id_day = 437
  system_id_night = 438
  channel_id = 493, 500, 497, 499, 494, 496, 498, 495, 501, 941, 940, 502
  background_low = 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
  background_high = 249, 249, 249, 249, 249, 249, 249, 249, 249, 249, 249, 249
  lr_input = 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1
  temperature = 20
  pressure = 1008

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