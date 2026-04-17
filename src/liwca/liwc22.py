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
>>> liwc = liwca.Liwc22(dry_run=True)
>>> liwc.wc(input="data.csv", output="results.csv")  # doctest: +SKIP

Amortize app-launch across many calls with the context-manager form:

>>> with liwca.Liwc22(auto_open=True, encoding="utf-8") as liwc:  # doctest: +SKIP
...     liwc.wc(input="data.csv", output="wc.csv")
...     liwc.freq(input="data.csv", output="freq.csv", n_gram=2)

See Also
--------
- LIWC CLI documentation: https://www.liwc.app/help/cli
- Python CLI example: https://github.com/ryanboyd/liwc-22-cli-python/blob/main/LIWC-22-cli_Example.py
"""

from __future__ import annotations

import csv
import logging
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import warnings
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pandas as pd
import pandera.pandas as pa

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
    "wc_output_schema",
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
    header_override: list[str] | None = None,
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
    arg is a ``str`` - so int-only calls remain zero-I/O.  When the caller
    already has the header in memory (e.g. from a DataFrame input) it can be
    passed via ``header_override`` to skip the file read entirely.
    """
    resolved: dict[str, Any] = dict(cli_args)

    header: list[str] | None = None
    if _needs_header(cli_args):
        if header_override is not None:
            header = header_override
        else:
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


# ---------------------------------------------------------------------------
# DataFrame input helpers
# ---------------------------------------------------------------------------


def _write_temp_input(df: pd.DataFrame) -> Path:
    """Write *df* to a fresh temp CSV file and return its path.

    The file is kept on disk (``delete=False``) so LIWC-CLI can reopen it on
    Windows; the caller is responsible for deletion in a ``finally`` block.
    """
    fd = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".csv",
        delete=False,
        newline="",
        encoding="utf-8",
    )
    path = Path(fd.name)
    fd.close()
    df.to_csv(path, index=False, quoting=csv.QUOTE_MINIMAL, encoding="utf-8")
    return path


def _validate_df_input(df: pd.DataFrame, *, mode: str, other_args: dict[str, Any]) -> None:
    """Reject obviously-broken DataFrame-input combinations."""
    if mode == "wc" and (
        other_args.get("console_text") is not None
        or other_args.get("environment_variable") is not None
    ):
        raise ValueError(
            "Cannot pass a DataFrame as `input` together with console_text or "
            "environment_variable; choose one input source."
        )
    if df.empty:
        raise ValueError("DataFrame `input` is empty.")


# ---------------------------------------------------------------------------
# ``wc`` output shaping
# ---------------------------------------------------------------------------


# Schema applied to the `wc`-mode output *after* the dynamic reshape in
# :func:`_shape_wc_output`.  The parsers here handle only the static parts
# (naming the column axis ``"Category"``); row-id renaming and Segment
# dropping are dynamic and happen upstream.
wc_output_schema = pa.DataFrameSchema(
    name="LIWC-22 wc output schema",
    description="Schema for LIWC-22 `wc`-mode output DataFrames after shaping.",
    columns={
        r"\S+": pa.Column(regex=True, required=True, nullable=True),
    },
    parsers=[
        pa.Parser(
            lambda df: df.rename_axis("Category", axis=1),
            name="Name column axis 'Category'",
        ),
    ],
    strict=False,
    coerce=False,
    unique_column_names=True,
    checks=[
        pa.Check(lambda df: len(df) > 0, name="At least one document row"),
    ],
)


def _derive_row_id_names(
    row_id_indices: Iterable[int | str] | None,
    *,
    input_columns: list[str] | None,
) -> list[str] | None:
    """Figure out the human-readable name(s) to restore for the Row ID column(s).

    Best-effort:

    * ``row_id_indices is None`` -> return ``None`` (keep LIWC's ``"Row ID"``).
    * all entries are ``str`` -> return them verbatim.
    * all entries are ``int`` and ``input_columns`` is known -> look them up.
    * otherwise -> return ``None`` (fall back to ``"Row ID"``).
    """
    if row_id_indices is None:
        return None
    values = list(row_id_indices)
    if not values:
        return None
    if all(isinstance(v, str) for v in values):
        return [str(v) for v in values]
    if all(isinstance(v, int) and not isinstance(v, bool) for v in values):
        if input_columns is None:
            return None
        try:
            return [input_columns[int(v)] for v in values]
        except IndexError:
            return None
    return None


