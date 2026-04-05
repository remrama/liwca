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

2. **Add a catalogue entry.** Add an entry to the ``CATALOGUE`` dict in
   ``src/liwca/_catalogue.py``:

   .. code-block:: python

      "mydict": DictInfo(
          description="My dictionary description.",
          format=".dic",
          source_url="https://example.com",
          source_label="Example",
          citation="doi:...",
          citation_url="https://doi.org/...",
      ),

   If the file is ``.dic`` or ``.dicx``, that is all you need — the standard
   readers handle it automatically. For non-standard formats (TSV, Excel,
   plain text, etc.), add a private reader function in the same file and
   reference it via the ``reader`` field:

   .. code-block:: python

      "mydict": DictInfo(
          ...
          reader=_read_raw_mydict,
      ),

3. **Tests and docs** are automatic — ``liwca.list_available()`` derives from
   the catalogue, and the dictionary table in the docs is auto-generated from
   ``CATALOGUE`` at build time.
