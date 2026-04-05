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

1. **Add a JSON entry.** Edit ``src/liwca/data/registry.json`` and add an
   entry. Compute the MD5 hash of the file (``md5sum filename.ext`` on
   Linux/macOS, or ``certutil -hashfile filename.ext MD5`` on Windows).

   For ``.dic`` or ``.dicx`` files (standard formats):

   .. code-block:: json

      "mydict": {
        "description": "My dictionary description.",
        "source_url": "https://example.com",
        "source_label": "Example",
        "citation": "doi:...",
        "citation_url": "https://doi.org/...",
        "filename": "mydict.dic",
        "hash": "md5:<hash>",
        "url": "https://example.com/download/mydict.dic"
      }

   For non-standard formats (TSV, Excel, plain text, etc.), also set the
   ``reader`` field to the name of a private reader function in
   ``src/liwca/_catalogue.py``:

   .. code-block:: json

      "mydict": {
        "description": "...",
        "reader": "_read_raw_mydict",
        "filename": "mydict.xlsx",
        "hash": "md5:<hash>",
        "url": "https://..."
      }

   Then add the reader function in ``_catalogue.py`` and register it in the
   ``_READERS`` dict.

2. **Tests and docs** are automatic — ``liwca.list_available()`` derives from
   the registry, and the dictionary table in the docs is auto-generated at
   build time.
