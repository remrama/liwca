"""
Reading, writing, and merging LIWC dictionary files (``.dic`` and ``.dicx``).

Dictionary File Formats
-----------------------
LIWC dictionaries map **terms** to one or more **categories**. Terms may include
a trailing wildcard (``*``) to match any token that starts with that prefix
(e.g., ``abandon*`` matches *abandoned*, *abandoning*, etc.). A single term can
belong to multiple categories.

**.dic format** - tab-delimited, used by LIWC desktop applications::

    %
    1\tCategoryA
    2\tCategoryB
    %
    term1\t1
    term2\t2
    term3\t1\t2

- Lines containing only ``%`` delimit the **header** (category definitions) from
  the **body** (term-category assignments).
- Header rows map an integer ID to a category name, separated by a tab.
- Body rows start with the term, followed by one or more category IDs (tab-separated).
- ``.dic`` is binary-only: a term either belongs to a category or doesn't.

**.dicx format** - CSV, used by LIWC-22 Dictionary Workbench. Two flavours::

    DicTerm,CategoryA,CategoryB        DicTerm,sentiment
    term1,X,                           great,0.9
    term2,,X                           awful,-0.7
    term3,X,X                          excellent,1.2

- *Binary* ``.dicx`` (left): cells are ``X`` (member) or empty (non-member).
- *Weighted* ``.dicx`` (right): cells are numeric weights (signed allowed,
  e.g. for sentiment lexicons like VADER).

API: six flat top-level reader/writer functions, no extension dispatch.
Pick the function whose name matches your file format AND value-type:
``read_dic`` / ``write_dic`` (binary, ``.dic``);
``read_dicx`` / ``write_dicx`` (binary, ``.dicx``);
``read_dicx_weighted`` / ``write_dicx_weighted`` (weighted, ``.dicx``).
Calling the wrong function for your data fails loudly with an error pointing
at the right one.
"""

import csv
import logging
import re
from pathlib import Path
from typing import Any, Union

import numpy as np
import pandas as pd
import pandera.pandas as pa

__all__ = [
    "create_dx",
    "drop_category",
    "dx_schema",
    "dx_weighted_schema",
    "merge_dx",
    "read_dic",
    "read_dicx",
    "read_dicx_weighted",
    "write_dic",
    "write_dicx",
    "write_dicx_weighted",
]


logger = logging.getLogger(__name__)


#######################################################################################
# Pandera schemas: binary dx_schema and weighted dx_weighted_schema
#######################################################################################

_dx_index = pa.Index(
    dtype="string",
    name="DicTerm",
    nullable=False,
    unique=True,
    ## Would like to use these, but bug in pandera prevents returning parsed index (Issue #1684)
    ## It applies the parsers, but does not return the parsed index.
    ## https://github.com/unionai-oss/pandera/issues/1684
    # parsers=[
    #     pa.Parser(lambda i: i.str.lower()),
    #     pa.Parser(lambda i: i.str.strip()),
    # ],
    checks=[
        pa.Check(lambda s: s.str.len() >= 1, name="Term length > 0"),
        pa.Check(lambda s: s.str.isupper().eq(False), name="No uppercase terms"),
    ],
)

_dx_shared_parsers = [
    pa.Parser(lambda df: df.rename_axis("DicTerm", axis=0), name="Name index 'DicTerm'"),
    pa.Parser(lambda df: df.rename_axis("Category", axis=1), name="Name columns 'Category'"),
    pa.Parser(lambda df: df.rename(index=str.lower), name="Lowercase index"),
    pa.Parser(lambda df: df.sort_index(axis=0), name="Sort index"),
    pa.Parser(lambda df: df.sort_index(axis=1), name="Sort columns"),
]

# Binary schema: int8 cells, must be 0 or 1, every term in at least one category.
dx_schema = pa.DataFrameSchema(
    name="LIWC dictionary DataFrame schema (binary)",
    description="Schema for binary (X/empty) LIWC dictionary DataFrames",
    columns={
        r"\S+": pa.Column(
            dtype="int8",
            regex=True,
            checks=[
                pa.Check.isin([0, 1]),
            ],
            required=True,
            nullable=False,
            description="Binary category membership (0 or 1).",
        ),
    },
    index=_dx_index,
    parsers=[
        *_dx_shared_parsers,
        # Binary-only: a row of all zeros is meaningless (term has no
        # categories) and gets dropped silently.
        pa.Parser(lambda df: df.loc[df.any(axis=1)], name="Drop terms with no categories"),
    ],
    strict=True,
    coerce=True,
    unique_column_names=True,
    checks=[
        pa.Check(lambda df: len(df) > 0, name="At least one term (row)"),
        pa.Check(lambda df: len(df.columns) > 0, name="At least one category (column)"),
        pa.Check(
            lambda df: df.any(axis=1).all(),
            name="Each term present in at least one category",
        ),
    ],
)

