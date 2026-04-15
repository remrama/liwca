"""
Python wrapper for the LIWC-22 CLI tool.

Builds and runs LIWC-22-cli commands as subprocesses. All seven analysis
modes are supported via the :func:`liwc22` Python function.

Requires LIWC-22 to be installed with the CLI on your PATH.
The LIWC-22 desktop application (or its license server) must be running
when you call the CLI - start it before invoking :func:`liwc22`, or pass
``auto_open=True`` to let liwca handle it.

See Also
--------
- LIWC CLI documentation: https://www.liwc.app/help/cli
- Python CLI example: https://github.com/ryanboyd/liwc-22-cli-python/blob/main/LIWC-22-cli_Example.py
"""

from __future__ import annotations

import argparse
import logging
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

__all__ = [
    "wc",
    "freq",
    "mem",
    "context",
    "arc",
    "ct",
    "lsm",
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
# Argument catalogue
# ---------------------------------------------------------------------------
# Every CLI argument - global, shared-mode, and mode-unique - is defined
# exactly once here.  Each entry is a dict of kwargs to pass to
# ``parser.add_argument()``, plus two extra keys:
#
#   "flags"  - list of flag strings (positional args to add_argument)
#   "is_bool" - True for store_true flags (emitted without a value)


def _a(flags: list[str], dest: str, *, is_bool: bool = False, **kw: Any) -> dict[str, Any]:
    """Shorthand to build a catalogue entry."""
    entry: dict[str, Any] = {"flags": flags, "dest": dest, "is_bool": is_bool}
    if is_bool:
        kw.setdefault("action", "store_true")
        kw.setdefault("default", False)
    else:
        kw.setdefault("default", None)
    entry["kw"] = kw
    return entry


ARG_CATALOGUE: dict[str, dict[str, Any]] = {}


def _register_args(*entries: dict[str, Any]) -> None:
    for e in entries:
        ARG_CATALOGUE[e["dest"]] = e


# ---- global flags --------------------------------------------------------

_register_args(
    _a(
        ["-curls", "--count-urls"],
        "count_urls",
        choices=["yes", "no"],
        help="Count URLs as a single word (default: yes). Only meaningful if url-regexp is set.",
    ),
    _a(
        ["-dec", "--precision"],
        "precision",
        type=int,
        help="Number of decimal places in output (0-16, default: 2).",
    ),
    _a(
        ["-delim", "--csv-delimiter"],
        "csv_delimiter",
        help=r"CSV delimiter character (default: ,). Use \\t for tab.",
    ),
    _a(["-e", "--encoding"], "encoding", help="Input file encoding (default: UTF-8)."),
    _a(
        ["-esc", "--csv-escape"],
        "csv_escape",
        help="CSV escape character (default: none).",
    ),
    _a(
        ["-prep", "--preprocess-cjk-text"],
        "preprocess_cjk",
        choices=["chinese", "japanese", "none"],
        help="Preprocess CJK text with Jieba (Chinese) or Kuromoji (Japanese) tokeniser.",
    ),
    _a(["-quote", "--csv-quote"], "csv_quote", help='CSV quote character (default: ").'),
    _a(
        ["-sh", "--skip-header"],
        "skip_header",
        choices=["yes", "no"],
        help="Skip the first row of an Excel/CSV file (default: yes).",
    ),
    _a(
        ["-subdir", "--include-subfolders"],
        "include_subfolders",
        choices=["yes", "no"],
        help="Include subfolders when analysing a directory (default: yes).",
    ),
    _a(
        ["-urlre", "--url-regexp"],
        "url_regexp",
        help="Regular expression used to capture URLs in text.",
    ),
    _a(
        ["-pint", "--prune-interval"],
        "prune_interval",
        type=int,
        help="Prune frequency list every N words to optimise RAM (default: 10000000).",
    ),
    _a(
        ["-pval", "--prune-threshold-value"],
        "prune_threshold_value",
        type=int,
        help="Minimum n-gram frequency retained during pruning (default: 5).",
    ),
    _a(
        ["-cd", "--column-delimiter"],
        "column_delimiter",
        help="Delimiter between grams in n-gram column names (default: space).",
    ),
)

# ---- shared mode flags ---------------------------------------------------
# These appear in 2+ modes with identical semantics.

_register_args(
    _a(["-i", "--input"], "input", help="Path to input file or folder."),
    _a(["-o", "--output"], "output", help='Output file/folder path, or "console".'),
    _a(
        ["-ccol", "--combine-columns"],
        "combine_columns",
        choices=["yes", "no"],
        help="Combine spreadsheet columns into a single text per row (default: yes).",
    ),
    _a(
        ["-ci", "--column-indices"],
        "column_indices",
        help="Comma-separated column indices (1-based) containing analysable "
        "text. All columns processed by default.",
    ),
    _a(
        ["-f", "--output-format"],
        "output_format",
        choices=["csv", "xlsx", "ndjson"],
        help="Output file format (default: csv).",
    ),
    _a(
        ["-s", "--segmentation"],
        "segmentation",
        help="Split text into segments. Syntax varies by mode - see mode help for details.",
    ),
    _a(
        ["-skip", "--skip-wc"],
        "skip_wc",
        type=int,
        help="Skip texts with word count less than this value (default: 10).",
    ),
    _a(
        ["-idind", "--index-of-id-column"],
        "index_of_id_column",
        type=int,
        help="Column index (1-based) to use as row identifier.",
    ),
    _a(
        ["-cl", "--conversion-list"],
        "conversion_list",
        help="Path to a conversion list or an internal list name "
        '(e.g. internal-EN). Use "none" for no conversion.',
    ),
    _a(
        ["-n", "--n-gram"],
        "n_gram",
        type=int,
        help="N-gram size (1-5). Inclusive of all lower n-grams (default: 1).",
    ),
    _a(
        ["-ts", "--trim-s"],
        "trim_s",
        choices=["yes", "no"],
        help='Trim trailing "\'s" from words (default: yes).',
    ),
    _a(
        ["-osnof", "--omit-speakers-number-of-turns"],
        "omit_speakers_num_turns",
        type=int,
        help="Omit speakers with fewer turns than this value (default: 0).",
    ),
    _a(
        ["-oswf", "--omit-speakers-word-count"],
        "omit_speakers_word_count",
        type=int,
        help="Omit speakers with word count less than this value (default: 10).",
    ),
    # -d as dictionary (wc, context)
    _a(
        ["-d", "--dictionary"],
        "dictionary",
        help="LIWC dictionary name (e.g. LIWC22, LIWC2015) or path to a "
        "custom .dicx file (default: LIWC22).",
    ),
    # -sl as stop-list (freq, mem) - value flag
    _a(
        ["-sl", "--stop-list"],
        "stop_list",
        help="Path to a stop list, an internal list name (e.g. internal-EN), "
        'or "none" (default: internal-EN).',
    ),
    # -sl as single-line (ct, lsm) - bool flag
    _a(
        ["-sl", "--single-line"],
        "single_line",
        is_bool=True,
        help="Don't combine untagged lines with the previous speaker. "
        "Lines without speaker tags will be ignored.",
    ),
)

# ---- mode-unique flags ---------------------------------------------------

_register_args(
    # wc only
    _a(
        ["-ces", "--clean-escaped-spaces"],
        "clean_escaped_spaces",
        choices=["0", "1"],
        help='With --input console: if 1, escaped spaces like "\\n" are '
        "converted to actual spaces (default: 1).",
    ),
    _a(
        ["-ct", "--console-text"],
        "console_text",
        help="Text string to analyse. Use with --input console.",
    ),
    _a(
        ["-ec", "--exclude-categories"],
        "exclude_categories",
        help="Comma-separated dictionary categories to exclude from output.",
    ),
    _a(
        ["-envvar", "--environment-variable"],
        "environment_variable",
        help="Environment variable name containing text. Use with --input envvar.",
    ),
    _a(
        ["-ic", "--include-categories"],
        "include_categories",
        help="Comma-separated dictionary categories to include in output.",
    ),
    _a(
        ["-id", "--row-id-indices"],
        "row_id_indices",
        help="Comma-separated column indices (1-based) for row identifiers. "
        "Multiple columns concatenated with ';'. Defaults to row number.",
    ),
    _a(
        ["-t", "--threads"],
        "threads",
        type=int,
        help="Number of processing threads (default: available cores − 1).",
    ),
    # freq only
    _a(
        ["-d", "--drop-words"],
        "drop_words",
        type=int,
        help="Drop n-grams with frequency less than this value (default: 5).",
    ),
    # mem only
    _a(
        ["--save-theme-scores"],
        "save_theme_scores",
        is_bool=True,
        help="Create and save theme scores table for PCA analysis.",
    ),
    _a(
        ["-epca", "--enable-pca"],
        "enable_pca",
        is_bool=True,
        help="Enable Principal Component Analysis (PCA) for MEM analysis.",
    ),
    _a(
        ["-memot", "--mem-output-type"],
        "mem_output_type",
        choices=["binary", "relative-freq", "raw-counts"],
        help="Document-term matrix format: binary (default), relative-freq, or raw-counts.",
    ),
    _a(
        ["-ttype", "--threshold-type"],
        "threshold_type",
        choices=["min-obspct", "min-freq", "top-obspct", "top-freq"],
        help="Cutoff type for word inclusion (default: min-obspct).",
    ),
    _a(
        ["-tval", "--threshold-value"],
        "threshold_value",
        type=float,
        help="Threshold cutoff value (default: 10.0).",
    ),
    # context only
    _a(
        ["-categ", "--category-to-contextualize"],
        "category_to_contextualize",
        help="Dictionary category to contextualise (default: first category).",
    ),
    _a(
        ["-inpunct", "--keep-punctuation-characters"],
        "keep_punctuation",
        choices=["yes", "no"],
        help="Include punctuation in context items (default: yes).",
    ),
    _a(
        ["-nleft", "--word-window-left"],
        "word_window_left",
        type=int,
        help="Context words to the left of the target word (default: 3).",
    ),
    _a(
        ["-nright", "--word-window-right"],
        "word_window_right",
        type=int,
        help="Context words to the right of the target word (default: 3).",
    ),
    _a(
        ["-wl", "--word-list"],
        "word_list",
        help='Path to a word list file for contextualisation. Wildcards ("*") allowed.',
    ),
    _a(
        ["-words", "--words-to-contextualize"],
        "words_to_contextualize",
        help='Comma-separated words to contextualise. Wildcards ("*") allowed.',
    ),
    # arc only
    _a(
        ["-dp", "--output-individual-data-points"],
        "output_data_points",
        choices=["yes", "no"],
        help="Output individual data points (default: yes).",
    ),
    _a(
        ["-scale", "--scaling-method"],
        "scaling_method",
        choices=["1", "2"],
        help="Scaling method: 1 = 0-100 scale (default), 2 = Z-score.",
    ),
    _a(
        ["-segs", "--segments-number"],
        "segments_number",
        type=int,
        help="Number of segments to divide text into (default: 5).",
    ),
    # ct only
    _a(
        ["-spl", "--speaker-list"],
        "speaker_list",
        help="Path to a text/csv/xlsx file containing a list of speakers.",
    ),
    _a(
        ["-rr", "--regex-removal"],
        "regex_removal",
        help="Regex pattern; first match is removed from each line.",
    ),
    # lsm only
    _a(
        ["-clsm", "--calculate-lsm"],
        "calculate_lsm",
        choices=["1", "2", "3"],
        help="LSM calculation type: 1 = person-level, 2 = group-level, 3 = both (default: 3).",
    ),
    _a(
        ["-gc", "--group-column"],
        "group_column",
        type=int,
        help="Group ID column index (1-based). Use 0 for no groups.",
    ),
    _a(
        ["-ot", "--output-type"],
        "output_type",
        choices=["1", "2"],
        help="Output type: 1 = one-to-many (default), 2 = pairwise.",
    ),
    _a(
        ["-pc", "--person-column"],
        "person_column",
        type=int,
        help="Person ID column index (1-based).",
    ),
    _a(
        ["-tc", "--text-column"],
        "text_column",
        type=int,
        help="Text column index (1-based).",
    ),
    _a(
        ["-expo", "--expanded-output"],
        "expanded_output",
        is_bool=True,
        help="Include expanded LSM output.",
    ),
)


# ---------------------------------------------------------------------------
# Mode definitions
# ---------------------------------------------------------------------------
# Each mode is fully declared as data: which args it uses, which are
# required, which globals it supports, and a short description.

MODE_DEFS: dict[str, dict[str, Any]] = {
    "wc": {
        "help": "LIWC word count analysis.",
        "description": "Run a standard LIWC-22 word count analysis.",
        "required": ["input", "output"],
        "optional": [
            "combine_columns",
            "clean_escaped_spaces",
            "column_indices",
            "console_text",
            "dictionary",
            "exclude_categories",
            "environment_variable",
            "output_format",
            "include_categories",
            "row_id_indices",
            "segmentation",
            "threads",
        ],
        "globals": {
            "count_urls",
            "precision",
            "csv_delimiter",
            "encoding",
            "csv_escape",
            "preprocess_cjk",
            "csv_quote",
            "skip_header",
            "include_subfolders",
            "url_regexp",
        },
    },
    "freq": {
        "help": "Word frequency analysis.",
        "description": "Compute word frequencies across input texts.",
        "required": ["input", "output"],
        "optional": [
            "combine_columns",
            "column_indices",
            "conversion_list",
            "drop_words",
            "output_format",
            "n_gram",
            "skip_wc",
            "stop_list",
            "trim_s",
        ],
        "globals": {
            "count_urls",
            "precision",
            "csv_delimiter",
            "encoding",
            "csv_escape",
            "preprocess_cjk",
            "csv_quote",
            "skip_header",
            "include_subfolders",
            "url_regexp",
            "prune_interval",
            "prune_threshold_value",
        },
    },
    "mem": {
        "help": "Meaning Extraction Method (MEM) analysis.",
        "description": "Run Meaning Extraction Method analysis.",
        "required": ["input", "output"],
        "optional": [
            "save_theme_scores",
            "combine_columns",
            "column_indices",
            "conversion_list",
            "enable_pca",
            "output_format",
            "index_of_id_column",
            "mem_output_type",
            "n_gram",
            "segmentation",
            "skip_wc",
            "stop_list",
            "trim_s",
            "threshold_type",
            "threshold_value",
        ],
        "globals": {
            "count_urls",
            "precision",
            "csv_delimiter",
            "encoding",
            "csv_escape",
            "preprocess_cjk",
            "csv_quote",
            "skip_header",
            "include_subfolders",
            "url_regexp",
            "prune_interval",
            "prune_threshold_value",
            "column_delimiter",
        },
    },
    "context": {
        "help": "Contextualizer analysis.",
        "description": "Run LIWC-22 Contextualizer analysis.",
        "required": ["input", "output"],
        "optional": [
            "category_to_contextualize",
            "combine_columns",
            "column_indices",
            "dictionary",
            "index_of_id_column",
            "keep_punctuation",
            "word_window_left",
            "word_window_right",
            "word_list",
            "words_to_contextualize",
        ],
        "globals": {
            "count_urls",
            "csv_delimiter",
            "encoding",
            "csv_escape",
            "preprocess_cjk",
            "csv_quote",
            "skip_header",
            "include_subfolders",
            "url_regexp",
        },
    },
    "arc": {
        "help": "Arc of Narrative analysis.",
        "description": "Analyse the narrative arc of texts.",
        "required": ["input", "output"],
        "optional": [
            "combine_columns",
            "column_indices",
            "output_data_points",
            "output_format",
            "index_of_id_column",
            "scaling_method",
            "segments_number",
            "skip_wc",
        ],
        "globals": {
            "count_urls",
            "precision",
            "csv_delimiter",
            "encoding",
            "csv_escape",
            "preprocess_cjk",
            "csv_quote",
            "skip_header",
            "include_subfolders",
            "url_regexp",
        },
    },
    "ct": {
        "help": "Convert transcript files to spreadsheet.",
        "description": "Convert separate transcript files into a single spreadsheet.",
        "required": ["input", "output", "speaker_list"],
        "optional": [
            "omit_speakers_num_turns",
            "omit_speakers_word_count",
            "regex_removal",
            "single_line",
        ],
        "globals": {
            "count_urls",
            "encoding",
            "preprocess_cjk",
            "include_subfolders",
            "url_regexp",
        },
    },
    "lsm": {
        "help": "Language Style Matching analysis.",
        "description": "Run Language Style Matching analysis.",
        "required": [
            "input",
            "output",
            "calculate_lsm",
            "group_column",
            "output_type",
            "person_column",
            "text_column",
        ],
        "optional": [
            "expanded_output",
            "output_format",
            "omit_speakers_num_turns",
            "omit_speakers_word_count",
            "segmentation",
            "single_line",
        ],
        "globals": {
            "precision",
            "csv_delimiter",
            "encoding",
            "csv_escape",
            "csv_quote",
            "skip_header",
        },
    },
}


# ---------------------------------------------------------------------------
# Command builder
# ---------------------------------------------------------------------------


def build_command(args: argparse.Namespace) -> list[str]:
    """Translate parsed :class:`~argparse.Namespace` into a LIWC-22-cli command list."""
    cmd: list[str] = [LIWC_CLI, "-m", args.mode]

    defn = MODE_DEFS[args.mode]
    all_keys = defn["required"] + defn["optional"] + list(defn["globals"])

    for dest in all_keys:
        entry = ARG_CATALOGUE[dest]
        cli_flag = entry["flags"][0]  # short flag

        if entry["is_bool"]:
            if getattr(args, dest, False):
                cmd.append(cli_flag)
        else:
            val = getattr(args, dest, None)
            if val is not None:
                cmd.extend([cli_flag, str(val)])

    return cmd


def _quote_for_display(cmd: list[str]) -> str:
    """Format a command list for human-readable display."""
    return " ".join(f'"{tok}"' if " " in tok else tok for tok in cmd)


# ---------------------------------------------------------------------------
# Shared execution logic
# ---------------------------------------------------------------------------


def _run(args: argparse.Namespace) -> int:
    """Run a LIWC-22 CLI command from a parsed namespace."""
    cmd = build_command(args)

    if args.dry_run:
        print(f"Command that would be executed:\n  {_quote_for_display(cmd)}")
        return 0

    # -- ensure LIWC-22 is running -------------------------------------------
    liwc_proc = None
    we_opened_it = False

    if not _is_liwc_running():
        if args.auto_open:
            logger.info("LIWC-22 is not running - starting it now …")
            liwc_proc = _open_liwc_app(use_license_server=not args.use_gui)
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
# Public API - one function per LIWC-22 analysis mode
# ---------------------------------------------------------------------------


def _run_mode(
    mode: str,
    *,
    auto_open: bool,
    use_gui: bool,
    dry_run: bool,
    **cli_args: Any,
) -> int:
    """Assemble an :class:`argparse.Namespace` from per-mode kwargs and invoke :func:`_run`."""
    ns = argparse.Namespace(
        mode=mode,
        auto_open=auto_open,
        use_gui=use_gui,
        dry_run=dry_run,
        **cli_args,
    )
    return _run(ns)


def wc(
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
    count_urls: str | None = None,
    precision: int | None = None,
    csv_delimiter: str | None = None,
    encoding: str | None = None,
    csv_escape: str | None = None,
    preprocess_cjk: str | None = None,
    csv_quote: str | None = None,
    skip_header: str | None = None,
    include_subfolders: str | None = None,
    url_regexp: str | None = None,
    auto_open: bool = False,
    use_gui: bool = False,
    dry_run: bool = False,
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
    count_urls : :class:`str`, optional
        Count URLs as a single word (default: yes). Only meaningful if
        *url_regexp* is set.
    precision : :class:`int`, optional
        Number of decimal places in output (0-16, default: 2).
    csv_delimiter : :class:`str`, optional
        CSV delimiter character (default: ``,``). Use ``\\t`` for tab.
    encoding : :class:`str`, optional
        Input file encoding (default: UTF-8).
    csv_escape : :class:`str`, optional
        CSV escape character (default: none).
    preprocess_cjk : :class:`str`, optional
        Preprocess CJK text with Jieba (Chinese) or Kuromoji (Japanese)
        tokeniser - one of ``chinese``, ``japanese``, ``none``.
    csv_quote : :class:`str`, optional
        CSV quote character (default: ``"``).
    skip_header : :class:`str`, optional
        Skip the first row of an Excel/CSV file (default: yes).
    include_subfolders : :class:`str`, optional
        Include subfolders when analysing a directory (default: yes).
    url_regexp : :class:`str`, optional
        Regular expression used to capture URLs in text.
    auto_open : :class:`bool`, optional
        If LIWC-22 is not running, launch it before analysis and close
        it afterwards (default ``False``).
    use_gui : :class:`bool`, optional
        When auto-opening, prefer the GUI app over the headless license
        server (default ``False``).
    dry_run : :class:`bool`, optional
        Print the CLI command without executing it (default ``False``).

    Returns
    -------
    :class:`int`
        Return code from the LIWC-22 CLI process (0 = success).

    Raises
    ------
    :class:`SystemExit`
        If LIWC-22 is not running and *auto_open* is ``False``.

    See Also
    --------
    count : Pure-Python word counting (no LIWC-22 required).
    `LIWC CLI documentation <https://www.liwc.app/help/cli>`_

    Examples
    --------
    >>> wc(input="data.txt", output="results.csv", dry_run=True)  # doctest: +SKIP
    0
    """
    return _run_mode(
        "wc",
        auto_open=auto_open,
        use_gui=use_gui,
        dry_run=dry_run,
        input=input,
        output=output,
        combine_columns=combine_columns,
        clean_escaped_spaces=clean_escaped_spaces,
        column_indices=column_indices,
        console_text=console_text,
        dictionary=dictionary,
        exclude_categories=exclude_categories,
        environment_variable=environment_variable,
        output_format=output_format,
        include_categories=include_categories,
        row_id_indices=row_id_indices,
        segmentation=segmentation,
        threads=threads,
        count_urls=count_urls,
        precision=precision,
        csv_delimiter=csv_delimiter,
        encoding=encoding,
        csv_escape=csv_escape,
        preprocess_cjk=preprocess_cjk,
        csv_quote=csv_quote,
        skip_header=skip_header,
        include_subfolders=include_subfolders,
        url_regexp=url_regexp,
    )


def freq(
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
    count_urls: str | None = None,
    precision: int | None = None,
    csv_delimiter: str | None = None,
    encoding: str | None = None,
    csv_escape: str | None = None,
    preprocess_cjk: str | None = None,
    csv_quote: str | None = None,
    skip_header: str | None = None,
    include_subfolders: str | None = None,
    url_regexp: str | None = None,
    prune_interval: int | None = None,
    prune_threshold_value: int | None = None,
    auto_open: bool = False,
    use_gui: bool = False,
    dry_run: bool = False,
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
    count_urls : :class:`str`, optional
        Count URLs as a single word (default: yes). Only meaningful if
        *url_regexp* is set.
    precision : :class:`int`, optional
        Number of decimal places in output (0-16, default: 2).
    csv_delimiter : :class:`str`, optional
        CSV delimiter character (default: ``,``). Use ``\\t`` for tab.
    encoding : :class:`str`, optional
        Input file encoding (default: UTF-8).
    csv_escape : :class:`str`, optional
        CSV escape character (default: none).
    preprocess_cjk : :class:`str`, optional
        Preprocess CJK text with Jieba (Chinese) or Kuromoji (Japanese)
        tokeniser - one of ``chinese``, ``japanese``, ``none``.
    csv_quote : :class:`str`, optional
        CSV quote character (default: ``"``).
    skip_header : :class:`str`, optional
        Skip the first row of an Excel/CSV file (default: yes).
    include_subfolders : :class:`str`, optional
        Include subfolders when analysing a directory (default: yes).
    url_regexp : :class:`str`, optional
        Regular expression used to capture URLs in text.
    prune_interval : :class:`int`, optional
        Prune frequency list every N words to optimise RAM
        (default: 10000000).
    prune_threshold_value : :class:`int`, optional
        Minimum n-gram frequency retained during pruning (default: 5).
    auto_open : :class:`bool`, optional
        If LIWC-22 is not running, launch it before analysis and close
        it afterwards (default ``False``).
    use_gui : :class:`bool`, optional
        When auto-opening, prefer the GUI app over the headless license
        server (default ``False``).
    dry_run : :class:`bool`, optional
        Print the CLI command without executing it (default ``False``).

    Returns
    -------
    :class:`int`
        Return code from the LIWC-22 CLI process (0 = success).

    Raises
    ------
    :class:`SystemExit`
        If LIWC-22 is not running and *auto_open* is ``False``.

    Examples
    --------
    >>> freq(input="corpus/", output="freqs.csv", n_gram=2, dry_run=True)  # doctest: +SKIP
    0
    """
    return _run_mode(
        "freq",
        auto_open=auto_open,
        use_gui=use_gui,
        dry_run=dry_run,
        input=input,
        output=output,
        combine_columns=combine_columns,
        column_indices=column_indices,
        conversion_list=conversion_list,
        drop_words=drop_words,
        output_format=output_format,
        n_gram=n_gram,
        skip_wc=skip_wc,
        stop_list=stop_list,
        trim_s=trim_s,
        count_urls=count_urls,
        precision=precision,
        csv_delimiter=csv_delimiter,
        encoding=encoding,
        csv_escape=csv_escape,
        preprocess_cjk=preprocess_cjk,
        csv_quote=csv_quote,
        skip_header=skip_header,
        include_subfolders=include_subfolders,
        url_regexp=url_regexp,
        prune_interval=prune_interval,
        prune_threshold_value=prune_threshold_value,
    )


def mem(
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
    count_urls: str | None = None,
    precision: int | None = None,
    csv_delimiter: str | None = None,
    encoding: str | None = None,
    csv_escape: str | None = None,
    preprocess_cjk: str | None = None,
    csv_quote: str | None = None,
    skip_header: str | None = None,
    include_subfolders: str | None = None,
    url_regexp: str | None = None,
    prune_interval: int | None = None,
    prune_threshold_value: int | None = None,
    column_delimiter: str | None = None,
    auto_open: bool = False,
    use_gui: bool = False,
    dry_run: bool = False,
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
        Create and save theme scores table for PCA analysis
        (default ``False``).
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
    count_urls : :class:`str`, optional
        Count URLs as a single word (default: yes). Only meaningful if
        *url_regexp* is set.
    precision : :class:`int`, optional
        Number of decimal places in output (0-16, default: 2).
    csv_delimiter : :class:`str`, optional
        CSV delimiter character (default: ``,``). Use ``\\t`` for tab.
    encoding : :class:`str`, optional
        Input file encoding (default: UTF-8).
    csv_escape : :class:`str`, optional
        CSV escape character (default: none).
    preprocess_cjk : :class:`str`, optional
        Preprocess CJK text with Jieba (Chinese) or Kuromoji (Japanese)
        tokeniser - one of ``chinese``, ``japanese``, ``none``.
    csv_quote : :class:`str`, optional
        CSV quote character (default: ``"``).
    skip_header : :class:`str`, optional
        Skip the first row of an Excel/CSV file (default: yes).
    include_subfolders : :class:`str`, optional
        Include subfolders when analysing a directory (default: yes).
    url_regexp : :class:`str`, optional
        Regular expression used to capture URLs in text.
    prune_interval : :class:`int`, optional
        Prune frequency list every N words to optimise RAM
        (default: 10000000).
    prune_threshold_value : :class:`int`, optional
        Minimum n-gram frequency retained during pruning (default: 5).
    column_delimiter : :class:`str`, optional
        Delimiter between grams in n-gram column names (default: space).
    auto_open : :class:`bool`, optional
        If LIWC-22 is not running, launch it before analysis and close
        it afterwards (default ``False``).
    use_gui : :class:`bool`, optional
        When auto-opening, prefer the GUI app over the headless license
        server (default ``False``).
    dry_run : :class:`bool`, optional
        Print the CLI command without executing it (default ``False``).

    Returns
    -------
    :class:`int`
        Return code from the LIWC-22 CLI process (0 = success).

    Raises
    ------
    :class:`SystemExit`
        If LIWC-22 is not running and *auto_open* is ``False``.

    Examples
    --------
    >>> mem(input="texts/", output="mem.csv", enable_pca=True, dry_run=True)  # doctest: +SKIP
    0
    """
    return _run_mode(
        "mem",
        auto_open=auto_open,
        use_gui=use_gui,
        dry_run=dry_run,
        input=input,
        output=output,
        save_theme_scores=save_theme_scores,
        combine_columns=combine_columns,
        column_indices=column_indices,
        conversion_list=conversion_list,
        enable_pca=enable_pca,
        output_format=output_format,
        index_of_id_column=index_of_id_column,
        mem_output_type=mem_output_type,
        n_gram=n_gram,
        segmentation=segmentation,
        skip_wc=skip_wc,
        stop_list=stop_list,
        trim_s=trim_s,
        threshold_type=threshold_type,
        threshold_value=threshold_value,
        count_urls=count_urls,
        precision=precision,
        csv_delimiter=csv_delimiter,
        encoding=encoding,
        csv_escape=csv_escape,
        preprocess_cjk=preprocess_cjk,
        csv_quote=csv_quote,
        skip_header=skip_header,
        include_subfolders=include_subfolders,
        url_regexp=url_regexp,
        prune_interval=prune_interval,
        prune_threshold_value=prune_threshold_value,
        column_delimiter=column_delimiter,
    )


def context(
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
    count_urls: str | None = None,
    csv_delimiter: str | None = None,
    encoding: str | None = None,
    csv_escape: str | None = None,
    preprocess_cjk: str | None = None,
    csv_quote: str | None = None,
    skip_header: str | None = None,
    include_subfolders: str | None = None,
    url_regexp: str | None = None,
    auto_open: bool = False,
    use_gui: bool = False,
    dry_run: bool = False,
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
        Path to a word list file for contextualisation.
        Wildcards (``*``) allowed.
    words_to_contextualize : :class:`str`, optional
        Comma-separated words to contextualise. Wildcards (``*``) allowed.
    count_urls : :class:`str`, optional
        Count URLs as a single word (default: yes). Only meaningful if
        *url_regexp* is set.
    csv_delimiter : :class:`str`, optional
        CSV delimiter character (default: ``,``). Use ``\\t`` for tab.
    encoding : :class:`str`, optional
        Input file encoding (default: UTF-8).
    csv_escape : :class:`str`, optional
        CSV escape character (default: none).
    preprocess_cjk : :class:`str`, optional
        Preprocess CJK text with Jieba (Chinese) or Kuromoji (Japanese)
        tokeniser - one of ``chinese``, ``japanese``, ``none``.
    csv_quote : :class:`str`, optional
        CSV quote character (default: ``"``).
    skip_header : :class:`str`, optional
        Skip the first row of an Excel/CSV file (default: yes).
    include_subfolders : :class:`str`, optional
        Include subfolders when analysing a directory (default: yes).
    url_regexp : :class:`str`, optional
        Regular expression used to capture URLs in text.
    auto_open : :class:`bool`, optional
        If LIWC-22 is not running, launch it before analysis and close
        it afterwards (default ``False``).
    use_gui : :class:`bool`, optional
        When auto-opening, prefer the GUI app over the headless license
        server (default ``False``).
    dry_run : :class:`bool`, optional
        Print the CLI command without executing it (default ``False``).

    Returns
    -------
    :class:`int`
        Return code from the LIWC-22 CLI process (0 = success).

    Raises
    ------
    :class:`SystemExit`
        If LIWC-22 is not running and *auto_open* is ``False``.

    Examples
    --------
    >>> context(input="data.txt", output="ctx.csv", dry_run=True)  # doctest: +SKIP
    0
    """
    return _run_mode(
        "context",
        auto_open=auto_open,
        use_gui=use_gui,
        dry_run=dry_run,
        input=input,
        output=output,
        category_to_contextualize=category_to_contextualize,
        combine_columns=combine_columns,
        column_indices=column_indices,
        dictionary=dictionary,
        index_of_id_column=index_of_id_column,
        keep_punctuation=keep_punctuation,
        word_window_left=word_window_left,
        word_window_right=word_window_right,
        word_list=word_list,
        words_to_contextualize=words_to_contextualize,
        count_urls=count_urls,
        csv_delimiter=csv_delimiter,
        encoding=encoding,
        csv_escape=csv_escape,
        preprocess_cjk=preprocess_cjk,
        csv_quote=csv_quote,
        skip_header=skip_header,
        include_subfolders=include_subfolders,
        url_regexp=url_regexp,
    )


def arc(
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
    count_urls: str | None = None,
    precision: int | None = None,
    csv_delimiter: str | None = None,
    encoding: str | None = None,
    csv_escape: str | None = None,
    preprocess_cjk: str | None = None,
    csv_quote: str | None = None,
    skip_header: str | None = None,
    include_subfolders: str | None = None,
    url_regexp: str | None = None,
    auto_open: bool = False,
    use_gui: bool = False,
    dry_run: bool = False,
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
    count_urls : :class:`str`, optional
        Count URLs as a single word (default: yes). Only meaningful if
        *url_regexp* is set.
    precision : :class:`int`, optional
        Number of decimal places in output (0-16, default: 2).
    csv_delimiter : :class:`str`, optional
        CSV delimiter character (default: ``,``). Use ``\\t`` for tab.
    encoding : :class:`str`, optional
        Input file encoding (default: UTF-8).
    csv_escape : :class:`str`, optional
        CSV escape character (default: none).
    preprocess_cjk : :class:`str`, optional
        Preprocess CJK text with Jieba (Chinese) or Kuromoji (Japanese)
        tokeniser - one of ``chinese``, ``japanese``, ``none``.
    csv_quote : :class:`str`, optional
        CSV quote character (default: ``"``).
    skip_header : :class:`str`, optional
        Skip the first row of an Excel/CSV file (default: yes).
    include_subfolders : :class:`str`, optional
        Include subfolders when analysing a directory (default: yes).
    url_regexp : :class:`str`, optional
        Regular expression used to capture URLs in text.
    auto_open : :class:`bool`, optional
        If LIWC-22 is not running, launch it before analysis and close
        it afterwards (default ``False``).
    use_gui : :class:`bool`, optional
        When auto-opening, prefer the GUI app over the headless license
        server (default ``False``).
    dry_run : :class:`bool`, optional
        Print the CLI command without executing it (default ``False``).

    Returns
    -------
    :class:`int`
        Return code from the LIWC-22 CLI process (0 = success).

    Raises
    ------
    :class:`SystemExit`
        If LIWC-22 is not running and *auto_open* is ``False``.

    Examples
    --------
    >>> arc(input="stories/", output="arc.csv", dry_run=True)  # doctest: +SKIP
    0
    """
    return _run_mode(
        "arc",
        auto_open=auto_open,
        use_gui=use_gui,
        dry_run=dry_run,
        input=input,
        output=output,
        combine_columns=combine_columns,
        column_indices=column_indices,
        output_data_points=output_data_points,
        output_format=output_format,
        index_of_id_column=index_of_id_column,
        scaling_method=scaling_method,
        segments_number=segments_number,
        skip_wc=skip_wc,
        count_urls=count_urls,
        precision=precision,
        csv_delimiter=csv_delimiter,
        encoding=encoding,
        csv_escape=csv_escape,
        preprocess_cjk=preprocess_cjk,
        csv_quote=csv_quote,
        skip_header=skip_header,
        include_subfolders=include_subfolders,
        url_regexp=url_regexp,
    )


def ct(
    *,
    input: str,
    output: str,
    speaker_list: str,
    omit_speakers_num_turns: int | None = None,
    omit_speakers_word_count: int | None = None,
    regex_removal: str | None = None,
    single_line: bool = False,
    count_urls: str | None = None,
    encoding: str | None = None,
    preprocess_cjk: str | None = None,
    include_subfolders: str | None = None,
    url_regexp: str | None = None,
    auto_open: bool = False,
    use_gui: bool = False,
    dry_run: bool = False,
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
    count_urls : :class:`str`, optional
        Count URLs as a single word (default: yes). Only meaningful if
        *url_regexp* is set.
    encoding : :class:`str`, optional
        Input file encoding (default: UTF-8).
    preprocess_cjk : :class:`str`, optional
        Preprocess CJK text with Jieba (Chinese) or Kuromoji (Japanese)
        tokeniser - one of ``chinese``, ``japanese``, ``none``.
    include_subfolders : :class:`str`, optional
        Include subfolders when analysing a directory (default: yes).
    url_regexp : :class:`str`, optional
        Regular expression used to capture URLs in text.
    auto_open : :class:`bool`, optional
        If LIWC-22 is not running, launch it before analysis and close
        it afterwards (default ``False``).
    use_gui : :class:`bool`, optional
        When auto-opening, prefer the GUI app over the headless license
        server (default ``False``).
    dry_run : :class:`bool`, optional
        Print the CLI command without executing it (default ``False``).

    Returns
    -------
    :class:`int`
        Return code from the LIWC-22 CLI process (0 = success).

    Raises
    ------
    :class:`SystemExit`
        If LIWC-22 is not running and *auto_open* is ``False``.

    Examples
    --------
    >>> ct(  # doctest: +SKIP
    ...     input="transcripts/",
    ...     output="merged.csv",
    ...     speaker_list="speakers.txt",
    ...     dry_run=True,
    ... )
    0
    """
    return _run_mode(
        "ct",
        auto_open=auto_open,
        use_gui=use_gui,
        dry_run=dry_run,
        input=input,
        output=output,
        speaker_list=speaker_list,
        omit_speakers_num_turns=omit_speakers_num_turns,
        omit_speakers_word_count=omit_speakers_word_count,
        regex_removal=regex_removal,
        single_line=single_line,
        count_urls=count_urls,
        encoding=encoding,
        preprocess_cjk=preprocess_cjk,
        include_subfolders=include_subfolders,
        url_regexp=url_regexp,
    )


def lsm(
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
    precision: int | None = None,
    csv_delimiter: str | None = None,
    encoding: str | None = None,
    csv_escape: str | None = None,
    csv_quote: str | None = None,
    skip_header: str | None = None,
    auto_open: bool = False,
    use_gui: bool = False,
    dry_run: bool = False,
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
    precision : :class:`int`, optional
        Number of decimal places in output (0-16, default: 2).
    csv_delimiter : :class:`str`, optional
        CSV delimiter character (default: ``,``). Use ``\\t`` for tab.
    encoding : :class:`str`, optional
        Input file encoding (default: UTF-8).
    csv_escape : :class:`str`, optional
        CSV escape character (default: none).
    csv_quote : :class:`str`, optional
        CSV quote character (default: ``"``).
    skip_header : :class:`str`, optional
        Skip the first row of an Excel/CSV file (default: yes).
    auto_open : :class:`bool`, optional
        If LIWC-22 is not running, launch it before analysis and close
        it afterwards (default ``False``).
    use_gui : :class:`bool`, optional
        When auto-opening, prefer the GUI app over the headless license
        server (default ``False``).
    dry_run : :class:`bool`, optional
        Print the CLI command without executing it (default ``False``).

    Returns
    -------
    :class:`int`
        Return code from the LIWC-22 CLI process (0 = success).

    Raises
    ------
    :class:`SystemExit`
        If LIWC-22 is not running and *auto_open* is ``False``.

    Examples
    --------
    >>> lsm(  # doctest: +SKIP
    ...     input="chat.csv",
    ...     output="lsm.csv",
    ...     calculate_lsm="3",
    ...     group_column=1,
    ...     output_type="1",
    ...     person_column=2,
    ...     text_column=3,
    ...     dry_run=True,
    ... )
    0
    """
    return _run_mode(
        "lsm",
        auto_open=auto_open,
        use_gui=use_gui,
        dry_run=dry_run,
        input=input,
        output=output,
        calculate_lsm=calculate_lsm,
        group_column=group_column,
        output_type=output_type,
        person_column=person_column,
        text_column=text_column,
        expanded_output=expanded_output,
        output_format=output_format,
        omit_speakers_num_turns=omit_speakers_num_turns,
        omit_speakers_word_count=omit_speakers_word_count,
        segmentation=segmentation,
        single_line=single_line,
        precision=precision,
        csv_delimiter=csv_delimiter,
        encoding=encoding,
        csv_escape=csv_escape,
        csv_quote=csv_quote,
        skip_header=skip_header,
    )
