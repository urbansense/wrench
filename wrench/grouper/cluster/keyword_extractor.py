import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Literal

import yake
from keybert import KeyBERT

from wrench.grouper.cluster.embedder import BaseEmbedder

SEED_KEYWORDS = [
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


class KeywordExtractorAdapter(ABC):
    @abstractmethod
    def extract_keywords(self, text: list[str], **kwargs) -> list[list[str]]:
        pass


class KeyBERTAdapter(KeywordExtractorAdapter):
    def __init__(
        self,
        embedder: BaseEmbedder,
        lang: Literal["en", "de"] = "en",
        seed_keywords: list[str] = SEED_KEYWORDS,
    ):
        self.keybert = KeyBERT(model=embedder.embedding_model)  # type: ignore

        dir_path = Path(__file__).parent / "stopwords"
        stopwords_path = os.path.join(dir_path, "stopwords-%s.txt" % lang[:2].lower())

        if not os.path.exists(stopwords_path):
            stop_words = []
        else:
            with open(stopwords_path) as f:
                stop_words = [line.rstrip("\n") for line in f]

        self.stop_words = stop_words
        self.seed_keywords = seed_keywords

    def extract_keywords(self, text: list[str], **kwargs) -> list[list[str]]:
        results = self.keybert.extract_keywords(
            text,
            stop_words=self.stop_words,
            seed_keywords=self.seed_keywords,
            top_n=7,
            **kwargs,
        )
        return [[kw for kw, _ in keywords] for keywords in results]


class YAKEAdapter(KeywordExtractorAdapter):
    def __init__(self, **yake_params):
        self.yake_extractor = yake.KeywordExtractor(**yake_params)

    def extract_keywords(
        self, text: list[str], top_n: int = 10, **kwargs
    ) -> list[list[str]]:
        results = [self.yake_extractor.extract_keywords(t) for t in text]

        # Take top_n results and extract keywords
        sorted_results = sorted(results, key=lambda x: x[0])[:top_n]
        return [keyword for score, keyword in sorted_results]  # type: ignore