# Weighted schema: float64 cells, signed values allowed (VADER, valence norms).
# Note: no "drop terms with no categories" parser - a row of all zeros is
# meaningful for a weighted dict (term scored zero everywhere).
dx_weighted_schema = pa.DataFrameSchema(
    name="LIWC dictionary DataFrame schema (weighted)",
    description="Schema for weighted (numeric) LIWC dictionary DataFrames; signed values allowed",
    columns={
        r"\S+": pa.Column(
            dtype="float64",
            regex=True,
            checks=[],  # no value-range check; signed weights are valid
            required=True,
            nullable=False,
            description="Per-category weight (any real number).",
        ),
    },
    index=_dx_index,
    parsers=_dx_shared_parsers,
    strict=True,
    coerce=True,
    unique_column_names=True,
    checks=[
        pa.Check(lambda df: len(df) > 0, name="At least one term (row)"),
        pa.Check(lambda df: len(df.columns) > 0, name="At least one category (column)"),
    ],
)


#######################################################################################
# LIWC dictionary DataFrame creation
#######################################################################################


@pa.check_output(schema=dx_schema)
def create_dx(categories: dict[str, list[str]]) -> pd.DataFrame:
    """
    Create a binary dictionary DataFrame from a category-to-terms mapping.

    Parameters
    ----------
    categories : dict[str, list[str]]
        Mapping of category names to lists of dictionary terms.
        Terms may include LIWC-style wildcards (e.g., ``"abandon*"``).

    Returns
    -------
    :class:`pandas.DataFrame`
        Validated dictionary DataFrame with terms as rows and categories as
        columns (binary int8 values).

    Examples
    --------
    >>> import liwca
    >>> dx = liwca.create_dx(
    ...     {
    ...         "sports": ["baseball", "football", "hockey"],
    ...         "weather": ["rain*", "snow", "wind*"],
    ...     }
    ... )
    """
    all_terms = sorted({term for terms in categories.values() for term in terms})
    assert all(len(x) > 0 for x in all_terms)
    df = pd.DataFrame(0, index=pd.Index(all_terms, dtype="string"), columns=list(categories))
    for cat, terms in categories.items():
        df.loc[terms, cat] = 1
    return df


#######################################################################################
# LIWC dictionary file reading - six flat functions, one per (format, value-type)
#######################################################################################


@pa.check_output(schema=dx_schema)
def read_dic(fp: Union[str, Path], **kwargs: Any) -> pd.DataFrame:
    """
    Read a binary LIWC dictionary from a ``.dic`` file.

    The ``.dic`` format is binary-only by spec: there is no weighted variant.
    For weighted dictionaries see :func:`read_dicx_weighted`.

    Parameters
    ----------
    fp : :class:`str` or :class:`~pathlib.Path`
        Path to a ``.dic`` file.
    **kwargs : Any
        Forwarded to :func:`open` (e.g. ``encoding="latin-1"`` for legacy files).

    Returns
    -------
    :class:`pandas.DataFrame`
        Validated binary dictionary DataFrame (int8 cells, 0/1).
    """
    logger.info("Reading binary .dic from %s", fp)
    kwargs.setdefault("encoding", "utf-8")
    with open(fp, "rt", **kwargs) as f:
        data = f.read()

    # Use regex to get everything between the first and last '%' character (both start on new lines)
    m = re.match(r"^%.*?$(?P<header>.*)^%.*?(?P<body>.*)", data, flags=re.DOTALL | re.MULTILINE)
    if m is None:
        raise ValueError(
            f"Failed to parse .dic file '{fp}': expected '%' delimiters separating header and body."
        )
    header = m.group("header").strip()
    body = m.group("body").strip()
    cat_ids, cat_names = zip(*[row.split("\t") for row in header.split("\n")])
    id_to_name = dict(zip(cat_ids, cat_names))

    # Long→wide pivot via pd.crosstab. Each (term, cat_id) pair becomes a row;
    # crosstab counts them per (DicTerm, Category), giving a binary indicator
    # matrix. Reindex to preserve the column order from the header.
    records = [
        (term, id_to_name[cid])
        for row in body.split("\n")
        for term, *ids in [row.split("\t")]
        for cid in ids
    ]
    long_df = pd.DataFrame(records, columns=["DicTerm", "Category"])
    df = (
        pd.crosstab(long_df["DicTerm"], long_df["Category"])
        .astype("int8")
        .reindex(columns=list(cat_names), fill_value=0)
    )
    df.index = df.index.astype("string")
    return df


