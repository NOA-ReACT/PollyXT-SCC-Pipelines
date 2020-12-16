***********************
Manage SCC Measurements
***********************

The tool includes some commands for managing your measurements at the SCC. Right
now, it can delete measurements from SCC:

.. code-block:: sh

  pollyxt_pipelines scc-delete <id1> ... [<idN>]


.. danger::
  This command does NOT confirm your input. It will delete the IDs you give right
  away. Please always double-check what you type.