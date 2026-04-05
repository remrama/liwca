Available Dictionaries
======================

liwca includes a registry of public LIWC-format dictionaries. Each dictionary
has a dedicated ``fetch_*`` function that downloads the file on first use and
returns it as a :class:`~pandas.DataFrame`.

.. code-block:: python

   import liwca

   dx = liwca.fetch_threat()
   dx.head()

Downloaded files are cached locally via
`Pooch <https://www.fatiando.org/pooch/latest/>`_. By default, files are
cached in your OS data directory:

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
original authors.** Citations are listed in each function's API documentation:
see :doc:`api`.


Dictionary catalogue
--------------------

.. autosummary::

   ~liwca.fetch_bigtwo
   ~liwca.fetch_honor
   ~liwca.fetch_mystical
   ~liwca.fetch_sleep
   ~liwca.fetch_threat
