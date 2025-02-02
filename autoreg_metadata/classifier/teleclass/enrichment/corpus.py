import math
from typing import Dict, List, Set

import numpy as np
import yake
from keybert import KeyBERT
from rank_bm25 import BM25Okapi

from autoreg_metadata.classifier.teleclass.core.config import CorpusConfig
from autoreg_metadata.classifier.teleclass.core.embeddings import EmbeddingService
from autoreg_metadata.classifier.teleclass.core.models.enrichment_models import (
    CorpusEnrichmentResult,
    EnrichedClass,
    TermScore,
)
from autoreg_metadata.classifier.teleclass.core.models.models import DocumentMeta
from autoreg_metadata.log import logger


class MultiWordPhraseExtractor:
    """Extract multi-word phrases from text using YAKE or KeyBERT"""

    def __init__(
        self, model: str, keybert_model: str = "all-mpnet-base-v2", top_n: int = 5
    ):
        if model == "yake":
            self.yake_extractor = yake.KeywordExtractor(
                lan="en",
                n=3,
                dedupLim=0.9,
                dedupFunc="seqm",
                windowsSize=1,
                top=top_n,
                features=None,
            )
            self.model = "yake"
        elif model == "keybert":
            self.bert_extractor = KeyBERT(model=keybert_model)
            self.model = "keybert"
        else:
            raise ValueError("Invalid model type. Choose 'yake' or 'keybert'")


