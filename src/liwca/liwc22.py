"""
Python wrapper for the LIWC-22 CLI tool.

Builds and runs LIWC-22-cli commands as subprocesses. All seven analysis
modes are exposed as methods on the :class:`Liwc22` class.

Requires LIWC-22 to be installed with the CLI on your PATH.
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

__all__ = ["Liwc22"]

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
# Single source of truth for (a) dest -> CLI flag and (b) which dests are
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

# Dests whose Python value is a :class:`bool` that maps to ``"1"`` / ``"0"``.
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

# Modes for which a ``pd.DataFrame`` input requires an explicit text-column
# selector.  Keys map to the dest that must be set when ``input`` is a
# DataFrame and mentions more than one column.  ``ct`` is absent because
# transcript-conversion operates on files, not tabular data.
_DF_TEXT_SELECTOR: dict[str, str] = {
    "wc": "column_indices",
    "freq": "column_indices",
    "mem": "column_indices",
    "context": "column_indices",
    "arc": "column_indices",
    "lsm": "text_column",
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


# ---------------------------------------------------------------------------
# Column resolution
# ---------------------------------------------------------------------------


def _read_header(
    input_path: str,
    *,
    csv_delimiter: str | None,
    encoding: str | None,
) -> list[str]:
    """Return the list of column names for ``input_path``."""
    path = Path(input_path)
    suffix = path.suffix.lower()

    if suffix in {".xlsx", ".xls"}:
        frame = pd.read_excel(path, nrows=0)
    else:
        frame = pd.read_csv(
            path,
            sep=csv_delimiter if csv_delimiter is not None else ",",
            encoding=encoding or "utf-8",
            nrows=0,
        )

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
    """Read the input file's header, validating the request first."""
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
    """Normalise every column arg in ``cli_args`` to a 1-based ``int``."""
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
# Input normalisation
# ---------------------------------------------------------------------------


def _coerce_to_list(value: Any) -> Any:
    """Wrap a single ``str``/``int`` into a one-element list; pass through otherwise.

    Applied to LIST_FLAGS before column resolution so that
    ``column_indices="text"`` doesn't silently explode into four char elements.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return [value]
    if isinstance(value, (str, int)):
        return [value]
    return list(value)


def _write_temp_input(df: pd.DataFrame) -> Path:
    """Write *df* to a fresh temp CSV file and return its path.

    The file is kept on disk (``delete=False``) so LIWC-CLI can reopen it on
    Windows; the caller is responsible for deletion.
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


def _prepare_frame_input(
    user_input: pd.DataFrame | pd.Series,
    *,
    mode: str,
    merged: dict[str, Any],
) -> tuple[Path, list[str]]:
    """Convert Series/DataFrame input into a temp CSV + header list.

    Mutates *merged* in place: fills in the text-column selector for Series
    input, and rewrites ``merged["input"]`` to the temp-file path.  Raises
    :class:`ValueError` on empty / malformed DataFrame input.
    """
    if isinstance(user_input, pd.Series):
        text_name = str(user_input.name) if user_input.name is not None else "text"
        user_input = user_input.to_frame(name=text_name)
        selector = _DF_TEXT_SELECTOR.get(mode)
        if selector == "column_indices" and merged.get("column_indices") is None:
            merged["column_indices"] = [text_name]
        elif selector == "text_column" and merged.get("text_column") is None:
            merged["text_column"] = text_name

    if mode == "ct":
        raise ValueError(
            "ct mode operates on transcript files, not DataFrames. "
            "Pass a path to a transcript file or folder as `input`."
        )
    if user_input.empty:
        raise ValueError("DataFrame `input` is empty.")
    if mode == "wc" and (
        merged.get("console_text") is not None or merged.get("environment_variable") is not None
    ):
        raise ValueError(
            "Cannot pass a DataFrame as `input` together with console_text "
            "or environment_variable; choose one input source."
        )
    selector = _DF_TEXT_SELECTOR.get(mode)
    if selector and merged.get(selector) is None:
        raise ValueError(
            f"When `input` is a DataFrame, {selector!r} must be set to "
            f"identify the text column. DataFrame has columns: "
            f"{list(user_input.columns)}."
        )

    input_columns = [str(c) for c in user_input.columns]
    temp_input = _write_temp_input(user_input)
    merged["input"] = str(temp_input)
    return temp_input, input_columns


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
    """Map LIWC's ``"Row ID"`` / ``"Row ID 1"`` / ... columns to user names."""
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

    1. Rename leading ``"Row ID"`` (or ``"Row ID 1"``, ...) columns back to
       *row_id_names*, when provided.
    2. Drop the ``"Segment"`` column if it has a single unique value;
       otherwise keep it for promotion to a second index level.
    3. Set the row-id column(s) (and ``"Segment"``, if kept) as the index.
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
    the step is skipped with a :class:`UserWarning`.
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


