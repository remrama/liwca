.. currentmodule:: liwca

API Reference
=============

I/O
---

Reading, writing, and merging LIWC dictionaries.

.. autosummary::
   :toctree: _autosummary

   read_dx
   write_dx
   merge_dx


LIWC-22 CLI
-----------

Python wrapper for the LIWC-22 command-line tool.

.. autosummary::
   :toctree: _autosummary

   liwc22


Word Counting
-------------

Pure-Python LIWC-style word counting.

.. autosummary::
   :toctree: _autosummary

   scikit


Fetching Dictionaries
---------------------

Remote LIWC-format dictionaries, fetched on demand and cached locally.

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


.. autosummary::
   :toctree: _autosummary

   fetch_bigtwo
   fetch_honor
   fetch_mystical
   fetch_sleep
   fetch_threat


Utility
-------

Miscellaneous utilities and helpers.

.. autosummary::
   :toctree: _autosummary

   set_log_level
