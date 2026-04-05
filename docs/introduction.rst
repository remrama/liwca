Introduction
============

Installation
------------

Install from PyPI::

   pip install --upgrade liwca

For development::

   git clone https://github.com/remrama/liwca.git
   cd liwca
   uv pip install -e ".[dev]"


Quickstart
----------

Reading and writing dictionaries
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import liwca

   # Read local dictionary files (.dic or .dicx)
   dx = liwca.read_dx("my_dictionary.dicx")

   # Fetch a public dictionary
   dx = liwca.fetch_dx("sleep")

   # Write to a different format
   liwca.write_dx(dx, "my_dictionary.dic")

   # Merge multiple dictionaries
   merged = liwca.merge_dx([dx_a, dx_b])


Counting words
~~~~~~~~~~~~~~

Pure-Python word counting, no LIWC-22 installation required.

.. code-block:: python

   import liwca

   dx = liwca.read_dx("my_dictionary.dicx")

   texts = ["I feel happy today", "This is a sad story"]
   results = liwca.count(texts, dx)  # proportions by default

   # Raw counts
   results = liwca.count(texts, dx, as_percentage=False)


CLI wrapper
~~~~~~~~~~~

Wraps ``liwc-22-cli`` for command-line analysis (requires LIWC-22).

.. code-block:: bash

   # Word count analysis
   liwca wc -i data.csv -o results.csv

   # Preview the command without executing
   liwca wc -i data.csv -o results.csv --dry-run