def _win_quote_arg(arg: str) -> str:
    """Canonical MSVCRT encoding of one arg for a Windows command line.

    Python's built-in :func:`subprocess.list2cmdline` encodes a lone ``"`` as
    bare ``\\"`` (unquoted).  Some command-line parsers - notably the Java
    runtime used by LIWC-22-cli - treat an unquoted ``\\"`` as a literal
    backslash followed by a quote-start, which then consumes the remainder of
    the command line as a quoted value.  The canonical encoding ``"\\""``
    (quoted, with the inner quote backslash-escaped) round-trips through
    every major Windows argv parser.

    This encoder follows the same rules as Microsoft's CommandLineToArgvW /
    the MSVCRT:

    * Empty arg -> ``""``.
    * No whitespace, no ``"``, no ``\\``: pass through unchanged.
    * Otherwise wrap in quotes, doubling any run of backslashes that precedes
      a ``"`` (or the closing quote) and escaping each ``"`` with ``\\``.
    """
    if not arg:
        return '""'
    if not any(c in arg for c in ' \t"\\'):
        return arg

    result: list[str] = ['"']
    backslashes = 0
    for c in arg:
        if c == "\\":
            backslashes += 1
            continue
        if c == '"':
            result.append("\\" * (2 * backslashes))
            result.append('\\"')
        else:
            result.append("\\" * backslashes)
            result.append(c)
        backslashes = 0
    # Trailing backslashes precede the closing quote - double them.
    result.append("\\" * (2 * backslashes))
    result.append('"')
    return "".join(result)


def _join_windows_cmdline(cmd: list[str]) -> str:
    return " ".join(_win_quote_arg(a) for a in cmd)


def _resolve_liwc_cli() -> str:
    """Return the path to LIWC-22-cli, preferring ``.exe`` on Windows.

    The ``.bat`` wrapper on Windows is dispatched via ``cmd.exe /c``, which
    re-parses the command line with CMD rules and mangles quote args even
    when we pre-encode them canonically.  Calling the ``.exe`` directly
    delivers our argv through MSVCRT parsing only.
    """
    exe_path: str | None = None
    if platform.system() == "Windows":
        exe_path = shutil.which(LIWC_CLI + ".exe")
    if exe_path is None:
        exe_path = shutil.which(LIWC_CLI)
    if exe_path is None:
        raise FileNotFoundError(
            f"{LIWC_CLI!r} not found on PATH. "
            "Make sure LIWC-22 is installed and its CLI is on your PATH."
        )
    return exe_path


