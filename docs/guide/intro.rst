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

Values are **proportions**: per-document, the sum of matched contributions
divided by total word count. For binary dictionaries this is the fraction
of doc tokens in each category (in ``[0, 1]``). For weighted dictionaries
it is the per-token mean weight (e.g., mean sentiment per word for a
VADER-style lexicon). See :func:`~liwca.count` for options including
``precision`` rounding and custom tokenizers.

Reading and writing local files
--------------------------------

There are six top-level reader/writer functions, each named for the file
format **and** value-type. Pick the function whose name matches your data;
calling the wrong one fails loudly:

.. code-block:: python

   # Binary dictionaries
   dx = liwca.read_dic("my_dictionary.dic")
   dx = liwca.read_dicx("my_dictionary.dicx")
   liwca.write_dic(dx, "out.dic")
   liwca.write_dicx(dx, "out.dicx")

   # Weighted (numeric) dictionaries -- e.g. VADER, valence lexicons
   dx = liwca.read_dicx_weighted("vader.dicx")
   liwca.write_dicx_weighted(dx, "out.dicx")

   # Combine and prune
   merged = liwca.merge_dx(dx_a, dx_b)        # mixing binary + weighted promotes to float
   trimmed = liwca.drop_category(dx, "Football")

The classic ``.dic`` format has no weighted variant by spec, so there is
no ``read_dic_weighted`` / ``write_dic_weighted``.