@pa.check_output(schema=dx_schema)
def read_dicx(fp: Union[str, Path], **kwargs: Any) -> pd.DataFrame:
    """
    Read a binary ``.dicx`` file.

    Cells must be either ``X`` (case-insensitive) or empty. Any other content
    -- including stray numerics like ``0.5`` or typos like ``Y`` -- raises a
    :class:`ValueError` with a hint pointing at :func:`read_dicx_weighted`.

    Parameters
    ----------
    fp : :class:`str` or :class:`~pathlib.Path`
        Path to a binary ``.dicx`` file.
    **kwargs : Any
        Forwarded to :func:`pandas.read_csv`.

    Returns
    -------
    :class:`pandas.DataFrame`
        Validated binary dictionary DataFrame (int8 cells, 0/1).
    """
    logger.info("Reading binary .dicx from %s", fp)
    kwargs.setdefault("index_col", "DicTerm")
    kwargs.setdefault("dtype", "string")
    # keep_default_na=False prevents pandas from coercing legitimate dictionary
    # terms like "na", "null", "n/a" into NaN (real-world hazard for some
    # non-English Hedonometer files).
    kwargs.setdefault("keep_default_na", False)
    df_str = (
        pd.read_csv(fp, **kwargs).rename_axis("Category", axis=1).apply(lambda c: c.str.strip())
    )
    if df_str.shape[1] == 0:
        raise ValueError(
            f"Dictionary file {fp} has no Category columns; "
            f"the file appears to contain only a `DicTerm` header (no terms or categories)."
        )
    cells = df_str.stack()
    invalid = ~cells.str.upper().isin({"X", ""})
    if invalid.any():
        bad_examples = sorted(set(cells[invalid].astype(str)))[:5]
        raise ValueError(
            f"Binary .dicx must contain only `X` or empty cells; "
            f"found non-binary values: {bad_examples}. "
            f"If this is a weighted dictionary, use `read_dicx_weighted` instead."
        )
    return (df_str.apply(lambda c: c.str.upper()) == "X").astype("int8")


@pa.check_output(schema=dx_weighted_schema)
def read_dicx_weighted(fp: Union[str, Path], **kwargs: Any) -> pd.DataFrame:
    """
    Read a weighted ``.dicx`` file.

    Cells must be numeric or empty (treated as ``0.0``). Any non-numeric
    content -- including the binary marker ``X`` -- raises a
    :class:`ValueError` with a hint pointing at :func:`read_dicx`.

    Parameters
    ----------
    fp : :class:`str` or :class:`~pathlib.Path`
        Path to a weighted ``.dicx`` file.
    **kwargs : Any
        Forwarded to :func:`pandas.read_csv`.

    Returns
    -------
    :class:`pandas.DataFrame`
        Validated weighted dictionary DataFrame (float64 cells; signed allowed).
    """
    logger.info("Reading weighted .dicx from %s", fp)
    kwargs.setdefault("index_col", "DicTerm")
    kwargs.setdefault("dtype", "string")
    # keep_default_na=False prevents pandas from coercing legitimate dictionary
    # terms like "na", "null", "n/a" into NaN. Empty cells stay as the empty
    # string, then we replace them with "0" before numeric coercion.
    kwargs.setdefault("keep_default_na", False)
    df_str = (
        pd.read_csv(fp, **kwargs)
        .rename_axis("Category", axis=1)
        .apply(lambda c: c.str.strip())
        .replace("", "0")
    )
    if df_str.shape[1] == 0:
        raise ValueError(
            f"Dictionary file {fp} has no Category columns; "
            f"the file appears to contain only a `DicTerm` header (no terms or categories)."
        )
    try:
        df = df_str.apply(pd.to_numeric).astype("float64")
    except ValueError as e:
        raise ValueError(
            f"Weighted .dicx must contain only numeric or empty cells; got: {e}. "
            f"If this is a binary dictionary, use `read_dicx` instead."
        ) from e
    return df


#######################################################################################
# LIWC dictionary file writing - six flat functions, one per (format, value-type)
#######################################################################################