def _format_cli_error(cmd: list[str], result: subprocess.CompletedProcess[str]) -> str:
    """Build a user-facing error string from a failed LIWC-22-cli result.

    LIWC-22-cli writes its error messages to stdout (mixed with a usage/help
    dump) and usually nothing to stderr.  We prefer lines that look like an
    actual error message ("ERROR", "Error:", "cannot", "not found", ...) and
    fall back to the last ~15 non-blank output lines if no such lines exist.
    Full output is available via the module logger at DEBUG level.
    """
    combined = (result.stdout or "") + "\n" + (result.stderr or "")
    lines = [ln.rstrip() for ln in combined.splitlines() if ln.strip()]
    error_markers = ("error", "cannot", "invalid", "not found", "failed", "missing")
    error_lines = [ln for ln in lines if any(m in ln.lower() for m in error_markers)]
    if error_lines:
        tail = "\n".join(error_lines[:10])
    elif lines:
        tail = "\n".join(lines[-15:])
    else:
        tail = "(no output captured)"
    return (
        f"LIWC-22-cli exited with status {result.returncode}.\n"
        f"Command: {_quote_for_display(cmd)}\n"
        f"Output:\n{tail}\n"
        "(Enable DEBUG logging on 'liwca.liwc22' for the full CLI output.)"
    )


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
    app_managed: bool = False,
) -> None:
    """Run a LIWC-22 CLI command built from a mode + flag dict.

    When ``app_managed=True`` the caller is responsible for the LIWC-22
    app lifecycle (e.g. the :class:`Liwc22` context manager already
    launched it in ``__enter__``) and this function skips the running
    check / launch entirely.

    On a non-zero exit, raises :class:`RuntimeError` with the command and a
    tail of the captured stderr - not a bare :class:`CalledProcessError` that
    lets the CLI's help-text dump spill through.
    """
    # Windows workaround: LIWC-22-cli.exe is a Java-launcher wrapper that
    # re-escapes argv before spawning java.exe.  A literal ``"`` as the value
    # of ``-quote`` survives our canonical MSVCRT encoding into the .exe, then
    # gets mangled during that second encoding - LIWC never sees ``-i`` /
    # ``-o``.  Since ``"`` is the CLI's own default for ``-quote``, omitting
    # the flag is behaviourally identical.  Other values (``'``, ``|``, ...)
    # round-trip correctly and are emitted as normal.
    if platform.system() == "Windows" and cli_args.get("csv_quote") == '"':
        cli_args = {k: v for k, v in cli_args.items() if k != "csv_quote"}

    cmd = build_command(mode, cli_args)

    if dry_run:
        print(f"Command that would be executed:\n  {_quote_for_display(cmd)}")
        return

    cmd[0] = _resolve_liwc_cli()

    # -- ensure LIWC-22 is running -------------------------------------------
    liwc_proc: subprocess.Popen[bytes] | None = None
    we_opened_it = False

    if not app_managed and not _is_liwc_running():
        if auto_open:
            logger.info("LIWC-22 is not running - starting it now …")
            liwc_proc = _open_liwc_app(use_license_server=not use_gui)
            we_opened_it = True
        else:
            raise RuntimeError(
                "LIWC-22 is not running. Start the LIWC-22 application "
                "(or the license server) first, or re-run with auto_open=True."
            )

    # -- run the analysis ----------------------------------------------------
    logger.info("Running: %s", _quote_for_display(cmd))
    try:
        # On Windows, Python's default list2cmdline mis-encodes a lone ``"``
        # as unquoted ``\"``, which LIWC-22-cli (Java) then misparses.  Build
        # the command line ourselves with canonical MSVCRT quoting and pass
        # it as a string so CreateProcess receives the argv we intended.
        if platform.system() == "Windows":
            popen_cmd: str | list[str] = _join_windows_cmdline(cmd)
        else:
            popen_cmd = cmd
        result = subprocess.run(popen_cmd, capture_output=True, text=True)
        if result.stdout:
            logger.debug("LIWC-22-cli stdout:\n%s", result.stdout)
        if result.stderr:
            logger.debug("LIWC-22-cli stderr:\n%s", result.stderr)
        if result.returncode != 0:
            raise RuntimeError(_format_cli_error(cmd, result))
    finally:
        if we_opened_it:
            logger.info("Shutting down LIWC-22 …")
            _close_liwc_app(liwc_proc)


# ---------------------------------------------------------------------------
# Public API - Liwc22 class
# ---------------------------------------------------------------------------


def _check_type(name: str, value: Any, allowed: type | tuple[type, ...]) -> None:
    """Raise :class:`TypeError` if *value* isn't an instance of *allowed*."""
    if not isinstance(value, allowed):
        if isinstance(allowed, tuple):
            names = " | ".join(t.__name__ for t in allowed)
        else:
            names = allowed.__name__
        raise TypeError(f"{name!r} must be {names}, got {type(value).__name__}.")


def _check_bool(name: str, value: Any) -> None:
    """Reject non-bool values (ints, strings) for bool-typed kwargs."""
    if not isinstance(value, bool):
        raise TypeError(f"{name!r} must be a bool, got {type(value).__name__}.")


