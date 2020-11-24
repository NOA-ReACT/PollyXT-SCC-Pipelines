***********
Network API
***********

All network operations are handled by the :code:`pollyxt_pipelines.scc_access` module and specifically,
the :code:`SCC` class. The code is based the work of Ioannis Binietoglou on
`SCC Access <https://repositories.imaa.cnr.it/public/scc_access>`_.

To programmatically access SCC, begin by importing :code:`pollyxt_pipelines.scc_access` and creating
a :code:`SCC_Credentials` object.

.. code-block:: python

  from pollyxt_pipelines.config import Config
  import pollyxt_pipelines.scc_access

  # TODO remove dependency on Config
  credentials = SCC_Credentials(Config())


Afterwards, you can access SCC as follows:

.. code-block:: python

  # As a context
  with scc_access.scc_session(credentials) as scc:
    # Do stuff with scc
    # ...
    scc.upload_file(...)

  # As a class
  scc = scc_access.SCC(credentials)
  scc.login()
  # ...


The context manager handles login/logout automatically. If you use the class yourself,
you should call :code:`login()` before attempting to call any other method.



API
===


.. automodule:: pollyxt_pipelines.scc_access
   :members:
   :show-inheritance:

Exceptions
----------
.. automodule:: pollyxt_pipelines.scc_access.exceptions
   :members:
   :show-inheritance:

Container types
---------------
.. automodule:: pollyxt_pipelines.scc_access.types
   :members:
   :show-inheritance: