Contributing
============

Development setup
-----------------

.. code-block:: bash

   git clone https://github.com/remrama/liwca.git
   cd liwca
   uv pip install -e ".[dev]"

Running tests, linting, and type checking:

.. code-block:: bash

   uv run pytest tests/ --cov=liwca --cov-report=term-missing
   uv run ruff check src/ tests/
   uv run ruff format src/ tests/
   uv run mypy


Code style
----------

- **Formatter/linter:** `Ruff <https://docs.astral.sh/ruff/>`_ — line length
  100, target Python 3.14, rules ``E, F, I, W, C90, NPY201``
- **Docstrings:** `NumPy convention <https://numpydoc.readthedocs.io/en/latest/format.html>`_
- **Formatting:** double quotes, LF line endings


Adding a new dictionary
-----------------------

To add a new publicly available dictionary to the registry:

1. **Add a fetch function.** Edit ``src/liwca/fetchers.py`` and add a
   ``fetch_<name>()`` function following the existing pattern. Include a NumPy
   docstring with a short summary, ``Returns``, ``Notes`` (with footnote
   references to the paper and source), ``References`` (numbered citations
   with doi links), and ``Examples``.

   For standard ``.dic`` or ``.dicx`` files:

   .. code-block:: python

      def fetch_mydict() -> pd.DataFrame:
          """
          Fetch the my dictionary dictionary.

          Returns
          -------
          :class:`pandas.DataFrame`
              Dictionary with ``"category_a"`` and ``"category_b"`` categories.

          Notes
          -----
          The my dictionary is described in Author et al.\\ [1]_
          and publicly available on Example Repository\\ [2]_.

          References
          ----------
          .. [1] Author et al., Year.
                 Title of the paper.
                 *Journal Name*
                 doi:`10.xxxx/example <https://doi.org/10.xxxx/example>`__
          .. [2] `https://example.com/download <https://example.com/download>`__

          Examples
          --------
          >>> import liwca
          >>> dx = liwca.fetch_mydict()  # doctest: +SKIP
          """
          return read_dx(_pup.fetch("mydict.dic"))

   For non-standard formats (TSV, Excel, plain text, etc.), add custom
   parsing inline in the function body and call ``dx_schema.validate(df)``
   before returning.

2. **Add to the registry.** Edit ``src/liwca/data/registry.txt`` and append
   a line with the filename, MD5 hash, and download URL:

   .. code-block:: text

      mydict.dic md5:<hash> https://example.com/download/mydict.dic

   Compute the MD5 hash of the file (``md5sum filename.ext`` on Linux/macOS,
   or ``certutil -hashfile filename.ext MD5`` on Windows).

3. **Export from the package.** Add ``fetch_<name>`` to ``__all__`` in
   ``src/liwca/fetchers.py`` and verify it is importable as
   ``liwca.fetch_<name>()``.

Sphinx picks up the new function automatically via ``autosummary``.
