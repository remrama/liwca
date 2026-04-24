.. _guide-datasets:

Fetching datasets
=================

Fetching dictionaries
---------------------

Each registered dictionary has a dedicated ``fetch_*`` function that downloads
the file on first use and returns it as a :class:`~pandas.DataFrame`:

.. code-block:: python

   from liwca.datasets import dictionaries

   dx = dictionaries.fetch_threat()

See :ref:`api-datasets-dictionaries` for all available dictionaries and their options.

Download location
-----------------

Downloaded files are cached locally via
`Pooch <https://www.fatiando.org/pooch/latest/>`_. By default, each dataset
category caches into its own subfolder under your OS data directory
(e.g. ``.../liwca/dictionaries/``). You can override the cache root by
setting the ``LIWCA_DATA_DIR`` environment variable before importing
liwca - dictionaries are then cached in ``$LIWCA_DATA_DIR/dictionaries/``:

.. code-block:: bash

   export LIWCA_DATA_DIR=/path/to/my/cache

Fetching paths
--------------

In special cases, ...
