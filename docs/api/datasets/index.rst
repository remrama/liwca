.. _api-datasets:

Datasets
========

.. currentmodule:: liwca.datasets

Remote LIWC-format dictionaries, published reference tables, and text
corpora, fetched on demand and cached locally.

Corpora
-------

Text corpora for LIWC analysis.

.. autosummary::

   corpora.fetch_autobiomemsim
   corpora.fetch_cmu_books
   corpora.fetch_cmu_movies
   corpora.fetch_hippocorpus
   corpora.fetch_liwc_demo_data
   corpora.fetch_sherlock
   corpora.fetch_rwritingprompts

Dictionaries
------------

LIWC-format dictionaries from published research.

.. autosummary::

   dictionaries.fetch_bigtwo
   dictionaries.fetch_honor
   dictionaries.fetch_mystical
   dictionaries.fetch_sleep
   dictionaries.fetch_threat

Tables
------

Reference tables and norms.

.. autosummary::

   tables.fetch_liwc2015norms
   tables.fetch_liwc22norms
   tables.fetch_psychnorms
   tables.fetch_scope

.. toctree::
   :hidden:

   corpora
   dictionaries
   tables
