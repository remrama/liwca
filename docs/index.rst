liwca
=====

**liwca** is a Linguistic Inquiry Word Count Assistant — a Python helper
library for working with `LIWC <https://liwc.app>`_ dictionaries, running
word counts, and calling the LIWC-22 CLI from Python.

.. code-block:: bash

   pip install liwca

Features
--------

**I/O** — Read, write, and merge LIWC dictionary files in
``.dic`` and ``.dicx`` formats.

**LIWC-22 CLI Wrapper** — Call the LIWC-22 command-line tool directly from
Python or the terminal.

**Word Counting** — Pure-Python LIWC-style word counting powered by
scikit-learn. No LIWC-22 installation required.

**Fetch Dictionaries** — Download and cache public LIWC dictionaries on demand.


.. code-block:: python

   import liwca

   dx = liwca.fetch_threat()
   results = liwca.scikit(["danger lurks ahead"], dx)


.. toctree::
   :hidden:

   introduction
   guide
   api
   contributing
