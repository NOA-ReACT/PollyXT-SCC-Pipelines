***********************
Manage SCC Measurements
***********************

The tool includes some commands for managing your measurements at the SCC.


Delete measurements
===================

You can delete measurements from SCC using the :code:`scc-delete` command as follows:

.. code-block:: sh

  pollyxt_pipelines scc-delete <id1> ... [<idN>]


.. danger::
  This command does NOT confirm your input. It will delete the IDs you give right
  away. Please always double-check what you type.


Re-run (re-process) measurements
================================

To ask SCC for a re-run of one or more measurement files, use the :code:`scc-rerun`
command:

.. code-block:: sh

  pollyxt_pipelines scc-rerun <id1> ... [<idN>]