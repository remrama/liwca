.. _guide-intro:

Getting Started
===============

Installation
------------

.. code-block:: bash

   pip install --upgrade liwca

Counting words
--------------

:func:`~liwca.count` takes texts and a dictionary DataFrame, and returns a
documents x categories table:

.. code-block:: python

   texts = ["The threat of danger loomed over the city", "A calm morning"]
   results = liwca.count(texts, dx)

Values are percentages of total words per document by default. See
:func:`~liwca.count` for options including raw counts and custom tokenizers.

Reading and writing local files
--------------------------------

.. code-block:: python

   dx = liwca.read_dx("my_dictionary.dicx")   # auto-detects .dic or .dicx
   liwca.write_dx(dx, "my_dictionary.dic")
   merged = liwca.merge_dx(dx_a, dx_b)