def _check_choice(name: str, value: Any, choices: Iterable[Any]) -> None:
    choices = tuple(choices)
    if value not in choices:
        raise ValueError(f"{name!r} must be one of {list(choices)}, got {value!r}.")


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
        CSV delimiter (default: ``","``).  Use ``"\\t"`` for TSV inputs.
    csv_escape : :class:`str`, optional
        CSV escape character.  ``None`` (default) means "no escape"; the flag
        is omitted from the CLI call.
    csv_quote : :class:`str`, optional
        CSV quote character (default: ``"``).  On Windows, the default value
        is silently omitted from the CLI call: LIWC-22-cli's Java launcher
        re-escapes argv and mangles ``-quote "`` into swallowing subsequent
        flags.  Since ``"`` is also the CLI's default, omission matches the
        documented behaviour; any other value (e.g. ``"'"``) is emitted
        normally.
    include_subfolders : :class:`bool`, optional
        If ``True`` (default), include subfolders when analysing a directory
        input.
    skip_header : :class:`bool`, optional
        If ``True`` (default), skip the first row of an Excel/CSV file (i.e.
        treat it as a header).  Setting ``False`` disables column-*name*
        resolution in the mode methods.
    preprocess_cjk : :class:`str`, optional
        Preprocess CJK text with Jieba (Chinese) or Kuromoji (Japanese)
        tokeniser - one of ``"chinese"``, ``"japanese"``, ``"none"`` (default).
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
        the app (or its license server) is already running.
    use_gui : :class:`bool`, optional
        When auto-opening, prefer the GUI app over the headless license
        server (default ``False``).
    dry_run : :class:`bool`, optional
        Print each CLI command without executing it (default ``False``).

    Examples
    --------
    >>> import liwca
    >>> liwc = liwca.Liwc22(dry_run=True)
    >>> liwc.wc("data.csv", "results.csv")  # doctest: +SKIP

    >>> with liwca.Liwc22() as liwc:  # doctest: +SKIP
    ...     liwc.wc("data.csv", "wc.csv", column_indices="text")
    ...     liwc.freq("data.csv", "freq.csv", n_gram=2)
    """

    def __init__(
        self,
        *,
        encoding: str = "utf-8",
        csv_delimiter: str = ",",
        csv_escape: str | None = None,
        csv_quote: str = '"',
        include_subfolders: bool = True,
        skip_header: bool = True,
        preprocess_cjk: str = "none",
        url_regexp: str | None = None,
        count_urls: bool = True,
        precision: int = 2,
        auto_open: bool = True,
        use_gui: bool = False,
        dry_run: bool = False,
    ) -> None:
        _check_type("encoding", encoding, str)
        _check_type("csv_delimiter", csv_delimiter, str)
        if csv_escape is not None:
            _check_type("csv_escape", csv_escape, str)
        _check_type("csv_quote", csv_quote, str)
        _check_bool("include_subfolders", include_subfolders)
        _check_bool("skip_header", skip_header)
        _check_choice("preprocess_cjk", preprocess_cjk, ("chinese", "japanese", "none"))
        if url_regexp is not None:
            _check_type("url_regexp", url_regexp, str)
        _check_bool("count_urls", count_urls)
        _check_type("precision", precision, int)
        if isinstance(precision, bool) or not 0 <= precision <= 16:
            raise ValueError(f"'precision' must be an int in 0..16, got {precision!r}.")
        _check_bool("auto_open", auto_open)
        _check_bool("use_gui", use_gui)
        _check_bool("dry_run", dry_run)

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

        1. Validate ``input`` / ``output`` types; coerce ``Path`` to ``str``.
        2. Merge hoisted globals (filtered by :data:`MODE_GLOBALS`).
        3. If ``input`` is a :class:`pandas.Series`, wrap to a 1-col
           DataFrame (auto-filling the text-column selector).
        4. If ``input`` is a :class:`pandas.DataFrame`, validate and write
           it to a temporary CSV; remember its in-memory columns.
        5. Coerce LIST_FLAGS (a bare ``str``/``int`` becomes a 1-element list).
        6. Resolve column args (0-based int -> 1-based; name -> 1-based).
        7. Run the CLI (raises on non-zero exit).
        8. For mode ``wc``: reshape the output file in place (skipped on dry runs).
        9. Delete the temp input (if any) in ``finally``.

        Returns the caller's ``output`` path.
        """
        user_input = cli_args.get("input")
        user_output = cli_args.get("output")

        # 1. Type-check and Path-coerce I/O.
        _check_type("input", user_input, (str, Path, pd.DataFrame, pd.Series))
        _check_type("output", user_output, (str, Path))
        if isinstance(user_input, Path):
            user_input = str(user_input)
            cli_args["input"] = user_input
        output_path = str(user_output)
        cli_args["output"] = output_path

        # 2. Merge hoisted globals.
        applicable = MODE_GLOBALS[mode]
        merged: dict[str, Any] = {k: v for k, v in self._globals.items() if k in applicable}
        merged.update(cli_args)

        # 3/4. Series/DataFrame input -> temp CSV.
        temp_input: Path | None = None
        input_columns: list[str] | None = None
        if isinstance(user_input, (pd.Series, pd.DataFrame)):
            temp_input, input_columns = _prepare_frame_input(user_input, mode=mode, merged=merged)

        try:
            # 5. Bare str/int -> 1-element list for LIST_FLAGS.
            for dest in LIST_FLAGS:
                if dest in merged:
                    merged[dest] = _coerce_to_list(merged[dest])

            # 6. Normalise column args (0-based int -> 1-based; name -> 1-based).
            merged = _resolve_columns(
                merged,
                input_path=merged.get("input"),
                csv_delimiter=self._globals.get("csv_delimiter"),
                encoding=self._globals.get("encoding"),
                skip_header=self._globals.get("skip_header"),
                header_override=input_columns,
            )

            # Preserve the caller's row_id_indices (strings or 0-based ints)
            # before resolution clobbers them into 1-based ints.
            row_id_names = _derive_row_id_names(
                _coerce_to_list(cli_args.get("row_id_indices")),
                input_columns=input_columns,
            )

            # 7. Run.  If we launched the app in __enter__, the context
            # manager owns its lifecycle - tell `_run` to skip the running
            # check (which can lag behind a fresh launch).
            _run(
                mode,
                merged,
                auto_open=self._auto_open,
                use_gui=self._use_gui,
                dry_run=self._dry_run,
                app_managed=self._app_owned,
            )

            # 8. wc-only: reshape the output file in place.
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
        input: str | Path | pd.DataFrame | pd.Series,
        output: str | Path,
        *,
        console_text: str | None = None,
        environment_variable: str | None = None,
        clean_escaped_spaces: bool = True,
        column_indices: int | str | Iterable[int | str] | None = None,
        combine_columns: bool = True,
        row_id_indices: int | str | Iterable[int | str] | None = None,
        dictionary: str = "LIWC22",
        include_categories: str | Iterable[str] | None = None,
        exclude_categories: str | Iterable[str] | None = None,
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
        input : str, :class:`~pathlib.Path`, DataFrame, or Series
            Path to an input file/folder, a :class:`pandas.DataFrame`, or a
            :class:`pandas.Series`.  DataFrame/Series input is written to a
            temp CSV, fed to LIWC-CLI, and the temp file is removed when the
            call returns.  A DataFrame requires *column_indices* to identify
            the text column(s).  A Series auto-wraps into a single-column
            frame using the Series name (or ``"text"``).  Use ``"console"``
            with *console_text* or ``"envvar"`` with *environment_variable*
            to analyse literal text.
        output : :class:`str` or :class:`~pathlib.Path`
            Output file/folder path, or ``"console"``.
        console_text : :class:`str`, optional
            Text string to analyse.  Use with ``input="console"``.
        environment_variable : :class:`str`, optional
            Environment variable name containing text.  Use with
            ``input="envvar"``.
        clean_escaped_spaces : :class:`bool`, optional
            With ``input="console"``: if ``True``, escaped spaces like
            ``\\n`` are converted to actual spaces (CLI default: ``True``).
        column_indices : :class:`int`, :class:`str`, or iterable thereof, optional
            Columns containing analysable text.  Each entry is either a
            0-based integer index or a column-name string (requires the
            input to have a header row).  A bare ``str`` or ``int`` is
            accepted for single-column selection.  All columns processed by
            default (not allowed for DataFrame input).
        combine_columns : :class:`bool`, optional
            If ``True``, combine spreadsheet columns into a single text per
            row (CLI default: ``True``).
        row_id_indices : :class:`int`, :class:`str`, or iterable thereof, optional
            Columns to use as row identifiers.  Multiple columns are
            concatenated with ``;``.  Defaults to row number.
        dictionary : :class:`str`, optional
            LIWC dictionary name (e.g. ``LIWC22``, ``LIWC2015``) or path to a
            custom ``.dicx`` file (default: LIWC22).
        include_categories : :class:`str` or iterable of :class:`str`, optional
            Dictionary categories to include in output.  Mutually exclusive
            with *exclude_categories*.
        exclude_categories : :class:`str` or iterable of :class:`str`, optional
            Dictionary categories to exclude from output.  Mutually exclusive
            with *include_categories*.
        segmentation : :class:`str`, optional
            Split text into segments.  See the `LIWC CLI documentation
            <https://www.liwc.app/help/cli>`_.
        output_format : :class:`str`, optional
            Output file format - one of ``csv``, ``xlsx``, ``ndjson`` (default: csv).
        threads : :class:`int`, optional
            Number of processing threads (default: available cores - 1).

        Returns
        -------
        :class:`str`
            The *output* path. On dry runs this is the path LIWC-22-cli
            *would* have written to - no file is created.

        Raises
        ------
        :class:`ValueError`
            If both *include_categories* and *exclude_categories* are set,
            or if *input* is a DataFrame without *column_indices*, or if
            *input* is an empty DataFrame, or if *input* is a DataFrame
            combined with *console_text* / *environment_variable*.
        :class:`TypeError`
            If *input* / *output* are of the wrong type.
        :class:`RuntimeError`
            If LIWC-22-cli exits with a non-zero status, or if LIWC-22 is not
            running and ``auto_open=False``.

        Notes
        -----
        After LIWC-CLI writes the output CSV, the file is reshaped in
        place via :data:`wc_output_schema`: row-id columns are renamed back
        to their source names, a constant ``"Segment"`` column is dropped,
        and the category columns sit under a column axis named
        ``"Category"`` when the file is loaded back into pandas.

        Examples
        --------
        >>> import pandas as pd
        >>> df = pd.DataFrame({"doc_id": ["a", "b"], "text": ["hi", "bye"]})
        >>> path = Liwc22().wc(  # doctest: +SKIP
        ...     df,
        ...     "wc.csv",
        ...     column_indices="text",
        ...     row_id_indices="doc_id",
        ... )
        """
        if include_categories is not None and exclude_categories is not None:
            raise ValueError(
                "Cannot pass both include_categories and exclude_categories; choose one."
            )
        _check_bool("clean_escaped_spaces", clean_escaped_spaces)
        _check_bool("combine_columns", combine_columns)
        _check_choice("output_format", output_format, ("csv", "xlsx", "ndjson"))
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
        input: str | Path | pd.DataFrame | pd.Series,
        output: str | Path,
        *,
        column_indices: int | str | Iterable[int | str] | None = None,
        combine_columns: bool = True,
        conversion_list: str | None = None,
        stop_list: str = "internal-EN",
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
        input : str, :class:`~pathlib.Path`, DataFrame, or Series
            Path to input file/folder, a DataFrame (requires
            *column_indices*), or a Series (auto-wraps).
        output : :class:`str` or :class:`~pathlib.Path`
            Output file/folder path, or ``"console"``.
        column_indices : :class:`int`, :class:`str`, or iterable thereof, optional
            Columns containing analysable text.  A bare ``str`` or ``int`` is
            accepted for single-column selection.  All columns processed by
            default (not allowed for DataFrame input).
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
            N-gram size (1-5), inclusive of all lower n-grams (default: 1).
        skip_wc : :class:`int`, optional
            Skip texts with word count less than this value (default: 10).
        drop_words : :class:`int`, optional
            Drop n-grams with frequency less than this value (default: 5).
        prune_interval : :class:`int`, optional
            Prune frequency list every N words to optimise RAM (default: 10_000_000).
        prune_threshold_value : :class:`int`, optional
            Minimum n-gram frequency retained during pruning (default: 5).
        output_format : :class:`str`, optional
            Output file format - one of ``csv``, ``xlsx``, ``ndjson`` (default: csv).

        Returns
        -------
        :class:`str`
            The *output* path.
        """
        _check_bool("combine_columns", combine_columns)
        _check_bool("trim_s", trim_s)
        _check_choice("n_gram", n_gram, (1, 2, 3, 4, 5))
        _check_choice("output_format", output_format, ("csv", "xlsx", "ndjson"))
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
        input: str | Path | pd.DataFrame | pd.Series,
        output: str | Path,
        *,
        column_indices: int | str | Iterable[int | str] | None = None,
        combine_columns: bool = True,
        index_of_id_column: int | str | None = None,
        conversion_list: str | None = None,
        stop_list: str = "internal-EN",
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

        Builds a document-term matrix over the input corpus and optionally
        runs Principal Component Analysis to surface latent themes.

        Parameters
        ----------
        input : str, :class:`~pathlib.Path`, DataFrame, or Series
            Path to input file/folder, a DataFrame (requires
            *column_indices*), or a Series (auto-wraps).
        output : :class:`str` or :class:`~pathlib.Path`
            Output file/folder path, or ``"console"``.
        column_indices : :class:`int`, :class:`str`, or iterable thereof, optional
            Columns containing analysable text.
        combine_columns : :class:`bool`, optional
            If ``True``, combine spreadsheet columns into a single text per row.
        index_of_id_column : :class:`int` or :class:`str`, optional
            Column to use as row identifier.
        conversion_list : :class:`str`, optional
            Path to a conversion list or an internal list name.
        stop_list : :class:`str`, optional
            Path to a stop list, an internal list name, or ``"none"``
            (default: ``"internal-EN"``).
        trim_s : :class:`bool`, optional
            If ``True``, trim trailing ``'s`` from words.
        n_gram : :class:`int`, optional
            N-gram size (1-5).
        skip_wc : :class:`int`, optional
            Skip texts with word count less than this value (default: 10).
        segmentation : :class:`str`, optional
            Split text into segments.
        threshold_type : :class:`str`, optional
            One of ``min-obspct`` (default), ``min-freq``, ``top-obspct``, ``top-freq``.
        threshold_value : :class:`float`, optional
            Threshold cutoff value (default: 10.0).
        mem_output_type : :class:`str`, optional
            Document-term matrix format - one of ``binary`` (default),
            ``relative-freq``, or ``raw-counts``.
        enable_pca : :class:`bool`, optional
            Enable Principal Component Analysis (default ``False``).
        save_theme_scores : :class:`bool`, optional
            Save the theme-scores table for PCA (default ``False``).
        column_delimiter : :class:`str`, optional
            Delimiter between grams in n-gram column names (default: space).
        prune_interval, prune_threshold_value : :class:`int`, optional
            RAM-pruning controls (defaults: 10_000_000 and 5).
        output_format : :class:`str`, optional
            One of ``csv``, ``xlsx``, ``ndjson`` (default: csv).
        """
        _check_bool("combine_columns", combine_columns)
        _check_bool("trim_s", trim_s)
        _check_bool("enable_pca", enable_pca)
        _check_bool("save_theme_scores", save_theme_scores)
        _check_choice("n_gram", n_gram, (1, 2, 3, 4, 5))
        _check_choice(
            "threshold_type",
            threshold_type,
            ("min-obspct", "min-freq", "top-obspct", "top-freq"),
        )
        _check_choice("mem_output_type", mem_output_type, ("binary", "relative-freq", "raw-counts"))
        _check_choice("output_format", output_format, ("csv", "xlsx", "ndjson"))
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
        input: str | Path | pd.DataFrame | pd.Series,
        output: str | Path,
        *,
        column_indices: int | str | Iterable[int | str] | None = None,
        combine_columns: bool = True,
        index_of_id_column: int | str | None = None,
        dictionary: str = "LIWC22",
        category_to_contextualize: str | None = None,
        word_list: str | None = None,
        words_to_contextualize: str | Iterable[str] | None = None,
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
        input : str, :class:`~pathlib.Path`, DataFrame, or Series
            Path to input file/folder, a DataFrame (requires
            *column_indices*), or a Series (auto-wraps).
        output : :class:`str` or :class:`~pathlib.Path`
            Output file/folder path, or ``"console"``.
        column_indices : :class:`int`, :class:`str`, or iterable thereof, optional
            Columns containing analysable text.
        combine_columns : :class:`bool`, optional
            If ``True``, combine spreadsheet columns into a single text per row.
        index_of_id_column : :class:`int` or :class:`str`, optional
            Column to use as row identifier.
        dictionary : :class:`str`, optional
            LIWC dictionary name or path to a custom ``.dicx`` file.
        category_to_contextualize : :class:`str`, optional
            Dictionary category to contextualise (default: first category).
        word_list : :class:`str`, optional
            Path to a word list file for contextualisation.
        words_to_contextualize : :class:`str` or iterable of :class:`str`, optional
            Words to contextualise.  Wildcards (``*``) allowed.
        word_window_left, word_window_right : :class:`int`, optional
            Context words around the target word (defaults: 3, 3).
        keep_punctuation : :class:`bool`, optional
            If ``True``, include punctuation in context items (CLI default: ``True``).
        """
        _check_bool("combine_columns", combine_columns)
        _check_bool("keep_punctuation", keep_punctuation)
        _check_type("word_window_left", word_window_left, int)
        _check_type("word_window_right", word_window_right, int)
        if word_window_left < 0 or word_window_right < 0:
            raise ValueError("word_window_left/right must be non-negative.")
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
        input: str | Path | pd.DataFrame | pd.Series,
        output: str | Path,
        *,
        column_indices: int | str | Iterable[int | str] | None = None,
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
        input : str, :class:`~pathlib.Path`, DataFrame, or Series
            Path to input file/folder, a DataFrame (requires
            *column_indices*), or a Series (auto-wraps).
        output : :class:`str` or :class:`~pathlib.Path`
            Output file/folder path, or ``"console"``.
        column_indices : :class:`int`, :class:`str`, or iterable thereof, optional
            Columns containing analysable text.
        combine_columns : :class:`bool`, optional
            If ``True``, combine spreadsheet columns into a single text per row.
        index_of_id_column : :class:`int` or :class:`str`, optional
            Column to use as row identifier.
        segments_number : :class:`int`, optional
            Number of segments to divide text into (default: 5).
        scaling_method : :class:`int`, optional
            Scaling method - ``1`` = 0-100 scale (default), ``2`` = Z-score.
        skip_wc : :class:`int`, optional
            Skip texts with word count less than this value (default: 10).
        output_data_points : :class:`bool`, optional
            If ``True``, output individual data points (CLI default: ``True``).
        output_format : :class:`str`, optional
            One of ``csv``, ``xlsx``, ``ndjson`` (default: csv).
        """
        _check_bool("combine_columns", combine_columns)
        _check_bool("output_data_points", output_data_points)
        _check_choice("scaling_method", scaling_method, (1, 2))
        _check_choice("output_format", output_format, ("csv", "xlsx", "ndjson"))
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
        input: str | Path,
        output: str | Path,
        *,
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
        input : :class:`str` or :class:`~pathlib.Path`
            Path to a transcript file or folder.  DataFrame/Series input is
            not supported - ``ct`` operates on raw transcripts.
        output : :class:`str` or :class:`~pathlib.Path`
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
            Don't combine untagged lines with the previous speaker (default ``False``).
        """
        _check_bool("single_line", single_line)
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
        input: str | Path | pd.DataFrame | pd.Series,
        output: str | Path,
        *,
        text_column: int | str | None = None,
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
        input : str, :class:`~pathlib.Path`, DataFrame, or Series
            Path to input file/folder, a DataFrame (requires *text_column*),
            or a Series (auto-wraps; *text_column* auto-filled).
        output : :class:`str` or :class:`~pathlib.Path`
            Output file/folder path, or ``"console"``.
        text_column : :class:`int` or :class:`str`, optional
            Column containing the text.  Required for non-Series input.
        person_column : :class:`int` or :class:`str`
            Person ID column.
        group_column : :class:`int` or :class:`str`, optional
            Group ID column.  ``None`` (the default) means "no groups".
        calculate_lsm : :class:`int`, optional
            ``1`` = person-level, ``2`` = group-level, ``3`` = both (default: 3).
        output_type : :class:`int`, optional
            ``1`` = one-to-many (default), ``2`` = pairwise.
        expanded_output : :class:`bool`, optional
            Include expanded LSM output (default ``False``).
        segmentation : :class:`str`, optional
            Split text into segments.
        omit_speakers_num_turns, omit_speakers_word_count : :class:`int`, optional
            Skip thresholds (defaults: 0, 10).
        single_line : :class:`bool`, optional
            Don't combine untagged lines with the previous speaker (default ``False``).
        output_format : :class:`str`, optional
            One of ``csv``, ``xlsx``, ``ndjson`` (default: csv).
        """
        _check_bool("expanded_output", expanded_output)
        _check_bool("single_line", single_line)
        _check_choice("calculate_lsm", calculate_lsm, (1, 2, 3))
        _check_choice("output_type", output_type, (1, 2))
        _check_choice("output_format", output_format, ("csv", "xlsx", "ndjson"))
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
