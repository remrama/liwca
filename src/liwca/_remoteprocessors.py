"""
Load various dictionary files
"""

from pathlib import Path
from typing import Any, Callable

import pandas as pd
import pooch

from .io import write_dx

__all__ = [
    "read_raw_sleep",
    "read_raw_threat",
]


def dicx_processor(func: Callable[[str], str]) -> Callable[[str, str, pooch.Pooch], str]:
    """
    Decorator to convert a non-DICX file to DICX.

    Parameters
    ----------
    func : Callable[[str], str]
        A function that takes a file path as input and returns a DataFrame.

    Returns
    -------
    Callable[[str, str, pooch.Pooch], str]
        A wrapped function that processes the file and converts it to DICX format.

    Notes
    -----
    The wrapped function will check if the file is already in DICX format and will raise an
    assertion error if it is. If the file needs to be processed (based on the action or if the
    output file does not exist), the function will apply the provided processing function to
    convert the raw file to a DataFrame and write it to a DICX file.
    """

    def wrapper(fname: str, action: str, pup: pooch.Pooch, *args: Any, **kwargs: Any) -> str:
        """
        Parameters
        ----------
        fname : str
            Full path of the zipped file in local storage
        action : str
            One of "download" (file doesn't exist and will download),
            "update" (file is outdated and will download), and
            "fetch" (file exists and is updated so no download).
        pup : Pooch
            The instance of Pooch that called the processor function.

        Returns
        -------
        fname : str
            The full path to the modified file.
        """
        fp = Path(fname)
        assert not fp.suffix == ".dicx", "File is already a DICX file. New file will overlap."
        out_fp = fp.with_suffix(".dicx")
        if action in ("update", "download") or not out_fp.exists():
            # Apply custom processing to convert the raw file to a DataFrame and write to DICX
            df = func(fname, *args, **kwargs)
            write_dx(df, out_fp)
        out_fname = str(out_fp)
        return out_fname

    return wrapper


@dicx_processor
def read_raw_sleep(fname: str) -> pd.DataFrame:
    """
    OSF repository: https://osf.io/9f3v2
    Full table: https://osf.io/8hfcs
    Paper: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9908817
    https://eutils.ncbi.nlm.nih.gov/
    Paper: https://onlinelibrary.wiley.com/doi/10.1111/sltb.12920
    Scrapable: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9908817/bin/SLTB-53-39-s001.docx
    Scrapable PDF: https://www.suicideinfo.ca/wp-content/uploads/2023/02/Inferring-sleep-disturbance-from-text-messages-of-suicide-attempt-survivors-A.pdf
    Short table: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9908817/table/sltb12920-tbl-0001/?report=objectonly
    Short table: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9908817/table/sltb12920-tbl-0001
    """
    words = pd.read_table(fname, skiprows=1, header=None).stack().str.lower().tolist()
    # Some duplicates, and based on SI table I think they were autocorrected during publication.
    # Replacing with values from Table S1 (in most cases, otherwise inferred bc term was added)
    words[words.index("can't sleep")] = "cant sleep"  # from Table S1
    words[words.index("couldn't sleep")] = "couldnt sleep"  # inferred
    words[words.index("didn't sleep")] = "didnt sleep"  # inferred
    dx = pd.Series(1, name="sleep", index=words).to_frame()
    return dx


@dicx_processor
def read_raw_threat(fname: str) -> pd.DataFrame:
    """
    Read/parse the Threat LIWC dictionary.

    Dictionary details
    ^^^^^^^^^^^^^^^^^^
    * **Name:** ``threat``
    * **Language:** English
    * **Source:** https://www.michelegelfand.com/threat-dictionary
    * **Citation:** `doi:10.1073/pnas.2113891119 <https://doi.org/10.1073/pnas.2113891119>`_

    Parameters
    ----------
    **kwargs : dict, optional
        Additional keyword arguments are passed to :func:`pooch.retrieve`.

    Returns
    -------
    dictionary : dict
        A dictionary with abbreviated category names as keys and category words as values.
    """
    with open(fname, "r", encoding="utf-8") as f:
        words = f.read().splitlines()
    dx = pd.Series(1, name="threat", index=words).to_frame()
    return dx
