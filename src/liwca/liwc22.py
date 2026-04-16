"""
Python wrapper for the LIWC-22 CLI tool.

Builds and runs LIWC-22-cli commands as subprocesses. All seven analysis
modes are exposed as methods on the :class:`Liwc22` class.

Requires LIWC-22 to be installed with the CLI on your PATH.
The LIWC-22 desktop application (or its license server) must be running
when you call the CLI - start it before using :class:`Liwc22`, or pass
``auto_open=True`` to let liwca handle it.

Examples
--------
>>> import liwca
>>> liwc = liwca.liwc22.Liwc22(dry_run=True)
>>> liwc.wc(input="data.csv", output="results.csv")  # doctest: +SKIP
0

Amortize app-launch across many calls with the context-manager form:

>>> with liwca.liwc22.Liwc22(auto_open=True, encoding="utf-8") as liwc:  # doctest: +SKIP
...     liwc.wc(input="data.csv", output="wc.csv")
...     liwc.freq(input="data.csv", output="freq.csv", n_gram=2)

See Also
--------
- LIWC CLI documentation: https://www.liwc.app/help/cli
- Python CLI example: https://github.com/ryanboyd/liwc-22-cli-python/blob/main/LIWC-22-cli_Example.py
"""

from __future__ import annotations

import logging
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

__all__ = [
    "Liwc22",
    "build_command",
    "FLAG_BY_DEST",
    "BOOL_FLAGS",
    "MODE_GLOBALS",
]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App management helpers
# ---------------------------------------------------------------------------

LIWC_APP_NAMES = {
    "Darwin": "LIWC-22",
    "Windows": "LIWC-22.exe",
    "Linux": "LIWC-22",
}

LIWC_LICENSE_SERVER = "LIWC-22-license-server"
LIWC_CLI = "LIWC-22-cli"


