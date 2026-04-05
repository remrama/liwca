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


Word Counting
-------------

Pure-Python LIWC-style word counting.

.. autosummary::
   :toctree: _autosummary

   scikit


LIWC-22 CLI
-----------

Python wrapper for the LIWC-22 command-line tool.

.. autosummary::
   :toctree: _autosummary

   liwc22


Fetching Dictionaries
---------------------

Remote LIWC-format dictionaries, fetched on demand and cached locally.

.. autosummary::
   :toctree: _autosummary

   fetch_bigtwo
   fetch_honor
   fetch_mystical
   fetch_sleep
   fetch_threat


Miscellaneous
-------------

Miscellaneous utilities and helpers.

.. autosummary::
   :toctree: _autosummary

   set_log_level
