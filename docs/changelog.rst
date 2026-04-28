.. _changelog:

Changelog
=========

Version 0.1.0
-------------

Released on: 2026/XX/XX

First public release of :bolditalic:`liwca`.

- Added :func:`liwca.datasets.dictionaries.fetch_scope` and
  :func:`liwca.datasets.dictionaries.fetch_psychnorms`: per-stem fetchers
  that slice a single column from the SCOPE / psychNorms metabase into a
  weighted ``.dicx`` dictionary. Companion helpers
  :func:`~liwca.datasets.dictionaries.list_scope_stems` and
  :func:`~liwca.datasets.dictionaries.list_psychnorms_stems` enumerate the
  available stems.
- **Breaking:** :func:`liwca.datasets.tables.fetch_scope` and
  :func:`liwca.datasets.tables.fetch_psychnorms` now return the
  column-classification *metadata* tables instead of the full word-level
  score matrices. For the score matrices, use the new per-stem fetchers
  in :mod:`liwca.datasets.dictionaries`.
