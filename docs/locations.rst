*********
Locations
*********

In PollyXT-Pipelines, a :code:`Location` represents a station where PollyXT is, or was, hosted. It
contains the station's coordinates and the related IDs for SCC. Specifically, for each station we know:

* **Name**: Station Name
* **Profile name**: The name used by WRF for this location
* **SCC Station ID**: The station ID registered with SCC, it's used in measurement IDs (e.g. :code:`aky`).
* **Latitude/Longitude**: The station coordinates
* **Altitude**: The station's altitude
* **System ID**: The SCC Lidar configuration ID for daytime and nightime

Currently, the application knows about *Antikythera* and *Finokalia*.



API
---

Locations are represented using :code:`NamedTuple` objects, you can add more in
:code:`pollyxt_pipelines.locations`. All known locations should be added in
the :code:`LOCATIONS` tuple. Some helper functions are also defined
to search stations by their name/IDs.

.. automodule:: pollyxt_pipelines.locations
   :members:
   :show-inheritance: