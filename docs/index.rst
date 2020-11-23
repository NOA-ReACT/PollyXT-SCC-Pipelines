PollyXT-Pipelines's documentation
=============================================

PollyXT-Pipelines is a tool and a library for processing PollyXT files, mainly related to the integration
with `Single Calculus Chain (SCC) <https://www.earlinet.org/index.php?id=281>`_. It currently supports
the following features:

* Conversion of PollyXT files to SCC format
* Create Sounding files from WRF profiles
* Batch upload to SCC for processing
* Batch download of products, both for new files and by date range

To get started, read the :doc:`Installation guide <installation>`. For users of Windows and Anaconda, there is
also a specific, more detailed guide available. You can also read the :doc:`Usage Overview <usage>` to get a sense
of the features and capabilities.

.. note::
   Both the project and the documentation are under continuous work! Please report any issues and/or
   suggestions at the `Github <https://github.com/NOA-ReACT/PollyXT-SCC-Pipelines>`_ repository!


User Guide
=================
.. toctree::
   :maxdepth: 3

   installation
   usage
   locations
   convert-scc
   auth
   scc-upload-download
   search-scc
   network-api