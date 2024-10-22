"""
IO module
"""

import csv
import re
from importlib.resources import files
from pathlib import Path
from typing import Any, Union

import numpy as np
import pandas as pd
import pandera as pa
import pooch

__all__ = [
    "fetch_dx",
    "merge_dx",
    "read_dx",
    "write_dx",
]


_pup = pooch.create(path=pooch.os_cache("liwca"), base_url="")
_pup.load_registry(fname=files("liwca.data").joinpath("registry.txt"))

_dicname_to_registry = {
    "honor": "Honor-Dictionary-English_2017.dic",  # Gelfand 2015
    "threat": "threat.txt",  # Gelfand 2022
    "sleep": "ladis2023-table1.tsv",  # Ladis 2023
    "bigtwo_a": "a_AgencyCommunion.dic",  # Pietraszkiewicz 2018
    "bigtwo_b": "b_AgencyCommunion.dic",  # Pietraszkiewicz 2018
    # "behav": "behavioral-activation-dictionary.dicx",
    # "bigtwo": "big-two-agency-communion-dictionary.dicx",
    # "bodytype": "body-type-dictionary.dicx",
    # "eprime": "english-prime-dictionary.dicx",
    # "foresight": "foresight-lexicon.dicx",
    # "imagination": "imagination-lexicon.dicx",
    # "mind": "mind-perception-dictionary.dicx",
    # "physio": "physiological-sensations-dictionary.dicx",
    # "qualia": "qualia-dictionary.dicx",
    # "self": "self-determinationself-talk-dictionary.dicx",
    # "sleep": "sleep-dictionary.dicx",
    # "threat": "threat-dictionary.dicx",
    # "vestibular": "vestibular.dic",
    # "weiref": "weighted-referential-activity-dictionary.dicx",
    # "wellbeing": "well-being-dictionary.dicx",
}


#######################################################################################
# Pandera shemas for pandas parsing (processing) and validation (checking)
#######################################################################################

