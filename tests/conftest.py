"""Shared fixtures for liwca tests.

The toy dictionary uses three sports categories - Basketball, Baseball, and
Football - so that expected counts are obvious at a glance.

Both .dic and .dicx fixtures represent the **same** 16-term dictionary
(5 per sport + "coach" in all three).  This makes format-conversion tests
straightforward: read either file, get the same DataFrame.

Tests that are not about format conversion use the .dicx fixture by default.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

DATA_DIR = Path(__file__).parent / "data"


# ---------------------------------------------------------------------------
# File-based fixtures (on-disk .dic / .dicx)
# ---------------------------------------------------------------------------


@pytest.fixture
def toy_dic_path() -> Path:
    """Path to the toy .dic fixture file (16 terms, 3 categories)."""
    return DATA_DIR / "toy.dic"


@pytest.fixture
def toy_dicx_path() -> Path:
    """Path to the toy .dicx fixture file (same 16 terms)."""
    return DATA_DIR / "toy.dicx"


@pytest.fixture
def toybad_dicx_path() -> Path:
    """Path to a .dicx fixture that parses but fails schema (uppercase terms)."""
    return DATA_DIR / "toybad.dicx"


@pytest.fixture
def toy_weighted_dicx_path() -> Path:
    """Path to the toy weighted .dicx fixture (5 terms x 3 categories, signed floats)."""
    return DATA_DIR / "toy_weighted.dicx"


# ---------------------------------------------------------------------------
# In-memory dictionary DataFrames
# ---------------------------------------------------------------------------


@pytest.fixture
def toy_dx() -> pd.DataFrame:
    """Small in-memory dictionary with only exact-match terms (no wildcards).

    3 terms, one per category - useful when wildcard behaviour is irrelevant.
    """
    dx = pd.DataFrame(
        {
            "Baseball": [0, 0, 1],
            "Basketball": [0, 1, 0],
            "Football": [1, 0, 0],
        },
        index=pd.Index(["huddle", "layup", "dugout"], dtype="string", name="DicTerm"),
    )
    dx.columns.name = "Category"
    return dx


@pytest.fixture
def toy_dx_wildcards(toy_dicx_path: Path) -> pd.DataFrame:
    """Full 16-term dictionary loaded from the .dicx fixture."""
    import liwca

    return liwca.read_dicx(toy_dicx_path)


@pytest.fixture
def toy_weighted_dx() -> pd.DataFrame:
    """Small in-memory weighted dictionary (signed floats).

    5 terms x 3 categories - models a multi-category sentiment lexicon.
    """
    dx = pd.DataFrame(
        {
            "Negative": [-0.7, 0.0, 0.0, -0.5, 0.0],
            "Neutral": [0.0, 0.0, 1.0, 0.0, 0.0],
            "Positive": [0.0, 0.9, 0.0, 0.0, 1.2],
        },
        index=pd.Index(
            ["awful", "great", "ok", "bad", "excellent"], dtype="string", name="DicTerm"
        ),
    ).astype("float64")
    dx.columns.name = "Category"
    return dx


# ---------------------------------------------------------------------------
# Sample texts
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Toy embeddings for DDR tests
# ---------------------------------------------------------------------------


@pytest.fixture
def toy_embeddings() -> dict[str, np.ndarray]:
    """Toy 3-D embeddings where sport terms cluster by direction.

    Basketball ~ [1, 0, 0], Baseball ~ [0, 1, 0], Football ~ [0, 0, 1].
    Common words sit near the origin so they don't dominate similarity.
    """
    return {
        # Basketball direction
        "hoop": np.array([1.0, 0.1, 0.0]),
        "dunk": np.array([0.9, 0.0, 0.1]),
        "rebound": np.array([0.85, 0.1, 0.05]),
        "layup": np.array([0.95, 0.05, 0.0]),
        "basket": np.array([0.9, 0.1, 0.0]),
        # Baseball direction
        "pitch": np.array([0.1, 0.9, 0.0]),
        "homer": np.array([0.0, 1.0, 0.1]),
        "dugout": np.array([0.05, 0.95, 0.0]),
        "inning": np.array([0.1, 0.85, 0.05]),
        "batter": np.array([0.1, 0.85, 0.05]),
        # Football direction
        "touchdown": np.array([0.0, 0.1, 0.9]),
        "quarterback": np.array([0.1, 0.0, 0.95]),
        "tackle": np.array([0.05, 0.05, 0.9]),
        "huddle": np.array([0.0, 0.1, 0.85]),
        "fumbl": np.array([0.05, 0.0, 0.9]),
        # Shared across sports
        "coach": np.array([0.4, 0.4, 0.4]),
        # Common words (not in dictionary)
        "the": np.array([0.1, 0.1, 0.1]),
        "and": np.array([0.1, 0.1, 0.1]),
        "a": np.array([0.1, 0.1, 0.1]),
        "player": np.array([0.3, 0.3, 0.3]),
        "grabbed": np.array([0.2, 0.2, 0.2]),
        "near": np.array([0.1, 0.1, 0.1]),
        "from": np.array([0.1, 0.1, 0.1]),
        "as": np.array([0.1, 0.1, 0.1]),
        "watched": np.array([0.15, 0.15, 0.15]),
        "threw": np.array([0.2, 0.2, 0.2]),
        "pass": np.array([0.2, 0.2, 0.2]),
        "before": np.array([0.1, 0.1, 0.1]),
        "hit": np.array([0.2, 0.2, 0.2]),
        "fastball": np.array([0.1, 0.8, 0.1]),
        "pitcher": np.array([0.1, 0.85, 0.05]),
        "pitched": np.array([0.1, 0.8, 0.1]),
    }


# ---------------------------------------------------------------------------
# Sample texts
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_texts() -> list[str]:
    """Short documents with clear sport associations for count tests."""
    return [
        "the player dunked and grabbed the rebound near the hoop",  # basketball
        "the pitcher pitched a fastball and the batter hit a homer",  # baseball
        "the quarterback threw a touchdown pass before the tackle",  # football
        "the coach watched from the dugout as the player dunked",  # mixed
        "",  # empty doc
    ]
