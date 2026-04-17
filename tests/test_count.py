"""Tests for liwca.count - LIWC word counting (count and liwc22)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

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

    def test_default_index_name(self, toy_dx_wildcards: pd.DataFrame) -> None:
        result = liwca.count(["hoop"], toy_dx_wildcards)
        assert result.index.name == "text_id"

    def test_series_unnamed_index_gets_text_id(self, toy_dx_wildcards: pd.DataFrame) -> None:
        series = pd.Series(["hoop", "dugout"], index=["game_a", "game_b"])
        result = liwca.count(series, toy_dx_wildcards)
        assert result.index.name == "text_id"

    def test_series_named_index_preserved(self, toy_dx_wildcards: pd.DataFrame) -> None:
        series = pd.Series(
            ["hoop", "dugout"],
            index=pd.Index(["game_a", "game_b"], name="dream_id"),
        )
        result = liwca.count(series, toy_dx_wildcards)
        assert result.index.name == "dream_id"

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

    def test_zero_vocab_match(self) -> None:
        """When the dictionary is all wildcards and none match, counts are zero."""
        dx = pd.DataFrame(
            {"CatA": [1]},
            index=pd.Index(["zzz*"], dtype="string", name="DicTerm"),
        )
        dx.columns.name = "Category"
        result = liwca.count(["hello world"], dx, as_percentage=False)
        assert result.loc[0, "CatA"] == 0
        assert result.loc[0, "WC"] == 2

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

    # -- return_words -------------------------------------------------------

    def test_return_words_default_is_dataframe(self, toy_dx_wildcards: pd.DataFrame) -> None:
        """Default return_words=False returns a single DataFrame."""
        result = liwca.count(["hoop"], toy_dx_wildcards)
        assert isinstance(result, pd.DataFrame)

    def test_return_words_returns_tuple(self, toy_dx_wildcards: pd.DataFrame) -> None:
        cats, words = liwca.count(["hoop"], toy_dx_wildcards, return_words=True)
        assert isinstance(cats, pd.DataFrame)
        assert isinstance(words, pd.DataFrame)

    def test_return_words_shape(self, toy_dx_wildcards: pd.DataFrame) -> None:
        texts = ["the player dunked and grabbed the rebound near the hoop"]
        cats, words = liwca.count(texts, toy_dx_wildcards, as_percentage=False, return_words=True)
        assert cats.shape[0] == 1
        assert words.shape[0] == 1
        # Words should have WC + one column per matched dictionary token
        assert "WC" in words.columns
        assert words.shape[1] > 1  # at least WC + some tokens

    def test_return_words_values(self, toy_dx_wildcards: pd.DataFrame) -> None:
        """Word counts match expected values for known tokens."""
        cats, words = liwca.count(
            ["hoop dunk dunk layup"],
            toy_dx_wildcards,
            as_percentage=False,
            return_words=True,
        )
        assert words.loc[0, "WC"] == 4
        assert words.loc[0, "hoop"] == 1
        assert words.loc[0, "layup"] == 1

    def test_return_words_wildcard_expanded(self, toy_dx_wildcards: pd.DataFrame) -> None:
        """Wildcard entries appear as expanded corpus tokens, not stems."""
        _, words = liwca.count(
            ["the pitcher dunked"],
            toy_dx_wildcards,
            as_percentage=False,
            return_words=True,
        )
        # "dunked" matches dunk*, "pitcher" matches pitch*
        assert "dunked" in words.columns
        assert "pitcher" in words.columns
        assert "dunk*" not in words.columns
        assert "pitch*" not in words.columns

    def test_return_words_percentage(self, toy_dx_wildcards: pd.DataFrame) -> None:
        """Word percentages use the same normalisation as categories."""
        cats, words = liwca.count(
            ["hoop and layup"],
            toy_dx_wildcards,
            return_words=True,
        )
        # 3 tokens, hoop=1 → 33.33%, layup=1 → 33.33%
        expected_pct = 1 / 3 * 100
        assert abs(words.loc[0, "hoop"] - expected_pct) < 0.01
        assert abs(words.loc[0, "layup"] - expected_pct) < 0.01

    def test_return_words_precision(self, toy_dx_wildcards: pd.DataFrame) -> None:
        _, words = liwca.count(
            ["hoop and layup"],
            toy_dx_wildcards,
            precision=2,
            return_words=True,
        )
        assert words.loc[0, "hoop"] == 33.33

    def test_return_words_no_matches_all_zero(self, toy_dx_wildcards: pd.DataFrame) -> None:
        """No dictionary matches → word columns are all zero."""
        _, words = liwca.count(
            ["the quick brown fox"],
            toy_dx_wildcards,
            as_percentage=False,
            return_words=True,
        )
        assert words.loc[0, "WC"] == 4
        # All token columns should be zero
        token_cols = [c for c in words.columns if c != "WC"]
        assert (words[token_cols].loc[0] == 0).all()

    def test_return_words_empty_vocab(self) -> None:
        """All-wildcard dictionary with no corpus matches → WC-only columns."""
        dx = pd.DataFrame(
            {"CatA": [1]},
            index=pd.Index(["zzz*"], dtype="string", name="DicTerm"),
        )
        dx.columns.name = "Category"
        _, words = liwca.count(["hello world"], dx, as_percentage=False, return_words=True)
        assert list(words.columns) == ["WC"]
        assert words.loc[0, "WC"] == 2

    def test_return_words_categories_unchanged(self, toy_dx_wildcards: pd.DataFrame) -> None:
        """Category results are identical whether or not return_words is set."""
        cats_only = liwca.count(["hoop and layup"], toy_dx_wildcards, as_percentage=False)
        cats_both, _ = liwca.count(
            ["hoop and layup"],
            toy_dx_wildcards,
            as_percentage=False,
            return_words=True,
        )
        pd.testing.assert_frame_equal(cats_only, cats_both)
