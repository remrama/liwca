"""Tests for liwca.liwc22 — Python API and command builder."""

from __future__ import annotations

import argparse

import pytest

from liwca.liwc22 import ARG_CATALOGUE, MODE_DEFS, build_command, liwc22


def _ns(mode: str, **kwargs) -> argparse.Namespace:
    """Build a namespace as liwc22() would, for testing build_command directly."""
    return argparse.Namespace(mode=mode, auto_open=False, use_gui=False, dry_run=False, **kwargs)


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
# Command building
# ---------------------------------------------------------------------------


class TestBuildCommand:
    """Tests for build_command — namespace → CLI args list."""

    def test_basic_wc_command(self) -> None:
        cmd = build_command(_ns("wc", input="data.txt", output="results.csv"))
        assert cmd[0] == "LIWC-22-cli"
        assert "-m" in cmd
        assert cmd[cmd.index("-m") + 1] == "wc"
        assert "-i" in cmd and "data.txt" in cmd
        assert "-o" in cmd and "results.csv" in cmd

    def test_optional_args_included_when_set(self) -> None:
        cmd = build_command(
            _ns("wc", input="in.txt", output="out.csv", dictionary="LIWC2015", threads=4)
        )
        assert "-d" in cmd and "LIWC2015" in cmd
        assert "-t" in cmd and "4" in cmd

    def test_optional_args_excluded_when_none(self) -> None:
        cmd = build_command(_ns("wc", input="in.txt", output="out.csv"))
        # dictionary was not set — should not appear
        assert "-d" not in cmd

    def test_bool_flag_included_when_true(self) -> None:
        cmd = build_command(_ns("mem", input="in.txt", output="out.csv", save_theme_scores=True))
        assert "--save-theme-scores" in cmd

    def test_bool_flag_excluded_when_false(self) -> None:
        cmd = build_command(_ns("mem", input="in.txt", output="out.csv", save_theme_scores=False))
        assert "--save-theme-scores" not in cmd

    def test_freq_mode_command(self) -> None:
        cmd = build_command(_ns("freq", input="corpus/", output="freqs.csv", n_gram=2))
        assert cmd[cmd.index("-m") + 1] == "freq"
        assert "-n" in cmd and "2" in cmd


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
