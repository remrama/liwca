"""
Reading, writing, and merging LIWC dictionary files (``.dic`` and ``.dicx``).
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
    "merge_dx",
    "read_dx",
    "write_dx",
]


logger = logging.getLogger(__name__)


#######################################################################################
# Pandera shemas for pandas parsing (processing) and validation (checking)
#######################################################################################

# Schema to validate LIWC dictionary pandas DataFrames
dx_schema = pa.DataFrameSchema(
    name="LIWC dictionary DataFrame schema",
    title="LIWC dictionary DataFrame schema",
    description="Schema for LIWC dictionary DataFrames",
    columns={
        r"\S+": pa.Column(
            dtype="int8",
            regex=True,
            checks=[
                pa.Check(lambda s: s.isin([0, 1]).all(), name="Only binary values (0 or 1)"),
                pa.Check(lambda s: s.any(), name="Term present in at least one category"),
            ],
            required=True,
            nullable=False,
            description="The column name of the dictionary.",
        ),
    },
    index=pa.Index(
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
            pa.Check.str_length(min_value=1, name="Term length > 0"),
            pa.Check(lambda s: s.str.islower(), name="Term all lowercase"),
        ],
    ),
    parsers=[
        pa.Parser(lambda df: df.rename_axis("DicTerm", axis=0), name="Name index 'DicTerm'"),
        pa.Parser(lambda df: df.rename_axis("Category", axis=1), name="Name columns 'Category'"),
        pa.Parser(lambda df: df.rename(index=str.lower), name="Lowercase index"),
        pa.Parser(lambda df: df.sort_index(axis=0), name="Sort index"),
        pa.Parser(lambda df: df.sort_index(axis=1), name="Sort columns"),
    ],
    strict=True,
    coerce=True,
    unique_column_names=True,
    checks=[
        pa.Check(lambda df: df.columns.name == "Category", name="Column index is named 'Category'"),
        pa.Check(lambda df: len(df) > 0, name="At least one term (row)"),
        pa.Check(lambda df: len(df.columns) > 0, name="At least one category (column)"),
        # pa.Check(lambda df: df.columns.isunique),
    ],
)


#######################################################################################
# LIWC dictionary DIC[X] file reading
#######################################################################################


def _read_dic(fp: Union[str, Path], **kwargs: Any) -> pd.DataFrame:
    """
    Reads a dictionary file and returns a pandas :py:class:`~pandas.DataFrame`.
    The file is expected to have a specific format where the header and body are
    separated by '%' characters. The header contains category IDs and names,
    while the body contains entries and their associated category IDs.

    Parameters
    ----------
    fp : Union[:class:`str`, :class:`~pathlib.Path`]
        The file path to the dictionary file.
    **kwargs : Any
        Additional keyword arguments to pass to the `open` function.

    Returns
    -------
    :class:`pandas.DataFrame`
        A DataFrame with the dictionary terms as the index and categories as columns.
        The values are binary (1 or 0) indicating the presence of a term in a category.

    Notes
    -----
    - The file is read with UTF-8 encoding by default.
    - The header and body are extracted using regular expressions.
    - The DataFrame's index is of type string.
    """
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
    columns = pd.Index(cat_names, name="Category")
    data = {}
    for row in body.split("\n"):
        entry, *ids = row.split("\t")
        row_data = [1 if x in ids else 0 for x in cat_ids]
        data[entry] = row_data
    df = pd.DataFrame.from_dict(data, columns=columns, dtype="int8", orient="index").rename_axis(
        "DicTerm"
    )
    df.index = df.index.astype("string")
    return df


def _read_dicx(fp: Union[str, Path], **kwargs: Any) -> pd.DataFrame:
    """
    Read a dictionary from a DICX file.

    Parameters
    ----------
    fp : Union[:class:`~str`, :class:`~pathlib.Path`]
        The filepath to read the dictionary from.
    kwargs : Any
        Additional keyword arguments to pass to `pd.read_csv`.

    Returns
    -------
    :class:`pandas.DataFrame`
        The dictionary read from the file.
    """
    kwargs.setdefault("index_col", "DicTerm")
    kwargs.setdefault("dtype", {"DicTerm": "string"})
    dic = (
        pd.read_csv(fp, **kwargs)
        .rename_axis("Category", axis=1)
        .fillna(False)
        .astype(bool)
        .astype("int8")
    )
    return dic


@pa.check_output(schema=dx_schema)
def read_dx(fp: Union[str, Path], **kwargs: Any) -> pd.DataFrame:
    """
    Read a dictionary from a LIWC DIC or DICX file.

    Parameters
    ----------
    fp : Union[:class:`str`, :class:`~pathlib.Path`]
        The filepath to read the dictionary from.
    kwargs : Any
        Additional keyword arguments to pass to `pd.read_csv`.

    Returns
    -------
    :class:`pandas.DataFrame`
        The dictionary read from the file.
    """
    logger.info("Reading dictionary from %s", fp)
    if (suffix := Path(fp).suffix) == ".dic":
        return _read_dic(fp, **kwargs)
    elif suffix == ".dicx":
        return _read_dicx(fp, **kwargs)
    else:
        raise ValueError(f"Unsupported file extension: {suffix}")


#######################################################################################
# LIWC dictionary DIC[X] file writing
#######################################################################################


def _write_dicx(dx: pd.DataFrame, fp: Union[str, Path], **kwargs: Any) -> None:
    """
    Write a dictionary to a DICX file.

    Parameters
    ----------
    dx : :class:`pandas.DataFrame`
        The dictionary to write.
    fp : Union[:class:`str`, :class:`~pathlib.Path`]
        The filepath to write the dictionary to.
    kwargs : any
        Additional keyword arguments to pass to :meth:`~pandas.DataFrame.to_csv`.
    """
    kwargs.setdefault("sep", ",")
    kwargs.setdefault("index", True)
    kwargs.setdefault("encoding", "utf-8")
    kwargs.setdefault("index_label", "DicTerm")
    kwargs.setdefault("lineterminator", "\n")
    dx.rename_axis(None, axis=1).replace({1: "X", 0: ""}).to_csv(fp, **kwargs)
    return None


def _write_dic(dx: pd.DataFrame, fp: Union[str, Path]) -> None:
    """
    Write a dictionary to a LIWC DIC file.

    Parameters
    ----------
    dx : :class:`pandas.DataFrame`
        The dictionary to write.
    fp : Union[:class:`str`, :class:`~pathlib.Path`]
        The filepath to write the dictionary to.
    """
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
def write_dx(dx: pd.DataFrame, fp: Union[str, Path], **kwargs: Any) -> None:
    """
    Write a dictionary to a LIWC DIC or DICX file.

    Parameters
    ----------
    dx : :class:`pandas.DataFrame`
        The dictionary to write.
    fp : Union[:class:`str`, :class:`~pathlib.Path`]
        The filepath to write the dictionary to.
    kwargs : Any
        Additional keyword arguments to pass to :meth:`~pandas.DataFrame.to_csv`.
    """
    logger.info("Writing dictionary (%d terms, %d categories) to %s", len(dx), dx.shape[1], fp)
    if (suffix := Path(fp).suffix) == ".dic":
        return _write_dic(dx, fp)
    elif suffix == ".dicx":
        return _write_dicx(dx, fp, **kwargs)
    else:
        raise ValueError(f"Unsupported file extension: {suffix}")


#######################################################################################
# DX DataFrame processing
#######################################################################################


@pa.check_output(schema=dx_schema)
def merge_dx(*dxs: pd.DataFrame) -> pd.DataFrame:
    """
    Merge multiple dictionaries into a single dictionary.

    Parameters
    ----------
    *dxs : :class:`pandas.DataFrame`
        Two or more dictionary DataFrames to merge.

    Returns
    -------
    :class:`pandas.DataFrame`
        The merged dictionary.

    Raises
    ------
    ValueError
        If fewer than two dictionaries are provided, or if any dictionaries
        share category names (columns).

    Examples
    --------
    >>> import liwca
    >>> dx_sleep = liwca.fetch_dx("sleep")
    >>> dx_threat = liwca.fetch_dx("threat")
    >>> merged = liwca.merge_dx(dx_sleep, dx_threat)
    >>> merged.tail(3)  # doctest: +NORMALIZE_WHITESPACE
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
    return pd.concat(dxs, axis=1, join="outer").fillna(0)


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
