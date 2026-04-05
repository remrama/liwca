liwca
=====

**liwca** is a Linguistic Inquiry Word Count Assistant — a Python helper
library for working with `LIWC <https://liwc.app>`_ dictionaries, running
word counts, and calling the LIWC-22 CLI from Python.

.. code-block:: bash

   pip install liwca

Features
--------

**Dictionary I/O** — Read, write, merge, and fetch LIWC dictionaries in
``.dic`` and ``.dicx`` formats. Several public dictionaries are available
through a built-in registry.

**Word Counting** — Pure-Python LIWC-style word counting powered by
scikit-learn. No LIWC-22 installation required. Supports wildcard
expansion against corpus vocabulary.

**LIWC-22 CLI Wrapper** — Call the LIWC-22 command-line tool directly from
Python or the terminal, with a data-driven argument interface.


.. code-block:: python

   import liwca

   dx = liwca.fetch_dx("threat")
   results = liwca.count(["danger lurks ahead"], dx)


.. toctree::
   :hidden:

   introduction
   guide
   dictionaries
   api
   contributing
