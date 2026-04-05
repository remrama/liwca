Available Dictionaries
======================

liwca includes a registry of public LIWC-format dictionaries that can be
fetched and cached locally with :func:`~liwca.fetch_dx` or
:func:`~liwca.fetch_path`.

To list all available dictionaries:

.. code-block:: python

   import liwca
   liwca.list_available()
   # ['bigtwo', 'honor', 'mystical', 'sleep', 'threat']


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

By default, files are cached in your OS data directory:

- **Linux:** ``~/.cache/liwca``
- **macOS:** ``~/Library/Caches/liwca``
- **Windows:** ``%LOCALAPPDATA%\liwca``

You can override this by setting the ``LIWCA_DATA_DIR`` environment variable
before importing liwca:

.. code-block:: bash

   export LIWCA_DATA_DIR=/path/to/my/cache


Citing dictionaries
-------------------

These dictionaries were created by independent research groups and shared
publicly for reuse. **If you use a dictionary in your work, please cite the
original authors.** Each dictionary entry below includes the citation(s) you
should use. You can also access citations programmatically:

.. code-block:: python

   info = liwca.get_dict_info("threat")
   for cite in info.citations:
       print(cite)


Dictionary catalogue
--------------------

.. dict-catalogue::