@pa.check_input(schema=dx_schema)
def write_dic(dx: pd.DataFrame, fp: Union[str, Path]) -> None:
    """
    Write a binary dictionary to a ``.dic`` file.

    Parameters
    ----------
    dx : :class:`pandas.DataFrame`
        Binary dictionary DataFrame (int8 cells, 0/1).
    fp : :class:`str` or :class:`~pathlib.Path`
        Output ``.dic`` filepath.
    """
    logger.info("Writing binary .dic (%d terms, %d categories) to %s", len(dx), dx.shape[1], fp)
    with open(fp, "wt", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow("%")
        writer.writerows([i, col] for i, col in enumerate(dx.columns, 1))
        writer.writerow("%")
        writer.writerows(
            dx.apply(lambda row: [row.name] + (np.flatnonzero(row) + 1).tolist(), axis=1).tolist()
        )
    return None


@pa.check_input(schema=dx_schema)
def write_dicx(dx: pd.DataFrame, fp: Union[str, Path], **kwargs: Any) -> None:
    """
    Write a binary dictionary to a ``.dicx`` file.

    Cells are written as ``X`` (member) or empty (non-member).

    Parameters
    ----------
    dx : :class:`pandas.DataFrame`
        Binary dictionary DataFrame (int8 cells, 0/1).
    fp : :class:`str` or :class:`~pathlib.Path`
        Output ``.dicx`` filepath.
    **kwargs : Any
        Forwarded to :meth:`pandas.DataFrame.to_csv`.
    """
    logger.info("Writing binary .dicx (%d terms, %d categories) to %s", len(dx), dx.shape[1], fp)
    kwargs.setdefault("sep", ",")
    kwargs.setdefault("index", True)
    kwargs.setdefault("encoding", "utf-8")
    kwargs.setdefault("index_label", "DicTerm")
    kwargs.setdefault("lineterminator", "\n")
    dx.rename_axis(None, axis=1).replace({1: "X", 0: ""}).to_csv(fp, **kwargs)
    return None


@pa.check_input(schema=dx_weighted_schema)
def write_dicx_weighted(dx: pd.DataFrame, fp: Union[str, Path], **kwargs: Any) -> None:
    """
    Write a weighted dictionary to a ``.dicx`` file.

    Cells are written as their numeric values directly.

    Parameters
    ----------
    dx : :class:`pandas.DataFrame`
        Weighted dictionary DataFrame (float64 cells).
    fp : :class:`str` or :class:`~pathlib.Path`
        Output ``.dicx`` filepath.
    **kwargs : Any
        Forwarded to :meth:`pandas.DataFrame.to_csv`.
    """
    logger.info("Writing weighted .dicx (%d terms, %d categories) to %s", len(dx), dx.shape[1], fp)
    kwargs.setdefault("sep", ",")
    kwargs.setdefault("index", True)
    kwargs.setdefault("encoding", "utf-8")
    kwargs.setdefault("index_label", "DicTerm")
    kwargs.setdefault("lineterminator", "\n")
    dx.rename_axis(None, axis=1).to_csv(fp, **kwargs)
    return None


#######################################################################################
# DX DataFrame processing - dtype-dispatched validation (no fallback)
#######################################################################################


def drop_category(dx: pd.DataFrame, categories: Union[str, list[str]]) -> pd.DataFrame:
    """
    Remove one or more categories from a dictionary.

    For binary dicts, terms that no longer belong to any remaining category
    are dropped automatically (per ``dx_schema``'s "drop terms with no
    categories" parser). For weighted dicts, all terms are preserved (a row
    of zeros is meaningful in a weighted dict).

    Parameters
    ----------
    dx : :class:`pandas.DataFrame`
        A dictionary DataFrame. Either binary (all int8) or weighted
        (all float64). Mixed dtypes raise :class:`TypeError`.
    categories : :class:`str` or list of :class:`str`
        Category name(s) to remove.

    Returns
    -------
    :class:`pandas.DataFrame`
        A new dictionary DataFrame without the specified categories,
        validated against the schema matching the input dtype.

    Raises
    ------
    KeyError
        If any of the given category names are not present in *dx*.
    TypeError
        If *dx* has mixed dtypes (some int8, some float64).

    Examples
    --------
    >>> import liwca
    >>> dx = liwca.create_dx({"sports": ["baseball", "hockey"], "weather": ["rain*", "snow"]})
    >>> liwca.drop_category(dx, "weather")  # doctest: +SKIP
    Category  sports
    DicTerm
    baseball       1
    hockey         1
    """
    if isinstance(categories, str):
        categories = [categories]
    missing = sorted(set(categories) - set(dx.columns))
    if missing:
        raise KeyError(f"Categories not found in dictionary: {missing}")
    logger.info("Dropping %d categories from %d-category dictionary", len(categories), dx.shape[1])
    result = dx.drop(columns=categories)
    if (dx.dtypes == "int8").all():
        return dx_schema.validate(result)
    elif (dx.dtypes == "float64").all():
        return dx_weighted_schema.validate(result)
    else:
        raise TypeError(
            f"Dictionary must have all-int8 (binary) or all-float64 (weighted) "
            f"columns; got dtypes {set(dx.dtypes.astype(str))}."
        )


def merge_dx(*dxs: pd.DataFrame) -> pd.DataFrame:
    """
    Merge multiple dictionaries into a single dictionary.

    If any input is weighted (float64 columns), all inputs are promoted to
    float64 and the result is validated against ``dx_weighted_schema``.
    Otherwise the result is binary (int8) and validated against
    ``dx_schema``.

    Parameters
    ----------
    *dxs : :class:`pandas.DataFrame`
        Two or more dictionary DataFrames to merge.

    Returns
    -------
    :class:`pandas.DataFrame`
        The merged dictionary, validated against the appropriate schema
        (binary if all inputs are binary, weighted if any is weighted).

    Raises
    ------
    ValueError
        If fewer than two dictionaries are provided, or if any dictionaries
        share category names (columns).

    Examples
    --------
    >>> import liwca
    >>> dx_sleep = liwca.fetch_sleep()  # doctest: +SKIP
    >>> dx_threat = liwca.fetch_threat()  # doctest: +SKIP
    >>> merged = liwca.merge_dx(dx_sleep, dx_threat)  # doctest: +SKIP
    >>> merged.tail(3)  # doctest: +SKIP
    Category   sleep  threat
    DicTerm
    worse          0       1
    worst          0       1
    you awake      1       0
    """
    if len(dxs) < 2:
        raise ValueError(f"merge_dx requires at least 2 dictionaries, got {len(dxs)}.")

    # Check for overlapping categories across all pairs.
    all_cols: list[str] = []
    for dx in dxs:
        overlap = set(dx.columns) & set(all_cols)
        if overlap:
            raise ValueError(
                f"Dictionaries have overlapping categories: {sorted(overlap)}. "
                "Each dictionary must have unique category names."
            )
        all_cols.extend(dx.columns)

    _warn_wildcard_overlaps(dxs)

    logger.info("Merging %d dictionaries", len(dxs))
    has_weighted = any(d.dtypes.eq("float64").any() for d in dxs)
    if has_weighted:
        promoted = [d.astype("float64") for d in dxs]
        merged = pd.concat(promoted, axis=1, join="outer").fillna(0.0)
        return dx_weighted_schema.validate(merged)
    merged = pd.concat(dxs, axis=1, join="outer").fillna(0).astype("int8")
    return dx_schema.validate(merged)


def _warn_wildcard_overlaps(dxs: tuple[pd.DataFrame, ...]) -> None:
    """Check for wildcard patterns that match literal terms in other dictionaries.

    A wildcard like ``sleep*`` in dictionary A will match a literal term like
    ``sleeping`` in dictionary B during counting. This means ``sleeping`` would
    be counted in both categories, while other words matching ``sleep*``
    (e.g., ``sleepy``) would only be counted in A's category. This asymmetry
    can produce misleading results.

    Issues a :func:`warnings.warn` for each detected overlap.
    """
    import warnings

    for i, dx_a in enumerate(dxs):
        wildcards_a = [t for t in dx_a.index if t.endswith("*")]
        if not wildcards_a:
            continue
        for j, dx_b in enumerate(dxs):
            if i == j:
                continue
            terms_b = set(dx_b.index)
            for wc in wildcards_a:
                prefix = wc[:-1]
                matches = sorted(t for t in terms_b if t.startswith(prefix) and t != wc)
                if matches:
                    warnings.warn(
                        f"Wildcard '{wc}' (in dictionary {i + 1}) matches terms in "
                        f"dictionary {j + 1}: {matches}. During counting, these terms "
                        f"will be counted in both dictionaries' categories, while other "
                        f"words matching '{wc}' will only be counted in dictionary "
                        f"{i + 1}'s categories.",
                        stacklevel=3,
                    )
