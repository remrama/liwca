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
   corpora.fetch_cmu_book_summaries
   corpora.fetch_cmu_movie_summaries
   corpora.fetch_hippocorpus
   corpora.fetch_liwc22_demo_data
   corpora.fetch_reddit_short_stories
   corpora.fetch_sherlock
   corpora.fetch_tedtalks

Dictionaries
------------

LIWC-format dictionaries from published research. Most are binary (each
term either belongs to a category or doesn't); :func:`~liwca.datasets.dictionaries.fetch_wrad`
returns a weighted dictionary (referential-activity scores).

.. autosummary::

   dictionaries.fetch_bigtwo
   dictionaries.fetch_emfd
   dictionaries.fetch_empath
   dictionaries.fetch_honor
   dictionaries.fetch_leeq
   dictionaries.fetch_mystical
   dictionaries.fetch_sleep
   dictionaries.fetch_threat
   dictionaries.fetch_wrad

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
