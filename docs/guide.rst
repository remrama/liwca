.. _guide:

Guide
=====

Installation
------------

.. code-block:: bash

   pip install --upgrade liwca


Fetching dictionaries
---------------------

Each registered dictionary has a dedicated ``fetch_*`` function that downloads
the file on first use and returns it as a :class:`~pandas.DataFrame`:

.. code-block:: python

   from liwca.datasets import dictionaries

   dx = dictionaries.fetch_threat()

See :ref:`api-dictionaries` for all available dictionaries and their options.

Downloaded files are cached locally via
`Pooch <https://www.fatiando.org/pooch/latest/>`_. By default, each dataset
category caches into its own subfolder under your OS data directory
(e.g. ``.../liwca/dictionaries/``). You can override the cache root by
setting the ``LIWCA_DATA_DIR`` environment variable before importing
liwca - dictionaries are then cached in ``$LIWCA_DATA_DIR/dictionaries/``:

.. code-block:: bash

   export LIWCA_DATA_DIR=/path/to/my/cache


Counting words
--------------

:func:`~liwca.count` takes texts and a dictionary DataFrame, and returns a
documents x categories table:

.. code-block:: python

   texts = ["The threat of danger loomed over the city", "A calm morning"]
   results = liwca.count(texts, dx)

Values are percentages of total words per document by default. See
:func:`~liwca.count` for options including raw counts and custom tokenizers.


Distributed Dictionary Representation
-------------------------------------

:func:`~liwca.ddr` performs semantic scoring of texts against dictionary categories
using cosine similarity in embedding space, following the Distributed Dictionary
Representation (DDR) method (Garten et al., 2018). This captures semantic proximity
even when exact dictionary words are absent from the text.

Pass a gensim model name to automatically download embeddings (requires
``pip install liwca[ddr]``):

.. code-block:: python

   results = liwca.ddr(texts, dx, "glove-wiki-gigaword-100")

Or bring your own embeddings as a dict-like mapping:

.. code-block:: python

   results = liwca.ddr(texts, dx, my_embeddings)

Values are cosine similarities in [-1, 1].  See :func:`~liwca.ddr` for full
parameter details.


Reading and writing local files
--------------------------------

.. code-block:: python

   dx = liwca.read_dx("my_dictionary.dicx")   # auto-detects .dic or .dicx
   liwca.write_dx(dx, "my_dictionary.dic")
   merged = liwca.merge_dx(dx_a, dx_b)


LIWC-22 wrapper
---------------

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
