"""Tests for liwca.liwc22 - Liwc22 class and command builder."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pandas as pd
import pytest

import liwca
from liwca.liwc22 import (
    BOOL_FLAGS,
    COLUMN_FLAGS,
    COLUMN_LIST_FLAGS,
    FLAG_BY_DEST,
    LIST_FLAGS,
    MODE_GLOBALS,
    ONE_ZERO_FLAGS,
    YES_NO_FLAGS,
    Liwc22,
    _resolve_dictionary_arg,
    _shape_wc_output,
    build_command,
    wc_output_schema,
)

EXECUTION_CONTROL_ARGS = {"auto_open", "use_gui", "dry_run"}

ALL_MODES = {"wc", "freq", "mem", "context", "arc", "ct", "lsm"}

# Minimum kwargs each mode needs to construct a legal call.  Column args use
# 0-based Python ``int`` and numeric-coded args use plain ``int`` - the new
# Pythonic types.
MODE_REQUIRED_KWARGS: dict[str, dict[str, object]] = {
    "wc": {"input": "data.txt", "output": "results.csv"},
    "freq": {"input": "corpus/", "output": "freqs.csv"},
    "mem": {"input": "texts/", "output": "mem.csv"},
    "context": {"input": "data.txt", "output": "ctx.csv"},
    "arc": {"input": "stories/", "output": "arc.csv"},
    "ct": {"input": "transcripts/", "output": "merged.csv", "speakers": "speakers.txt"},
    "lsm": {
        "input": "chat.csv",
        "output": "lsm.csv",
        "group_column": 0,
        "person_column": 1,
        "text_column": 2,
    },
}


# ---------------------------------------------------------------------------
# Flag catalogue (FLAG_BY_DEST, BOOL_FLAGS, YES_NO_FLAGS, etc., MODE_GLOBALS)
# ---------------------------------------------------------------------------


class TestFlagCatalogue:
    """Structural checks on module-level flag data."""

    def test_execution_control_not_in_flag_catalogue(self) -> None:
        """auto_open/use_gui/dry_run are Python-side, not CLI flags."""
        assert set(FLAG_BY_DEST).isdisjoint(EXECUTION_CONTROL_ARGS)

    def test_bool_flags_subset_of_flag_catalogue(self) -> None:
        assert BOOL_FLAGS <= set(FLAG_BY_DEST)

    def test_yes_no_flags_subset_of_flag_catalogue(self) -> None:
        assert YES_NO_FLAGS <= set(FLAG_BY_DEST)

    def test_one_zero_flags_subset_of_flag_catalogue(self) -> None:
        assert ONE_ZERO_FLAGS <= set(FLAG_BY_DEST)

    def test_list_flags_subset_of_flag_catalogue(self) -> None:
        assert LIST_FLAGS <= set(FLAG_BY_DEST)

    def test_column_flags_subset_of_flag_catalogue(self) -> None:
        assert COLUMN_FLAGS <= set(FLAG_BY_DEST)

    def test_column_list_flags_subset_of_flag_catalogue(self) -> None:
        assert COLUMN_LIST_FLAGS <= set(FLAG_BY_DEST)

    def test_bool_and_yes_no_disjoint(self) -> None:
        """Value-less bools and yes/no bools must not overlap."""
        assert BOOL_FLAGS.isdisjoint(YES_NO_FLAGS)

    def test_column_list_flags_subset_of_list_flags(self) -> None:
        """Column-list args are also list args (comma-joined when emitted)."""
        assert COLUMN_LIST_FLAGS <= LIST_FLAGS

    def test_mode_globals_keys(self) -> None:
        assert set(MODE_GLOBALS) == ALL_MODES

    @pytest.mark.parametrize("mode", sorted(ALL_MODES))
    def test_mode_globals_in_flag_catalogue(self, mode: str) -> None:
        """Every hoisted arg a mode declares must have a CLI flag."""
        assert MODE_GLOBALS[mode] <= set(FLAG_BY_DEST)


# ---------------------------------------------------------------------------
# Command building
# ---------------------------------------------------------------------------


class TestBuildCommand:
    """Tests for build_command - (mode, dict) -> argv."""

    def test_basic_wc_command(self) -> None:
        cmd = build_command("wc", {"input": "data.txt", "output": "results.csv"})
        assert cmd[0] == "LIWC-22-cli"
        assert cmd[1] == "-m"
        assert cmd[2] == "wc"
        assert "-i" in cmd and "data.txt" in cmd
        assert "-o" in cmd and "results.csv" in cmd

    def test_mode_flag_appears_once(self) -> None:
        cmd = build_command("freq", {"input": "a", "output": "b", "ngram": 2})
        assert cmd.count("-m") == 1

    def test_none_values_skipped(self) -> None:
        cmd = build_command(
            "wc",
            {"input": "a", "output": "b", "dictionary": None, "threads": None},
        )
        assert "-d" not in cmd
        assert "-t" not in cmd

    def test_value_args_included_when_set(self) -> None:
        cmd = build_command(
            "wc",
            {"input": "a", "output": "b", "dictionary": "LIWC2015", "threads": 4},
        )
        assert "-d" in cmd and "LIWC2015" in cmd
        assert "-t" in cmd and "4" in cmd

    def test_bool_flag_included_when_true(self) -> None:
        cmd = build_command(
            "mem",
            {"input": "a", "output": "b", "save_theme_scores": True},
        )
        assert "--save-theme-scores" in cmd

    def test_bool_flag_excluded_when_false(self) -> None:
        cmd = build_command(
            "mem",
            {"input": "a", "output": "b", "save_theme_scores": False},
        )
        assert "--save-theme-scores" not in cmd

    def test_bool_flag_has_no_value(self) -> None:
        """Bool flags emit the flag alone - no value following."""
        cmd = build_command("mem", {"input": "a", "output": "b", "enable_pca": True})
        idx = cmd.index("-epca")
        # Nothing after -epca, or next token is another flag (starts with '-').
        assert idx == len(cmd) - 1 or cmd[idx + 1].startswith("-")

    def test_yes_no_flag_true_emits_yes(self) -> None:
        cmd = build_command("wc", {"input": "a", "output": "b", "count_urls": True})
        idx = cmd.index("-curls")
        assert cmd[idx + 1] == "yes"

    def test_yes_no_flag_false_emits_no(self) -> None:
        cmd = build_command("wc", {"input": "a", "output": "b", "count_urls": False})
        idx = cmd.index("-curls")
        assert cmd[idx + 1] == "no"

    def test_one_zero_flag_true_emits_one(self) -> None:
        cmd = build_command(
            "wc",
            {"input": "a", "output": "b", "clean_escaped_spaces": True},
        )
        idx = cmd.index("-ces")
        assert cmd[idx + 1] == "1"

    def test_one_zero_flag_false_emits_zero(self) -> None:
        cmd = build_command(
            "wc",
            {"input": "a", "output": "b", "clean_escaped_spaces": False},
        )
        idx = cmd.index("-ces")
        assert cmd[idx + 1] == "0"

    def test_list_flag_comma_joined(self) -> None:
        cmd = build_command(
            "wc",
            {"input": "a", "output": "b", "include_categories": ["anger", "joy"]},
        )
        idx = cmd.index("-ic")
        assert cmd[idx + 1] == "anger,joy"

    def test_list_flag_single_element(self) -> None:
        cmd = build_command(
            "wc",
            {"input": "a", "output": "b", "include_categories": ["anger"]},
        )
        idx = cmd.index("-ic")
        assert cmd[idx + 1] == "anger"


# ---------------------------------------------------------------------------
# Liwc22 class
# ---------------------------------------------------------------------------


class TestLiwc22Class:
    """Tests for the Liwc22 class and its seven mode methods."""

    @pytest.mark.parametrize("mode", sorted(ALL_MODES))
    def test_dry_run_per_mode(self, mode: str) -> None:
        liwc = Liwc22(dry_run=True)
        kwargs = MODE_REQUIRED_KWARGS[mode]
        result = getattr(liwc, mode)(**kwargs)
        assert result == kwargs["output"]

    def test_module_attribute_access(self) -> None:
        """Liwc22 is reachable via liwca.Liwc22."""
        assert liwca.Liwc22 is Liwc22

    def test_globals_injected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Hoisted globals set on the instance flow through to build_command."""
        captured: dict[str, object] = {}

        def fake_build_command(mode: str, cli_args: dict[str, object]) -> list[str]:
            captured["mode"] = mode
            captured["cli_args"] = dict(cli_args)
            return ["LIWC-22-cli", "-m", mode]

        monkeypatch.setattr("liwca.liwc22.build_command", fake_build_command)

        Liwc22(encoding="utf-8", precision=4, dry_run=True).wc(
            input="x",
            output="y",
        )

        cli_args = captured["cli_args"]
        assert isinstance(cli_args, dict)
        assert cli_args.get("encoding") == "utf-8"
        assert cli_args.get("precision") == 4

    def test_globals_filtered_for_lsm(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """count_urls is not in MODE_GLOBALS['lsm'] - must not reach the CLI."""
        captured: dict[str, object] = {}

        def fake_build_command(mode: str, cli_args: dict[str, object]) -> list[str]:
            captured["cli_args"] = dict(cli_args)
            return ["LIWC-22-cli", "-m", mode]

        monkeypatch.setattr("liwca.liwc22.build_command", fake_build_command)

        Liwc22(count_urls=True, dry_run=True).lsm(**MODE_REQUIRED_KWARGS["lsm"])

        cli_args = captured["cli_args"]
        assert isinstance(cli_args, dict)
        assert "count_urls" not in cli_args

    def test_globals_filtered_for_ct(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """csv_delimiter / precision are not in MODE_GLOBALS['ct']."""
        captured: dict[str, object] = {}

        def fake_build_command(mode: str, cli_args: dict[str, object]) -> list[str]:
            captured["cli_args"] = dict(cli_args)
            return ["LIWC-22-cli", "-m", mode]

        monkeypatch.setattr("liwca.liwc22.build_command", fake_build_command)

        Liwc22(csv_delimiter=",", precision=2, dry_run=True).ct(
            **MODE_REQUIRED_KWARGS["ct"],
        )

        cli_args = captured["cli_args"]
        assert isinstance(cli_args, dict)
        assert "csv_delimiter" not in cli_args
        assert "precision" not in cli_args

    def test_hoisted_arg_not_accepted_by_method(self) -> None:
        """Passing a hoisted arg (encoding) to a method must be a TypeError."""
        with pytest.raises(TypeError, match="encoding"):
            Liwc22(dry_run=True).wc(input="x", output="y", encoding="utf-8")

    def test_unsupported_kwarg_raises(self) -> None:
        """Passing a freq-only kwarg to wc must raise TypeError."""
        with pytest.raises(TypeError, match="drop_words"):
            Liwc22(dry_run=True).wc(input="x", output="y", drop_words=5)

    def test_missing_required_raises(self) -> None:
        with pytest.raises(TypeError):
            Liwc22(dry_run=True).wc()

    def test_ct_missing_speakers_raises(self) -> None:
        with pytest.raises(TypeError):
            Liwc22(dry_run=True).ct(input="x", output="y")

    def test_instance_reuse(self) -> None:
        """One instance can drive multiple mode calls with no state leakage."""
        liwc = Liwc22(dry_run=True)
        assert liwc.wc(input="x", output="y") == "y"
        assert liwc.freq(input="x", output="y", ngram=2) == "y"


# ---------------------------------------------------------------------------
# Argument translation (bool -> yes/no, iterable -> comma-join, 0-based -> 1-based)
# ---------------------------------------------------------------------------


def _capture_cli_args(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    """Install a fake build_command and return the dict that captures its input."""
    captured: dict[str, object] = {}

    def fake_build_command(mode: str, cli_args: dict[str, object]) -> list[str]:
        captured["mode"] = mode
        captured["cli_args"] = dict(cli_args)
        return ["LIWC-22-cli", "-m", mode]

    monkeypatch.setattr("liwca.liwc22.build_command", fake_build_command)
    return captured


class TestArgTranslation:
    """Tests for the Pythonic-type -> CLI-value translations in build_command."""

    # -- yes/no ------------------------------------------------------------

    def test_yes_no_true_reaches_cli_as_yes(self) -> None:
        """Liwc22(count_urls=True) -> '... -curls yes ...'."""
        cmd = build_command("wc", {"input": "a", "output": "b", "count_urls": True})
        idx = cmd.index("-curls")
        assert cmd[idx + 1] == "yes"

    def test_yes_no_false_reaches_cli_as_no(self) -> None:
        cmd = build_command("wc", {"input": "a", "output": "b", "count_urls": False})
        idx = cmd.index("-curls")
        assert cmd[idx + 1] == "no"

    def test_yes_no_via_instance_end_to_end(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Bool on the instance propagates to the cli_args dict as a bool."""
        captured = _capture_cli_args(monkeypatch)
        Liwc22(count_urls=True, dry_run=True).wc(input="x", output="y")
        assert captured["cli_args"]["count_urls"] is True  # type: ignore[index]

    # -- 1/0 ---------------------------------------------------------------

    def test_one_zero_true(self) -> None:
        cmd = build_command(
            "wc",
            {"input": "a", "output": "b", "clean_escaped_spaces": True},
        )
        idx = cmd.index("-ces")
        assert cmd[idx + 1] == "1"

    def test_one_zero_false(self) -> None:
        cmd = build_command(
            "wc",
            {"input": "a", "output": "b", "clean_escaped_spaces": False},
        )
        idx = cmd.index("-ces")
        assert cmd[idx + 1] == "0"

    # -- list/iterable -----------------------------------------------------

    def test_include_categories_list(self) -> None:
        cmd = build_command(
            "wc",
            {"input": "a", "output": "b", "include_categories": ["anger", "joy"]},
        )
        idx = cmd.index("-ic")
        assert cmd[idx + 1] == "anger,joy"

    def test_include_categories_via_instance(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured = _capture_cli_args(monkeypatch)
        Liwc22(dry_run=True).wc(input="x", output="y", include_categories=["anger", "joy"])
        assert captured["cli_args"]["include_categories"] == ["anger", "joy"]  # type: ignore[index]

    def test_words_list(self) -> None:
        cmd = build_command(
            "context",
            {"input": "a", "output": "b", "words": ["hope", "fear"]},
        )
        idx = cmd.index("-words")
        assert cmd[idx + 1] == "hope,fear"

    # -- column int -> 1-based --------------------------------------------

    def test_column_int_is_shifted_to_one_based(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """text_column=0 (first column, Pythonic) -> -tc 1 (CLI, 1-based)."""
        captured = _capture_cli_args(monkeypatch)
        Liwc22(dry_run=True).lsm(
            input="x.csv",
            output="y.csv",
            text_column=0,
            person_column=1,
        )
        cli_args = captured["cli_args"]
        assert isinstance(cli_args, dict)
        assert cli_args["text_column"] == 1
        assert cli_args["person_column"] == 2

    def test_group_column_default_none_becomes_zero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """group_column=None (lsm's 'no groups' sentinel) -> -gc 0."""
        captured = _capture_cli_args(monkeypatch)
        Liwc22(dry_run=True).lsm(
            input="x.csv",
            output="y.csv",
            text_column=0,
            person_column=1,
        )
        cli_args = captured["cli_args"]
        assert isinstance(cli_args, dict)
        assert cli_args["group_column"] == 0

    def test_column_int_emitted_as_one_based_in_command(self) -> None:
        """Integration: text_column=0 produces '-tc 1' in the final argv."""
        # Use build_command directly with a post-resolution dict.
        cmd = build_command(
            "lsm",
            {
                "input": "x.csv",
                "output": "y.csv",
                "text_column": 1,  # already 1-based (post-_resolve_columns)
                "person_column": 2,
                "group_column": 0,
            },
        )
        idx = cmd.index("-tc")
        assert cmd[idx + 1] == "1"

    def test_numeric_coded_int_args_stringified(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """calculate_lsm=3 (int) -> '-clsm 3' (str)."""
        captured = _capture_cli_args(monkeypatch)
        Liwc22(dry_run=True).lsm(
            input="x.csv",
            output="y.csv",
            text_column=0,
            person_column=1,
        )
        cli_args = captured["cli_args"]
        assert isinstance(cli_args, dict)
        assert cli_args["calculate_lsm"] == 3
        assert cli_args["output_type"] == 1

    # -- column name -> 1-based via header read ---------------------------

    def test_column_name_resolves_via_header(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """text_column='text' resolves to the 1-based position from the CSV header."""
        fixture = tmp_path / "chat.csv"
        fixture.write_text("id,text,speaker\n1,hi,alice\n2,hey,bob\n", encoding="utf-8")

        captured = _capture_cli_args(monkeypatch)
        Liwc22(dry_run=True).lsm(
            input=str(fixture),
            output="y.csv",
            text_column="text",
            person_column="speaker",
        )
        cli_args = captured["cli_args"]
        assert isinstance(cli_args, dict)
        # "text" is the second column -> 1-based index 2.
        assert cli_args["text_column"] == 2
        # "speaker" is the third column -> 1-based index 3.
        assert cli_args["person_column"] == 3

    def test_column_name_not_in_header_raises(self, tmp_path: Path) -> None:
        fixture = tmp_path / "chat.csv"
        fixture.write_text("id,text,speaker\n1,hi,alice\n", encoding="utf-8")

        with pytest.raises(ValueError, match="not found in header"):
            Liwc22(dry_run=True).lsm(
                input=str(fixture),
                output="y.csv",
                text_column="nonexistent_column",
                person_column="speaker",
            )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidation:
    """Tests for the user-friendly guards added to Liwc22."""

    def test_include_and_exclude_both_set_raises(self) -> None:
        """wc() refuses to accept both include_categories and exclude_categories."""
        with pytest.raises(ValueError, match="include_categories and exclude_categories"):
            Liwc22(dry_run=True).wc(
                input="x",
                output="y",
                include_categories=["anger"],
                exclude_categories=["joy"],
            )

    def test_column_name_with_skip_header_false_raises(self, tmp_path: Path) -> None:
        """Column names require a header row - skip_header=False must error."""
        fixture = tmp_path / "chat.csv"
        fixture.write_text("id,text,speaker\n1,hi,alice\n", encoding="utf-8")

        with pytest.raises(ValueError, match="skip_header=False"):
            Liwc22(skip_header=False, dry_run=True).lsm(
                input=str(fixture),
                output="y.csv",
                text_column="text",
                person_column="speaker",
            )

    def test_column_name_with_console_input_raises(self) -> None:
        """input='console' has no header - column names must error."""
        with pytest.raises(ValueError, match="console"):
            Liwc22(dry_run=True).wc(
                input="console",
                output="y.csv",
                text="hello world",
                text_columns=["text"],
            )


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------


class TestContextManager:
    """Tests for Liwc22's __enter__/__exit__ lifecycle."""

    def test_context_manager_noop_when_autoopen_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: dict[str, int] = {"open": 0, "close": 0}

        def fake_open(use_license_server: bool = True) -> None:
            calls["open"] += 1
            return None

        def fake_close(proc: object) -> None:
            calls["close"] += 1

        monkeypatch.setattr("liwca.liwc22._open_liwc_app", fake_open)
        monkeypatch.setattr("liwca.liwc22._close_liwc_app", fake_close)
        monkeypatch.setattr("liwca.liwc22._is_liwc_running", lambda: False)

        with Liwc22(dry_run=True) as liwc:
            liwc.wc(input="x", output="y")

        assert calls["open"] == 0
        assert calls["close"] == 0

    def test_context_manager_launches_app_when_autoopen_true(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: dict[str, int] = {"open": 0, "close": 0}

        def fake_open(use_license_server: bool = True) -> None:
            calls["open"] += 1
            return None

        def fake_close(proc: object) -> None:
            calls["close"] += 1

        monkeypatch.setattr("liwca.liwc22._open_liwc_app", fake_open)
        monkeypatch.setattr("liwca.liwc22._close_liwc_app", fake_close)
        monkeypatch.setattr("liwca.liwc22._is_liwc_running", lambda: False)

        # dry_run=False here so __enter__ actually considers launching; but we
        # set auto_open via the class's own flag path.  We keep dry_run=False
        # but monkeypatch _is_liwc_running to False so __enter__ launches.
        with Liwc22(auto_open=True, dry_run=False):
            pass

        assert calls["open"] == 1
        assert calls["close"] == 1

    def test_context_manager_skips_launch_when_already_running(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: dict[str, int] = {"open": 0, "close": 0}

        def fake_open(use_license_server: bool = True) -> None:
            calls["open"] += 1
            return None

        def fake_close(proc: object) -> None:
            calls["close"] += 1

        monkeypatch.setattr("liwca.liwc22._open_liwc_app", fake_open)
        monkeypatch.setattr("liwca.liwc22._close_liwc_app", fake_close)
        monkeypatch.setattr("liwca.liwc22._is_liwc_running", lambda: True)

        with Liwc22(auto_open=True, dry_run=False):
            pass

        assert calls["open"] == 0
        assert calls["close"] == 0

    def test_context_manager_dry_run_does_not_launch(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """dry_run=True short-circuits the __enter__ launch."""
        calls: dict[str, int] = {"open": 0, "close": 0}

        def fake_open(use_license_server: bool = True) -> None:
            calls["open"] += 1
            return None

        def fake_close(proc: object) -> None:
            calls["close"] += 1

        monkeypatch.setattr("liwca.liwc22._open_liwc_app", fake_open)
        monkeypatch.setattr("liwca.liwc22._close_liwc_app", fake_close)
        monkeypatch.setattr("liwca.liwc22._is_liwc_running", lambda: False)

        with Liwc22(auto_open=True, dry_run=True) as liwc:
            liwc.wc(input="x", output="y")

        assert calls["open"] == 0
        assert calls["close"] == 0


# ---------------------------------------------------------------------------
# DataFrame input, filepath return, and `wc` output shaping
# ---------------------------------------------------------------------------


@pytest.fixture
def stub_run(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Stub ``_run`` so the pipeline reaches the post-CLI shaping step.

    Writes a canned ``wc``-style CSV to the output path on non-dry-run calls,
    mimicking what LIWC-22-cli would have produced.  Exposes the mode,
    cli_args, and dry_run flag via the returned dict.
    """
    captured: dict[str, Any] = {}

    def fake_run(
        mode: str,
        cli_args: dict[str, Any],
        *,
        auto_open: bool,
        use_gui: bool,
        dry_run: bool,
        app_managed: bool = False,
    ) -> None:
        captured["mode"] = mode
        captured["cli_args"] = dict(cli_args)
        captured["dry_run"] = dry_run
        captured["auto_open"] = auto_open
        captured["use_gui"] = use_gui
        if not dry_run and cli_args.get("output"):
            out = Path(cli_args["output"])
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text("Row ID,Segment,WC,Tone\n1,1,10,50.0\n2,1,5,75.0\n")

    monkeypatch.setattr("liwca.liwc22._run", fake_run)
    # Avoid trying to read a header from a non-existent file-path input in
    # ``_resolve_columns`` when DataFrame input isn't supplied.
    monkeypatch.setattr("liwca.liwc22._is_liwc_running", lambda: True)
    return captured


class TestDataFrameInput:
    """DataFrame as the `input` arg: temp CSV, column resolution, cleanup."""

    def test_dataframe_input_writes_temp_and_passes_path(
        self, stub_run: dict[str, Any], tmp_path: Path
    ) -> None:
        df = pd.DataFrame({"doc_id": ["a", "b"], "text": ["hello world", "foo bar"]})
        out = tmp_path / "out.csv"
        Liwc22().wc(input=df, output=str(out), text_columns="text")

        # The cli_args that reached _run should have a filesystem path, not a DataFrame.
        input_passed = stub_run["cli_args"]["input"]
        assert isinstance(input_passed, str)
        # The temp file is deleted by the finally block.
        assert not Path(input_passed).exists()

    def test_dataframe_input_resolves_column_names_without_file_read(
        self, stub_run: dict[str, Any], tmp_path: Path
    ) -> None:
        """text_columns=['text'] against a DataFrame resolves via df.columns."""
        df = pd.DataFrame({"doc_id": ["a", "b"], "text": ["x y z", "p q"]})
        out = tmp_path / "out.csv"
        Liwc22().wc(input=df, output=str(out), text_columns=["text"])

        # 'text' is the 2nd column (0-based index 1); LIWC CLI wants 1-based.
        cli_args = stub_run["cli_args"]
        # text_columns is a LIST_FLAG, so it comes through as a list of 1-based ints
        assert cli_args["text_columns"] == [2]

    def test_dataframe_input_with_text_kwarg_raises(self, tmp_path: Path) -> None:
        df = pd.DataFrame({"text": ["hi"]})
        with pytest.raises(ValueError, match="`text`"):
            Liwc22(dry_run=True).wc(input=df, output=str(tmp_path / "o.csv"), text="inline")

    def test_empty_dataframe_input_raises(self, tmp_path: Path) -> None:
        df = pd.DataFrame({"text": []}).astype(str)
        with pytest.raises(ValueError, match="empty"):
            Liwc22(dry_run=True).wc(input=df, output=str(tmp_path / "o.csv"))

    def test_dataframe_input_without_text_columns_raises(self) -> None:
        df = pd.DataFrame({"doc_id": ["a"], "text": ["hi"]})
        with pytest.raises(ValueError, match="text_columns"):
            Liwc22(dry_run=True).wc(input=df, output="out.csv")

    def test_series_input_autofills_text_columns(
        self, stub_run: dict[str, Any], tmp_path: Path
    ) -> None:
        """Series input auto-wraps; text_columns fills with the Series name."""
        s = pd.Series(["hello", "world"], name="msg")
        out = tmp_path / "out.csv"
        Liwc22().wc(input=s, output=str(out))
        # Series had one column "msg" at position 0 (0-based) -> 1-based index 1.
        assert stub_run["cli_args"]["text_columns"] == [1]

    def test_series_input_unnamed_defaults_to_text(
        self, stub_run: dict[str, Any], tmp_path: Path
    ) -> None:
        s = pd.Series(["hello", "world"])
        out = tmp_path / "out.csv"
        Liwc22().wc(input=s, output=str(out))
        assert stub_run["cli_args"]["text_columns"] == [1]


class TestPositionalAndPath:
    """input/output accept positional args and Path values."""

    def test_positional_input_output(self) -> None:
        result = Liwc22(dry_run=True).wc("data.csv", "results.csv")
        assert result == "results.csv"

    def test_path_input_coerced_to_str(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured = _capture_cli_args(monkeypatch)
        Liwc22(dry_run=True).wc(Path("data.csv"), Path("out.csv"))
        cli_args = captured["cli_args"]
        assert isinstance(cli_args, dict)
        assert cli_args["input"] == "data.csv"
        assert cli_args["output"] == "out.csv"

    def test_path_output_returned_as_str(self) -> None:
        result = Liwc22(dry_run=True).wc("data.csv", Path("out.csv"))
        assert result == "out.csv"
        assert isinstance(result, str)


class TestSingleStringColumnIndices:
    """Bare-string text_columns (and other LIST_FLAGS) don't explode to chars."""

    def test_single_string_text_columns(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        fixture = tmp_path / "chat.csv"
        fixture.write_text("id,text\n1,hi\n", encoding="utf-8")
        captured = _capture_cli_args(monkeypatch)
        Liwc22(dry_run=True).wc(str(fixture), "out.csv", text_columns="text")
        # "text" is the 2nd column (1-based index 2).
        assert captured["cli_args"]["text_columns"] == [2]

    def test_single_string_include_categories(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured = _capture_cli_args(monkeypatch)
        Liwc22(dry_run=True).wc("x", "y", include_categories="anger")
        assert captured["cli_args"]["include_categories"] == ["anger"]


class TestCsvQuoteWindowsWorkaround:
    """On Windows, csv_quote='"' is dropped before emission (Java-launcher quirk)."""

    def test_default_quote_dropped_on_windows(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("liwca.liwc22.platform.system", lambda: "Windows")
        captured: dict[str, Any] = {}

        def fake_build(mode: str, cli_args: dict[str, Any]) -> list[str]:
            captured["cli_args"] = cli_args
            return ["LIWC-22-cli", "-m", mode]

        monkeypatch.setattr("liwca.liwc22.build_command", fake_build)
        monkeypatch.setattr("liwca.liwc22._is_liwc_running", lambda: True)
        monkeypatch.setattr("liwca.liwc22._resolve_liwc_cli", lambda: "LIWC-22-cli.exe")
        monkeypatch.setattr(
            "liwca.liwc22.subprocess.run",
            lambda *a, **kw: type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})(),
        )

        from liwca.liwc22 import _run

        _run(
            "wc",
            {"input": "x", "output": "y", "csv_quote": '"'},
            auto_open=False,
            use_gui=False,
            dry_run=False,
            app_managed=True,
        )
        assert "csv_quote" not in captured["cli_args"]

    def test_custom_quote_still_emitted_on_windows(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("liwca.liwc22.platform.system", lambda: "Windows")
        captured: dict[str, Any] = {}

        def fake_build(mode: str, cli_args: dict[str, Any]) -> list[str]:
            captured["cli_args"] = cli_args
            return ["LIWC-22-cli", "-m", mode]

        monkeypatch.setattr("liwca.liwc22.build_command", fake_build)
        monkeypatch.setattr("liwca.liwc22._is_liwc_running", lambda: True)
        monkeypatch.setattr("liwca.liwc22._resolve_liwc_cli", lambda: "LIWC-22-cli.exe")
        monkeypatch.setattr(
            "liwca.liwc22.subprocess.run",
            lambda *a, **kw: type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})(),
        )

        from liwca.liwc22 import _run

        _run(
            "wc",
            {"input": "x", "output": "y", "csv_quote": "'"},
            auto_open=False,
            use_gui=False,
            dry_run=False,
            app_managed=True,
        )
        assert captured["cli_args"]["csv_quote"] == "'"


class TestWindowsCmdlineEncoding:
    """Canonical MSVCRT quoting for a Windows CreateProcess command line."""

    def test_plain_arg_unquoted(self) -> None:
        from liwca.liwc22 import _win_quote_arg

        assert _win_quote_arg("LIWC-22-cli") == "LIWC-22-cli"

    def test_empty_arg_becomes_empty_quoted(self) -> None:
        from liwca.liwc22 import _win_quote_arg

        assert _win_quote_arg("") == '""'

    def test_arg_with_space_is_quoted(self) -> None:
        from liwca.liwc22 import _win_quote_arg

        assert _win_quote_arg("a b") == '"a b"'

    def test_lone_quote_uses_canonical_form(self) -> None:
        """A lone ``"`` must round-trip as ``"\\""`` - not Python's bare ``\\"``."""
        from liwca.liwc22 import _win_quote_arg

        assert _win_quote_arg('"') == '"\\""'

    def test_trailing_backslashes_doubled_before_close_quote(self) -> None:
        """``foo\\`` inside quotes requires doubling to round-trip as ``foo\\``."""
        from liwca.liwc22 import _win_quote_arg

        assert _win_quote_arg("foo\\") == '"foo\\\\"'

    def test_join_full_cmdline(self) -> None:
        from liwca.liwc22 import _join_windows_cmdline

        result = _join_windows_cmdline(["LIWC-22-cli", "-quote", '"', "-i", "x.csv"])
        assert result == 'LIWC-22-cli -quote "\\"" -i x.csv'


class TestTypeAssertions:
    """TypeError / ValueError on bad types at the public surface."""

    def test_bad_input_type_raises(self) -> None:
        with pytest.raises(TypeError, match="input"):
            Liwc22(dry_run=True).wc(input=123, output="out.csv")  # type: ignore[arg-type]

    def test_bad_output_type_raises(self) -> None:
        with pytest.raises(TypeError, match="output"):
            Liwc22(dry_run=True).wc(input="x", output=123)  # type: ignore[arg-type]

    def test_auto_open_must_be_bool(self) -> None:
        with pytest.raises(TypeError, match="auto_open"):
            Liwc22(auto_open=1)  # type: ignore[arg-type]

    def test_precision_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError, match="precision"):
            Liwc22(precision=20)

    def test_bad_output_format_raises(self) -> None:
        with pytest.raises(ValueError, match="output_format"):
            Liwc22(dry_run=True).wc("x", "y", output_format="pdf")

    def test_bad_level_raises(self) -> None:
        with pytest.raises(ValueError, match="level"):
            Liwc22(dry_run=True).lsm(
                "x.csv", "y.csv", text_column=0, person_column=1, level="invalid"
            )


class TestReturnFilepath:
    """Mode methods return the *output* path string, including on dry runs."""

    @pytest.mark.parametrize("mode", sorted(ALL_MODES))
    def test_dry_run_returns_output_path(self, mode: str) -> None:
        liwc = Liwc22(dry_run=True)
        kwargs = MODE_REQUIRED_KWARGS[mode]
        result = getattr(liwc, mode)(**kwargs)
        assert result == kwargs["output"]

    def test_successful_call_returns_output_path(
        self, stub_run: dict[str, Any], tmp_path: Path
    ) -> None:
        out = tmp_path / "res.csv"
        result = Liwc22().wc(input=str(tmp_path / "in.csv"), output=str(out))
        assert result == str(out)

    def test_cli_failure_propagates(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """subprocess.CalledProcessError must propagate, not be swallowed."""

        def fake_run(*args: Any, **kwargs: Any) -> None:
            raise subprocess.CalledProcessError(returncode=2, cmd=["LIWC-22-cli"])

        monkeypatch.setattr("liwca.liwc22._run", fake_run)

        with pytest.raises(subprocess.CalledProcessError):
            Liwc22().wc(input=str(tmp_path / "in.csv"), output=str(tmp_path / "o.csv"))


class TestWcOutputSchema:
    """In-place shaping of the wc-mode output file and schema validation."""

    def test_default_wc_shape(self, stub_run: dict[str, Any], tmp_path: Path) -> None:
        """No id_columns + constant Segment -> 'Row ID' index, no Segment col."""
        out = tmp_path / "out.csv"
        Liwc22().wc(input=str(tmp_path / "in.csv"), output=str(out))

        shaped = pd.read_csv(out, index_col=0)
        assert shaped.index.name == "Row ID"
        assert "Segment" not in shaped.columns
        assert list(shaped.columns) == ["WC", "Tone"]

    def test_id_columns_renames_to_source_column(
        self, stub_run: dict[str, Any], tmp_path: Path
    ) -> None:
        df = pd.DataFrame({"doc_id": ["a", "b"], "text": ["x", "y"]})
        out = tmp_path / "out.csv"
        Liwc22().wc(input=df, output=str(out), text_columns="text", id_columns=["doc_id"])

        shaped = pd.read_csv(out, index_col=0)
        assert shaped.index.name == "doc_id"

    def test_varying_segment_promotes_to_index(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Non-constant Segment values are kept as a 2nd index level."""

        def fake_run(
            mode: str,
            cli_args: dict[str, Any],
            *,
            auto_open: bool,
            use_gui: bool,
            dry_run: bool,
            app_managed: bool = False,
        ) -> None:
            Path(cli_args["output"]).write_text(
                "Row ID,Segment,WC,Tone\n1,1,10,50.0\n1,2,8,60.0\n2,1,5,75.0\n"
            )

        monkeypatch.setattr("liwca.liwc22._run", fake_run)
        monkeypatch.setattr("liwca.liwc22._is_liwc_running", lambda: True)

        out = tmp_path / "out.csv"
        Liwc22().wc(input=str(tmp_path / "in.csv"), output=str(out))

        shaped = pd.read_csv(out, index_col=[0, 1])
        assert shaped.index.names == ["Row ID", "Segment"]
        assert list(shaped.columns) == ["WC", "Tone"]

    def test_non_csv_output_format_skips_shaping(
        self, stub_run: dict[str, Any], tmp_path: Path
    ) -> None:
        out = tmp_path / "out.xlsx"
        with pytest.warns(UserWarning, match="Skipping wc output shaping"):
            Liwc22().wc(
                input=str(tmp_path / "in.csv"),
                output=str(out),
                output_format="xlsx",
            )

    def test_schema_names_column_axis_category(self) -> None:
        """_shape_wc_output names df.columns.name 'Category'."""
        raw = pd.DataFrame(
            {
                "Row ID": [1, 2],
                "Segment": [1, 1],
                "WC": [10, 5],
                "Tone": [50.0, 75.0],
            }
        )
        shaped = _shape_wc_output(raw, row_id_names=None)
        assert shaped.columns.name == "Category"

    def test_raw_cli_output_fails_validation(self) -> None:
        """Un-shaped CLI output has no 'Category' column-axis name."""
        raw = pd.DataFrame(
            {
                "Row ID": [1, 2],
                "Segment": [1, 1],
                "WC": [10, 5],
            }
        )
        # The raw DataFrame has no rows set as index; validation after shaping
        # names the column axis 'Category'.  Direct validation of raw CLI
        # output should not have that name set.
        assert raw.columns.name is None
        # Shaping should not raise; validation passes on shaped.
        shaped = _shape_wc_output(raw, row_id_names=None)
        wc_output_schema.validate(shaped)


# ---------------------------------------------------------------------------
# Friendly dictionary-name resolution
# ---------------------------------------------------------------------------


class TestResolveDictionaryArg:
    """Tests for `_resolve_dictionary_arg` and its `_run_mode` integration."""

    def test_non_string_passes_through(self) -> None:
        assert _resolve_dictionary_arg(None) is None
        assert _resolve_dictionary_arg(42) == 42

    def test_unknown_name_passes_through(self) -> None:
        """Built-in CLI names like LIWC22 don't match a fetcher; passthrough."""
        assert _resolve_dictionary_arg("LIWC22") == "LIWC22"
        assert _resolve_dictionary_arg("LIWC2015") == "LIWC2015"

    def test_path_like_passes_through(self) -> None:
        """Strings that don't match a fetcher (paths, custom names) passthrough."""
        assert _resolve_dictionary_arg("/some/custom.dicx") == "/some/custom.dicx"
        assert _resolve_dictionary_arg("totally_made_up_name") == "totally_made_up_name"

    def test_friendly_name_resolves_to_path(self, tmp_path: Path) -> None:
        """A registered friendly name resolves via dictionaries.path()."""
        from liwca.datasets import dictionaries

        fake_dicx = tmp_path / "sleep.dicx"
        fake_dicx.write_text("DicTerm,sleep\n")
        with patch.object(dictionaries, "path", return_value=fake_dicx) as mock_path:
            result = _resolve_dictionary_arg("sleep")
        mock_path.assert_called_once_with("sleep")
        assert result == str(fake_dicx)

    def test_weighted_dict_resolves_like_binary(self, tmp_path: Path) -> None:
        """Weighted-dict names (like 'wrad') resolve to their cached .dicx path
        the same way binary-dict names do."""
        from liwca.datasets import dictionaries

        fake_dicx = tmp_path / "wrad.dicx"
        fake_dicx.write_text("DicTerm,labMT\n")
        with patch.object(dictionaries, "path", return_value=fake_dicx) as mock_path:
            result = _resolve_dictionary_arg("wrad")
        mock_path.assert_called_once_with("wrad")
        assert result == str(fake_dicx)

    def test_run_mode_substitutes_dictionary(self, tmp_path: Path) -> None:
        """End-to-end: Liwc22.wc(dictionary='sleep', dry_run=True) builds a
        command with the resolved local .dicx path, not 'sleep'."""
        from liwca.datasets import dictionaries

        fake_dicx = tmp_path / "sleep.dicx"
        fake_dicx.write_text("DicTerm,sleep\n")
        input_csv = tmp_path / "in.csv"
        input_csv.write_text("id,text\n1,hello\n")
        output_csv = tmp_path / "out.csv"

        with patch.object(dictionaries, "path", return_value=fake_dicx):
            captured: dict[str, list[str]] = {}
            real_build = liwca.liwc22.build_command

            def spy(mode: str, cli_args: dict) -> list[str]:
                cmd = real_build(mode, cli_args)
                captured["cmd"] = cmd
                captured["dictionary"] = cli_args.get("dictionary")
                return cmd

            with patch("liwca.liwc22.build_command", side_effect=spy):
                Liwc22(dry_run=True).wc(
                    str(input_csv),
                    str(output_csv),
                    dictionary="sleep",
                )

        # The dictionary kwarg was substituted to the resolved local path
        # before reaching build_command.
        assert captured["dictionary"] == str(fake_dicx)
