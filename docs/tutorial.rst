Tutorial
========

This tutorial walks through the core features of **liwca**: fetching
dictionaries, counting words, and working with dictionary files.


Fetching a public dictionary
----------------------------

Several public LIWC-format dictionaries are bundled in the liwca registry.
Use :func:`~liwca.fetch_dx` to download and cache one:

.. code-block:: python

   import liwca

   dx = liwca.fetch_dx("threat")
   print(dx.shape)          # (n_terms, n_categories)
   print(dx.columns.tolist())  # ['threat']
   dx.head()

Every dictionary is returned as a :class:`~pandas.DataFrame` with a binary
(0/1) matrix — rows are dictionary terms (index ``DicTerm``), columns are
categories.


Counting words in text
----------------------

:func:`~liwca.count` takes an iterable of documents and a dictionary
DataFrame, and returns a documents × categories table:

.. code-block:: python

   texts = [
       "The threat of danger loomed over the city",
       "It was a calm and peaceful morning",
   ]

   result = liwca.count(texts, dx)
   print(result)

By default, values are **proportions** (percentage of total words per
document).  Pass ``as_proportion=False`` for raw counts:

.. code-block:: python

   result = liwca.count(texts, dx, as_proportion=False)
   print(result)

The ``WC`` column always shows the total word count for each document,
regardless of how many words matched the dictionary.


Using a pandas Series
~~~~~~~~~~~~~~~~~~~~~

If your texts live in a :class:`~pandas.Series`, the index carries through:

.. code-block:: python

   import pandas as pd

   texts = pd.Series(
       ["The threat was real", "A sunny day"],
       index=["doc_a", "doc_b"],
   )
   result = liwca.count(texts, dx, as_proportion=False)
   print(result)


Reading and writing dictionary files
-------------------------------------

liwca supports both LIWC ``.dic`` and ``.dicx`` file formats:

.. code-block:: python

   # Read a local dictionary file
   dx = liwca.read_dx("path/to/my_dictionary.dicx")

   # Write to a different format
   liwca.write_dx(dx, "my_dictionary.dic")


Merging dictionaries
--------------------

Combine multiple dictionaries into one with :func:`~liwca.merge_dx`:

.. code-block:: python

   dx_sleep = liwca.fetch_dx("sleep")
   dx_threat = liwca.fetch_dx("threat")

   merged = liwca.merge_dx([dx_sleep, dx_threat])
   print(merged.columns.tolist())  # ['sleep', 'threat']

   # Now count with both dictionaries at once
   result = liwca.count(texts, merged)
   print(result)

Terms that appear in only one dictionary get ``0`` in the other's columns.


Using the LIWC-22 CLI wrapper
-----------------------------

If you have `LIWC-22 <https://liwc.app>`_ installed, liwca can call its CLI
directly — either from the command line or from Python:

.. code-block:: bash

   # Command line
   liwca wc -i data.csv -o results.csv

   # Preview without executing
   liwca wc -i data.csv -o results.csv --dry-run

.. code-block:: python

   # Python API
   liwca.cli("wc", input="data.csv", output="results.csv")

   # Dry run
   liwca.cli("wc", input="data.csv", output="results.csv", dry_run=True)
