**************
Authentication
**************

To access the online features of SCC (upload/query/download), you must be authenticated using
your SCC credentials. There are two pairs of credentials:

* HTTP Login: The credentials for the first login when you access https://scc.imaa.cnr.it/
* Account Login: The credentials for the login menu, top right of the homepage

You need to provide both for the application to work. You can set them using the :code:`login` command:

.. code-block:: sh
  pollyxt_pipelines login


.. danger::
  The application config is stored in :code:`%APPDATA%/PollyXT_Pipelines/pollyxt_pipelines.ini` if
  you are on Windows and in :code:`~/.config/pollyxt_pipelines.ini` if you are on Linux. Please think
  of the security implications of this, since thee passwords are stored in **plain-text**. Make sure
  no one else has access to these files.