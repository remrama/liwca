"""Tests for the DDR (Distributed Dictionary Representation) module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

import liwca
from liwca.ddr import _load_embeddings, _load_gensim_model

# ---------------------------------------------------------------------------
# Basic functionality
# ---------------------------------------------------------------------------


class TestDDRBasic:
    """Core DDR scoring behaviour."""

    def test_output_shape(self, toy_dx_wildcards, toy_embeddings, sample_texts):
        result = liwca.ddr(sample_texts, toy_dx_wildcards, toy_embeddings)
        assert result.shape == (len(sample_texts), toy_dx_wildcards.shape[1])

    def test_output_columns_sorted_no_wc(self, toy_dx_wildcards, toy_embeddings, sample_texts):
        result = liwca.ddr(sample_texts, toy_dx_wildcards, toy_embeddings)
        assert list(result.columns) == sorted(toy_dx_wildcards.columns)
        assert "WC" not in result.columns

    def test_output_index_name(self, toy_dx_wildcards, toy_embeddings, sample_texts):
        result = liwca.ddr(sample_texts, toy_dx_wildcards, toy_embeddings)
        assert result.index.name == "text_id"

    def test_cosine_range(self, toy_dx_wildcards, toy_embeddings, sample_texts):
        result = liwca.ddr(sample_texts, toy_dx_wildcards, toy_embeddings)
        valid = result.values[~np.isnan(result.values)]
        assert (valid >= -1.0).all() and (valid <= 1.0).all()

    def test_basketball_sentence_highest(self, toy_dx_wildcards, toy_embeddings):
        texts = ["the player dunked and grabbed the rebound near the hoop"]
        result = liwca.ddr(texts, toy_dx_wildcards, toy_embeddings)
        assert result.loc[0, "Basketball"] == result.loc[0].max()

    def test_baseball_sentence_highest(self, toy_dx_wildcards, toy_embeddings):
        texts = ["the pitcher pitched a fastball and the batter hit a homer"]
        result = liwca.ddr(texts, toy_dx_wildcards, toy_embeddings)
        assert result.loc[0, "Baseball"] == result.loc[0].max()

    def test_football_sentence_highest(self, toy_dx_wildcards, toy_embeddings):
        texts = ["the quarterback threw a touchdown pass before the tackle"]
        result = liwca.ddr(texts, toy_dx_wildcards, toy_embeddings)
        assert result.loc[0, "Football"] == result.loc[0].max()


# ---------------------------------------------------------------------------
# Index handling
# ---------------------------------------------------------------------------


class TestDDRIndex:
    """Index propagation from different input types."""

    def test_list_gets_range_index(self, toy_dx, toy_embeddings):
        result = liwca.ddr(["layup and hoop"], toy_dx, toy_embeddings)
        assert isinstance(result.index, pd.RangeIndex)
        assert result.index.name == "text_id"

    def test_series_preserves_named_index(self, toy_dx, toy_embeddings):
        texts = pd.Series(["layup and hoop"], index=pd.Index(["doc_a"], name="my_id"))
        result = liwca.ddr(texts, toy_dx, toy_embeddings)
        assert result.index.name == "my_id"
        assert result.index[0] == "doc_a"

    def test_series_unnamed_index_gets_text_id(self, toy_dx, toy_embeddings):
        texts = pd.Series(["layup and hoop"])
        result = liwca.ddr(texts, toy_dx, toy_embeddings)
        assert result.index.name == "text_id"


# ---------------------------------------------------------------------------
# Wildcard stem handling
# ---------------------------------------------------------------------------


class TestDDRWildcards:
    """Wildcard terms use stem for embedding lookup."""

    def test_wildcard_stem_lookup(self, toy_embeddings):
        """dunk* in dictionary should use 'dunk' embedding."""
        dx = pd.DataFrame(
            {"Sport": [1]},
            index=pd.Index(["dunk*"], dtype="string", name="DicTerm"),
        )
        dx.columns.name = "Category"
        result = liwca.ddr(["the player dunked hard"], dx, toy_embeddings)
        assert not np.isnan(result.loc[0, "Sport"])

    def test_wildcard_stem_not_in_vocab(self, toy_embeddings):
        """Wildcard whose stem is OOV is skipped gracefully."""
        dx = pd.DataFrame(
            {"Sport": [1, 1]},
            index=pd.Index(["zzzzz*", "dunk*"], dtype="string", name="DicTerm"),
        )
        dx.columns.name = "Category"
        result = liwca.ddr(["the player dunked"], dx, toy_embeddings)
        assert not np.isnan(result.loc[0, "Sport"])


# ---------------------------------------------------------------------------
# OOV behaviour
# ---------------------------------------------------------------------------


class TestDDROOV:
    """Out-of-vocabulary handling."""

    def test_all_oov_document_returns_nan(self, toy_dx, toy_embeddings):
        result = liwca.ddr(["xyzzy plugh"], toy_dx, toy_embeddings)
        assert result.loc[0].isna().all()

    def test_empty_document_returns_nan(self, toy_dx, toy_embeddings):
        result = liwca.ddr([""], toy_dx, toy_embeddings)
        assert result.loc[0].isna().all()

    def test_all_oov_category_returns_nan(self, toy_embeddings):
        dx = pd.DataFrame(
            {"Known": [1, 0], "Unknown": [0, 1]},
            index=pd.Index(["hoop", "xyzzy"], dtype="string", name="DicTerm"),
        )
        dx.columns.name = "Category"
        result = liwca.ddr(["hoop game"], dx, toy_embeddings)
        assert not np.isnan(result.loc[0, "Known"])
        assert np.isnan(result.loc[0, "Unknown"])

    def test_partial_oov_still_works(self, toy_dx, toy_embeddings):
        """Document with some OOV tokens still produces valid scores."""
        result = liwca.ddr(["layup xyzzy plugh"], toy_dx, toy_embeddings)
        assert not result.loc[0].isna().all()


# ---------------------------------------------------------------------------
# Precision
# ---------------------------------------------------------------------------


class TestDDRPrecision:
    """Rounding of cosine similarity values."""

    def test_precision_rounds(self, toy_dx, toy_embeddings):
        result = liwca.ddr(["layup and dugout"], toy_dx, toy_embeddings, precision=2)
        for val in result.values.flat:
            if not np.isnan(val):
                assert val == round(val, 2)

    def test_precision_none_no_rounding(self, toy_dx, toy_embeddings):
        result = liwca.ddr(["layup and dugout"], toy_dx, toy_embeddings)
        # With no precision, at least one value should have >2 decimal places
        has_long_decimal = any(
            val != round(val, 2) for val in result.values.flat if not np.isnan(val)
        )
        assert has_long_decimal


# ---------------------------------------------------------------------------
# Custom tokenizer
# ---------------------------------------------------------------------------


class TestDDRCustomTokenizer:
    """Custom tokenizer parameter."""

    def test_custom_tokenizer_is_used(self, toy_dx, toy_embeddings):
        called = []

        def my_tokenizer(text):
            called.append(text)
            return text.lower().split()

        liwca.ddr(["layup dugout"], toy_dx, toy_embeddings, tokenizer=my_tokenizer)
        assert len(called) == 1
        assert called[0] == "layup dugout"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestDDREdgeCases:
    """Edge cases and error conditions."""

    def test_single_document(self, toy_dx, toy_embeddings):
        result = liwca.ddr(["layup"], toy_dx, toy_embeddings)
        assert result.shape == (1, toy_dx.shape[1])

    def test_single_category(self, toy_embeddings):
        dx = pd.DataFrame(
            {"Sport": [1]},
            index=pd.Index(["hoop"], dtype="string", name="DicTerm"),
        )
        dx.columns.name = "Category"
        result = liwca.ddr(["hoop game"], dx, toy_embeddings)
        assert list(result.columns) == ["Sport"]

    def test_no_embeddings_match_raises(self):
        dx = pd.DataFrame(
            {"Cat": [1]},
            index=pd.Index(["xyzzy"], dtype="string", name="DicTerm"),
        )
        dx.columns.name = "Category"
        empty_emb: dict[str, np.ndarray] = {}
        with pytest.raises(ValueError, match="Cannot determine embedding dimensionality"):
            liwca.ddr(["xyzzy plugh"], dx, empty_emb)

    def test_multiple_documents(self, toy_dx, toy_embeddings):
        texts = ["layup", "dugout", "huddle"]
        result = liwca.ddr(texts, toy_dx, toy_embeddings)
        assert result.shape == (3, toy_dx.shape[1])


# ---------------------------------------------------------------------------
# Embedding loading
# ---------------------------------------------------------------------------


class TestLoadEmbeddings:
    """_load_embeddings helper - string and mapping paths."""

    def test_mapping_returned_as_is(self, toy_embeddings):
        result = _load_embeddings(toy_embeddings)
        assert result is toy_embeddings

    def test_string_calls_gensim(self):
        _load_gensim_model.cache_clear()
        mock_kv = MagicMock()
        mock_gensim = MagicMock()
        mock_gensim.downloader.load.return_value = mock_kv
        with patch.dict(
            "sys.modules",
            {"gensim": mock_gensim, "gensim.downloader": mock_gensim.downloader},
        ):
            result = _load_embeddings("glove-wiki-gigaword-50")
            mock_gensim.downloader.load.assert_called_once_with("glove-wiki-gigaword-50")
            assert result is mock_kv
        _load_gensim_model.cache_clear()

    def test_string_without_gensim_raises(self):
        _load_gensim_model.cache_clear()
        with patch.dict("sys.modules", {"gensim": None, "gensim.downloader": None}):
            with pytest.raises(ImportError, match="pip install liwca\\[ddr\\]"):
                _load_embeddings("glove-wiki-gigaword-50")
        _load_gensim_model.cache_clear()


# ---------------------------------------------------------------------------
# Integration
# ---------------------------------------------------------------------------


class TestDDRIntegration:
    """Read a dictionary file, then run DDR."""

    def test_read_then_ddr(self, toy_dicx_path, toy_embeddings):
        dx = liwca.read_dicx(toy_dicx_path)
        result = liwca.ddr(["the player dunked near the hoop"], dx, toy_embeddings)
        assert result.shape == (1, dx.shape[1])
        assert result.loc[0, "Basketball"] == result.loc[0].max()
