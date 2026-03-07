"""Shared defaults and constants for the KINETIC pipeline."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

# -- Cache directory (used by Classifier and LLMTopicGenerator) --
CACHE_DIR = Path(".kineticache")

# -- Default local embedder model --
DEFAULT_EMBEDDER_MODEL = "intfloat/multilingual-e5-large-instruct"

# -- Keyword extraction (KeyBERT) defaults --
KEYWORD_TOP_N = 7
KEYWORD_DIVERSITY = 0.5
KEYWORD_NR_CANDIDATES = 20

# -- Co-occurrence network --
COOCCURRENCE_TOP_N = 7

# -- Classifier outlier detection (IQR method) --
OUTLIER_PERCENTILE_LOW = 10
OUTLIER_PERCENTILE_HIGH = 90
OUTLIER_IQR_MULTIPLIER = 1.5

# -- Classifier similarity scoring --
# Temperature for softmax applied to cosine similarity scores.
# Values < 1 sharpen the distribution (amplify small differences between scores).
# Typical range: 0.01 – 0.1. Lower = more aggressive separation.
SIMILARITY_TEMPERATURE = 0.05

# -- LLM generation --
LLM_TEMPERATURE = 0.0
LLM_MAX_TOKENS = 8192

# -- Seed keywords for KeyBERT extraction --
SEED_KEYWORDS: list[str] = [
    "mobility",
    "environment",
    "energy",
    "administration",
    "living",
    "education",
    "work",
    "culture",
    "trade",
    "construction",
    "health",
    "agriculture",
    "craft",
    "tourism",
    "information technology",
]


def load_stopwords(lang: Literal["de", "en"]) -> list[str]:
    """Load language-specific stopwords from the stopwords directory."""
    stopwords_path = (
        Path(__file__).parent / "stopwords" / f"stopwords-{lang[:2].lower()}.txt"
    )
    if not os.path.exists(stopwords_path):
        return []
    with open(stopwords_path) as f:
        return [line.rstrip("\n") for line in f]
