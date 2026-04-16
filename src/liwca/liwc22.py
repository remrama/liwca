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
import warnings
from collections.abc import Iterable
from pathlib import Path
from typing import Any

__all__ = [
    "Liwc22",
    "build_command",
    "FLAG_BY_DEST",
    "BOOL_FLAGS",
    "YES_NO_FLAGS",
    "ONE_ZERO_FLAGS",
    "LIST_FLAGS",
    "COLUMN_FLAGS",
    "COLUMN_LIST_FLAGS",
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

# Dests whose Python value is a :class:`bool` that maps to the CLI value
# ``"yes"`` or ``"no"`` (the LIWC-22 CLI uses yes/no string enums for these).
YES_NO_FLAGS: frozenset[str] = frozenset(
    {
        "count_urls",
        "include_subfolders",
        "skip_header",
        "combine_columns",
        "trim_s",
        "keep_punctuation",
        "output_data_points",
    }
)

# Dests whose Python value is a :class:`bool` that maps to the CLI value
# ``"1"`` or ``"0"``.  Currently only ``clean_escaped_spaces`` uses this
# encoding but the category exists for symmetry with :data:`YES_NO_FLAGS`.
ONE_ZERO_FLAGS: frozenset[str] = frozenset({"clean_escaped_spaces"})

# Dests whose Python value is an iterable of strings, emitted as a single
# comma-joined CLI argument.  Column-list entries (``column_indices``,
# ``row_id_indices``) are resolved to 1-based ints by :func:`_resolve_columns`
# *before* ``build_command`` sees them, so every element is safely stringable
# by the time it reaches the comma-join.
LIST_FLAGS: frozenset[str] = frozenset(
    {
        "include_categories",
        "exclude_categories",
        "words_to_contextualize",
        "column_indices",
        "row_id_indices",
    }
)

# Dests that accept a single column reference - a 0-based Python ``int`` or a
# column-name ``str``.  :func:`_resolve_columns` normalises both to a 1-based
# int before ``build_command``.
COLUMN_FLAGS: frozenset[str] = frozenset(
    {
        "index_of_id_column",
        "group_column",
        "person_column",
        "text_column",
    }
)

# Dests that accept an iterable of column references (``int | str``), with
# the same 0-based-int / column-name semantics as :data:`COLUMN_FLAGS`.
COLUMN_LIST_FLAGS: frozenset[str] = frozenset(
    {
        "column_indices",
        "row_id_indices",
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

    Args whose value is ``None`` are skipped (unset).  Each dest is
    emitted according to its category:

    * :data:`BOOL_FLAGS` - emit the flag alone when ``True``; omit when
      ``False``.
    * :data:`YES_NO_FLAGS` - emit ``flag yes`` or ``flag no``.
    * :data:`ONE_ZERO_FLAGS` - emit ``flag 1`` or ``flag 0``.
    * :data:`LIST_FLAGS` - emit ``flag a,b,c`` (comma-joined).
    * Everything else - emit ``flag value`` (``value`` stringified).

    Column args (:data:`COLUMN_FLAGS`, :data:`COLUMN_LIST_FLAGS`) are
    normalised to 1-based ints by :func:`_resolve_columns` *before* being
    passed here, so they are treated as ordinary value/list flags.

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
        elif dest in YES_NO_FLAGS:
            cmd.extend([flag, "yes" if value else "no"])
        elif dest in ONE_ZERO_FLAGS:
            cmd.extend([flag, "1" if value else "0"])
        elif dest in LIST_FLAGS:
            cmd.extend([flag, ",".join(str(v) for v in value)])
        else:
            cmd.extend([flag, str(value)])
    return cmd


def _read_header(
    input_path: str,
    *,
    csv_delimiter: str | None,
    encoding: str | None,
) -> list[str]:
    """Return the list of column names for ``input_path``.

    Picks the pandas reader from the file extension - ``.xlsx`` / ``.xls``
    use :func:`pandas.read_excel`; everything else is treated as a
    delimited text file and read with :func:`pandas.read_csv`.  When no
    explicit ``csv_delimiter`` is passed, the delimiter defaults to a tab
    for ``.tsv`` inputs and a comma otherwise.
    """
    import pandas as pd

    path = Path(input_path)
    suffix = path.suffix.lower()

    if suffix in {".xlsx", ".xls"}:
        frame = pd.read_excel(path, nrows=0)
    else:
        delim = csv_delimiter if csv_delimiter is not None else ("\t" if suffix == ".tsv" else ",")
        frame = pd.read_csv(path, sep=delim, encoding=encoding or "utf-8", nrows=0)

    return [str(c) for c in frame.columns]


def _needs_header(cli_args: dict[str, Any]) -> bool:
    """Return ``True`` if any column arg in ``cli_args`` is a name (``str``)."""
    for dest in COLUMN_FLAGS:
        if isinstance(cli_args.get(dest), str):
            return True
    for dest in COLUMN_LIST_FLAGS:
        value = cli_args.get(dest)
        if value is not None and any(isinstance(v, str) for v in value):
            return True
    return False


def _acquire_header(
    input_path: Any,
    *,
    csv_delimiter: str | None,
    encoding: str | None,
    skip_header: bool | None,
) -> list[str]:
    """Read the input file's header, validating the request first.

    Raises :class:`ValueError` if the input configuration rules out a
    meaningful header row (e.g. ``skip_header=False``, console/envvar input,
    directory input, or a missing path).
    """
    if skip_header is False:
        raise ValueError(
            "Cannot pass a column name when skip_header=False; "
            "the input has no header row to look up names in. "
            "Use a 0-based integer index instead."
        )
    if not isinstance(input_path, str):
        raise ValueError("Cannot resolve column names: no `input` path was provided.")
    if input_path.lower() in {"console", "envvar"}:
        raise ValueError(
            f"Cannot resolve column names when input={input_path!r}; "
            "use a 0-based integer index instead."
        )
    if Path(input_path).is_dir():
        raise ValueError(
            "Cannot resolve column names when the input is a directory; "
            "use a 0-based integer index instead."
        )
    return _read_header(input_path, csv_delimiter=csv_delimiter, encoding=encoding)


def _coerce_column(value: Any, dest: str, header: list[str] | None, input_path: Any) -> Any:
    """Translate one column-arg value to its 1-based CLI form."""
    if value is None:
        return None
    if isinstance(value, bool):
        # ``bool`` is a subclass of ``int``; reject explicitly so a stray
        # True/False doesn't silently become column 2/1.
        raise TypeError(
            f"Column arg {dest!r} received a bool; pass an int (0-based) or a column-name string."
        )
    if isinstance(value, int):
        return value + 1
    if isinstance(value, str):
        assert header is not None  # caller guarantees this when a name is passed
        try:
            return header.index(value) + 1
        except ValueError:
            raise ValueError(
                f"Column {value!r} not found in header of {input_path!r}. "
                f"Available columns: {header}"
            ) from None
    raise TypeError(
        f"Column arg {dest!r} must be an int (0-based) or str "
        f"(column name), not {type(value).__name__}."
    )


def _resolve_columns(
    cli_args: dict[str, Any],
    *,
    input_path: Any,
    csv_delimiter: str | None,
    encoding: str | None,
    skip_header: bool | None,
) -> dict[str, Any]:
    """Normalise every column arg in ``cli_args`` to a 1-based ``int``.

    Each value in :data:`COLUMN_FLAGS` or :data:`COLUMN_LIST_FLAGS` is
    translated as follows:

    * ``int``  - interpreted as a 0-based Python index, emitted as 1-based.
    * ``str``  - resolved to the 1-based position of the column in the
      input file's header row.
    * ``None`` - left as-is; the caller decides whether to emit.

    The special case ``group_column=None`` (the ``lsm`` mode's sentinel for
    "no groups") is rewritten to the literal ``0`` the CLI expects.

    A single header read is performed lazily - only if at least one column
    arg is a ``str`` - so int-only calls remain zero-I/O.
    """
    resolved: dict[str, Any] = dict(cli_args)

    header: list[str] | None = None
    if _needs_header(cli_args):
        header = _acquire_header(
            input_path,
            csv_delimiter=csv_delimiter,
            encoding=encoding,
            skip_header=skip_header,
        )

    for dest in COLUMN_FLAGS:
        if dest not in cli_args:
            continue
        value = cli_args[dest]
        if dest == "group_column" and value is None:
            # lsm's sentinel for "no groups" - the CLI expects literal 0.
            resolved[dest] = 0
        else:
            resolved[dest] = _coerce_column(value, dest, header, input_path)

    for dest in COLUMN_LIST_FLAGS:
        if dest not in cli_args or cli_args[dest] is None:
            continue
        resolved[dest] = [_coerce_column(v, dest, header, input_path) for v in cli_args[dest]]

    return resolved


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
        Input file encoding (CLI default: UTF-8).
    csv_delimiter : :class:`str`, optional
        CSV delimiter character (CLI default: ``,``).  Use ``"\\t"`` for tab-
        separated files.  Passing a ``.tsv`` input without setting this emits a
        :class:`UserWarning`.
    csv_escape : :class:`str`, optional
        CSV escape character (CLI default: none).
    csv_quote : :class:`str`, optional
        CSV quote character (CLI default: ``"``).
    include_subfolders : :class:`bool`, optional
        If ``True``, include subfolders when analysing a directory input.
        ``None`` leaves the CLI default ("yes") in place.
    skip_header : :class:`bool`, optional
        If ``True``, skip the first row of an Excel/CSV file (i.e. treat it as
        a header).  ``None`` leaves the CLI default ("yes") in place.  Setting
        ``False`` disables column-*name* resolution in the mode methods.
    preprocess_cjk : :class:`str`, optional
        Preprocess CJK text with Jieba (Chinese) or Kuromoji (Japanese)
        tokeniser - one of ``"chinese"``, ``"japanese"``, ``"none"``.
    url_regexp : :class:`str`, optional
        Regular expression used to capture URLs in text.
    count_urls : :class:`bool`, optional
        If ``True``, count URLs as a single word.  Only meaningful if
        *url_regexp* is set.  ``None`` leaves the CLI default ("yes") in place.
    precision : :class:`int`, optional
        Number of decimal places in output (0-16, CLI default: 2).
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
        # I/O encoding
        encoding: str | None = None,
        csv_delimiter: str | None = None,
        csv_escape: str | None = None,
        csv_quote: str | None = None,
        # File / folder handling
        include_subfolders: bool | None = None,
        skip_header: bool | None = None,
        # Text preprocessing
        preprocess_cjk: str | None = None,
        url_regexp: str | None = None,
        count_urls: bool | None = None,
        # Output
        precision: int | None = None,
        # Execution control
        auto_open: bool = False,
        use_gui: bool = False,
        dry_run: bool = False,
    ) -> None:
        self._globals: dict[str, Any] = {
            "encoding": encoding,
            "csv_delimiter": csv_delimiter,
            "csv_escape": csv_escape,
            "csv_quote": csv_quote,
            "include_subfolders": include_subfolders,
            "skip_header": skip_header,
            "preprocess_cjk": preprocess_cjk,
            "url_regexp": url_regexp,
            "count_urls": count_urls,
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
        """Merge hoisted globals, validate, resolve columns, and run."""
        # 1. Merge hoisted globals (filtered by MODE_GLOBALS[mode]).
        applicable = MODE_GLOBALS[mode]
        merged: dict[str, Any] = {k: v for k, v in self._globals.items() if k in applicable}
        merged.update(cli_args)

        # 2. Soft-validate: TSV input without an explicit delimiter.
        input_path = merged.get("input")
        if (
            isinstance(input_path, str)
            and input_path.lower().endswith(".tsv")
            and self._globals.get("csv_delimiter") is None
        ):
            warnings.warn(
                "Input looks like a TSV but csv_delimiter is not set; pass "
                r"csv_delimiter='\t' to Liwc22(...) to parse it as tab-separated.",
                UserWarning,
                stacklevel=3,
            )

        # 3. Normalise column args (0-based int -> 1-based; name -> 1-based).
        merged = _resolve_columns(
            merged,
            input_path=input_path,
            csv_delimiter=self._globals.get("csv_delimiter"),
            encoding=self._globals.get("encoding"),
            skip_header=self._globals.get("skip_header"),
        )

        # 4. Run.  If we already launched the app in __enter__, don't re-launch.
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
        console_text: str | None = None,
        environment_variable: str | None = None,
        clean_escaped_spaces: bool | None = None,
        column_indices: Iterable[int | str] | None = None,
        combine_columns: bool | None = None,
        row_id_indices: Iterable[int | str] | None = None,
        dictionary: str | None = None,
        include_categories: Iterable[str] | None = None,
        exclude_categories: Iterable[str] | None = None,
        segmentation: str | None = None,
        output_format: str | None = None,
        threads: int | None = None,
    ) -> int:
        """
        Run a standard LIWC-22 word count analysis.

        Scores each input text against a LIWC dictionary (default ``LIWC22``)
        and reports per-category word counts or percentages.

        Parameters
        ----------
        input : :class:`str`
            Path to input file or folder.  Use ``"console"`` with
            *console_text* or ``"envvar"`` with *environment_variable* to
            analyse literal text.
        output : :class:`str`
            Output file/folder path, or ``"console"``.
        console_text : :class:`str`, optional
            Text string to analyse.  Use with ``input="console"``.
        environment_variable : :class:`str`, optional
            Environment variable name containing text.  Use with
            ``input="envvar"``.
        clean_escaped_spaces : :class:`bool`, optional
            With ``input="console"``: if ``True``, escaped spaces like
            ``\\n`` are converted to actual spaces (CLI default: ``True``).
        column_indices : iterable of :class:`int` or :class:`str`, optional
            Columns containing analysable text.  Each entry is either a
            0-based integer index or a column-name string (requires the
            input to have a header row).  All columns processed by default.
        combine_columns : :class:`bool`, optional
            If ``True``, combine spreadsheet columns into a single text per
            row (CLI default: ``True``).
        row_id_indices : iterable of :class:`int` or :class:`str`, optional
            Columns to use as row identifiers - 0-based integer indices or
            column-name strings.  Multiple columns are concatenated with
            ``;``.  Defaults to row number.
        dictionary : :class:`str`, optional
            LIWC dictionary name (e.g. ``LIWC22``, ``LIWC2015``) or path to a
            custom ``.dicx`` file (default: LIWC22).
        include_categories : iterable of :class:`str`, optional
            Dictionary categories to include in output.  Mutually exclusive
            with *exclude_categories*.
        exclude_categories : iterable of :class:`str`, optional
            Dictionary categories to exclude from output.  Mutually exclusive
            with *include_categories*.
        segmentation : :class:`str`, optional
            Split text into segments.  Syntax varies by mode - see the
            `LIWC CLI documentation <https://www.liwc.app/help/cli>`_.
        output_format : :class:`str`, optional
            Output file format - one of ``csv``, ``xlsx``, ``ndjson`` (default: csv).
        threads : :class:`int`, optional
            Number of processing threads (default: available cores - 1).

        Returns
        -------
        :class:`int`
            Return code from the LIWC-22 CLI process (0 = success).

        Raises
        ------
        :class:`ValueError`
            If both *include_categories* and *exclude_categories* are set.
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
        if include_categories is not None and exclude_categories is not None:
            raise ValueError(
                "Cannot pass both include_categories and exclude_categories; choose one."
            )
        return self._run_mode(
            "wc",
            {
                "input": input,
                "output": output,
                "console_text": console_text,
                "environment_variable": environment_variable,
                "clean_escaped_spaces": clean_escaped_spaces,
                "column_indices": column_indices,
                "combine_columns": combine_columns,
                "row_id_indices": row_id_indices,
                "dictionary": dictionary,
                "include_categories": include_categories,
                "exclude_categories": exclude_categories,
                "segmentation": segmentation,
                "output_format": output_format,
                "threads": threads,
            },
        )

    def freq(
        self,
        *,
        input: str,
        output: str,
        column_indices: Iterable[int | str] | None = None,
        combine_columns: bool | None = None,
        conversion_list: str | None = None,
        stop_list: str | None = None,
        trim_s: bool | None = None,
        n_gram: int | None = None,
        skip_wc: int | None = None,
        drop_words: int | None = None,
        prune_interval: int | None = None,
        prune_threshold_value: int | None = None,
        output_format: str | None = None,
    ) -> int:
        """
        Compute word (and n-gram) frequencies across input texts.

        Parameters
        ----------
        input : :class:`str`
            Path to input file or folder.
        output : :class:`str`
            Output file/folder path, or ``"console"``.
        column_indices : iterable of :class:`int` or :class:`str`, optional
            Columns containing analysable text - 0-based integer indices or
            column-name strings (requires the input to have a header row).
            All columns processed by default.
        combine_columns : :class:`bool`, optional
            If ``True``, combine spreadsheet columns into a single text per
            row (CLI default: ``True``).
        conversion_list : :class:`str`, optional
            Path to a conversion list or an internal list name (e.g.
            ``internal-EN``). Use ``"none"`` for no conversion.
        stop_list : :class:`str`, optional
            Path to a stop list, an internal list name (e.g. ``internal-EN``),
            or ``"none"`` (default: internal-EN).
        trim_s : :class:`bool`, optional
            If ``True``, trim trailing ``'s`` from words (CLI default: ``True``).
        n_gram : :class:`int`, optional
            N-gram size (1-5). Inclusive of all lower n-grams (default: 1).
        skip_wc : :class:`int`, optional
            Skip texts with word count less than this value (default: 10).
        drop_words : :class:`int`, optional
            Drop n-grams with frequency less than this value (default: 5).
        prune_interval : :class:`int`, optional
            Prune frequency list every N words to optimise RAM (default: 10000000).
        prune_threshold_value : :class:`int`, optional
            Minimum n-gram frequency retained during pruning (default: 5).
        output_format : :class:`str`, optional
            Output file format - one of ``csv``, ``xlsx``, ``ndjson`` (default: csv).

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
                "column_indices": column_indices,
                "combine_columns": combine_columns,
                "conversion_list": conversion_list,
                "stop_list": stop_list,
                "trim_s": trim_s,
                "n_gram": n_gram,
                "skip_wc": skip_wc,
                "drop_words": drop_words,
                "prune_interval": prune_interval,
                "prune_threshold_value": prune_threshold_value,
                "output_format": output_format,
            },
        )

    def mem(
        self,
        *,
        input: str,
        output: str,
        column_indices: Iterable[int | str] | None = None,
        combine_columns: bool | None = None,
        index_of_id_column: int | str | None = None,
        conversion_list: str | None = None,
        stop_list: str | None = None,
        trim_s: bool | None = None,
        n_gram: int | None = None,
        skip_wc: int | None = None,
        segmentation: str | None = None,
        threshold_type: str | None = None,
        threshold_value: float | None = None,
        mem_output_type: str | None = None,
        enable_pca: bool = False,
        save_theme_scores: bool = False,
        column_delimiter: str | None = None,
        prune_interval: int | None = None,
        prune_threshold_value: int | None = None,
        output_format: str | None = None,
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
        column_indices : iterable of :class:`int` or :class:`str`, optional
            Columns containing analysable text - 0-based integer indices or
            column-name strings.  All columns processed by default.
        combine_columns : :class:`bool`, optional
            If ``True``, combine spreadsheet columns into a single text per
            row (CLI default: ``True``).
        index_of_id_column : :class:`int` or :class:`str`, optional
            Column to use as row identifier - 0-based integer index or
            column-name string.
        conversion_list : :class:`str`, optional
            Path to a conversion list or an internal list name (e.g.
            ``internal-EN``). Use ``"none"`` for no conversion.
        stop_list : :class:`str`, optional
            Path to a stop list, an internal list name (e.g. ``internal-EN``),
            or ``"none"`` (default: internal-EN).
        trim_s : :class:`bool`, optional
            If ``True``, trim trailing ``'s`` from words (CLI default: ``True``).
        n_gram : :class:`int`, optional
            N-gram size (1-5). Inclusive of all lower n-grams (default: 1).
        skip_wc : :class:`int`, optional
            Skip texts with word count less than this value (default: 10).
        segmentation : :class:`str`, optional
            Split text into segments. Syntax varies by mode.
        threshold_type : :class:`str`, optional
            Cutoff type for word inclusion - one of ``min-obspct`` (default),
            ``min-freq``, ``top-obspct``, ``top-freq``.
        threshold_value : :class:`float`, optional
            Threshold cutoff value (default: 10.0).
        mem_output_type : :class:`str`, optional
            Document-term matrix format - one of ``binary`` (default),
            ``relative-freq``, or ``raw-counts``.
        enable_pca : :class:`bool`, optional
            Enable Principal Component Analysis for MEM (default ``False``).
        save_theme_scores : :class:`bool`, optional
            Create and save theme scores table for PCA analysis (default ``False``).
        column_delimiter : :class:`str`, optional
            Delimiter between grams in n-gram column names (default: space).
        prune_interval : :class:`int`, optional
            Prune frequency list every N words to optimise RAM (default: 10000000).
        prune_threshold_value : :class:`int`, optional
            Minimum n-gram frequency retained during pruning (default: 5).
        output_format : :class:`str`, optional
            Output file format - one of ``csv``, ``xlsx``, ``ndjson`` (default: csv).

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
                "column_indices": column_indices,
                "combine_columns": combine_columns,
                "index_of_id_column": index_of_id_column,
                "conversion_list": conversion_list,
                "stop_list": stop_list,
                "trim_s": trim_s,
                "n_gram": n_gram,
                "skip_wc": skip_wc,
                "segmentation": segmentation,
                "threshold_type": threshold_type,
                "threshold_value": threshold_value,
                "mem_output_type": mem_output_type,
                "enable_pca": enable_pca,
                "save_theme_scores": save_theme_scores,
                "column_delimiter": column_delimiter,
                "prune_interval": prune_interval,
                "prune_threshold_value": prune_threshold_value,
                "output_format": output_format,
            },
        )

    def context(
        self,
        *,
        input: str,
        output: str,
        column_indices: Iterable[int | str] | None = None,
        combine_columns: bool | None = None,
        index_of_id_column: int | str | None = None,
        dictionary: str | None = None,
        category_to_contextualize: str | None = None,
        word_list: str | None = None,
        words_to_contextualize: Iterable[str] | None = None,
        word_window_left: int | None = None,
        word_window_right: int | None = None,
        keep_punctuation: bool | None = None,
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
        column_indices : iterable of :class:`int` or :class:`str`, optional
            Columns containing analysable text - 0-based integer indices or
            column-name strings.  All columns processed by default.
        combine_columns : :class:`bool`, optional
            If ``True``, combine spreadsheet columns into a single text per
            row (CLI default: ``True``).
        index_of_id_column : :class:`int` or :class:`str`, optional
            Column to use as row identifier - 0-based integer index or
            column-name string.
        dictionary : :class:`str`, optional
            LIWC dictionary name (e.g. ``LIWC22``, ``LIWC2015``) or path to a
            custom ``.dicx`` file (default: LIWC22).
        category_to_contextualize : :class:`str`, optional
            Dictionary category to contextualise (default: first category).
        word_list : :class:`str`, optional
            Path to a word list file for contextualisation.  Wildcards (``*``)
            allowed.
        words_to_contextualize : iterable of :class:`str`, optional
            Words to contextualise.  Wildcards (``*``) allowed.
        word_window_left : :class:`int`, optional
            Context words to the left of the target word (default: 3).
        word_window_right : :class:`int`, optional
            Context words to the right of the target word (default: 3).
        keep_punctuation : :class:`bool`, optional
            If ``True``, include punctuation in context items (CLI default:
            ``True``).

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
                "column_indices": column_indices,
                "combine_columns": combine_columns,
                "index_of_id_column": index_of_id_column,
                "dictionary": dictionary,
                "category_to_contextualize": category_to_contextualize,
                "word_list": word_list,
                "words_to_contextualize": words_to_contextualize,
                "word_window_left": word_window_left,
                "word_window_right": word_window_right,
                "keep_punctuation": keep_punctuation,
            },
        )

    def arc(
        self,
        *,
        input: str,
        output: str,
        column_indices: Iterable[int | str] | None = None,
        combine_columns: bool | None = None,
        index_of_id_column: int | str | None = None,
        segments_number: int | None = None,
        scaling_method: int | None = None,
        skip_wc: int | None = None,
        output_data_points: bool | None = None,
        output_format: str | None = None,
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
        column_indices : iterable of :class:`int` or :class:`str`, optional
            Columns containing analysable text - 0-based integer indices or
            column-name strings.  All columns processed by default.
        combine_columns : :class:`bool`, optional
            If ``True``, combine spreadsheet columns into a single text per
            row (CLI default: ``True``).
        index_of_id_column : :class:`int` or :class:`str`, optional
            Column to use as row identifier - 0-based integer index or
            column-name string.
        segments_number : :class:`int`, optional
            Number of segments to divide text into (default: 5).
        scaling_method : :class:`int`, optional
            Scaling method - ``1`` = 0-100 scale (default), ``2`` = Z-score.
        skip_wc : :class:`int`, optional
            Skip texts with word count less than this value (default: 10).
        output_data_points : :class:`bool`, optional
            If ``True``, output individual data points (CLI default: ``True``).
        output_format : :class:`str`, optional
            Output file format - one of ``csv``, ``xlsx``, ``ndjson`` (default: csv).

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
                "column_indices": column_indices,
                "combine_columns": combine_columns,
                "index_of_id_column": index_of_id_column,
                "segments_number": segments_number,
                "scaling_method": scaling_method,
                "skip_wc": skip_wc,
                "output_data_points": output_data_points,
                "output_format": output_format,
            },
        )

    def ct(
        self,
        *,
        input: str,
        output: str,
        speaker_list: str,
        regex_removal: str | None = None,
        omit_speakers_num_turns: int | None = None,
        omit_speakers_word_count: int | None = None,
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
        regex_removal : :class:`str`, optional
            Regex pattern; first match is removed from each line.
        omit_speakers_num_turns : :class:`int`, optional
            Omit speakers with fewer turns than this value (default: 0).
        omit_speakers_word_count : :class:`int`, optional
            Omit speakers with word count less than this value (default: 10).
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
                "regex_removal": regex_removal,
                "omit_speakers_num_turns": omit_speakers_num_turns,
                "omit_speakers_word_count": omit_speakers_word_count,
                "single_line": single_line,
            },
        )

    def lsm(
        self,
        *,
        input: str,
        output: str,
        text_column: int | str,
        person_column: int | str,
        group_column: int | str | None = None,
        calculate_lsm: int | None = None,
        output_type: int | None = None,
        expanded_output: bool = False,
        segmentation: str | None = None,
        omit_speakers_num_turns: int | None = None,
        omit_speakers_word_count: int | None = None,
        single_line: bool = False,
        output_format: str | None = None,
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
        text_column : :class:`int` or :class:`str`
            Column containing the text - 0-based integer index or
            column-name string (requires the input to have a header row).
        person_column : :class:`int` or :class:`str`
            Person ID column - 0-based integer index or column-name string.
        group_column : :class:`int` or :class:`str`, optional
            Group ID column - 0-based integer index or column-name string.
            ``None`` (the default) means "no groups".
        calculate_lsm : :class:`int`, optional
            LSM calculation type - ``1`` = person-level, ``2`` = group-level,
            ``3`` = both (default: 3).
        output_type : :class:`int`, optional
            Output type - ``1`` = one-to-many (default), ``2`` = pairwise.
        expanded_output : :class:`bool`, optional
            Include expanded LSM output (default ``False``).
        segmentation : :class:`str`, optional
            Split text into segments. Syntax varies by mode.
        omit_speakers_num_turns : :class:`int`, optional
            Omit speakers with fewer turns than this value (default: 0).
        omit_speakers_word_count : :class:`int`, optional
            Omit speakers with word count less than this value (default: 10).
        single_line : :class:`bool`, optional
            Don't combine untagged lines with the previous speaker. Lines
            without speaker tags will be ignored (default ``False``).
        output_format : :class:`str`, optional
            Output file format - one of ``csv``, ``xlsx``, ``ndjson`` (default: csv).

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
        ...     text_column="text",
        ...     person_column="speaker",
        ...     calculate_lsm=3,
        ...     output_type=1,
        ... )
        0
        """
        return self._run_mode(
            "lsm",
            {
                "input": input,
                "output": output,
                "text_column": text_column,
                "person_column": person_column,
                "group_column": group_column,
                "calculate_lsm": calculate_lsm,
                "output_type": output_type,
                "expanded_output": expanded_output,
                "segmentation": segmentation,
                "omit_speakers_num_turns": omit_speakers_num_turns,
                "omit_speakers_word_count": omit_speakers_word_count,
                "single_line": single_line,
                "output_format": output_format,
            },
        )
