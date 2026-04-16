"""Tests for liwca.liwc22 - Liwc22 class and command builder."""

from __future__ import annotations

import pytest

import liwca
from liwca.liwc22 import (
    BOOL_FLAGS,
    FLAG_BY_DEST,
    MODE_GLOBALS,
    Liwc22,
    build_command,
)

EXECUTION_CONTROL_ARGS = {"auto_open", "use_gui", "dry_run"}

ALL_MODES = {"wc", "freq", "mem", "context", "arc", "ct", "lsm"}

# Minimum kwargs each mode needs to construct a legal call.
MODE_REQUIRED_KWARGS: dict[str, dict[str, object]] = {
    "wc": {"input": "data.txt", "output": "results.csv"},
    "freq": {"input": "corpus/", "output": "freqs.csv"},
    "mem": {"input": "texts/", "output": "mem.csv"},
    "context": {"input": "data.txt", "output": "ctx.csv"},
    "arc": {"input": "stories/", "output": "arc.csv"},
    "ct": {"input": "transcripts/", "output": "merged.csv", "speaker_list": "speakers.txt"},
    "lsm": {
        "input": "chat.csv",
        "output": "lsm.csv",
        "calculate_lsm": "3",
        "group_column": 1,
        "output_type": "1",
        "person_column": 2,
        "text_column": 3,
    },
}


# ---------------------------------------------------------------------------
# Flag catalogue (FLAG_BY_DEST, BOOL_FLAGS, MODE_GLOBALS)
# ---------------------------------------------------------------------------


class TestFlagCatalogue:
    """Structural checks on module-level flag data."""

    def test_execution_control_not_in_flag_catalogue(self) -> None:
        """auto_open/use_gui/dry_run are Python-side, not CLI flags."""
        assert set(FLAG_BY_DEST).isdisjoint(EXECUTION_CONTROL_ARGS)

    def test_bool_flags_subset_of_flag_catalogue(self) -> None:
        assert BOOL_FLAGS <= set(FLAG_BY_DEST)

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
        cmd = build_command("freq", {"input": "a", "output": "b", "n_gram": 2})
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


# ---------------------------------------------------------------------------
# Liwc22 class
# ---------------------------------------------------------------------------


class TestLiwc22Class:
    """Tests for the Liwc22 class and its seven mode methods."""

    @pytest.mark.parametrize("mode", sorted(ALL_MODES))
    def test_dry_run_per_mode(self, mode: str) -> None:
        liwc = Liwc22(dry_run=True)
        rc = getattr(liwc, mode)(**MODE_REQUIRED_KWARGS[mode])
        assert rc == 0

    def test_module_attribute_access(self) -> None:
        """Liwc22 is reachable via liwca.liwc22.Liwc22."""
        assert liwca.liwc22.Liwc22 is Liwc22

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

        Liwc22(count_urls="yes", dry_run=True).lsm(**MODE_REQUIRED_KWARGS["lsm"])

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

    def test_ct_missing_speaker_list_raises(self) -> None:
        with pytest.raises(TypeError):
            Liwc22(dry_run=True).ct(input="x", output="y")

    def test_instance_reuse(self) -> None:
        """One instance can drive multiple mode calls with no state leakage."""
        liwc = Liwc22(dry_run=True)
        assert liwc.wc(input="x", output="y") == 0
        assert liwc.freq(input="x", output="y", n_gram=2) == 0


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
