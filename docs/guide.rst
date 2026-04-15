Getting Started
===============

Installation
------------

.. code-block:: bash

   pip install --upgrade liwca

For development:

.. code-block:: bash

   git clone https://github.com/remrama/liwca.git
   cd liwca
   uv pip install -e ".[dev]"


Fetching dictionaries
---------------------

Each registered dictionary has a dedicated ``fetch_*`` function that downloads
the file on first use and returns it as a :class:`~pandas.DataFrame`:

.. code-block:: python

   import liwca

   dx = liwca.fetch_threat()

See :ref:`api-fetchers` for all available dictionaries and their options.

Downloaded files are cached locally via
`Pooch <https://www.fatiando.org/pooch/latest/>`_. By default, files are
cached in your OS data directory. You can override this by setting the ``LIWCA_DATA_DIR`` environment variable
before importing liwca:

.. code-block:: bash

   export LIWCA_DATA_DIR=/path/to/my/cache


Counting words
--------------

:func:`~liwca.count` takes texts and a dictionary DataFrame, and returns a
documents × categories table:

.. code-block:: python

   texts = ["The threat of danger loomed over the city", "A calm morning"]
   results = liwca.count(texts, dx)

Values are percentages of total words per document by default. See
:func:`~liwca.count` for options including raw counts and custom tokenizers.


DDR (semantic scoring)
----------------------

:func:`~liwca.ddr` scores texts against dictionary categories using cosine
similarity in embedding space, following the Distributed Dictionary
Representation method (Garten et al., 2018).  This captures semantic proximity
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

If LIWC-22 is installed, call it from Python. The LIWC-22 desktop application
(or its license server) must be running when you call the CLI:

.. code-block:: python

   liwca.liwc22.wc(input="data.csv", output="results.csv")

There is one function per analysis mode: :func:`~liwca.liwc22.wc`,
:func:`~liwca.liwc22.freq`, :func:`~liwca.liwc22.mem`,
:func:`~liwca.liwc22.context`, :func:`~liwca.liwc22.arc`,
:func:`~liwca.liwc22.ct`, :func:`~liwca.liwc22.lsm`. Pass
``auto_open=True`` to let liwca start and stop LIWC-22 automatically.

See the :ref:`API reference <api-liwc22>` for each mode's full argument
list, and the
`LIWC CLI documentation <https://www.liwc.app/help/cli>`_ and
`Python CLI example <https://github.com/ryanboyd/liwc-22-cli-python/blob/main/LIWC-22-cli_Example.py>`_
for more details.
