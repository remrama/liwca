---
name: add-dictionary
description: >
  Scaffolds a new public dictionary into the liwca registry.
  Edits registry.txt, fetchers.py, api.rst, test_fetchers.py, and test_remote.py.
  Use when a contributor wants to add a new remote dictionary.
argument-hint: "[dictionary-name]"
disable-model-invocation: true
---

# Add a new public dictionary to liwca

You are adding a new remote dictionary to the liwca project. The dictionary
name was optionally passed as: `$ARGUMENTS`

## Step 1 --- Gather information

Ask the user for the following. If `$ARGUMENTS` provides the name, skip that
question. Do NOT ask about file format, categories, or example terms --- you
will auto-detect those in Step 2.

1. **Name** --- short lowercase identifier (e.g., `threat`, `sleep`, `honor`).
   This becomes `fetch_<name>()`.
2. **Download URL** --- direct-download link to the dictionary file.
3. **Citation** --- author(s), year, title, journal, and DOI.
4. **Source page URL** --- landing page or repository where the dictionary is
   publicly available (for the `[2]` reference in the docstring).

## Step 2 --- Download, hash, and inspect

Download the file and compute its MD5 hash using pooch. Then inspect the file
to determine format, categories, and example terms.

```python
import pooch
path = pooch.retrieve("<URL>", known_hash=None)
md5 = "md5:" + pooch.file_hash(path, alg="md5")
print(md5)
```

After downloading, read and inspect the file to auto-detect:
- **File format and parsing approach** (from extension + content)
- **Category names** (from headers, columns, or structure)
- **3--5 example terms** for the integration test `_EXAMPLES` dict

For `.dic` and `.dicx` files, `read_dx()` handles parsing automatically.
For other formats, determine the correct pandas call and any cleanup needed.

## Step 3 --- Edit 5 files

All lists in the project are in **alphabetical order**. Insert new entries at
the correct position.

### 3a. `src/liwca/data/registry.txt`

Add a line in alphabetical order by filename:

```
<filename>.<ext> md5:<hash> <url>
```

### 3b. `src/liwca/fetchers.py`

**Add to `__all__`** --- insert `"fetch_<name>"` alphabetically.

**Add the fetch function** in alphabetical order among existing functions.

#### Template A: Standard `.dic` / `.dicx` file

```python
def fetch_<name>() -> pd.DataFrame:
    """
    Fetch the <human name> dictionary.

    Returns
    -------
    :class:`pandas.DataFrame`
        Dictionary with ``"cat_a"`` and ``"cat_b"`` categories.

    Notes
    -----
    The <human name> dictionary is described in <First Author> et al.\\ [1]_
    and publicly available on <Platform>\\ [2]_.

    References
    ----------
    .. [1] <Authors>, <Year>.
           <Title>.
           *<Journal>*
           doi:`<DOI_ID> <https://doi.org/<DOI_ID>>`__
    .. [2] `<SOURCE_URL> <<SOURCE_URL>>`__

    Examples
    --------
    >>> import liwca
    >>> dx = liwca.fetch_<name>()  # doctest: +SKIP
    """
    return read_dx(_pup.fetch("<filename>.<ext>"))
```

#### Template B: Non-standard file (xlsx, tsv, txt, etc.)

```python
def fetch_<name>() -> pd.DataFrame:
    """
    <SAME DOCSTRING STRUCTURE AS TEMPLATE A>
    """
    path = _pup.fetch("<filename>.<ext>")
    # ... custom parsing into a DataFrame with DicTerm index ...
    logger.debug("Read <name> dictionary: %d terms from %s", len(df), path)
    return dx_schema.validate(df)
```

The output DataFrame must have:
- Index named `"DicTerm"` (lowercase string terms)
- Columns named after categories, with int8 values of 0 or 1

Look at `fetch_mystical` (xlsx), `fetch_sleep` (tsv), and `fetch_threat`
(txt) in `src/liwca/fetchers.py` for concrete non-standard parsing examples.

### 3c. `docs/api.rst`

In the `.. autosummary::` block under `.. _api-fetchers:`, add
`fetch_<name>` alphabetically. Use 3 spaces of indentation.

### 3d. `tests/test_fetchers.py`

Two edits:

1. **`_FETCH_FUNCTIONS` list** --- add `liwca.fetch_<name>,` alphabetically.
2. **`TestRegistryIntegrity.test_all_filenames_registered`** --- add the
   filename string to the `expected` set. This is easy to miss!

If the function accepts parameters (like `fetch_bigtwo`'s `version`), add
specific parameter tests following the `test_fetch_bigtwo_*` pattern.

### 3e. `tests/test_remote.py`

1. **`_FETCH_FUNCTIONS` list** --- add `("<name>", liwca.fetch_<name>),`
   alphabetically.
2. **`_EXAMPLES` dict** --- add `"<name>": [<terms>],` using the example
   terms detected in Step 2.

## Step 4 --- Verify

Run and fix any issues:

```bash
uv run ruff check src/liwca/fetchers.py tests/test_fetchers.py tests/test_remote.py
uv run ruff format src/liwca/fetchers.py tests/test_fetchers.py tests/test_remote.py
uv run pytest tests/test_fetchers.py -x -q
```

Do NOT run `tests/test_remote.py` automatically --- it downloads real files.
Ask the user before running it.

## Checklist

Before finishing, confirm every item:

- [ ] `registry.txt` has the new line with correct md5 hash and URL
- [ ] `fetchers.py` --- function added to `__all__` alphabetically
- [ ] `fetchers.py` --- function defined with full NumPy docstring
- [ ] `api.rst` --- function listed in autosummary block
- [ ] `test_fetchers.py` --- function in `_FETCH_FUNCTIONS`
- [ ] `test_fetchers.py` --- filename in `test_all_filenames_registered` expected set
- [ ] `test_remote.py` --- `(name, function)` tuple in `_FETCH_FUNCTIONS`
- [ ] `test_remote.py` --- example terms in `_EXAMPLES`
- [ ] Ruff passes with no errors
- [ ] `pytest tests/test_fetchers.py` passes
