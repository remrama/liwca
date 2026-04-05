"""Tests for liwca.liwc22 — CLI wrapper and Python API."""

from __future__ import annotations

import pytest

from liwca.liwc22 import (
    ARG_CATALOGUE,
    MODE_DEFS,
    build_command,
    build_parser,
    liwc22,
)

# ---------------------------------------------------------------------------
# Argument catalogue & mode definitions
# ---------------------------------------------------------------------------


class TestModeDefs:
    """Structural tests for the data-driven mode/arg definitions."""

    @pytest.mark.parametrize("mode", list(MODE_DEFS))
    def test_mode_has_required_keys(self, mode: str) -> None:
        defn = MODE_DEFS[mode]
        for key in ("help", "description", "required", "optional", "globals"):
            assert key in defn, f"Mode {mode!r} missing key {key!r}"

    @pytest.mark.parametrize("mode", list(MODE_DEFS))
    def test_mode_args_in_catalogue(self, mode: str) -> None:
        """Every arg referenced by a mode must exist in ARG_CATALOGUE."""
        defn = MODE_DEFS[mode]
        all_keys = defn["required"] + defn["optional"] + list(defn["globals"])
        for key in all_keys:
            assert key in ARG_CATALOGUE, (
                f"Mode {mode!r} references arg {key!r} not in ARG_CATALOGUE"
            )

    def test_all_modes_present(self) -> None:
        expected = {"wc", "freq", "mem", "context", "arc", "ct", "lsm"}
        assert set(MODE_DEFS) == expected


# ---------------------------------------------------------------------------
# Parser construction
# ---------------------------------------------------------------------------


class TestBuildParser:
    """Tests for the argparse parser built from MODE_DEFS."""

    def test_parser_creates_subparsers(self) -> None:
        parser = build_parser()
        # Should be able to parse a known mode
        args = parser.parse_args(["wc", "-i", "in.txt", "-o", "out.csv"])
        assert args.mode == "wc"

    def test_required_args_enforced(self) -> None:
        parser = build_parser()
        with pytest.raises(SystemExit):
            # wc requires -i and -o; omitting them should fail
            parser.parse_args(["wc"])

    def test_optional_args_default_none(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["wc", "-i", "in.txt", "-o", "out.csv"])
        assert args.dictionary is None
        assert args.threads is None

    def test_dry_run_flag(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["wc", "-i", "in.txt", "-o", "out.csv", "--dry-run"])
        assert args.dry_run is True

    def test_auto_open_flag(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["wc", "-i", "in.txt", "-o", "out.csv", "--auto-open"])
        assert args.auto_open is True


# ---------------------------------------------------------------------------
# Command building
# ---------------------------------------------------------------------------


class TestBuildCommand:
    """Tests for build_command — namespace → CLI args list."""

    def test_basic_wc_command(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["wc", "-i", "data.txt", "-o", "results.csv"])
        cmd = build_command(args)
        assert cmd[0] == "LIWC-22-cli"
        assert "-m" in cmd
        assert cmd[cmd.index("-m") + 1] == "wc"
        assert "-i" in cmd
        assert "data.txt" in cmd
        assert "-o" in cmd
        assert "results.csv" in cmd

    def test_optional_args_included_when_set(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            ["wc", "-i", "in.txt", "-o", "out.csv", "-d", "LIWC2015", "-t", "4"]
        )
        cmd = build_command(args)
        assert "-d" in cmd
        assert "LIWC2015" in cmd
        assert "-t" in cmd
        assert "4" in cmd

    def test_optional_args_excluded_when_none(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["wc", "-i", "in.txt", "-o", "out.csv"])
        cmd = build_command(args)
        # -d (dictionary) was not set, so it shouldn't appear
        assert "-d" not in cmd or cmd[cmd.index("-d") + 1] != "None"

    def test_bool_flag_included_when_true(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["mem", "-i", "in.txt", "-o", "out.csv", "--save-theme-scores"])
        cmd = build_command(args)
        assert "--save-theme-scores" in cmd

    def test_bool_flag_excluded_when_false(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["mem", "-i", "in.txt", "-o", "out.csv"])
        cmd = build_command(args)
        assert "--save-theme-scores" not in cmd

    def test_freq_mode_command(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["freq", "-i", "corpus/", "-o", "freqs.csv", "-n", "2"])
        cmd = build_command(args)
        assert cmd[cmd.index("-m") + 1] == "freq"
        assert "-n" in cmd
        assert "2" in cmd


# ---------------------------------------------------------------------------
# Python API (liwc22 function)
# ---------------------------------------------------------------------------


class TestLiwc22Function:
    """Tests for the liwc22() Python API."""

    def test_dry_run_returns_zero(self) -> None:
        rc = liwc22("wc", input="data.txt", output="results.csv", dry_run=True)
        assert rc == 0

    def test_dry_run_freq(self) -> None:
        rc = liwc22("freq", input="corpus/", output="freqs.csv", n_gram=2, dry_run=True)
        assert rc == 0

    def test_unknown_mode_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown mode"):
            liwc22("nonexistent", input="x", output="y", dry_run=True)

    def test_dry_run_lsm(self) -> None:
        rc = liwc22(
            "lsm",
            input="chat.csv",
            output="lsm.csv",
            calculate_lsm="3",
            group_column=1,
            output_type="1",
            person_column=2,
            text_column=3,
            dry_run=True,
        )
        assert rc == 0