class CorpusEnricher:
    def __init__(
        self,
        config: CorpusConfig,
        embedding: EmbeddingService,
    ):
        self.embedder = embedding
        self.keyword_model = MultiWordPhraseExtractor(
            model=config.phrase_extractor, keybert_model=self.embedder.model_name
        )
        self.class_terms: Dict[str, EnrichedClass] = {}
        self.logger = logger.getChild(self.__class__.__name__)

    def enrich(
        self,
        collection: List[DocumentMeta],
    ) -> CorpusEnrichmentResult:
        """
        Enrich taxonomy using documents

        Args:
            collection: List of DocumentMeta containing documents and its assigned core classes

        Returns:
            Dictionary mapping class names to their enriched terms with scores
        """
        # Convert documents to dictionary format with IoT structure
        doc_dict = {}

        class_set: Set[str] = set()

        for doc in collection:
            if not doc.initial_core_classes:
                raise ValueError(
                    f"Initial core classes for document {str(doc.id)} not defined"
                )
            doc_dict[str(doc.id)] = doc
            class_set.update(doc.initial_core_classes)

        for class_name in class_set:
            # Get documents assigned to this class
            self.logger.info("Enriching class: %s", class_name)
            class_docs = [
                doc_dict[str(doc.id)]
                for doc in collection
                if doc.initial_core_classes and class_name in doc.initial_core_classes
            ]

            # Get sibling data
            sibling_docs = self.get_sibling_data(class_name, doc_dict, collection)

            term_scores = self.enrich_class(class_name, class_docs, sibling_docs)

            enriched_class = EnrichedClass(class_name=class_name, terms=term_scores)

            self.class_terms[class_name] = enriched_class

        return CorpusEnrichmentResult(ClassEnrichment=self.class_terms)

    def get_sibling_data(
        self,
        class_name: str,
        documents: Dict[str, DocumentMeta],
        collection: List[DocumentMeta],
    ) -> Dict[str, List[DocumentMeta]]:
        """
        Get documents assigned to sibling classes, preserving IoT format
        """
        sibling_docs: Dict[str, List[DocumentMeta]] = {}
        # Group documents by their assigned classes
        for doc in collection:
            if doc.initial_core_classes:
                for cls in doc.initial_core_classes:
                    if cls != class_name:
                        if cls not in sibling_docs:
                            sibling_docs[cls] = []
                        if str(doc.id) in documents:  # Make sure document exists
                            sibling_docs[cls].append(documents[str(doc.id)])

        return sibling_docs

    def calculate_popularity(self, term: str, documents: List[str]) -> float:
        """
        Calculate popularity for multi-word terms with more precise matching
        """
        term = term.lower().strip()
        term_words = term.split()

        df = 0
        for doc in documents:
            doc = doc.lower()
            if len(term_words) == 1:
                # Single word - match as whole word
                if term in doc.split():
                    df += 1
            else:
                # Multi-word phrase - exact phrase match
                if term in doc:
                    df += 1

        return math.log(1 + df)

    def calculate_distinctiveness(
        self, term: str, class_docs: List[str], sibling_docs: Dict[str, List[str]]
    ) -> float:
        """
        Calculate distinctiveness using BM25 scores with phrase preservation
        """
        term = term.lower().strip()

        # Prepare documents with phrase preservation
        def prepare_doc(doc: str) -> List[str]:
            # Keep the phrase together in tokenization
            doc = doc.lower()
            # Replace term with a single token if it appears
            if term in doc:
                doc = doc.replace(term, term.replace(" ", "_"))
            return doc.split()

        # Tokenize documents preserving phrases
        tokenized_class_docs = [prepare_doc(doc) for doc in class_docs]
        class_bm25 = BM25Okapi(tokenized_class_docs)
        # Use the term as a single token
        term_token = term.replace(" ", "_")
        class_score = class_bm25.get_scores([term_token])[0]

        # Calculate scores for sibling classes
        sibling_scores = []
        for sib_docs in sibling_docs.values():
            tokenized_sib_docs = [prepare_doc(doc) for doc in sib_docs]
            sib_bm25 = BM25Okapi(tokenized_sib_docs)
            sib_score = sib_bm25.get_scores([term_token])[0]
            sibling_scores.append(sib_score)

        # Apply softmax
        all_scores = np.array([class_score] + sibling_scores)
        # Add small epsilon to prevent division by zero
        exp_scores = np.exp(all_scores - np.max(all_scores))
        softmax_scores = exp_scores / (exp_scores.sum() + 1e-10)

        return softmax_scores[0]

    def calculate_semantic_similarity(self, term: str, class_name: str) -> float:
        """
        Calculate semantic similarity using sentence transformer embeddings
        """
        term_embedding = self.embedder.get_embeddings(term)
        class_embedding = self.embedder.get_embeddings(class_name)

        similarity = self.embedder.encoder.similarity(
            term_embedding, class_embedding
        ).item()

        return similarity

    def extract_key_phrases(self, text: str, top_n: int = 5) -> List[str]:
        if self.keyword_model.model == "keybert":
            keywords = self.keyword_model.bert_extractor.extract_keywords(
                docs=text,
                keyphrase_ngram_range=(1, 3),  # Extract phrases of 1-3 words
                stop_words="english",
                use_maxsum=True,
                nr_candidates=10,
                top_n=top_n,
            )
        elif self.keyword_model.model == "yake":
            keywords = self.keyword_model.yake_extractor.extract_keywords(text)
        else:
            raise ValueError("Invalid model type. Choose 'yake' or 'keybert'")

        return [keyword for keyword, _ in keywords]

    def extract_candidate_terms(self, iot_data_list: List[DocumentMeta]) -> Set[str]:
        """
        Extract candidate terms from IoT data
        """
        terms = set()
        # Extract terms from descriptions
        text = " ".join(data.content for data in iot_data_list)
        words = self.extract_key_phrases(text, top_n=5)

        # Add single words
        terms.update(words)

        return terms

    def enrich_class(
        self,
        class_name: str,
        input_class: List[DocumentMeta],
        class_siblings: Dict[str, List[DocumentMeta]],
        top_k: int = 3,
    ) -> Set[TermScore]:
        """
        Enrich a class with terms from IoT data
        """
        # Convert IoT data to text documents
        class_docs = [doc.content for doc in input_class]

        sibling_docs = {
            sib: [d.content for d in docs] for sib, docs in class_siblings.items()
        }

        # Extract candidate terms
        self.logger.info("Extracting candidate terms")
        candidate_terms = self.extract_candidate_terms(input_class)
        self.logger.debug("Candidate terms: %s", candidate_terms)

        # Score terms
        scores = []
        for term in candidate_terms:
            # Calculate component scores
            self.logger.info("Calculating component scores for term: %s", term)
            popularity = self.calculate_popularity(term, class_docs)
            distinctiveness = self.calculate_distinctiveness(
                term, class_docs, sibling_docs
            )
            semantic_similarity = self.calculate_semantic_similarity(term, class_name)

            self.logger.debug(
                "\nPopularity: %10.3f\nDistinctiveness: %10.3f\nSemantic Similarity: %10.3f",
                popularity,
                distinctiveness,
                semantic_similarity,
            )

            scores.append(
                TermScore(
                    term=term,
                    popularity=popularity,
                    distinctiveness=distinctiveness,
                    semantic_similarity=semantic_similarity,
                )
            )

        # Sort by affinity score and return top-k
        scores.sort(key=lambda x: x.affinity_score, reverse=True)
        return set(scores[:top_k])