def _build_row_id_rename_map(columns: Iterable[Any], row_id_names: list[str]) -> dict[str, str]:
    """Map LIWC's ``"Row ID"`` / ``"Row ID 1"`` / ... columns to user names.

    LIWC-CLI names a single row-id column ``"Row ID"`` and multi-column
    row_id_indices as ``"Row ID 1"``, ``"Row ID 2"``, etc.  This builder
    returns a rename dict from those labels to the caller's original names.
    """
    col_list = [str(c) for c in columns]
    rename: dict[str, str] = {}
    if len(row_id_names) == 1 and "Row ID" in col_list:
        rename["Row ID"] = row_id_names[0]
        return rename
    for i, name in enumerate(row_id_names, start=1):
        label = f"Row ID {i}"
        if label in col_list:
            rename[label] = name
    return rename


def _shape_wc_output(df: pd.DataFrame, *, row_id_names: list[str] | None) -> pd.DataFrame:
    """Apply the ``wc``-specific DataFrame shape.

    Steps:

    1. Rename leading ``"Row ID"`` (or ``"Row ID 1"``, ``"Row ID 2"``, ...)
       columns back to *row_id_names*, when provided.
    2. Drop the ``"Segment"`` column if it has a single unique value
       (i.e. no segmentation was used); otherwise keep it for promotion to
       a second index level.
    3. Set the row-id column(s) (and ``"Segment"``, if kept) as the
       DataFrame index.
    4. Validate via :data:`wc_output_schema` - this also names the column
       axis ``"Category"``.
    """
    # 1. Rename leading row-id columns.
    if row_id_names is not None:
        rename_map = _build_row_id_rename_map(df.columns, row_id_names)
        if rename_map:
            df = df.rename(columns=rename_map)
        id_cols = [n for n in row_id_names if n in df.columns]
    else:
        id_cols = [c for c in df.columns if str(c) == "Row ID" or str(c).startswith("Row ID ")]

    # 2. Segment handling.
    segment_kept = False
    if "Segment" in df.columns:
        if df["Segment"].nunique(dropna=False) > 1:
            segment_kept = True
        else:
            df = df.drop(columns="Segment")

    # 3. Set index.
    index_cols: list[Any] = list(id_cols) + (["Segment"] if segment_kept else [])
    if index_cols:
        df = df.set_index(index_cols)

    # 4. Validate + static parsers (column-axis rename).
    return wc_output_schema.validate(df)


