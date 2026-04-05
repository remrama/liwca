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

1. **Add the registry entry.** Append a line to
   ``src/liwca/data/registry.txt`` with the format::

      filename.ext md5:<hash> <download_url>

   Compute the MD5 hash of the file (``md5sum filename.ext`` on Linux/macOS,
   or ``certutil -hashfile filename.ext MD5`` on Windows).

2. **If the file is ``.dic`` or ``.dicx``**, you are done — the standard
   readers will handle it automatically.

3. **If the file is a non-standard format** (TSV, Excel, plain text, etc.),
   add a reader function in ``src/liwca/_remoteprocessors.py``:

   .. code-block:: python

      def read_raw_mydict(fname: str) -> pd.DataFrame:
          """Read/parse the MyDict dictionary.

          Dictionary details
          ^^^^^^^^^^^^^^^^^^
          * **Name:** ``mydict``
          * **Language:** English
          * **Source:** https://example.com
          * **Citation:** `doi:... <https://doi.org/...>`_

          Parameters
          ----------
          fname : :class:`str`
              Path to the raw file.

          Returns
          -------
          :class:`pandas.DataFrame`
              Dictionary DataFrame with binary (0/1) values.
          """
          # Parse the file into a DataFrame with:
          #   - Index named "DicTerm" (string, lowercase)
          #   - Columns as category names
          #   - Values: 1 (term in category) or 0 (not)
          ...

   Then register it in the ``READERS`` dict at the bottom of the file:

   .. code-block:: python

      READERS = {
          ...
          "mydict": read_raw_mydict,
      }

4. **Add a test.** Add the new dictionary name to the parametrize list in
   ``tests/test_remote.py`` (it should already be picked up automatically
   via ``liwca.list_available()``).

5. **Document it.** Add an entry to the table in ``docs/dictionaries.rst``.
