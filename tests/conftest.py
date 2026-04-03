"""Shared fixtures for liwca tests.

The toy dictionary uses three sports categories — Basketball, Baseball, and
Football — so that expected counts are obvious at a glance.

Both .dic and .dicx fixtures represent the **same** 16-term dictionary
(5 per sport + "coach" in all three).  This makes format-conversion tests
straightforward: read either file, get the same DataFrame.

Tests that are not about format conversion use the .dicx fixture by default.
"""

from __future__ import annotations

from pathlib import Path

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


# ---------------------------------------------------------------------------
# In-memory dictionary DataFrames
# ---------------------------------------------------------------------------


@pytest.fixture
def toy_dx() -> pd.DataFrame:
    """Small in-memory dictionary with only exact-match terms (no wildcards).

    3 terms, one per category — useful when wildcard behaviour is irrelevant.
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

    return liwca.read_dx(toy_dicx_path)


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