def _shape_wc_output_file(
    path: str,
    *,
    row_id_names: list[str] | None,
    output_format: str | None,
) -> None:
    """Read the CLI's ``wc`` output CSV, shape it, and write it back in place.

    If *output_format* is set to anything other than ``"csv"`` / ``None``,
    the step is skipped with a :class:`UserWarning` - we only safely
    round-trip CSV here.
    """
    if output_format is not None and str(output_format).lower() != "csv":
        warnings.warn(
            f"Skipping wc output shaping: output_format={output_format!r} "
            "is not CSV; re-run with output_format='csv' (or omit it) to "
            "get the shaped result.",
            UserWarning,
            stacklevel=3,
        )
        return

    df = pd.read_csv(path)
    shaped = _shape_wc_output(df, row_id_names=row_id_names)
    # Clear the column-axis name before writing; pandas otherwise writes an
    # awkward extra header row.  "Category" lives as an in-memory convention.
    shaped = shaped.rename_axis(None, axis=1)
    shaped.to_csv(path, index=True)


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
) -> None:
    """Run a LIWC-22 CLI command built from a mode + flag dict.

    Executes the subprocess for its side effect (reading *input* and
    writing *output*).  Raises :class:`subprocess.CalledProcessError` on a
    non-zero CLI exit, or :class:`FileNotFoundError` if LIWC-22-cli is not
    on the PATH.  The app teardown in ``finally`` still runs when we
    launched the app ourselves.
    """
    cmd = build_command(mode, cli_args)

    if dry_run:
        print(f"Command that would be executed:\n  {_quote_for_display(cmd)}")
        return

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
        subprocess.run(cmd, check=True)
    finally:
        if we_opened_it:
            logger.info("Shutting down LIWC-22 …")
            _close_liwc_app(liwc_proc)


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
        Input file encoding (default: ``"utf-8"``).
    csv_delimiter : :class:`str`, optional
        CSV delimiter character (CLI default: ``,``).  Use ``"\\t"`` for tab-
        separated files.  Left as ``None`` by default so that ``.tsv`` inputs
        are auto-detected; passing a ``.tsv`` input without setting this emits
        a :class:`UserWarning`.
    csv_escape : :class:`str`, optional
        CSV escape character (CLI default: none).
    csv_quote : :class:`str`, optional
        CSV quote character (default: ``"``).
    include_subfolders : :class:`bool`, optional
        If ``True`` (default), include subfolders when analysing a directory
        input.
    skip_header : :class:`bool`, optional
        If ``True`` (default), skip the first row of an Excel/CSV file (i.e.
        treat it as a header).  Setting ``False`` disables column-*name*
        resolution in the mode methods.
    preprocess_cjk : :class:`str`, optional
        Preprocess CJK text with Jieba (Chinese) or Kuromoji (Japanese)
        tokeniser - one of ``"chinese"``, ``"japanese"``, ``"none"``.
    url_regexp : :class:`str`, optional
        Regular expression used to capture URLs in text.
    count_urls : :class:`bool`, optional
        If ``True`` (default), count URLs as a single word.  Only meaningful
        if *url_regexp* is set.
    precision : :class:`int`, optional
        Number of decimal places in output (0-16, default: ``2``).
    auto_open : :class:`bool`, optional
        If LIWC-22 is not running, launch it before each analysis and close
        it afterwards (default ``True``).  Set to ``False`` to require that
        the app (or its license server) is already running.  When used as a
        context manager, the app is launched once on ``__enter__`` and closed
        on ``__exit__``.
    use_gui : :class:`bool`, optional
        When auto-opening, prefer the GUI app over the headless license
        server (default ``False``).
    dry_run : :class:`bool`, optional
        Print each CLI command without executing it (default ``False``).

    Examples
    --------
    >>> import liwca
    >>> liwc = liwca.Liwc22(dry_run=True)
    >>> liwc.wc(input="data.csv", output="results.csv")  # doctest: +SKIP

    >>> with liwca.Liwc22(auto_open=True, encoding="utf-8") as liwc:  # doctest: +SKIP
    ...     liwc.wc(input="data.csv", output="wc.csv")
    ...     liwc.freq(input="data.csv", output="freq.csv", n_gram=2)
    """

    def __init__(
        self,
        *,
        # I/O encoding
        encoding: str = "utf-8",
        csv_delimiter: str | None = None,
        csv_escape: str | None = None,
        csv_quote: str = '"',
        # File / folder handling
        include_subfolders: bool = True,
        skip_header: bool = True,
        # Text preprocessing
        preprocess_cjk: str | None = None,
        url_regexp: str | None = None,
        count_urls: bool = True,
        # Output
        precision: int = 2,
        # Execution control
        auto_open: bool = True,
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

    def _run_mode(self, mode: str, cli_args: dict[str, Any]) -> str:
        """Merge hoisted globals, prepare I/O, run, and shape the output.

        Pipeline:

        1. Merge hoisted globals (filtered by :data:`MODE_GLOBALS`).
        2. If ``input`` is a :class:`pandas.DataFrame`, validate and write
           it to a temporary CSV; remember its in-memory columns for
           column-name resolution.
        3. Soft-warn on ``.tsv`` file input without an explicit
           ``csv_delimiter`` (DataFrame input never triggers this).
        4. Resolve column args (0-based int -> 1-based; name -> 1-based).
        5. Run the CLI (raises on non-zero exit).  Skipped when
           ``dry_run=True`` - the command is printed instead.
        6. For mode ``wc``: reshape the output file in place via
           :func:`_shape_wc_output_file`.  Skipped on dry runs (nothing was
           written).
        7. Delete the temp input (if any) in ``finally``.

        Always returns the caller's ``output`` path - on dry runs this is
        "the path LIWC-22-cli *would* have written".
        """
        # 1. Merge hoisted globals.
        applicable = MODE_GLOBALS[mode]
        merged: dict[str, Any] = {k: v for k, v in self._globals.items() if k in applicable}
        merged.update(cli_args)

        user_input = merged.get("input")
        # `output` is a required kwarg on every mode method, so it's always
        # present in cli_args.
        output_path: str = merged["output"]

        # 2. DataFrame input -> temp CSV.  Track for cleanup.
        temp_input: Path | None = None
        input_columns: list[str] | None = None
        if isinstance(user_input, pd.DataFrame):
            _validate_df_input(user_input, mode=mode, other_args=merged)
            input_columns = [str(c) for c in user_input.columns]
            temp_input = _write_temp_input(user_input)
            merged["input"] = str(temp_input)

        try:
            # 3. Soft-validate: TSV input without an explicit delimiter.
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

            # 4. Normalise column args (0-based int -> 1-based; name -> 1-based).
            merged = _resolve_columns(
                merged,
                input_path=input_path,
                csv_delimiter=self._globals.get("csv_delimiter"),
                encoding=self._globals.get("encoding"),
                skip_header=self._globals.get("skip_header"),
                header_override=input_columns,
            )

            # Preserve the caller's row_id_indices (strings or 0-based ints)
            # before resolution clobbers them into 1-based ints.  Used by the
            # wc output shaper to rename LIWC's "Row ID" back to the source
            # column name(s).
            row_id_names = _derive_row_id_names(
                cli_args.get("row_id_indices"),
                input_columns=input_columns,
            )

            # 5. Run.  If we already launched the app in __enter__, don't re-launch.
            auto_open_for_call = self._auto_open and not self._app_owned
            _run(
                mode,
                merged,
                auto_open=auto_open_for_call,
                use_gui=self._use_gui,
                dry_run=self._dry_run,
            )

            # 6. wc-only: reshape the output file in place.  Nothing was
            #    written on a dry run, so the shaping step is skipped.
            if not self._dry_run and mode == "wc":
                _shape_wc_output_file(
                    output_path,
                    row_id_names=row_id_names,
                    output_format=merged.get("output_format"),
                )

            return output_path
        finally:
            if temp_input is not None:
                temp_input.unlink(missing_ok=True)

    # -- mode methods --------------------------------------------------------

    def wc(
        self,
        *,
        input: str | pd.DataFrame,
        output: str,
        console_text: str | None = None,
        environment_variable: str | None = None,
        clean_escaped_spaces: bool = True,
        column_indices: Iterable[int | str] | None = None,
        combine_columns: bool = True,
        row_id_indices: Iterable[int | str] | None = None,
        dictionary: str = "LIWC22",
        include_categories: Iterable[str] | None = None,
        exclude_categories: Iterable[str] | None = None,
        segmentation: str | None = None,
        output_format: str = "csv",
        threads: int | None = None,
    ) -> str:
        """
        Run a standard LIWC-22 word count analysis.

        Scores each input text against a LIWC dictionary (default ``LIWC22``)
        and reports per-category word counts or percentages.

        Parameters
        ----------
        input : :class:`str` or :class:`pandas.DataFrame`
            Path to input file or folder, OR a :class:`pandas.DataFrame`
            whose columns are the text / id / speaker columns you want to
            analyse.  DataFrame input is written to a temp CSV, fed to
            LIWC-CLI, and the temp file is removed when the call returns.
            Use ``"console"`` with *console_text* or ``"envvar"`` with
            *environment_variable* to analyse literal text.
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
        :class:`str`
            The *output* path.  On dry runs this is the path LIWC-22-cli
            *would* have written to - no file is created.

        Raises
        ------
        :class:`ValueError`
            If both *include_categories* and *exclude_categories* are set,
            or if *input* is a DataFrame combined with *console_text* /
            *environment_variable*, or if *input* is an empty DataFrame.
        :class:`subprocess.CalledProcessError`
            If LIWC-22-cli exits with a non-zero status.
        :class:`SystemExit`
            If LIWC-22 is not running and ``auto_open=False`` was passed at
            construction.

        Notes
        -----
        After LIWC-CLI writes the output CSV, the file is reshaped in
        place via :data:`wc_output_schema`: if *row_id_indices* was
        supplied (names or positions), the output's ``"Row ID"`` column is
        renamed back to those source names; a constant ``"Segment"``
        column (no segmentation) is dropped, otherwise it is promoted to
        a second index level; category columns sit under a column axis
        named ``"Category"`` when the file is loaded back into pandas.

        See Also
        --------
        ~liwca.count : Pure-Python word counting (no LIWC-22 required).

        Examples
        --------
        >>> import pandas as pd
        >>> df = pd.DataFrame({"doc_id": ["a", "b"], "text": ["hi", "bye"]})
        >>> path = Liwc22().wc(  # doctest: +SKIP
        ...     input=df,
        ...     output="wc.csv",
        ...     column_indices=["text"],
        ...     row_id_indices=["doc_id"],
        ... )
        >>> results = pd.read_csv(path, index_col=0)  # doctest: +SKIP
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
        input: str | pd.DataFrame,
        output: str,
        column_indices: Iterable[int | str] | None = None,
        combine_columns: bool = True,
        conversion_list: str | None = None,
        stop_list: str | None = None,
        trim_s: bool = True,
        n_gram: int = 1,
        skip_wc: int = 10,
        drop_words: int = 5,
        prune_interval: int = 10_000_000,
        prune_threshold_value: int = 5,
        output_format: str = "csv",
    ) -> str:
        """
        Compute word (and n-gram) frequencies across input texts.

        Parameters
        ----------
        input : :class:`str` or :class:`pandas.DataFrame`
            Path to input file or folder, OR a :class:`pandas.DataFrame`.
            DataFrame input is written to a temp CSV, fed to LIWC-CLI, and
            the temp file is removed when the call returns.
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
        :class:`str`
            The *output* path.  On dry runs this is the path LIWC-22-cli
            *would* have written to - no file is created.

        Raises
        ------
        :class:`ValueError`
            If *input* is an empty DataFrame.
        :class:`subprocess.CalledProcessError`
            If LIWC-22-cli exits with a non-zero status.
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
        input: str | pd.DataFrame,
        output: str,
        column_indices: Iterable[int | str] | None = None,
        combine_columns: bool = True,
        index_of_id_column: int | str | None = None,
        conversion_list: str | None = None,
        stop_list: str | None = None,
        trim_s: bool = True,
        n_gram: int = 1,
        skip_wc: int = 10,
        segmentation: str | None = None,
        threshold_type: str = "min-obspct",
        threshold_value: float = 10.0,
        mem_output_type: str = "binary",
        enable_pca: bool = False,
        save_theme_scores: bool = False,
        column_delimiter: str = " ",
        prune_interval: int = 10_000_000,
        prune_threshold_value: int = 5,
        output_format: str = "csv",
    ) -> str:
        """
        Run Meaning Extraction Method (MEM) analysis.

        Builds a document-term matrix over the input corpus and optionally runs
        Principal Component Analysis to surface latent themes.

        Parameters
        ----------
        input : :class:`str` or :class:`pandas.DataFrame`
            Path to input file or folder, OR a :class:`pandas.DataFrame`.
            DataFrame input is written to a temp CSV, fed to LIWC-CLI, and
            the temp file is removed when the call returns.
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
        :class:`str`
            The *output* path.  On dry runs this is the path LIWC-22-cli
            *would* have written to - no file is created.

        Raises
        ------
        :class:`ValueError`
            If *input* is an empty DataFrame.
        :class:`subprocess.CalledProcessError`
            If LIWC-22-cli exits with a non-zero status.
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
        input: str | pd.DataFrame,
        output: str,
        column_indices: Iterable[int | str] | None = None,
        combine_columns: bool = True,
        index_of_id_column: int | str | None = None,
        dictionary: str = "LIWC22",
        category_to_contextualize: str | None = None,
        word_list: str | None = None,
        words_to_contextualize: Iterable[str] | None = None,
        word_window_left: int = 3,
        word_window_right: int = 3,
        keep_punctuation: bool = True,
    ) -> str:
        """
        Run LIWC-22 Contextualizer analysis.

        Extracts the surrounding context (configurable window of words to the
        left and right) for each occurrence of a target word or dictionary
        category.

        Parameters
        ----------
        input : :class:`str` or :class:`pandas.DataFrame`
            Path to input file or folder, OR a :class:`pandas.DataFrame`.
            DataFrame input is written to a temp CSV, fed to LIWC-CLI, and
            the temp file is removed when the call returns.
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
        :class:`str`
            The *output* path.  On dry runs this is the path LIWC-22-cli
            *would* have written to - no file is created.

        Raises
        ------
        :class:`ValueError`
            If *input* is an empty DataFrame.
        :class:`subprocess.CalledProcessError`
            If LIWC-22-cli exits with a non-zero status.
        :class:`SystemExit`
            If LIWC-22 is not running and ``auto_open=False`` was passed at
            construction.

        Examples
        --------
        >>> Liwc22(dry_run=True).context(input="data.txt", output="ctx.csv")  # doctest: +SKIP
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
        input: str | pd.DataFrame,
        output: str,
        column_indices: Iterable[int | str] | None = None,
        combine_columns: bool = True,
        index_of_id_column: int | str | None = None,
        segments_number: int = 5,
        scaling_method: int = 1,
        skip_wc: int = 10,
        output_data_points: bool = True,
        output_format: str = "csv",
    ) -> str:
        """
        Analyse the narrative arc of texts.

        Scores how a text's narrative trajectory (staging, plot progression,
        cognitive tension) varies across segments.

        Parameters
        ----------
        input : :class:`str` or :class:`pandas.DataFrame`
            Path to input file or folder, OR a :class:`pandas.DataFrame`.
            DataFrame input is written to a temp CSV, fed to LIWC-CLI, and
            the temp file is removed when the call returns.
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
        :class:`str`
            The *output* path.  On dry runs this is the path LIWC-22-cli
            *would* have written to - no file is created.

        Raises
        ------
        :class:`ValueError`
            If *input* is an empty DataFrame.
        :class:`subprocess.CalledProcessError`
            If LIWC-22-cli exits with a non-zero status.
        :class:`SystemExit`
            If LIWC-22 is not running and ``auto_open=False`` was passed at
            construction.

        Examples
        --------
        >>> Liwc22(dry_run=True).arc(input="stories/", output="arc.csv")  # doctest: +SKIP
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
        input: str | pd.DataFrame,
        output: str,
        speaker_list: str,
        regex_removal: str | None = None,
        omit_speakers_num_turns: int = 0,
        omit_speakers_word_count: int = 10,
        single_line: bool = False,
    ) -> str:
        """
        Convert separate transcript files into a single spreadsheet.

        Parameters
        ----------
        input : :class:`str` or :class:`pandas.DataFrame`
            Path to input file or folder, OR a :class:`pandas.DataFrame`.
            DataFrame input is written to a temp CSV, fed to LIWC-CLI, and
            the temp file is removed when the call returns.
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
        :class:`str`
            The *output* path.  On dry runs this is the path LIWC-22-cli
            *would* have written to - no file is created.

        Raises
        ------
        :class:`ValueError`
            If *input* is an empty DataFrame.
        :class:`subprocess.CalledProcessError`
            If LIWC-22-cli exits with a non-zero status.
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
        input: str | pd.DataFrame,
        output: str,
        text_column: int | str,
        person_column: int | str,
        group_column: int | str | None = None,
        calculate_lsm: int = 3,
        output_type: int = 1,
        expanded_output: bool = False,
        segmentation: str | None = None,
        omit_speakers_num_turns: int = 0,
        omit_speakers_word_count: int = 10,
        single_line: bool = False,
        output_format: str = "csv",
    ) -> str:
        """
        Run Language Style Matching (LSM) analysis.

        Computes how closely speakers align in their use of function words,
        either person-to-person or within groups.

        Parameters
        ----------
        input : :class:`str` or :class:`pandas.DataFrame`
            Path to input file or folder, OR a :class:`pandas.DataFrame`.
            DataFrame input is written to a temp CSV, fed to LIWC-CLI, and
            the temp file is removed when the call returns.
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
        :class:`str`
            The *output* path.  On dry runs this is the path LIWC-22-cli
            *would* have written to - no file is created.

        Raises
        ------
        :class:`ValueError`
            If *input* is an empty DataFrame.
        :class:`subprocess.CalledProcessError`
            If LIWC-22-cli exits with a non-zero status.
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
