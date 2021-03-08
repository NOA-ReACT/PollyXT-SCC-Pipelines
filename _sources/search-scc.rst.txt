***************************************
Searching and downloading historic data
***************************************

The commands :code:`scc-search` and :code:`scc-search-download` can be used to search and download
"old" processing results, without having to provide the measurement IDs yourself. You can use
:code:`scc-search` to see what is available and then use :code:`scc-search-download` to download
files of interest.



Searching
=========

.. code-block:: sh

  pollyxt_pipelines scc-search [--location [<...>]] [--to-csv <...>] <date-start> <date-end>

* :code:`date-start` :badge-blue:`required`: First day to search (inclusive)
* :code:`date-end` :badge-blue:`required`: Last day to search (exclusive)
* :code:`--location=`: Optionally filter by a measurement station
* :code:`--detailed-status`: Fetch processing status codes (eg. 127) for each product. This option **must** be used with :code:`--to-csv=`.
* :code:`--to-csv=`: Optionally store the results in a CSV file. This file can also be used with :code:`scc-download`


This command should output a table with all measurements for the given time period and the available products. When using
:code:`--detailed-status`, the resulting CSV will contain the processing status codes for each product. This option requires at least N
request for N measurements so it should be avoided if not required.

Sample CSV file (without :code:`--detailed-status`):

.. code-block:: csv
    id,station_id,location,date_start,date_end,date_creation,date_updated,hirelpp,cloudmask,elpp,elda,eldec,elic,elquick,is_processing
    20210307aky0930,Antikythera,aky,2021-03-07T09:30:00,2021-03-07T10:30:00,2021-03-07T13:46:00,2021-03-07T13:46:00,OK,OK,OK,ERROR,NO_RUN,NO_RUN,OK,OK
    20210307aky1030,Antikythera,aky,2021-03-07T10:30:00,2021-03-07T11:30:00,2021-03-07T13:46:00,2021-03-07T13:46:00,OK,OK,OK,ERROR,NO_RUN,NO_RUN,OK,OK
    20210307aky1130,Antikythera,aky,2021-03-07T11:30:00,2021-03-07T12:30:00,2021-03-07T13:46:00,2021-03-07T13:46:00,OK,OK,OK,ERROR,NO_RUN,NO_RUN,OK,OK


Sample CSV file (with :code:`--detailed-status`):

.. code-block:: csv
    station_id,location,date_start,date_end,date_creation,date_updated,upload,hirelpp,cloudmask,elpp,elic
    20210307aky0930,Antikythera,aky,2021-03-07T09:30:00,2021-03-07T10:30:00,2021-03-07T13:46:00,2021-03-07T13:46:00,127,127,127,-127,127
    20210307aky1030,Antikythera,aky,2021-03-07T10:30:00,2021-03-07T11:30:00,2021-03-07T13:46:00,2021-03-07T13:46:00,127,127,127,-127,127
    20210307aky1130,Antikythera,aky,2021-03-07T11:30:00,2021-03-07T12:30:00,2021-03-07T13:46:00,2021-03-07T13:46:00,127,127,127,-127,127


Downloading
===========

.. code-block:: sh

  pollyxt_pipelines scc-search-download [--location [<...>]] <date-start> <date-end>

* :code:`date-start` :badge-blue:`required`: First day to search (inclusive)
* :code:`date-end` :badge-blue:`required`: Last day to search (exclusive)
* :code:`--location=`: Optionally filter by a measurement station
* :code:`--no-hirelpp`: Do not download HiRELPP products
* :code:`--no-cloudmask`: Do not download cloudmask products
* :code:`--no-elpp`: Do not download ELPP files
* :code:`--no-optical`: Do not download optical (ELDA or ELDEC) files
* :code:`--no-elic`: Do not download ELIC files

By default, this command downloads all products but you can specifically excluse some using the
:code:`--no-*` options.



Examples
========

Search for all files between 2020-01-01 and 2020-02-01 from Finokalia.

.. code-block:: sh

  pollyxt_pipelines scc-search 2020-01-01 2020-02-01 --location=Finokalia

Download all files between 2020-10-07 and 2020-10-10 from all stations

.. code-block:: sh

  pollyxt_pipelines scc-search-download 2020-10-07 2020-10-10

Download all files, excluding optical products, between 2020-10-07 and 2020-10-10 from Antikythera:

.. code-block:: sh

  pollyxt_pipelines scc-search-download 2020-10-07 2020-10-10 --no-optical --location=Antikythera



API
===

All network-related operationg are handled by the :code:`pollyxt_pipelines.scc_access` module, which
has a :code:`SCC` class. For more information read the :doc:`Network API <network-api>` page.