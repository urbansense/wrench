from abc import ABC, abstractmethod
from typing import Literal

import numpy as np
import openai
import yake
from keybert import KeyBERT, KeyLLM
from keybert.llm import OpenAI

from wrench.grouper.kinetic.embedder import BaseEmbedder
from wrench.utils.config import LLMConfig

from .defaults import SEED_KEYWORDS, load_stopwords


class KeywordExtractorAdapter(ABC):
    @abstractmethod
    def extract_keywords(self, text: list[str], **kwargs) -> list[list[str]]:
        pass


class KeyLLMAdapter(KeywordExtractorAdapter):
    def __init__(
        self,
        embedder: BaseEmbedder,
        llm_config: LLMConfig,
        lang: Literal["en", "de"] = "en",
        seed_keywords=SEED_KEYWORDS,
    ):
        client = openai.OpenAI(api_key=llm_config.api_key, base_url=llm_config.base_url)
        self.keyllm = KeyLLM(
            llm=OpenAI(
                client=client,
                model=llm_config.model,
            ),
        )

        self.embedder = embedder
        self.stop_words = load_stopwords(lang)
        self.seed_keywords = seed_keywords

    def extract_keywords(self, text, **kwargs):
        embeddings = self.embedder.embed(text)

        results = self.keyllm.extract_keywords(
            docs=text, check_vocab=True, embeddings=embeddings
        )
        return results


class KeyBERTAdapter(KeywordExtractorAdapter):
    def __init__(
        self,
        embedder: BaseEmbedder,
        lang: Literal["en", "de"] = "en",
        seed_keywords: list[str] = SEED_KEYWORDS,
    ):
        self.keybert = KeyBERT(model=embedder.embedding_model)  # type: ignore
        self.stop_words = load_stopwords(lang)
        self.seed_keywords = seed_keywords

    def extract_keywords(
        self,
        text: list[str],
        embeddings: np.ndarray | None = None,
        top_n=7,
        use_mmr: bool = False,
        use_maxsum: bool = False,
        nr_candidates: int = 20,
        diversity: float = 0.5,
        threshold: float | None = None,
        **kwargs,
    ) -> list[list[str]]:
        results = self.keybert.extract_keywords(
            text,
            stop_words=self.stop_words,
            seed_keywords=self.seed_keywords,
            doc_embeddings=embeddings,
            top_n=top_n,
            use_mmr=use_mmr,
            use_maxsum=use_maxsum,
            diversity=diversity,
            nr_candidates=nr_candidates,
            threshold=threshold,
        )
        return [[kw for kw, _ in keywords] for keywords in results]


class YAKEAdapter(KeywordExtractorAdapter):
    def __init__(self, **yake_params):
        self.yake_extractor = yake.KeywordExtractor(**yake_params)

    def extract_keywords(
        self, text: list[str], top_n: int = 10, **kwargs
    ) -> list[list[str]]:
        results = [self.yake_extractor.extract_keywords(t) for t in text]

        # For each document, take top_n keywords
        return [
            [keyword for keyword, _ in doc_results[:top_n]] for doc_results in results
        ]
