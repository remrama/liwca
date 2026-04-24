.. _guide-liwc22:

LIWC-22-cli wrapper
===================

Auto-open
---------

If LIWC-22 is installed, call it from Python through the
:class:`~liwca.Liwc22` class. The LIWC-22 desktop application (or
its license server) must be running when you call the CLI:

.. code-block:: python

   import pandas as pd

   liwc = liwca.Liwc22(encoding="utf-8", precision=4)
   df = pd.DataFrame({"doc_id": ["a", "b"], "text": ["...", "..."]})
   out_path = liwc.wc(
       input=df,  # DataFrame or path
       output="results.csv",
       row_id_indices=["doc_id"],
   )
   results = pd.read_csv(out_path, index_col=0)

Different modes
---------------

The ``input`` argument accepts either a filepath or a
:class:`pandas.DataFrame` - DataFrames are written to a temp CSV, fed to
``liwc-22-cli``, and cleaned up afterwards. Each mode method returns the
``output`` path on success (or ``None`` when ``dry_run=True``). For mode
``wc`` the output file is reshaped in place via ``wc_output_schema``:
``Row ID`` is renamed back to the source column name when
``row_id_indices`` is given, the constant ``Segment`` column is dropped
(or promoted to a second index level when segmentation is used), and the
column axis is named ``Category``.

Cross-cutting options (encoding, CSV formatting, URL handling, precision,
execution-control flags) are set once at construction. Each of the seven
mode methods - :meth:`~liwca.Liwc22.wc`,
:meth:`~liwca.Liwc22.freq`, :meth:`~liwca.Liwc22.mem`,
:meth:`~liwca.Liwc22.context`, :meth:`~liwca.Liwc22.arc`,
:meth:`~liwca.Liwc22.ct`, :meth:`~liwca.Liwc22.lsm` - then
takes only mode-specific kwargs.

Arguments
---------

Arguments are Pythonic: booleans for yes/no flags, iterables of strings for
comma-list args, and column references as either 0-based ``int`` or column
names (``str``, resolved against the input's header row):

.. code-block:: python

   liwc = liwca.Liwc22(count_urls=True, encoding="utf-8")
   liwc.wc(
       input="data.csv",
       output="results.csv",
       include_categories=["anger", "joy"],
   )
   liwc.lsm(
       input="chat.csv",
       output="lsm.csv",
       text_column="text",
       person_column="speaker",
       calculate_lsm=3,
       output_type=1,
   )

Pass ``auto_open=True`` to let liwca start and stop LIWC-22 automatically.
Use as a context manager to amortize the app-launch cost across multiple
calls:

.. code-block:: python

   with liwca.Liwc22(auto_open=True) as liwc:
       liwc.wc(input="data.csv", output="wc.csv")
       liwc.freq(input="data.csv", output="freq.csv", n_gram=2)

See the :ref:`API reference <api-liwc22>` for the full argument lists, and
the `LIWC CLI documentation <https://www.liwc.app/help/cli>`_ and
`Python CLI example <https://github.com/ryanboyd/liwc-22-cli-python/blob/main/LIWC-22-cli_Example.py>`_
for more details.
