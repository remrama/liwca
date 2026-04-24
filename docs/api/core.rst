.. _api-core:

Core
====

.. currentmodule:: liwca

Input/Output
------------

Reading, writing, and merging LIWC dictionaries.

.. autosummary::
   :toctree: ../_autosummary
   :nosignatures:

   create_dx
   read_dx
   write_dx
   merge_dx
   drop_category

LIWC-22 CLI
-----------

Python wrapper for the LIWC-22 command-line tool. All seven analysis
modes are exposed as methods on :class:`Liwc22`.

.. autoclass:: Liwc22
   :members: wc, freq, mem, context, arc, ct, lsm, __enter__, __exit__
   :member-order: bysource
   :show-inheritance:

Word Counting
-------------

Pure-Python LIWC-style word counting.

.. autosummary::
   :toctree: ../_autosummary
   :nosignatures:

   count

DDR Scoring
-----------

Distributed Dictionary Representation — semantic scoring via word embeddings.

.. autosummary::
   :toctree: ../_autosummary
   :nosignatures:

   ddr

Utility
-------

Miscellaneous utilities and helpers.

.. autosummary::
   :toctree: ../_autosummary
   :nosignatures:

   set_log_level
