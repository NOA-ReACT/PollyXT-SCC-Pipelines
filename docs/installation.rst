************
Installation
************

Install with pip
================

The project is available on PyPI so it can easily be installed using :code:`pip`:


.. code-block:: sh

  pip install pollyxt_pipelines


Afterwards, the :code:`pollyxt_pipelines` command should be available to use.


.. code-block:: sh

  pollyxt_pipelines --help



Anaconda
========

If you are using Anaconda to manage your Python packages, it is recommended to create
a new environment just for :code:`pollyxt_pipelines`. To create such an environment, run the following
commands in a terminal (or Anaconda Prompt):

.. code-block:: sh

  conda create -n pollyenv python=3.8
  conda activate pollyenv
  pip install pollyxt_pipelines

You can replace :code:`pollyenv` with a name of your choice.

.. caution::
  If you do not create a new environment, :code:`pip` could mess up the installed packages and ruin your setup. It's always
  better to utilize environments, as shown above.


If the installation succeeds, you should be able to use the application anytime by running:

.. code-block:: sh

  conda activate pollyenv
  pollyxt_pipelines # ...

