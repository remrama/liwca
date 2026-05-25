.. _api-core:

Core
====

.. currentmodule:: liwca

.. _api-io:

Input/Output
------------

Reading, writing, creating, and merging LIWC dictionaries. Each reader and
writer commits to one file format **and** one value-type; the caller picks
the function whose name matches the data. Two schemas validate each shape:
:data:`dx_schema` for binary dictionaries and :data:`dx_weighted_schema`
for weighted dictionaries (signed values allowed, e.g. for sentiment
lexicons like VADER).

.. autosummary::
   :toctree: ../_autosummary
   :nosignatures:

   create_dx
   read_dic
   read_dicx
   read_dicx_weighted
   write_dic
   write_dicx
   write_dicx_weighted
   merge_dx
   drop_category
   dx_schema
   dx_weighted_schema

.. _api-liwc22:

LIWC-22 CLI
-----------

Python wrapper for the LIWC-22 command-line tool. All seven analysis
modes are exposed as methods on :class:`Liwc22`.

.. autosummary::
   :toctree: ../_autosummary
   :nosignatures:

   Liwc22

.. _api-counting:

Word Counting
-------------

Pure-Python LIWC-style word counting.

.. autosummary::
   :toctree: ../_autosummary
   :nosignatures:

   count

.. _api-ddr:

DDR Scoring
-----------

Distributed Dictionary Representation — semantic scoring via word embeddings.

.. autosummary::
   :toctree: ../_autosummary
   :nosignatures:

   ddr

.. _api-utility:

Utility
-------

Miscellaneous utilities and helpers.

.. autosummary::
   :toctree: ../_autosummary
   :nosignatures:

   set_log_level
