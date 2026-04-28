"""Remote text corpora - per-corpus fetch functions.

Each function downloads its corpus to a local cache (if not already
present) and returns a :class:`pathlib.Path` to the downloaded file.
The cache location defaults to
``pooch.os_cache("liwca") / "corpora"`` and can be overridden by
setting the ``LIWCA_DATA_DIR`` environment variable - corpora are
then cached in ``$LIWCA_DATA_DIR/corpora/``.

Power users who want the raw local file path can call
``liwca.datasets.corpora._pup.fetch(filename)`` directly.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import pooch
from tqdm.auto import tqdm

from ._common import AuthorizedZenodoDownloader, CacheCsv, UnzipToCsv, make_pup
from ._common import get_location as _get_location

__all__ = [
    "fetch_autobiomemsim",
    "fetch_cmu_book_summaries",
    "fetch_cmu_movie_summaries",
    "fetch_hippocorpus",
    "fetch_liwc22_demo_data",
    "fetch_reddit_short_stories",
    "fetch_sherlock",
    "fetch_tedtalks",
    "get_location",
]

logger = logging.getLogger(__name__)

_pup = make_pup("corpora")


def get_location() -> Path:
    """Return the local cache directory used by the corpus fetchers."""
    return _get_location(_pup)


# ---------------------------------------------------------------------------
# Fetch functions
# ---------------------------------------------------------------------------


def fetch_autobiomemsim() -> pd.DataFrame:
    """
    Fetch Autobiographical Memory Similarity corpus.

    Data for:
    Tomita et al., 2021, *bioRxiv*,
    The similarity structure of real-world memories.
    doi:`10.1101/2021.01.28.428278 <https://doi.org/10.1101/2021.01.28.428278>`__

    See the `GitHub repository <https://github.com/HLab/AutobioMemorySimilarity>`__ for more info.

    Returns
    -------
    :class:`pandas.DataFrame`
        :class:`~pandas.DataFrame` of the ``memories_dataset*.txt`` files.
    """
    member_fnames = [
        "Dataset1.xlsx",
        "Dataset2.xlsx",
        "memories_dataset1.txt",
        "memories_dataset2.txt",
    ]
    members = [f"AutobioMemorySimilarity-main/{fn}" for fn in member_fnames]

    def _build(member_paths: list[Path]) -> pd.DataFrame:
        txt_paths = sorted(p for p in member_paths if p.name.startswith("memories_dataset"))
        data = []
        for fpath in tqdm(txt_paths, desc="Parsing AutobioMemorySimilarity"):
            txt = fpath.read_text(encoding="utf-8").strip()
            entry_list = txt.split("=" * 49 + "\n" + "=" * 49)
            for entry in entry_list:
                if entry:
                    components = entry.strip().split("\n\n\n")
                    author, condition, memory_a, memory_b, similarity = components
                    author = int(author.split()[1])
                    memory_a = memory_a.split("Memory A:", 1)[1].strip()
                    memory_b = memory_b.split("Memory B:", 1)[1].strip()
                    # similarity = similarity.split("How A and B are similar/dissimilar:", 1)
                    # save both memory A and memory B (2 rows w/ same author ID)
                    data.append({"author": author, "text": memory_a})
                    data.append({"author": author, "text": memory_b})
        return pd.DataFrame.from_records(data, index="author")

    csv_path = _pup.fetch(
        "autobiomemsem.zip",
        processor=UnzipToCsv(_build, "autobiomemsem.csv", members=members),
    )
    return pd.read_csv(csv_path, index_col="author")


def fetch_cmu_book_summaries() -> pd.DataFrame:
    """
    Fetch the CMU Book Summary Corpus.

    Plot summaries for ~16k books from Wikipedia and associated metadata.

    Distributed `by Carnegie Mellon University
    <https://www.cs.cmu.edu/~dbamman/booksummaries.html>`__.

    If used, cite:
    Bamman & Smith., 2013.
    New alignment methods for discriminative book summarization.
    doi:`10.48550/arXiv.1305.1319 <https://doi.org/10.48550/arXiv.1305.1319>`__

    Returns
    -------
    :class:`pandas.DataFrame`
        :class:`~pandas.DataFrame` of the ``booksummaries.txt`` file.
    """
    processor = pooch.Untar(members=["booksummaries/booksummaries.txt"])
    fnames = _pup.fetch("cmu-book-summaries.tar.gz", processor=processor)
    fpaths = {Path(fn).name: Path(fn) for fn in fnames}
    fpath = fpaths["booksummaries.txt"]
    column_names = [
        "WikipediaID",
        "FreebaseID",
        "BookTitle",
        "BookAuthor",
        "PublicationDate",
        "Genres",
        "Summary",
    ]
    df = pd.read_csv(fpath, sep="\t", names=column_names, index_col="WikipediaID").sort_index()
    return df


def fetch_cmu_movie_summaries() -> pd.DataFrame:
    """
    Fetch the CMU Movie Summary Corpus.

    Plot summaries for ~42k movies from Wikipedia and associated metadata.

    Distributed `by Carnegie Mellon University
    <https://www.cs.cmu.edu/~dbamman/moviesummaries.html>`__.

    If used, cite:
    Bamman et al., 2013.
    Learning latent personas of film characters.
    `https://aclanthology.org/P13-1035.pdf <https://aclanthology.org/P13-1035.pdf>`__

    Returns
    -------
    :class:`pandas.DataFrame`
        :class:`~pandas.DataFrame` of the ``plot_summaries.txt`` file.
    """
    fnames = _pup.fetch("cmu-movie-summaries.tar.gz", processor=pooch.Untar())
    fpaths = {Path(fn).name: Path(fn) for fn in fnames}
    fpath = fpaths["plot_summaries.txt"]
    column_names = ["WikipediaID", "Summary"]
    df = pd.read_csv(fpath, sep="\t", names=column_names, index_col="WikipediaID").sort_index()
    return df


def fetch_hippocorpus() -> pd.DataFrame:
    """
    Fetch the Hippocorpus.

    A crowdsourced corpus of imagined, recalled, and retold stories.

    Distributed `by Microsoft Research <https://www.microsoft.com/en-us/download/details.aspx?id=105291>`__.

    Direct download link:
    `https://download.microsoft.com/download/3/c/3/3c388755-ac68-4858-8343-9acfb33c631d/hippocorpus-u20220112.zip
    <https://download.microsoft.com/download/3/c/3/3c388755-ac68-4858-8343-9acfb33c631d/hippocorpus-u20220112.zip>`__

    If used, cite:
    Sap et al., 2020.
    Recollection versus imagination:
    Exploring human memory and cognition via neural language models.
    *Proceedings of the 58th Annual Meeting of the Association for Computational Linguistics*
    doi:`10.18653/v1/2020.acl-main.178 <https://doi.org/10.18653/v1/2020.acl-main.178>`__

    .. seealso::
        Sap et al., 2022.
        Quantifying the narrative flow of imagined versus autobiographical stories
        *PNAS* doi:`10.1073/pnas.2211715119 <https://doi.org/10.1073/pnas.2211715119>`__

    Returns
    -------
    :class:`pandas.DataFrame`
        :class:`~pandas.DataFrame` of the ``hcV3-stories.csv`` file.

    Notes
    -----
    Also available `on Kaggle <https://www.kaggle.com/datasets/saurabhshahane/hippocorpus>`__
    and `on Hugging Face <https://huggingface.co/datasets/allenai/hippocorpus>`__.
    """
    processor = pooch.Unzip(
        members=[
            "hcV3-eventAnnots.csv",
            "hcv3-eventAnnotsAggOverWorkers.csv",
            "hcV3-stories.csv",
            "hippoCorpusV2.csv",
            "LinktoStudyTemplates.txt",
            "V2README.txt",
            "V3README.txt",
        ]
    )
    fnames = _pup.fetch("hippocorpus.zip", processor=processor)
    fpaths = {Path(fn).name: Path(fn) for fn in fnames}
    fpath = fpaths["hcV3-stories.csv"]
    df = pd.read_csv(fpath)
    return df


def fetch_liwc22_demo_data() -> pd.DataFrame:
    """
    Fetch the LIWC-22 Demo Dataset corpus.

    A zip of example input/output files distributed with the LIWC-22
    application. Useful for trying analysis pipelines without having
    to bring your own texts.

    Distributed `on the LIWC website <https://www.liwc.app/help/workbench>`__.

    Direct link to downloaded file:
    `https://www.liwc.app/static/files/liwc-22-demo-data.zip
    <https://www.liwc.app/static/files/liwc-22-demo-data.zip>`__

    If used, cite the LIWC-22 Psychometrics Manual:
    Boyd et al., 2022. The development and psychometric properties of LIWC-22.

    Returns
    -------
    :class:`pandas.DataFrame`
        :class:`~pandas.DataFrame` of all the individual ``.txt`` files from unzipped file.
    """

    def _build(member_paths: list[Path]) -> pd.DataFrame:
        data = {}
        for p in tqdm(member_paths, desc="Parsing LIWC-22 demo data"):
            if p.name in {"LICENSE.txt", "README.txt"}:
                continue
            try:
                text = p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                text = p.read_text(encoding="windows-1252")
            data[p.stem] = text
        return pd.Series(data, name="text").rename_axis("text_id").to_frame()

    csv_path = _pup.fetch(
        "liwc22-demo-data.zip",
        processor=UnzipToCsv(_build, "liwc22-demo-data.csv"),
    )
    return pd.read_csv(csv_path, index_col="text_id")


def fetch_reddit_short_stories() -> pd.DataFrame:
    """
    Fetch the Reddit Short Stories corpus.

    A collection of posts from r/WritingPrompts.

    Distributed `on GitHub <https://github.com/tdude92/reddit-short-stories>`__.

    Returns
    -------
    :class:`pandas.DataFrame`
        :class:`~pandas.DataFrame` of the ``reddit_short_stories.txt`` file.

    Notes
    -----
    Also available `on Kaggle <https://www.kaggle.com/trevordu/reddit-short-stories>`__.
    """

    def _build(source_path: Path) -> pd.DataFrame:
        data = []
        txt = source_path.read_text(encoding="utf-8")
        for line in txt.splitlines():
            # Remove the corpus-specific control tokens before storing.
            cleaned = (
                line.replace("<nl> ", "")  # new-line symbols in the stories
                .replace("<sos> ", "")  # start-of-story
                .replace(" <eos>", "")  # end-of-story
            )
            data.append(cleaned)
        return pd.Series(data, name="text").rename_axis("text_id").to_frame()

    csv_path = _pup.fetch(
        "reddit-short-stories.txt",
        processor=CacheCsv(_build, "reddit-short-stories.csv"),
    )
    return pd.read_csv(csv_path, index_col="text_id")


def fetch_sherlock() -> pd.DataFrame:
    """
    Fetch the Sherlock Topic Model Paper corpus.

    Distributed `on GitHub <https://github.com/ContextLab/sherlock-topic-model-paper>`__.

    If used, cite:
    Heusser et al., 2021,
    Geometric models reveal behavioural and neural signatures
    of transforming naturalistic experiences into episodic memories.
    *Nat Hum Behav* doi:`10.1038/s41562-021-01051-6 <https://doi.org/10.1038/s41562-021-01051-6>`__

    Returns
    -------
    :class:`pandas.DataFrame`
        :class:`~pandas.DataFrame` of all ``NN* transcript.txt`` files.
    """
    member_fnames = [f"NN{i + 1} transcript.txt" for i in range(17)]
    member_fnames.append("Sherlock_Segments_1000_NN_2017.xlsx")
    members = [f"sherlock-topic-model-paper-1.0/data/raw/{fn}" for fn in member_fnames]

    def _build(member_paths: list[Path]) -> pd.DataFrame:
        data = {}
        for p in tqdm(member_paths, desc="Parsing Sherlock transcripts"):
            if p.suffix != ".txt":
                continue
            author_int = int(p.name.split()[0][2:])
            author = f"NN{author_int:02d}"
            data[author] = p.read_text(encoding="windows-1252").strip()
        return pd.Series(data, name="text").rename_axis("text_id").sort_index().to_frame()

    csv_path = _pup.fetch(
        "sherlock.zip",
        processor=UnzipToCsv(_build, "sherlock.csv", members=members),
    )
    return pd.read_csv(csv_path, index_col="text_id")


def fetch_tedtalks(language: str = "en") -> pd.DataFrame:
    """
    Fetch the TED Talks Transcripts for NLP corpus.

    Distributed `on Kaggle
    <https://www.kaggle.com/datasets/miguelcorraljr/ted-ultimate-dataset>`__.

    Parameters
    ----------
    language : :class:`~str`
        The language of the TED talk transcripts to fetch.

    Returns
    -------
    :class:`pandas.DataFrame`
        :class:`~pandas.DataFrame` of the TED talk transcripts of the chosen language.
    """
    languages = {
        "en",
        "es",
        "fr",
        "he",
        "it",
        "ja",
        "ko",
        "pt-br",
        "ru",
        "tr",
        "zh-cn",
        "zh-tw",
    }
    members = [f"2020-05-01/ted_talks_{x}.csv" for x in languages]
    processor = pooch.Unzip(members=members)
    fnames = _pup.fetch("tedtalks.zip", processor=processor)
    fpaths = {Path(fn).name: Path(fn) for fn in fnames}
    fpath = fpaths[f"ted_talks_{language}.csv"]
    df = pd.read_csv(fpath)
    return df


def _fetch_testkitchen() -> pd.DataFrame:
    """
    Fetch the LIWC Test Kitchen corpus.

    .. note:: This is a restricted file that requires approved access.
    """

    def _build(member_paths: list[Path]) -> pd.DataFrame:
        # Single pass over TK_<fullname>/<shortname>_*.txt: read each file
        # and populate source_map the first time a given <shortname> is seen.
        data = {}
        source_map: dict[str, str] = {}
        for p in tqdm(member_paths, desc="Parsing LIWC Test Kitchen"):
            if not p.parent.name.startswith("TK_"):
                continue
            source_shortname = p.stem.split("_")[0]
            source_map.setdefault(source_shortname, p.parent.name.split("_", 1)[1])
            try:
                text = p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                text = p.read_text(encoding="windows-1252")
            data[p.stem] = text.strip().strip('"').strip()
        ser = pd.Series(data, name="text").rename_axis("text_id")
        df = ser.to_frame()
        df.index = df.index.str.split("_").str[0].map(source_map)
        return df

    csv_path = _pup.fetch(
        "testkitchen.zip",
        downloader=AuthorizedZenodoDownloader(),
        processor=UnzipToCsv(_build, "testkitchen.csv"),
    )
    return pd.read_csv(csv_path, index_col="text_id")
