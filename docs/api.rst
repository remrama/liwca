API Reference
=============

Dictionary I/O
--------------

Reading, writing, merging, and fetching LIWC dictionaries.

.. automodule:: liwca.io
   :members: read_dx, write_dx, merge_dx, fetch_dx, fetch_path, list_available


Word Counting
-------------

Pure-Python LIWC-style word counting.

.. automodule:: liwca.count
   :members: count


LIWC-22 CLI
------------

Python wrapper for the LIWC-22 command-line tool.

.. automodule:: liwca.liwc22
   :members: cli, main


Remote Dictionary Readers
-------------------------

Reader functions for non-standard remote dictionary formats.

.. automodule:: liwca._remoteprocessors
   :members: read_raw_sleep, read_raw_threat, read_raw_mystical