# Schema to validate LIWC dictionary pandas DataFrames
dx_schema = pa.DataFrameSchema(
    name="LIWC dictionary DataFrame schema",
    title="LIWC dictionary DataFrame schema",
    description="Schema for LIWC dictionary DataFrames",
    columns={
        "\S+": pa.Column(
            dtype="int64",
            regex=True,
            checks=[pa.Check.isin([0, 1]), pa.Check(lambda s: s.any())],
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
        checks=[pa.Check.str_length(min_value=1), pa.Check(lambda s: s.str.islower())],
    ),
    parsers=[
        pa.Parser(lambda df: df.rename_axis("DicTerm", axis=0)),
        pa.Parser(lambda df: df.rename_axis("Category", axis=1)),
        pa.Parser(lambda df: df.sort_index(axis=0).sort_index(axis=1)),
    ],
    strict=True,
    coerce=True,
    unique_column_names=True,
    checks=[
        pa.Check(lambda df: df.columns.name == "Category"),
        # pa.Check(lambda df: df.columns.isunique),
    ],
)


#######################################################################################
# LIWC dictionary DIC[X] file reading
#######################################################################################


def _read_dic(fp: Union[str, Path], **kwargs: Any) -> pd.DataFrame:
    """
    Read a dictionary from a LIWC DIC file.

    Parameters
    ----------
    fp : Path
        The filepath to read the dictionary from.
    kwargs : dict
        Additional keyword arguments to pass to `pd.read_csv`.

    Returns
    -------
    pd.DataFrame
        The dictionary read from the file.
    """
    kwargs.setdefault("encoding", "utf-8")
    with open(fp, "rt", **kwargs) as f:
        data = f.read()

    # Use regex to get everything between the first and last '%' character (both starting on new lines)
    m = re.match(
        r"^%.*?$(?P<header>.*)^%.*?(?P<body>.*)", data, flags=re.DOTALL | re.MULTILINE
    )
    if m is not None:
        header = m.group("header").strip()
        body = m.group("body").strip()
    cat_ids, cat_names = zip(*[row.split() for row in header.split("\n")])
    columns = pd.Index(cat_names, name="Category")  #.astype("string") Can't use bc of bug when pandera checks for unique column names
    # id2cat =p {int(row.split()[1]): row.split()[0] for row in header.split("\n")}
    # cat2id = {v: k for k, v in col2id.items()}
    # columns = pd.Index(cat2id, name="Category").astype("string")
    data = {}
    for row in body.split("\n"):
        entry, *ids = row.split("\t", 1)
        row_data = [1 if x in ids else 0 for x in cat_ids]
        # ids = np.asarray(ids, dtype=int)
        # ids = [int(x) for x in ids]
        # row_data = np.isin(list(id2term), ids).astype(int)
        # row_data = [1 if x in ids else 0 for x in id2cat]
        data[entry] = row_data
    df = pd.DataFrame.from_dict(
        data, columns=columns, dtype="int", orient="index"
    ).rename_axis("DictTerm")
    df.index = df.index.astype("string")
    return df


def _read_dicx(fp: Union[str, Path], **kwargs: Any) -> pd.DataFrame:
    """
    Read a dictionary from a DICX file.

    Parameters
    ----------
    fp : Path
        The filepath to read the dictionary from.
    kwargs : dict
        Additional keyword arguments to pass to `pd.read_csv`.

    Returns
    -------
    pd.DataFrame
        The dictionary read from the file.
    """
    kwargs.setdefault("index_col", "DicTerm")
    kwargs.setdefault("dtype", {"DicTerm": "string"})
    dic = (
        pd.read_csv(fp, **kwargs)
        .rename_axis("Category", axis=1)
        .fillna(False)
        .astype(bool)
        .astype(int)
    )
    return dic


@pa.check_output(schema=dx_schema)
def read_dx(fp: Union[str, Path], **kwargs: Any) -> pd.DataFrame:
    """
    Read a dictionary from a LIWC DIC or DICX file.

    Parameters
    ----------
    fp : Path
        The filepath to read the dictionary from.
    kwargs : dict
        Additional keyword arguments to pass to `pd.read_csv`.

    Returns
    -------
    pd.DataFrame
        The dictionary read from the file.
    """
    if (suffix := Path(fp).suffix) == ".dic":
        return _read_dic(fp, **kwargs)
    elif suffix == ".dicx":
        return _read_dicx(fp, **kwargs)
    else:
        raise ValueError(f"Unsupported file extension: {suffix}")


#######################################################################################
# LIWC dictionary DIC[X] file writing
#######################################################################################


def _write_to_dicx(dx: pd.DataFrame, fp: Union[str, Path], **kwargs: Any) -> None:
    """
    Write a dictionary to a DICX file.

    Parameters
    ----------
    dic : pd.DataFrame
        The dictionary to write.
    fp : Path
        The filepath to write the dictionary to.
    kwargs : dict
        Additional keyword arguments to pass to `pd.DataFrame.to_csv`.
    """
    kwargs.setdefault("sep", ",")
    kwargs.setdefault("index", True)
    kwargs.setdefault("encoding", "utf-8")
    kwargs.setdefault("index_label", "DicTerm")
    kwargs.setdefault("lineterminator", "\n")
    dx.rename_axis(None, axis=1).replace({1: "X", 0: ""}).to_csv(fp, **kwargs)
    return None


def _write_to_dic(dx: pd.DataFrame, fp: Union[str, Path]) -> None:
    """
    Write a dictionary to a LIWC DIC file.

    Parameters
    ----------
    dic : pd.DataFrame
        The dictionary to write.
    fp : Path
        The filepath to write the dictionary to.
    """
    with open(fp, "wt", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow("%")
        writer.writerows([col, i] for i, col in enumerate(dx.columns, 1))
        writer.writerow("%")
        writer.writerows(
            dx.apply(
                lambda row: [row.name] + (np.flatnonzero(row) + 1).tolist(), axis=1
            ).tolist()
        )
    return None


@pa.check_input(schema=dx_schema)
def write_dx(dx: pd.DataFrame, fp: Union[str, Path], **kwargs: Any) -> None:
    """
    Write a dictionary to a LIWC DIC or DICX file.

    Parameters
    ----------
    dx : pd.DataFrame
        The dictionary to write.
    fp : Path
        The filepath to write the dictionary to.
    kwargs : dict
        Additional keyword arguments to pass to `pd.DataFrame.to_csv`.
    """
    if (suffix := Path(fp).suffix) == ".dic":
        return _write_to_dic(dx, fp)
    elif suffix == ".dicx":
        return _write_to_dicx(dx, fp, **kwargs)
    else:
        raise ValueError(f"Unsupported file extension: {suffix}")


#######################################################################################
# DX DataFrame processing
#######################################################################################


@pa.check_output(schema=dx_schema)
def merge_dx(dxs: list[pd.DataFrame], **kwargs: Any) -> pd.DataFrame:
    """
    Merge multiple dictionaries into a single dictionary.

    Parameters
    ----------
    dxs : list of pd.DataFrame
        The list of dictionaries to merge.
    kwargs : dict
        Additional keyword arguments to pass to `pd.concat`.

    Returns
    -------

    pd.DataFrame
        The merged dictionary.
    """
    kwargs.setdefault("axis", 1)
    kwargs.setdefault("join", "outer")
    # kwargs.setdefault("sort", True)  # Should not need to sort, but pandera bug requires it
    # return pd.concat(dxs, **kwargs).sort_index(axis=1).fillna(0)
    return pd.concat(dxs, **kwargs).fillna(0)


#######################################################################################
# Pooch remote fetching and processing
#######################################################################################


@pa.check_output(schema=dx_schema)
def fetch_dx(dic_name: str, **kwargs: Any) -> pd.DataFrame:
    """
    Fetch a remote dictionary and load as a :class:`~pandas.DataFrame`.

    This will first use :mod:`pooch` to download raw file to local cache if not already downloaded.
    Then it will read the file, applying any custom corrections, into a :class:`~pandas.DataFrame`.

    If raw file is not a readable `.dic` or `.dicx` file, it will be unpacked, processed, and rewritten as `.dicx`.

    Fetch/retrieve a dictionary from the registry.
    Download the dictionary file if it is not already downloaded.

    Parameters
    ----------
    dic_name : str
        The name of the dictionary to fetch.

    Returns
    -------
    dict
        The dictionary local filepath.
    """
    name_in_registry = _dicname_to_registry[dic_name]
    # Get the processor function for the dictionary, if available
    from . import _remoteprocessors
    kwargs.setdefault("processor", getattr(_remoteprocessors, f"read_raw_{dic_name}", None))
    fp = _pup.fetch(name_in_registry, **kwargs)
    df = read_dx(fp)
    return df
