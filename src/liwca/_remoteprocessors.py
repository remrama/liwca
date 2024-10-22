"""
Load various dictionary files
"""

from pathlib import Path

import pandas as pd

from .io import write_dx

__all__ = [
    "read_raw_sleep",
    "read_raw_threat",
]


def dicx_processor(func):
    """
    Decorator to convert a non-DICX file to DICX.
    """

    def wrapper(fname, action, pup, *args, **kwargs):
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
            The full path to the unzipped file. (Return the same fname is your
            processor doesn't modify the file).
        """
        assert (
            not Path(fname).suffix == ".dicx"
        ), "File is already a DICX file. New file will overlap."
        out_fp = Path(fname).with_suffix(".dicx")
        # if action in ("update", "download") or not out_fp.exists():
        # Apply custom processing to convert the raw file to a DataFrame and write to DICX
        df = func(fname, *args, **kwargs)
        write_dx(df, out_fp)
        return str(out_fp)

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

    Post-processing hook to unzip a file and return the unzipped file name.

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
       The full path to the unzipped file. (Return the same fname is your
       processor doesn't modify the file).

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


# def _read_raw_honor(**kwargs):
#     """
#     Fetch and read the Honor LIWC dictionary.

#     Dictionary details
#     ^^^^^^^^^^^^^^^^^^
#     * **Name:** ``honor``
#     * **Language:** English
#     * **Source:** https://www.michelegelfand.com/honor-dictionary
#     * **Citation:** `doi:10.1002/job.2026 <https://doi.org/10.1002/job.2026>`_

#     .. note::
#         This .dic file has lots of weird and inconsistent spacing.
#         For example, different numbers of tabs between "columns",
#         some spaces thrown in, and different number of tabs ending each line.

#     Parameters
#     ----------
#     version : str or None
#         Name of version. If ``None`` (default), fetches the latest version.
#     load : bool or callable
#         If ``True`` (default), fetch the file and load it as a :class:`~pandas.DataFrame`.
#         If ``False``, fetch the file and return the local filepath.
#         If a callable, fetch the file an load it with the custom callable.
#     **kwargs : dict, optional
#         Additional keyword arguments are passed to :func:`pooch.retrieve`.

#     Returns
#     -------
#     Filepath or DataFrame

#     See Also
#     --------
#     :func:`liwca.fetch_gelfand`
#     """
#     # dataset = inspect.stack()[0][3].split("_")[-1]
#     # fp = _retrieve_lexicon(dataset=dataset, version=version, **kwargs)
#     fp = fetch_dic("honor", **kwargs)
#     ## Custom loader ##
#     data = _read_txt(fp)  # windows-1251/latin1
#     # data = data.replace("“Honor”", '"Honor"')
#     ## Fix tab-separation ##
#     # First remove any end-of-line tabs or spaces
#     data1 = re.sub(r"\s+$", r"\n", data, flags=re.MULTILINE).strip()
#     # Replace any tabs followed by additional spacing with a single tab
#     data2 = re.sub(r"\t\s+", r"\t", data1, flags=re.MULTILINE)
#     # This pattern is slightly different than the more generic one,
#     # because the file has lots of weird/inconsistent formatting.
#     categories = re.findall(r"^([0-9]+)\t(.*)$", data, flags=re.MULTILINE)
#     # categories = re.findall(r"^(\d+)\t(.*)$", data, flags=re.MULTILINE)
#     # categories = re.findall(r"^(\d+)\s+([^\t]+)$", data, flags=re.MULTILINE)
#     categories = {k: v.strip() for k, v in categories}
#     # words = re.findall(r"^([^\t%0-9]+)((?:\s+\d+)*)", data, flags=re.MULTILINE)
#     # words = re.findall(r"^([^\t\%0-9]+)((?:\s+\d+)*)", data, flags=re.MULTILINE)
#     # words = re.findall(r"^([a-zA-Z\*]+)((?:\s+\d+)*)", data, flags=re.MULTILINE)
#     words = re.findall(r"^([^\s\%0-9][^\t]+)((?:\s+\d+)*)", data, flags=re.MULTILINE)
#     words = {k: v.strip().split() for k, v in words}
#     unknown_category_ids = ["800", "999"]
#     words = {
#         k: [categories[x] for x in v if x not in unknown_category_ids]
#         for k, v in words.items()
#     }
#     # words = {k: re.findall(r"\d+", a) for k, v in categories}
#     # dictionary = {catname: catkey for catkey, catname in categories.items()}
#     df = pd.DataFrame(
#         data=False, index=list(words), columns=list(categories.values()), dtype=bool
#     )
#     df = df.sort_index(axis=0).sort_index(axis=1)  # Speeding loop up?
#     for k, v in words.items():
#         df.loc[k, v] = True
#     return df
