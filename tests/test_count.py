"""Tests for liwca.count — pure-Python LIWC word counting."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import liwca
from liwca.count import _default_tokenize, _expand_wildcards

# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------


class TestDefaultTokenizer:
    """Tests for the built-in regex tokenizer."""

    def test_basic_split(self) -> None:
        assert _default_tokenize("Hello World") == ["hello", "world"]

    def test_lowercases(self) -> None:
        assert _default_tokenize("LOUD") == ["loud"]

    def test_preserves_contractions(self) -> None:
        tokens = _default_tokenize("I don't think he's right")
        assert "don't" in tokens
        assert "he's" in tokens

    def test_strips_punctuation(self) -> None:
        tokens = _default_tokenize("wait, really? yes!")
        assert tokens == ["wait", "really", "yes"]

    def test_empty_string(self) -> None:
        assert _default_tokenize("") == []

    def test_numbers_excluded(self) -> None:
        tokens = _default_tokenize("scored 3 goals")
        assert "3" not in tokens
        assert "scored" in tokens


# ---------------------------------------------------------------------------
# Wildcard expansion
# ---------------------------------------------------------------------------


class TestExpandWildcards:
    """Tests for _expand_wildcards."""

    def test_no_wildcards_passthrough(self, toy_dx: pd.DataFrame) -> None:
        """A dictionary without wildcards is returned unchanged."""
        result = _expand_wildcards(toy_dx, {"huddle", "layup", "dugout"})
        pd.testing.assert_frame_equal(result, toy_dx)

    def test_wildcard_matches_prefix(self, toy_dx_wildcards: pd.DataFrame) -> None:
        corpus = {"dunked", "dunking", "hoop", "batter"}
        result = _expand_wildcards(toy_dx_wildcards, corpus)
        assert "dunked" in result.index
        assert "dunking" in result.index
        assert "dunk*" not in result.index

    def test_wildcard_no_match_dropped(self, toy_dx_wildcards: pd.DataFrame) -> None:
        """Wildcard with no corpus matches produces no expanded rows."""
        corpus = {"hoop", "dugout", "coach"}  # no wildcard matches
        result = _expand_wildcards(toy_dx_wildcards, corpus)
        assert "dunk*" not in result.index
        assert "pitch*" not in result.index

    def test_exact_and_wildcard_merge(self) -> None:
        """If a token matches both an exact entry and a wildcard, categories merge."""
        dx = pd.DataFrame(
            {"Baseball": [1, 0], "Basketball": [0, 1]},
            index=pd.Index(["basket", "basket*"], dtype="string", name="DicTerm"),
        )
        dx.columns.name = "Category"

        result = _expand_wildcards(dx, {"basket", "basketball"})
        # "basket" matches both exact (Baseball) and wildcard (Basketball)
        assert result.loc["basket", "Baseball"] == 1
        assert result.loc["basket", "Basketball"] == 1
        # "basketball" only matches basket*
        assert result.loc["basketball", "Baseball"] == 0
        assert result.loc["basketball", "Basketball"] == 1

    def test_overlapping_wildcards(self) -> None:
        """Multiple wildcards matching the same token merge their categories."""
        dx = pd.DataFrame(
            {"CategoryA": [1, 0], "CategoryB": [0, 1]},
            index=pd.Index(["touch*", "touchdown*"], dtype="string", name="DicTerm"),
        )
        dx.columns.name = "Category"

        result = _expand_wildcards(dx, {"touchdowns", "touching"})
        # "touchdowns" matches both touch* and touchdown*
        assert result.loc["touchdowns", "CategoryA"] == 1
        assert result.loc["touchdowns", "CategoryB"] == 1
        # "touching" matches only touch*
        assert result.loc["touching", "CategoryA"] == 1
        assert result.loc["touching", "CategoryB"] == 0


# ---------------------------------------------------------------------------
# count()
# ---------------------------------------------------------------------------


class TestCount:
    """Tests for the main count() function.

    All tests use the .dicx-backed toy_dx_wildcards fixture (16 terms).
    """

    def test_basketball_sentence(self, toy_dx_wildcards: pd.DataFrame) -> None:
        result = liwca.count(
            ["the player dunked and grabbed the rebound near the hoop"],
            toy_dx_wildcards,
            as_percentage=False,
        )
        # dunked(dunk*) + rebound(rebound*) + hoop(exact) = 3
        assert result.loc[0, "Basketball"] == 3
        assert result.loc[0, "Baseball"] == 0
        assert result.loc[0, "Football"] == 0

    def test_baseball_sentence(self, toy_dx_wildcards: pd.DataFrame) -> None:
        result = liwca.count(
            ["the pitcher pitched a fastball and the batter hit a homer"],
            toy_dx_wildcards,
            as_percentage=False,
        )
        # pitcher(pitch*) + pitched(pitch*) + batter(exact) + homer(homer*) = 4
        assert result.loc[0, "Baseball"] == 4
        assert result.loc[0, "Basketball"] == 0

    def test_football_sentence(self, toy_dx_wildcards: pd.DataFrame) -> None:
        result = liwca.count(
            ["the quarterback threw a touchdown pass before the tackle"],
            toy_dx_wildcards,
            as_percentage=False,
        )
        # quarterback(exact) + touchdown(touchdown*) + tackle(tackle*) = 3
        assert result.loc[0, "Football"] == 3
        assert result.loc[0, "Baseball"] == 0

    def test_coach_scores_all_three(self, toy_dx_wildcards: pd.DataFrame) -> None:
        """coach is in all three categories."""
        result = liwca.count(
            ["the coach spoke"],
            toy_dx_wildcards,
            as_percentage=False,
        )
        assert result.loc[0, "Baseball"] == 1
        assert result.loc[0, "Basketball"] == 1
        assert result.loc[0, "Football"] == 1

    def test_word_count_column(self, toy_dx_wildcards: pd.DataFrame) -> None:
        result = liwca.count(
            ["hoop layup dunk"],
            toy_dx_wildcards,
            as_percentage=False,
        )
        assert result.loc[0, "WC"] == 3

    def test_proportions(self, toy_dx_wildcards: pd.DataFrame) -> None:
        # "hoop and layup" = 3 tokens, 2 basketball matches → 66.67%
        result = liwca.count(["hoop and layup"], toy_dx_wildcards)
        expected_pct = 2 / 3 * 100
        assert abs(result.loc[0, "Basketball"] - expected_pct) < 0.01

    def test_empty_document(self, toy_dx_wildcards: pd.DataFrame) -> None:
        result = liwca.count([""], toy_dx_wildcards)
        assert result.loc[0, "WC"] == 0
        assert result.loc[0, "Basketball"] == 0.0
        assert result.loc[0, "Baseball"] == 0.0
        assert result.loc[0, "Football"] == 0.0

    def test_series_preserves_index(self, toy_dx_wildcards: pd.DataFrame) -> None:
        series = pd.Series(["hoop", "dugout"], index=["game_a", "game_b"])
        result = liwca.count(series, toy_dx_wildcards)
        assert list(result.index) == ["game_a", "game_b"]

    def test_custom_tokenizer(self, toy_dx_wildcards: pd.DataFrame) -> None:
        result = liwca.count(
            ["anything goes here"],
            toy_dx_wildcards,
            tokenizer=lambda t: ["hoop"],
            as_percentage=False,
        )
        assert result.loc[0, "Basketball"] == 1
        assert result.loc[0, "WC"] == 1

    def test_multiple_documents(
        self, toy_dx_wildcards: pd.DataFrame, sample_texts: list[str]
    ) -> None:
        result = liwca.count(sample_texts, toy_dx_wildcards, as_percentage=False)
        assert result.shape[0] == len(sample_texts)
        assert "WC" in result.columns

    def test_no_dictionary_matches(self, toy_dx_wildcards: pd.DataFrame) -> None:
        result = liwca.count(
            ["the quick brown fox jumped over the lazy dog"],
            toy_dx_wildcards,
            as_percentage=False,
        )
        assert result.loc[0, "Basketball"] == 0
        assert result.loc[0, "Baseball"] == 0
        assert result.loc[0, "Football"] == 0
        assert result.loc[0, "WC"] == 9

    def test_wc_counts_all_tokens(self, toy_dx_wildcards: pd.DataFrame) -> None:
        """WC should reflect total words, not just matched words."""
        result = liwca.count(
            ["the hoop is over there by the door"],
            toy_dx_wildcards,
            as_percentage=False,
        )
        assert result.loc[0, "WC"] == 8
        assert result.loc[0, "Basketball"] == 1

    def test_repeated_word(self, toy_dx_wildcards: pd.DataFrame) -> None:
        result = liwca.count(
            ["dunk dunk dunk"],
            toy_dx_wildcards,
            as_percentage=False,
        )
        assert result.loc[0, "Basketball"] == 3

    def test_precision_rounds_proportions(self, toy_dx_wildcards: pd.DataFrame) -> None:
        # "hoop and layup" = 3 tokens, 2 basketball matches → 66.6666...%
        result = liwca.count(["hoop and layup"], toy_dx_wildcards, precision=2)
        assert result.loc[0, "Basketball"] == 66.67

    def test_precision_does_not_affect_wc(self, toy_dx_wildcards: pd.DataFrame) -> None:
        result = liwca.count(["hoop and layup"], toy_dx_wildcards, precision=0)
        assert result.loc[0, "WC"] == 3  # integer, not rounded float

    def test_precision_ignored_when_raw_counts(self, toy_dx_wildcards: pd.DataFrame) -> None:
        result = liwca.count(["hoop and layup"], toy_dx_wildcards, as_percentage=False, precision=2)
        assert result.loc[0, "Basketball"] == 2  # raw count, unaffected

    def test_output_columns(self, toy_dx_wildcards: pd.DataFrame) -> None:
        result = liwca.count(["hello"], toy_dx_wildcards)
        expected_cols = ["WC"] + sorted(toy_dx_wildcards.columns)
        assert list(result.columns) == expected_cols

    def test_as_proportion_deprecation_warning(self, toy_dx_wildcards: pd.DataFrame) -> None:
        """Using the deprecated as_proportion parameter emits FutureWarning."""
        with pytest.warns(FutureWarning, match="as_proportion.*deprecated"):
            result = liwca.count(["hoop"], toy_dx_wildcards, as_proportion=False)
        assert result.loc[0, "Basketball"] == 1  # raw count, as_proportion=False respected

    def test_integration_read_then_count(self, toy_dicx_path: Path) -> None:
        """Integration: read a dictionary file, then count."""
        dx = liwca.read_dx(toy_dicx_path)
        result = liwca.count(
            ["the coach watched the pitcher from the dugout"],
            dx,
            as_percentage=False,
        )
        # coach → all 3; pitcher(pitch*) → Baseball; dugout → Baseball
        assert result.loc[0, "Baseball"] == 3
        assert result.loc[0, "Basketball"] == 1
        assert result.loc[0, "Football"] == 1
