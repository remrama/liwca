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
- **Breaking:** :class:`liwca.Liwc22` mode-method kwargs were renamed to be
  more pythonic and consistent with sklearn/pandas. The argument order in
  each mode method was also reorganised - identity (``dictionary``,
  ``text_columns``, ``id_columns``/``id_column``) comes first, behaviour
  knobs in the middle, output-shape near the end, and rare escape hatches
  (``text``, ``env_var``) at the tail. No deprecation aliases - update
  call sites directly.

  Cross-mode column selectors:

  * ``column_indices`` -> ``text_columns`` (wc/freq/mem/context/arc).
  * ``row_id_indices`` -> ``id_columns`` (wc).
  * ``index_of_id_column`` -> ``id_column`` (mem/context/arc).

  Mode-specific renames:

  * ``console_text`` -> ``text`` (wc).
  * ``environment_variable`` -> ``env_var`` (wc).
  * ``category_to_contextualize`` -> ``category`` (context).
  * ``words_to_contextualize`` -> ``words`` (context).
  * ``output_data_points`` -> ``include_data_points`` (arc).
  * ``mem_output_type`` -> ``dtm_format`` (mem).
  * ``expanded_output`` -> ``expanded`` (lsm).
  * ``regex_removal`` -> ``remove_regex`` (ct).
  * ``prune_threshold_value`` -> ``prune_threshold`` (freq/mem).
  * ``omit_speakers_num_turns`` -> ``min_turns`` (ct/lsm).
  * ``omit_speakers_word_count`` -> ``min_words`` (ct/lsm).
  * ``segments_number`` -> ``n_segments`` (arc).
  * ``n_gram`` -> ``ngram`` (freq/mem).
  * ``speaker_list`` -> ``speakers`` (ct).
  * ``url_regexp`` -> ``url_regex`` (constructor).

  Behavioural simplifications (rename + type change):

  * ``word_window_left`` and ``word_window_right`` collapsed into a single
    ``word_window: int | tuple[int, int]`` (context). An ``int`` applies
    to both sides; a ``(left, right)`` tuple sets them independently
    (default: ``3``).
  * ``calculate_lsm: int (1/2/3)`` -> ``level: Literal["person", "group",
    "both"]`` (lsm; default ``"both"``).
  * ``output_type: int (1/2)`` -> ``pairwise: bool`` (lsm; ``False`` =
    one-to-many, ``True`` = pairwise; default ``False``).
  * ``scaling_method: int (1/2)`` -> ``scaling: Literal["percent",
    "zscore"]`` (arc; default ``"percent"``).
