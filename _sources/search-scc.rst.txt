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
* :code:`--to-csv=`: Optionally store the results in a CSV file. This file can also be used with :code:`scc-download`


This command should output a table with all measurements for the given time period and the available products.




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