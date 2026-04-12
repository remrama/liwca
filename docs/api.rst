.. currentmodule:: liwca

API Reference
=============

.. _api-io:

I/O
---

Reading, writing, and merging LIWC dictionaries.

.. autosummary::
   :toctree: _autosummary

   create_dx
   read_dx
   write_dx
   merge_dx
   drop_category


.. _api-liwc22:

LIWC-22 CLI
-----------

Python wrapper for the LIWC-22 command-line tool.

.. autosummary::
   :toctree: _autosummary

   liwc22


.. _api-count:

Word Counting
-------------

Pure-Python LIWC-style word counting.

.. autosummary::
   :toctree: _autosummary

   count


.. _api-ddr:

DDR Scoring
-----------

Distributed Dictionary Representation — semantic scoring via word embeddings.

.. autosummary::
   :toctree: _autosummary

   ddr


.. _api-fetchers:

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


.. _api-utility:

Utility
-------

Miscellaneous utilities and helpers.

.. autosummary::
   :toctree: _autosummary

   set_log_level
