"""Tests for liwca.liwc22 - per-mode Python API and command builder."""

from __future__ import annotations

import argparse
import inspect

import pytest

import liwca
from liwca.liwc22 import (
    ARG_CATALOGUE,
    MODE_DEFS,
    arc,
    build_command,
    context,
    ct,
    freq,
    lsm,
    mem,
    wc,
)

EXECUTION_CONTROL_ARGS = {"auto_open", "use_gui", "dry_run"}

MODE_FUNCTIONS = {
    "wc": wc,
    "freq": freq,
    "mem": mem,
    "context": context,
    "arc": arc,
    "ct": ct,
    "lsm": lsm,
}


def _ns(mode: str, **kwargs) -> argparse.Namespace:
    """Build a namespace as the per-mode functions would, for testing build_command directly."""
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

    def test_execution_control_not_in_catalogue(self) -> None:
        """Library-level flags must not collide with CLI arg names."""
        assert set(ARG_CATALOGUE).isdisjoint(EXECUTION_CONTROL_ARGS)


# ---------------------------------------------------------------------------
# Command building
# ---------------------------------------------------------------------------


class TestBuildCommand:
    """Tests for build_command - namespace → CLI args list."""

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
        # dictionary was not set - should not appear
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
# Per-mode Python API
# ---------------------------------------------------------------------------


class TestModeFunctions:
    """Tests for the seven per-mode Python functions."""

    def test_dry_run_wc(self) -> None:
        rc = wc(input="data.txt", output="results.csv", dry_run=True)
        assert rc == 0

    def test_dry_run_freq(self) -> None:
        rc = freq(input="corpus/", output="freqs.csv", n_gram=2, dry_run=True)
        assert rc == 0

    def test_dry_run_mem(self) -> None:
        rc = mem(input="texts/", output="mem.csv", enable_pca=True, dry_run=True)
        assert rc == 0

    def test_dry_run_context(self) -> None:
        rc = context(input="data.txt", output="ctx.csv", dry_run=True)
        assert rc == 0

    def test_dry_run_arc(self) -> None:
        rc = arc(input="stories/", output="arc.csv", dry_run=True)
        assert rc == 0

    def test_dry_run_ct(self) -> None:
        rc = ct(
            input="transcripts/",
            output="merged.csv",
            speaker_list="speakers.txt",
            dry_run=True,
        )
        assert rc == 0

    def test_dry_run_lsm(self) -> None:
        rc = lsm(
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

    def test_unsupported_kwarg_raises(self) -> None:
        """Passing a freq-only kwarg to wc must raise TypeError."""
        with pytest.raises(TypeError, match="drop_words"):
            wc(input="x", output="y", drop_words=5, dry_run=True)

    def test_missing_required_raises(self) -> None:
        """Omitting a required kwarg must raise TypeError."""
        with pytest.raises(TypeError):
            wc(dry_run=True)

    def test_ct_missing_speaker_list_raises(self) -> None:
        """ct requires speaker_list in addition to input/output."""
        with pytest.raises(TypeError):
            ct(input="x", output="y", dry_run=True)

    @pytest.mark.parametrize("mode", list(MODE_FUNCTIONS))
    def test_module_attribute_access(self, mode: str) -> None:
        """Each mode function is reachable via `liwca.liwc22.<mode>`."""
        fn = getattr(liwca.liwc22, mode)
        assert callable(fn)
        assert fn is MODE_FUNCTIONS[mode]


class TestSignatureMatchesModeDefs:
    """Guard against drift between hand-written signatures and MODE_DEFS."""

    @pytest.mark.parametrize("mode", list(MODE_DEFS))
    def test_signature_matches_mode_defs(self, mode: str) -> None:
        fn = MODE_FUNCTIONS[mode]
        params = set(inspect.signature(fn).parameters)
        cli_params = params - EXECUTION_CONTROL_ARGS
        defn = MODE_DEFS[mode]
        expected = set(defn["required"]) | set(defn["optional"]) | set(defn["globals"])
        assert cli_params == expected, (
            f"Mode {mode!r} signature drift: "
            f"extra={cli_params - expected}, missing={expected - cli_params}"
        )

    @pytest.mark.parametrize("mode", list(MODE_DEFS))
    def test_execution_control_args_present(self, mode: str) -> None:
        fn = MODE_FUNCTIONS[mode]
        params = set(inspect.signature(fn).parameters)
        assert EXECUTION_CONTROL_ARGS.issubset(params)

    @pytest.mark.parametrize("mode", list(MODE_DEFS))
    def test_required_params_have_no_default(self, mode: str) -> None:
        fn = MODE_FUNCTIONS[mode]
        sig = inspect.signature(fn)
        for dest in MODE_DEFS[mode]["required"]:
            param = sig.parameters[dest]
            assert param.default is inspect.Parameter.empty, (
                f"Required param {dest!r} on {mode!r} should have no default"
            )
