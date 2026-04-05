Available Dictionaries
======================

liwca includes a registry of public LIWC-format dictionaries that can be
fetched and cached locally with :func:`~liwca.fetch_dx` or
:func:`~liwca.fetch_path`.

To list all available dictionaries:

.. code-block:: python

   import liwca
   liwca.list_available()
   # ['bigtwo_a', 'bigtwo_b', 'honor', 'mystical', 'sleep', 'threat']


Dictionary catalogue
--------------------

.. dict-catalogue::


Fetching dictionaries
---------------------

Use :func:`~liwca.fetch_dx` to download and load a dictionary as a
:class:`~pandas.DataFrame`:

.. code-block:: python

   dx = liwca.fetch_dx("threat")
   dx.head()

The file is downloaded once and cached locally via
`Pooch <https://www.fatiando.org/pooch/latest/>`_.

To get only the cached file path without loading:

.. code-block:: python

   fp = liwca.fetch_path("threat")


Cache location
~~~~~~~~~~~~~~

By default, files are cached in your OS data directory:

- **Linux:** ``~/.cache/liwca``
- **macOS:** ``~/Library/Caches/liwca``
- **Windows:** ``%LOCALAPPDATA%\liwca``

You can override this by setting the ``LIWCA_DATA_DIR`` environment variable
before importing liwca:

.. code-block:: bash

   export LIWCA_DATA_DIR=/path/to/my/cache