def _is_liwc_running() -> bool:
    """Check whether LIWC-22 (GUI or license server) is already running."""
    system = platform.system()
    try:
        if system == "Windows":
            result = subprocess.run(
                ["tasklist"],
                capture_output=True,
                text=True,
            )
            return "liwc-22" in result.stdout.lower()
        else:
            result = subprocess.run(
                ["pgrep", "-fi", "liwc-22"],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
    except FileNotFoundError:
        return False


def _open_liwc_app(use_license_server: bool = True) -> subprocess.Popen[bytes] | None:
    """Launch LIWC-22 in the background and return the Popen handle."""
    if use_license_server and shutil.which(LIWC_LICENSE_SERVER):
        exe = LIWC_LICENSE_SERVER
    else:
        app_name = LIWC_APP_NAMES.get(platform.system(), "LIWC-22")
        exe_path = shutil.which(app_name)
        if exe_path is None:
            mac_path = Path("/Applications/LIWC-22.app")
            if mac_path.exists():
                proc = subprocess.Popen(["open", "-a", "LIWC-22"])
                time.sleep(5)
                return proc
            sys.exit(
                "ERROR: Could not locate LIWC-22 application. "
                "Make sure it is installed and on your PATH."
            )
        exe = exe_path

    logger.info("Starting %s …", exe)
    proc = subprocess.Popen(
        [exe],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(5)
    return proc


def _close_liwc_app(proc: subprocess.Popen[bytes] | None) -> None:
    """Terminate a LIWC process that we opened."""
    if proc is None:
        return
    try:
        proc.terminate()
        proc.wait(timeout=10)
    except Exception:
        proc.kill()


# ---------------------------------------------------------------------------
# Flag catalogue
# ---------------------------------------------------------------------------
# Single source of truth for (a) dest → CLI flag and (b) which dests are
# value-less bool flags.  build_command consults these to translate a dict
# of Python kwargs into an argv list for the LIWC-22 CLI.

# dest -> CLI flag (short form where one exists; long form otherwise)
FLAG_BY_DEST: dict[str, str] = {
    # --- globals ---
    "count_urls": "-curls",
    "precision": "-dec",
    "csv_delimiter": "-delim",
    "encoding": "-e",
    "csv_escape": "-esc",
    "preprocess_cjk": "-prep",
    "csv_quote": "-quote",
    "skip_header": "-sh",
    "include_subfolders": "-subdir",
    "url_regexp": "-urlre",
    "prune_interval": "-pint",
    "prune_threshold_value": "-pval",
    "column_delimiter": "-cd",
    # --- shared across multiple modes ---
    "input": "-i",
    "output": "-o",
    "combine_columns": "-ccol",
    "column_indices": "-ci",
    "output_format": "-f",
    "segmentation": "-s",
    "skip_wc": "-skip",
    "index_of_id_column": "-idind",
    "conversion_list": "-cl",
    "n_gram": "-n",
    "trim_s": "-ts",
    "omit_speakers_num_turns": "-osnof",
    "omit_speakers_word_count": "-oswf",
    "dictionary": "-d",
    "stop_list": "-sl",
    "single_line": "-sl",
    # --- mode-unique ---
    "clean_escaped_spaces": "-ces",
    "console_text": "-ct",
    "exclude_categories": "-ec",
    "environment_variable": "-envvar",
    "include_categories": "-ic",
    "row_id_indices": "-id",
    "threads": "-t",
    "drop_words": "-d",
    "save_theme_scores": "--save-theme-scores",
    "enable_pca": "-epca",
    "mem_output_type": "-memot",
    "threshold_type": "-ttype",
    "threshold_value": "-tval",
    "category_to_contextualize": "-categ",
    "keep_punctuation": "-inpunct",
    "word_window_left": "-nleft",
    "word_window_right": "-nright",
    "word_list": "-wl",
    "words_to_contextualize": "-words",
    "output_data_points": "-dp",
    "scaling_method": "-scale",
    "segments_number": "-segs",
    "speaker_list": "-spl",
    "regex_removal": "-rr",
    "calculate_lsm": "-clsm",
    "group_column": "-gc",
    "output_type": "-ot",
    "person_column": "-pc",
    "text_column": "-tc",
    "expanded_output": "-expo",
}

# Dests in FLAG_BY_DEST that are bool flags (emit flag alone when True;
# omitted when False).  Everything else is a value flag.
BOOL_FLAGS: frozenset[str] = frozenset(
    {
        "single_line",
        "save_theme_scores",
        "enable_pca",
        "expanded_output",
    }
)


# ---------------------------------------------------------------------------
# Mode globals
# ---------------------------------------------------------------------------
# Which hoisted :class:`Liwc22` constructor CLI args apply to each mode's
# CLI subprocess.  ``_run_mode`` filters ``self._globals`` through this
# mapping so that e.g. ``--count-urls`` is never passed to ``lsm`` (which
# does not accept it).

_ALL_HOISTED: frozenset[str] = frozenset(
    {
        "encoding",
        "count_urls",
        "preprocess_cjk",
        "include_subfolders",
        "url_regexp",
        "csv_delimiter",
        "csv_escape",
        "csv_quote",
        "skip_header",
        "precision",
    }
)

MODE_GLOBALS: dict[str, frozenset[str]] = {
    "wc": _ALL_HOISTED,
    "freq": _ALL_HOISTED,
    "mem": _ALL_HOISTED,
    "arc": _ALL_HOISTED,
    "context": _ALL_HOISTED - {"precision"},
    "ct": _ALL_HOISTED
    - {
        "csv_delimiter",
        "csv_escape",
        "csv_quote",
        "skip_header",
        "precision",
    },
    "lsm": _ALL_HOISTED
    - {
        "count_urls",
        "preprocess_cjk",
        "include_subfolders",
        "url_regexp",
    },
}


# ---------------------------------------------------------------------------
# Command builder
# ---------------------------------------------------------------------------


def build_command(mode: str, cli_args: dict[str, Any]) -> list[str]:
    """Assemble the LIWC-22-cli argv for a mode and flag dict.

    Args whose value is ``None`` are skipped (unset).  Bool flags (listed
    in :data:`BOOL_FLAGS`) emit the flag alone when ``True`` and are
    omitted when ``False``.  All other flags emit ``flag value``.

    Parameters
    ----------
    mode : :class:`str`
        LIWC-22 analysis mode (``"wc"``, ``"freq"``, ``"mem"``, ``"context"``,
        ``"arc"``, ``"ct"``, or ``"lsm"``).
    cli_args : :class:`dict`
        Mapping from dest (Python kwarg name) to value.  Keys must be in
        :data:`FLAG_BY_DEST`.

    Returns
    -------
    :class:`list` of :class:`str`
        The complete command, starting with ``"LIWC-22-cli"``.
    """
    cmd: list[str] = [LIWC_CLI, "-m", mode]
    for dest, value in cli_args.items():
        if value is None:
            continue
        flag = FLAG_BY_DEST[dest]
        if dest in BOOL_FLAGS:
            if value:
                cmd.append(flag)
        else:
            cmd.extend([flag, str(value)])
    return cmd


def _quote_for_display(cmd: list[str]) -> str:
    """Format a command list for human-readable display."""
    return " ".join(f'"{tok}"' if " " in tok else tok for tok in cmd)


# ---------------------------------------------------------------------------
# Shared execution logic
# ---------------------------------------------------------------------------


def _run(
    mode: str,
    cli_args: dict[str, Any],
    *,
    auto_open: bool,
    use_gui: bool,
    dry_run: bool,
) -> int:
    """Run a LIWC-22 CLI command built from a mode + flag dict."""
    cmd = build_command(mode, cli_args)

    if dry_run:
        print(f"Command that would be executed:\n  {_quote_for_display(cmd)}")
        return 0

    # -- ensure LIWC-22 is running -------------------------------------------
    liwc_proc: subprocess.Popen[bytes] | None = None
    we_opened_it = False

    if not _is_liwc_running():
        if auto_open:
            logger.info("LIWC-22 is not running - starting it now …")
            liwc_proc = _open_liwc_app(use_license_server=not use_gui)
            we_opened_it = True
        else:
            sys.exit(
                "ERROR: LIWC-22 is not running. Start the LIWC-22 application "
                "(or the license server) first, or re-run with auto_open=True."
            )

    # -- run the analysis ----------------------------------------------------
    logger.info("Running: %s", _quote_for_display(cmd))
    try:
        result = subprocess.run(cmd, check=True)
        rc = result.returncode
    except FileNotFoundError:
        logger.error(
            "'%s' not found. Make sure LIWC-22 is installed and the CLI is on your PATH.",
            LIWC_CLI,
        )
        rc = 1
    except subprocess.CalledProcessError as exc:
        logger.error("LIWC-22-cli exited with return code %d.", exc.returncode)
        rc = exc.returncode
    finally:
        if we_opened_it:
            logger.info("Shutting down LIWC-22 …")
            _close_liwc_app(liwc_proc)

    return rc


# ---------------------------------------------------------------------------
# Public API - Liwc22 class
# ---------------------------------------------------------------------------


class Liwc22:
    """
    Wrapper around ``LIWC-22-cli``.

    Set cross-cutting options (encoding, CSV formatting, URL handling,
    precision, and execution-control flags) once at construction, then call
    the seven per-mode methods (:meth:`wc`, :meth:`freq`, :meth:`mem`,
    :meth:`context`, :meth:`arc`, :meth:`ct`, :meth:`lsm`) repeatedly.  Each
    method takes only the kwargs specific to that mode - the hoisted
    options are injected automatically.

    Can be used as a context manager to amortize the LIWC-22 app launch and
    shutdown across multiple calls when ``auto_open=True``.

    Parameters
    ----------
    encoding : :class:`str`, optional
        Input file encoding (default: UTF-8).
    count_urls : :class:`str`, optional
        Count URLs as a single word - one of ``"yes"``, ``"no"`` (default: yes).
        Only meaningful if *url_regexp* is set.
    preprocess_cjk : :class:`str`, optional
        Preprocess CJK text with Jieba (Chinese) or Kuromoji (Japanese)
        tokeniser - one of ``"chinese"``, ``"japanese"``, ``"none"``.
    include_subfolders : :class:`str`, optional
        Include subfolders when analysing a directory - one of ``"yes"``,
        ``"no"`` (default: yes).
    url_regexp : :class:`str`, optional
        Regular expression used to capture URLs in text.
    csv_delimiter : :class:`str`, optional
        CSV delimiter character (default: ``,``). Use ``\\t`` for tab.
    csv_escape : :class:`str`, optional
        CSV escape character (default: none).
    csv_quote : :class:`str`, optional
        CSV quote character (default: ``"``).
    skip_header : :class:`str`, optional
        Skip the first row of an Excel/CSV file - one of ``"yes"``, ``"no"``
        (default: yes).
    precision : :class:`int`, optional
        Number of decimal places in output (0-16, default: 2).
    auto_open : :class:`bool`, optional
        If LIWC-22 is not running, launch it before each analysis and close
        it afterwards (default ``False``).  When used as a context manager,
        the app is launched once on ``__enter__`` and closed on ``__exit__``.
    use_gui : :class:`bool`, optional
        When auto-opening, prefer the GUI app over the headless license
        server (default ``False``).
    dry_run : :class:`bool`, optional
        Print each CLI command without executing it (default ``False``).

    Examples
    --------
    >>> import liwca
    >>> liwc = liwca.liwc22.Liwc22(dry_run=True)
    >>> liwc.wc(input="data.csv", output="results.csv")  # doctest: +SKIP
    0

    >>> with liwca.liwc22.Liwc22(auto_open=True, encoding="utf-8") as liwc:  # doctest: +SKIP
    ...     liwc.wc(input="data.csv", output="wc.csv")
    ...     liwc.freq(input="data.csv", output="freq.csv", n_gram=2)
    """

    def __init__(
        self,
        *,
        encoding: str | None = None,
        count_urls: str | None = None,
        preprocess_cjk: str | None = None,
        include_subfolders: str | None = None,
        url_regexp: str | None = None,
        csv_delimiter: str | None = None,
        csv_escape: str | None = None,
        csv_quote: str | None = None,
        skip_header: str | None = None,
        precision: int | None = None,
        auto_open: bool = False,
        use_gui: bool = False,
        dry_run: bool = False,
    ) -> None:
        self._globals: dict[str, Any] = {
            "encoding": encoding,
            "count_urls": count_urls,
            "preprocess_cjk": preprocess_cjk,
            "include_subfolders": include_subfolders,
            "url_regexp": url_regexp,
            "csv_delimiter": csv_delimiter,
            "csv_escape": csv_escape,
            "csv_quote": csv_quote,
            "skip_header": skip_header,
            "precision": precision,
        }
        self._auto_open = auto_open
        self._use_gui = use_gui
        self._dry_run = dry_run
        self._app_owned = False
        self._liwc_proc: subprocess.Popen[bytes] | None = None

    # -- context manager -----------------------------------------------------

    def __enter__(self) -> "Liwc22":
        if self._auto_open and not self._dry_run and not _is_liwc_running():
            self._liwc_proc = _open_liwc_app(use_license_server=not self._use_gui)
            self._app_owned = True
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self._app_owned:
            logger.info("Shutting down LIWC-22 …")
            _close_liwc_app(self._liwc_proc)
            self._app_owned = False
            self._liwc_proc = None

    # -- internal seam -------------------------------------------------------

    def _run_mode(self, mode: str, cli_args: dict[str, Any]) -> int:
        """Merge hoisted globals (filtered by :data:`MODE_GLOBALS`) and run."""
        applicable = MODE_GLOBALS[mode]
        merged: dict[str, Any] = {k: v for k, v in self._globals.items() if k in applicable}
        merged.update(cli_args)
        # If we already launched the app in __enter__, don't re-launch per call.
        auto_open_for_call = self._auto_open and not self._app_owned
        return _run(
            mode,
            merged,
            auto_open=auto_open_for_call,
            use_gui=self._use_gui,
            dry_run=self._dry_run,
        )

    # -- mode methods --------------------------------------------------------

    def wc(
        self,
        *,
        input: str,
        output: str,
        combine_columns: str | None = None,
        clean_escaped_spaces: str | None = None,
        column_indices: str | None = None,
        console_text: str | None = None,
        dictionary: str | None = None,
        exclude_categories: str | None = None,
        environment_variable: str | None = None,
        output_format: str | None = None,
        include_categories: str | None = None,
        row_id_indices: str | None = None,
        segmentation: str | None = None,
        threads: int | None = None,
    ) -> int:
        """
        Run a standard LIWC-22 word count analysis.

        Scores each input text against a LIWC dictionary (default ``LIWC22``)
        and reports per-category word counts or percentages.

        Parameters
        ----------
        input : :class:`str`
            Path to input file or folder.
        output : :class:`str`
            Output file/folder path, or ``"console"``.
        combine_columns : :class:`str`, optional
            Combine spreadsheet columns into a single text per row (default: yes).
        clean_escaped_spaces : :class:`str`, optional
            With ``--input console``: if ``1``, escaped spaces like ``\\n`` are
            converted to actual spaces (default: 1).
        column_indices : :class:`str`, optional
            Comma-separated column indices (1-based) containing analysable text.
            All columns processed by default.
        console_text : :class:`str`, optional
            Text string to analyse. Use with ``--input console``.
        dictionary : :class:`str`, optional
            LIWC dictionary name (e.g. ``LIWC22``, ``LIWC2015``) or path to a
            custom ``.dicx`` file (default: LIWC22).
        exclude_categories : :class:`str`, optional
            Comma-separated dictionary categories to exclude from output.
        environment_variable : :class:`str`, optional
            Environment variable name containing text. Use with ``--input envvar``.
        output_format : :class:`str`, optional
            Output file format - one of ``csv``, ``xlsx``, ``ndjson`` (default: csv).
        include_categories : :class:`str`, optional
            Comma-separated dictionary categories to include in output.
        row_id_indices : :class:`str`, optional
            Comma-separated column indices (1-based) for row identifiers.
            Multiple columns concatenated with ``;``. Defaults to row number.
        segmentation : :class:`str`, optional
            Split text into segments. Syntax varies by mode - see the
            `LIWC CLI documentation <https://www.liwc.app/help/cli>`_.
        threads : :class:`int`, optional
            Number of processing threads (default: available cores - 1).

        Returns
        -------
        :class:`int`
            Return code from the LIWC-22 CLI process (0 = success).

        Raises
        ------
        :class:`SystemExit`
            If LIWC-22 is not running and ``auto_open=False`` was passed at
            construction.

        See Also
        --------
        ~liwca.count : Pure-Python word counting (no LIWC-22 required).

        Examples
        --------
        >>> Liwc22(dry_run=True).wc(input="data.txt", output="results.csv")  # doctest: +SKIP
        0
        """
        return self._run_mode(
            "wc",
            {
                "input": input,
                "output": output,
                "combine_columns": combine_columns,
                "clean_escaped_spaces": clean_escaped_spaces,
                "column_indices": column_indices,
                "console_text": console_text,
                "dictionary": dictionary,
                "exclude_categories": exclude_categories,
                "environment_variable": environment_variable,
                "output_format": output_format,
                "include_categories": include_categories,
                "row_id_indices": row_id_indices,
                "segmentation": segmentation,
                "threads": threads,
            },
        )

    def freq(
        self,
        *,
        input: str,
        output: str,
        combine_columns: str | None = None,
        column_indices: str | None = None,
        conversion_list: str | None = None,
        drop_words: int | None = None,
        output_format: str | None = None,
        n_gram: int | None = None,
        skip_wc: int | None = None,
        stop_list: str | None = None,
        trim_s: str | None = None,
        prune_interval: int | None = None,
        prune_threshold_value: int | None = None,
    ) -> int:
        """
        Compute word (and n-gram) frequencies across input texts.

        Parameters
        ----------
        input : :class:`str`
            Path to input file or folder.
        output : :class:`str`
            Output file/folder path, or ``"console"``.
        combine_columns : :class:`str`, optional
            Combine spreadsheet columns into a single text per row (default: yes).
        column_indices : :class:`str`, optional
            Comma-separated column indices (1-based) containing analysable text.
            All columns processed by default.
        conversion_list : :class:`str`, optional
            Path to a conversion list or an internal list name (e.g.
            ``internal-EN``). Use ``"none"`` for no conversion.
        drop_words : :class:`int`, optional
            Drop n-grams with frequency less than this value (default: 5).
        output_format : :class:`str`, optional
            Output file format - one of ``csv``, ``xlsx``, ``ndjson`` (default: csv).
        n_gram : :class:`int`, optional
            N-gram size (1-5). Inclusive of all lower n-grams (default: 1).
        skip_wc : :class:`int`, optional
            Skip texts with word count less than this value (default: 10).
        stop_list : :class:`str`, optional
            Path to a stop list, an internal list name (e.g. ``internal-EN``),
            or ``"none"`` (default: internal-EN).
        trim_s : :class:`str`, optional
            Trim trailing ``'s`` from words (default: yes).
        prune_interval : :class:`int`, optional
            Prune frequency list every N words to optimise RAM (default: 10000000).
        prune_threshold_value : :class:`int`, optional
            Minimum n-gram frequency retained during pruning (default: 5).

        Returns
        -------
        :class:`int`
            Return code from the LIWC-22 CLI process (0 = success).

        Raises
        ------
        :class:`SystemExit`
            If LIWC-22 is not running and ``auto_open=False`` was passed at
            construction.

        Examples
        --------
        >>> Liwc22(dry_run=True).freq(  # doctest: +SKIP
        ...     input="corpus/",
        ...     output="freqs.csv",
        ...     n_gram=2,
        ... )
        0
        """
        return self._run_mode(
            "freq",
            {
                "input": input,
                "output": output,
                "combine_columns": combine_columns,
                "column_indices": column_indices,
                "conversion_list": conversion_list,
                "drop_words": drop_words,
                "output_format": output_format,
                "n_gram": n_gram,
                "skip_wc": skip_wc,
                "stop_list": stop_list,
                "trim_s": trim_s,
                "prune_interval": prune_interval,
                "prune_threshold_value": prune_threshold_value,
            },
        )

    def mem(
        self,
        *,
        input: str,
        output: str,
        save_theme_scores: bool = False,
        combine_columns: str | None = None,
        column_indices: str | None = None,
        conversion_list: str | None = None,
        enable_pca: bool = False,
        output_format: str | None = None,
        index_of_id_column: int | None = None,
        mem_output_type: str | None = None,
        n_gram: int | None = None,
        segmentation: str | None = None,
        skip_wc: int | None = None,
        stop_list: str | None = None,
        trim_s: str | None = None,
        threshold_type: str | None = None,
        threshold_value: float | None = None,
        prune_interval: int | None = None,
        prune_threshold_value: int | None = None,
        column_delimiter: str | None = None,
    ) -> int:
        """
        Run Meaning Extraction Method (MEM) analysis.

        Builds a document-term matrix over the input corpus and optionally runs
        Principal Component Analysis to surface latent themes.

        Parameters
        ----------
        input : :class:`str`
            Path to input file or folder.
        output : :class:`str`
            Output file/folder path, or ``"console"``.
        save_theme_scores : :class:`bool`, optional
            Create and save theme scores table for PCA analysis (default ``False``).
        combine_columns : :class:`str`, optional
            Combine spreadsheet columns into a single text per row (default: yes).
        column_indices : :class:`str`, optional
            Comma-separated column indices (1-based) containing analysable text.
            All columns processed by default.
        conversion_list : :class:`str`, optional
            Path to a conversion list or an internal list name (e.g.
            ``internal-EN``). Use ``"none"`` for no conversion.
        enable_pca : :class:`bool`, optional
            Enable Principal Component Analysis for MEM (default ``False``).
        output_format : :class:`str`, optional
            Output file format - one of ``csv``, ``xlsx``, ``ndjson`` (default: csv).
        index_of_id_column : :class:`int`, optional
            Column index (1-based) to use as row identifier.
        mem_output_type : :class:`str`, optional
            Document-term matrix format - one of ``binary`` (default),
            ``relative-freq``, or ``raw-counts``.
        n_gram : :class:`int`, optional
            N-gram size (1-5). Inclusive of all lower n-grams (default: 1).
        segmentation : :class:`str`, optional
            Split text into segments. Syntax varies by mode.
        skip_wc : :class:`int`, optional
            Skip texts with word count less than this value (default: 10).
        stop_list : :class:`str`, optional
            Path to a stop list, an internal list name (e.g. ``internal-EN``),
            or ``"none"`` (default: internal-EN).
        trim_s : :class:`str`, optional
            Trim trailing ``'s`` from words (default: yes).
        threshold_type : :class:`str`, optional
            Cutoff type for word inclusion - one of ``min-obspct`` (default),
            ``min-freq``, ``top-obspct``, ``top-freq``.
        threshold_value : :class:`float`, optional
            Threshold cutoff value (default: 10.0).
        prune_interval : :class:`int`, optional
            Prune frequency list every N words to optimise RAM (default: 10000000).
        prune_threshold_value : :class:`int`, optional
            Minimum n-gram frequency retained during pruning (default: 5).
        column_delimiter : :class:`str`, optional
            Delimiter between grams in n-gram column names (default: space).

        Returns
        -------
        :class:`int`
            Return code from the LIWC-22 CLI process (0 = success).

        Raises
        ------
        :class:`SystemExit`
            If LIWC-22 is not running and ``auto_open=False`` was passed at
            construction.

        Examples
        --------
        >>> Liwc22(dry_run=True).mem(  # doctest: +SKIP
        ...     input="texts/",
        ...     output="mem.csv",
        ...     enable_pca=True,
        ... )
        0
        """
        return self._run_mode(
            "mem",
            {
                "input": input,
                "output": output,
                "save_theme_scores": save_theme_scores,
                "combine_columns": combine_columns,
                "column_indices": column_indices,
                "conversion_list": conversion_list,
                "enable_pca": enable_pca,
                "output_format": output_format,
                "index_of_id_column": index_of_id_column,
                "mem_output_type": mem_output_type,
                "n_gram": n_gram,
                "segmentation": segmentation,
                "skip_wc": skip_wc,
                "stop_list": stop_list,
                "trim_s": trim_s,
                "threshold_type": threshold_type,
                "threshold_value": threshold_value,
                "prune_interval": prune_interval,
                "prune_threshold_value": prune_threshold_value,
                "column_delimiter": column_delimiter,
            },
        )

    def context(
        self,
        *,
        input: str,
        output: str,
        category_to_contextualize: str | None = None,
        combine_columns: str | None = None,
        column_indices: str | None = None,
        dictionary: str | None = None,
        index_of_id_column: int | None = None,
        keep_punctuation: str | None = None,
        word_window_left: int | None = None,
        word_window_right: int | None = None,
        word_list: str | None = None,
        words_to_contextualize: str | None = None,
    ) -> int:
        """
        Run LIWC-22 Contextualizer analysis.

        Extracts the surrounding context (configurable window of words to the
        left and right) for each occurrence of a target word or dictionary
        category.

        Parameters
        ----------
        input : :class:`str`
            Path to input file or folder.
        output : :class:`str`
            Output file/folder path, or ``"console"``.
        category_to_contextualize : :class:`str`, optional
            Dictionary category to contextualise (default: first category).
        combine_columns : :class:`str`, optional
            Combine spreadsheet columns into a single text per row (default: yes).
        column_indices : :class:`str`, optional
            Comma-separated column indices (1-based) containing analysable text.
            All columns processed by default.
        dictionary : :class:`str`, optional
            LIWC dictionary name (e.g. ``LIWC22``, ``LIWC2015``) or path to a
            custom ``.dicx`` file (default: LIWC22).
        index_of_id_column : :class:`int`, optional
            Column index (1-based) to use as row identifier.
        keep_punctuation : :class:`str`, optional
            Include punctuation in context items (default: yes).
        word_window_left : :class:`int`, optional
            Context words to the left of the target word (default: 3).
        word_window_right : :class:`int`, optional
            Context words to the right of the target word (default: 3).
        word_list : :class:`str`, optional
            Path to a word list file for contextualisation. Wildcards (``*``) allowed.
        words_to_contextualize : :class:`str`, optional
            Comma-separated words to contextualise. Wildcards (``*``) allowed.

        Returns
        -------
        :class:`int`
            Return code from the LIWC-22 CLI process (0 = success).

        Raises
        ------
        :class:`SystemExit`
            If LIWC-22 is not running and ``auto_open=False`` was passed at
            construction.

        Examples
        --------
        >>> Liwc22(dry_run=True).context(input="data.txt", output="ctx.csv")  # doctest: +SKIP
        0
        """
        return self._run_mode(
            "context",
            {
                "input": input,
                "output": output,
                "category_to_contextualize": category_to_contextualize,
                "combine_columns": combine_columns,
                "column_indices": column_indices,
                "dictionary": dictionary,
                "index_of_id_column": index_of_id_column,
                "keep_punctuation": keep_punctuation,
                "word_window_left": word_window_left,
                "word_window_right": word_window_right,
                "word_list": word_list,
                "words_to_contextualize": words_to_contextualize,
            },
        )

    def arc(
        self,
        *,
        input: str,
        output: str,
        combine_columns: str | None = None,
        column_indices: str | None = None,
        output_data_points: str | None = None,
        output_format: str | None = None,
        index_of_id_column: int | None = None,
        scaling_method: str | None = None,
        segments_number: int | None = None,
        skip_wc: int | None = None,
    ) -> int:
        """
        Analyse the narrative arc of texts.

        Scores how a text's narrative trajectory (staging, plot progression,
        cognitive tension) varies across segments.

        Parameters
        ----------
        input : :class:`str`
            Path to input file or folder.
        output : :class:`str`
            Output file/folder path, or ``"console"``.
        combine_columns : :class:`str`, optional
            Combine spreadsheet columns into a single text per row (default: yes).
        column_indices : :class:`str`, optional
            Comma-separated column indices (1-based) containing analysable text.
            All columns processed by default.
        output_data_points : :class:`str`, optional
            Output individual data points (default: yes).
        output_format : :class:`str`, optional
            Output file format - one of ``csv``, ``xlsx``, ``ndjson`` (default: csv).
        index_of_id_column : :class:`int`, optional
            Column index (1-based) to use as row identifier.
        scaling_method : :class:`str`, optional
            Scaling method - ``"1"`` = 0-100 scale (default), ``"2"`` = Z-score.
        segments_number : :class:`int`, optional
            Number of segments to divide text into (default: 5).
        skip_wc : :class:`int`, optional
            Skip texts with word count less than this value (default: 10).

        Returns
        -------
        :class:`int`
            Return code from the LIWC-22 CLI process (0 = success).

        Raises
        ------
        :class:`SystemExit`
            If LIWC-22 is not running and ``auto_open=False`` was passed at
            construction.

        Examples
        --------
        >>> Liwc22(dry_run=True).arc(input="stories/", output="arc.csv")  # doctest: +SKIP
        0
        """
        return self._run_mode(
            "arc",
            {
                "input": input,
                "output": output,
                "combine_columns": combine_columns,
                "column_indices": column_indices,
                "output_data_points": output_data_points,
                "output_format": output_format,
                "index_of_id_column": index_of_id_column,
                "scaling_method": scaling_method,
                "segments_number": segments_number,
                "skip_wc": skip_wc,
            },
        )

    def ct(
        self,
        *,
        input: str,
        output: str,
        speaker_list: str,
        omit_speakers_num_turns: int | None = None,
        omit_speakers_word_count: int | None = None,
        regex_removal: str | None = None,
        single_line: bool = False,
    ) -> int:
        """
        Convert separate transcript files into a single spreadsheet.

        Parameters
        ----------
        input : :class:`str`
            Path to input file or folder.
        output : :class:`str`
            Output file/folder path, or ``"console"``.
        speaker_list : :class:`str`
            Path to a text/csv/xlsx file containing a list of speakers.
        omit_speakers_num_turns : :class:`int`, optional
            Omit speakers with fewer turns than this value (default: 0).
        omit_speakers_word_count : :class:`int`, optional
            Omit speakers with word count less than this value (default: 10).
        regex_removal : :class:`str`, optional
            Regex pattern; first match is removed from each line.
        single_line : :class:`bool`, optional
            Don't combine untagged lines with the previous speaker. Lines
            without speaker tags will be ignored (default ``False``).

        Returns
        -------
        :class:`int`
            Return code from the LIWC-22 CLI process (0 = success).

        Raises
        ------
        :class:`SystemExit`
            If LIWC-22 is not running and ``auto_open=False`` was passed at
            construction.

        Examples
        --------
        >>> Liwc22(dry_run=True).ct(  # doctest: +SKIP
        ...     input="transcripts/",
        ...     output="merged.csv",
        ...     speaker_list="speakers.txt",
        ... )
        0
        """
        return self._run_mode(
            "ct",
            {
                "input": input,
                "output": output,
                "speaker_list": speaker_list,
                "omit_speakers_num_turns": omit_speakers_num_turns,
                "omit_speakers_word_count": omit_speakers_word_count,
                "regex_removal": regex_removal,
                "single_line": single_line,
            },
        )

    def lsm(
        self,
        *,
        input: str,
        output: str,
        calculate_lsm: str,
        group_column: int,
        output_type: str,
        person_column: int,
        text_column: int,
        expanded_output: bool = False,
        output_format: str | None = None,
        omit_speakers_num_turns: int | None = None,
        omit_speakers_word_count: int | None = None,
        segmentation: str | None = None,
        single_line: bool = False,
    ) -> int:
        """
        Run Language Style Matching (LSM) analysis.

        Computes how closely speakers align in their use of function words,
        either person-to-person or within groups.

        Parameters
        ----------
        input : :class:`str`
            Path to input file or folder.
        output : :class:`str`
            Output file/folder path, or ``"console"``.
        calculate_lsm : :class:`str`
            LSM calculation type - ``"1"`` = person-level, ``"2"`` = group-level,
            ``"3"`` = both (default: 3).
        group_column : :class:`int`
            Group ID column index (1-based). Use ``0`` for no groups.
        output_type : :class:`str`
            Output type - ``"1"`` = one-to-many (default), ``"2"`` = pairwise.
        person_column : :class:`int`
            Person ID column index (1-based).
        text_column : :class:`int`
            Text column index (1-based).
        expanded_output : :class:`bool`, optional
            Include expanded LSM output (default ``False``).
        output_format : :class:`str`, optional
            Output file format - one of ``csv``, ``xlsx``, ``ndjson`` (default: csv).
        omit_speakers_num_turns : :class:`int`, optional
            Omit speakers with fewer turns than this value (default: 0).
        omit_speakers_word_count : :class:`int`, optional
            Omit speakers with word count less than this value (default: 10).
        segmentation : :class:`str`, optional
            Split text into segments. Syntax varies by mode.
        single_line : :class:`bool`, optional
            Don't combine untagged lines with the previous speaker. Lines
            without speaker tags will be ignored (default ``False``).

        Returns
        -------
        :class:`int`
            Return code from the LIWC-22 CLI process (0 = success).

        Raises
        ------
        :class:`SystemExit`
            If LIWC-22 is not running and ``auto_open=False`` was passed at
            construction.

        Examples
        --------
        >>> Liwc22(dry_run=True).lsm(  # doctest: +SKIP
        ...     input="chat.csv",
        ...     output="lsm.csv",
        ...     calculate_lsm="3",
        ...     group_column=1,
        ...     output_type="1",
        ...     person_column=2,
        ...     text_column=3,
        ... )
        0
        """
        return self._run_mode(
            "lsm",
            {
                "input": input,
                "output": output,
                "calculate_lsm": calculate_lsm,
                "group_column": group_column,
                "output_type": output_type,
                "person_column": person_column,
                "text_column": text_column,
                "expanded_output": expanded_output,
                "output_format": output_format,
                "omit_speakers_num_turns": omit_speakers_num_turns,
                "omit_speakers_word_count": omit_speakers_word_count,
                "segmentation": segmentation,
                "single_line": single_line,
            },
        )
