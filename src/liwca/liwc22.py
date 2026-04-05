"""
Python wrapper for the LIWC-22 CLI tool.

Replicates the LIWC-22-cli interface using argparse with subparsers
for each analysis mode. Builds the appropriate CLI command and runs
it as a subprocess.

Provides both a Python API (:func:`cli`) and a command-line entrypoint
(``liwca`` console script).

Requires LIWC-22 to be installed with the CLI on your PATH.

References
----------
- https://www.liwc.app/help/cli
- https://github.com/ryanboyd/liwc-22-cli-python/blob/main/LIWC-22-cli_Example.py
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
    "cli",
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
# Every CLI argument — global, shared-mode, and mode-unique — is defined
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
        help="Split text into segments. Syntax varies by mode — see mode help for details.",
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
    # -sl as stop-list (freq, mem) — value flag
    _a(
        ["-sl", "--stop-list"],
        "stop_list",
        help="Path to a stop list, an internal list name (e.g. internal-EN), "
        'or "none" (default: internal-EN).',
    ),
    # -sl as single-line (ct, lsm) — bool flag
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
# Parser construction
# ---------------------------------------------------------------------------


def _add_arg(parser: argparse.ArgumentParser, dest: str, *, required: bool = False) -> None:
    """Add a single argument from the catalogue to *parser*."""
    entry = ARG_CATALOGUE[dest]
    kw = dict(entry["kw"])  # copy so we don't mutate the catalogue
    if required and not entry["is_bool"]:
        kw["required"] = True
    parser.add_argument(*entry["flags"], dest=dest, **kw)


def _make_auto_open_parser() -> argparse.ArgumentParser:
    """Parent parser for the --auto-open / --dry-run flags."""
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument(
        "--auto-open",
        action="store_true",
        default=False,
        help="If LIWC-22 is not running, launch it before analysis and close it afterwards.",
    )
    p.add_argument(
        "--use-gui",
        action="store_true",
        default=False,
        help="When auto-opening, prefer the GUI app over the headless license server.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Print the CLI command without executing it.",
    )
    return p


def build_parser() -> argparse.ArgumentParser:
    """Construct the full :class:`~argparse.ArgumentParser` from :data:`MODE_DEFS`."""
    auto_open = _make_auto_open_parser()

    parser = argparse.ArgumentParser(
        prog="liwca",
        description="Python wrapper around the LIWC-22 command-line interface.\n"
        "Select a mode and pass the appropriate arguments.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(
        dest="mode",
        title="analysis modes",
        description="Available LIWC-22 analysis modes.",
        required=True,
    )

    for mode, defn in MODE_DEFS.items():
        # Build a parent parser with only this mode's global flags.
        global_parent = argparse.ArgumentParser(add_help=False)
        for key in defn["globals"]:
            _add_arg(global_parent, key)

        sp = subparsers.add_parser(
            mode,
            parents=[global_parent, auto_open],
            help=defn["help"],
            description=defn["description"],
        )

        for dest in defn["required"]:
            _add_arg(sp, dest, required=True)
        for dest in defn["optional"]:
            _add_arg(sp, dest)

    return parser


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
# Python API
# ---------------------------------------------------------------------------


def cli(
    mode: str,
    *,
    auto_open: bool = False,
    use_gui: bool = False,
    dry_run: bool = False,
    **kwargs: Any,
) -> int:
    """
    Execute a LIWC-22 CLI analysis from Python.

    Parameters
    ----------
    mode : :class:`str`
        Analysis mode — one of ``"wc"``, ``"freq"``, ``"mem"``,
        ``"context"``, ``"arc"``, ``"ct"``, ``"lsm"``.
    auto_open : :class:`bool`, optional
        If LIWC-22 is not running, launch it before analysis and close
        it afterwards (default ``False``).
    use_gui : :class:`bool`, optional
        When auto-opening, prefer the GUI app over the headless license
        server (default ``False``).
    dry_run : :class:`bool`, optional
        Print the CLI command without executing it (default ``False``).
    **kwargs : :class:`~typing.Any`
        Mode-specific arguments.  Use the Python ``dest`` names from the
        argument catalogue (underscored, e.g. ``input="data.txt"``,
        ``output="results.csv"``, ``output_format="xlsx"``).

    Returns
    -------
    :class:`int`
        Return code from the LIWC-22 CLI process (0 = success).

    Raises
    ------
    :class:`ValueError`
        If *mode* is not a recognised analysis mode.
    :class:`SystemExit`
        If LIWC-22 is not running and *auto_open* is ``False``.

    Examples
    --------
    >>> cli("wc", input="data.txt", output="results.csv")  # doctest: +SKIP
    0
    >>> cli("wc", input="data.txt", output="results.csv", dry_run=True)  # doctest: +SKIP
    0
    """
    if mode not in MODE_DEFS:
        raise ValueError(f"Unknown mode {mode!r}. Choose from: {', '.join(MODE_DEFS)}")

    # Build a namespace that looks like argparse output.
    ns = argparse.Namespace(
        mode=mode,
        auto_open=auto_open,
        use_gui=use_gui,
        dry_run=dry_run,
        **kwargs,
    )

    return _run(ns)


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
            logger.info("LIWC-22 is not running — starting it now …")
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
# Console entrypoint
# ---------------------------------------------------------------------------


def main() -> int:
    """Console script entrypoint for the ``liwca`` command.

    Returns
    -------
    :class:`int`
        Return code from the LIWC-22 CLI process (0 = success).
    """
    parser = build_parser()
    args = parser.parse_args()
    return _run(args)


if __name__ == "__main__":
    raise SystemExit(main())
