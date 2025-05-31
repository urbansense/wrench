import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Literal

import community as cd
import networkx as nx
from flair.data import Sentence
from flair.models import SequenceTagger
from keybert import KeyBERT
from sentence_transformers import SentenceTransformer


def _remove_uuids_and_numbers(text):
    # First, define the regex patterns
    find_uuid = r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
    find_numbers = r"\d"

    # First remove UUIDs
    text = re.sub(find_uuid, "", text)

    # Then remove any remaining digits
    text = re.sub(find_numbers, "", text)

    return text


def _remove_special_and_whitespace(text):
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[^\w\s]", "", text)
    return text


def _remove_entities(text: str, tagger: SequenceTagger) -> str:
    # wrap & tag
    sentence = Sentence(text)

    tagger.predict(sentence)
    # find all LOC spans
    loc_spans = [
        ent.text
        for ent in sentence.get_spans("ner")
        if ent.tag == "LOC" or ent.tag == "ORG" or ent.tag == "PERS"
    ]
    # remove each span (escape for regex) and collapse extra spaces
    cleaned = text
    for span in set(loc_spans):
        cleaned = re.sub(r"\b{}\b".format(re.escape(span)), "", cleaned)
    # normalize whitespace
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned


def preprocess(
    docs: list[str],
    lang: Literal["en", "de", "fr", "sp", "nl"] = "en",
    with_entity_extraction: bool = True,
):
    """
    Preprocess input documents. Yields processed documents one by one.

    Runs entity extraction and removes all location, organization, and person entities.

    Args:
        docs (list(str)): The documents to be processed in string format.
        lang (str): The language of the documents to be processed in ISO 3166-A-2
            format, defaults to "en"
        with_entity_extraction (bool): Extract and remove location, organization,
            and person entities from text.

    Yields:
        str: A processed document.
    """
    # maps lang format for yake to lang format for flair
    language_map = {
        "en": "english",
        "de": "german",
        "nl": "dutch",
        "fr": "french",
        "sp": "spanish",
    }

    tagger = None  # Initialize tagger to None
    if with_entity_extraction:
        tagger = SequenceTagger.load(f"flair/ner-{language_map[lang]}-large")

    for text in docs:
        processed_text = _remove_uuids_and_numbers(text)
        processed_text = _remove_special_and_whitespace(processed_text)

        if with_entity_extraction and tagger:  # Check if tagger is loaded
            processed_text = _remove_entities(processed_text, tagger)

        yield processed_text  # Yield processed text


def extract_keywords(
    docs: list[str], embedder: SentenceTransformer, lang: Literal["de", "en"] = "de"
) -> list[list[str]]:
    """Extracts keywords from a list of documents using the specified extractor.

    Args:
        docs: A sequence of strings, where each string is a document.
        embedder: A pre-initialized SentenceTransformer model to use in KeyBERT.
        lang: The language of the documents (default is 'de').

    Returns:
        A list of lists, where each inner list contains the keywords for a document.
    """
    dir_path = Path(__file__).parent / "stopwords"
    stopwords_path = os.path.join(dir_path, "stopwords-%s.txt" % lang[:2].lower())

    if not os.path.exists(stopwords_path):
        # TODO: implement logger here and log that stopwords is not found for $lang
        stop_words = []
    else:
        with open(stopwords_path) as f:
            stop_words = [line.rstrip("\n") for line in f]

    seed_keywords = [
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
        "information tehcnology",
    ]

    kw_extractor = KeyBERT(model=embedder)

    # keywords_list: list[list[str]] = []
    keywords_list = kw_extractor.extract_keywords(
        docs=docs, stop_words=stop_words, seed_keywords=seed_keywords
    )

    return [[kw for kw, _ in keywords] for keywords in keywords_list]


def build_cooccurence_network(keywords_per_doc: list[list[str]]) -> dict[str, list]:
    """Builds a keyword co-occurrence network and visualizes it.

    The function identifies communities (clusters) of keywords and extracts the most
    central keywords from each community.

    Args:
        keywords_per_doc: A list of lists, where each inner list contains keywords
                          for a specific document.

    Returns:
        A dictionary where keys are cluster identifiers (e.g., 'cluster_0') and
        values are lists of the top 5 most central keywords in that cluster.
    """
    G = nx.Graph()

    for kw_list in keywords_per_doc:
        for i, u in enumerate(kw_list):
            for v in kw_list[i + 1 :]:
                if G.has_edge(u, v):
                    G[u][v]["weight"] += 1
                else:
                    G.add_edge(u, v, weight=1)

    partition = cd.best_partition(G, weight="weight")

    comms = defaultdict(list)
    for node, comm_id in partition.items():
        comms[comm_id].append(node)

    essential = {}
    for comm_id, kws in comms.items():
        # compute weighted degree
        deg = {kw: G.degree(kw, weight="weight") for kw in kws}
        # select top 5 (or whatever you need)
        top5 = sorted(deg, key=deg.get, reverse=True)[:7]
        essential[f"cluster_{comm_id}"] = top5

    # centrality = dict(G.degree(weight="weight"))

    # # Generate positions for all nodes
    # pos = nx.spring_layout(G, weight="weight", seed=42)

    # # Extract community IDs and centrality values
    # colors = [partition[node] for node in G.nodes()]
    # # Adjust node sizes: ensure a minimum size and scale by centrality
    # sizes = [max(100, centrality.get(node, 0) * 300) for node in G.nodes()]

    # # Draw nodes
    # nx.draw_networkx_nodes(G, pos, node_color=colors, node_size=sizes, cmap=plt.cm.Set3)

    # # Draw edges
    # nx.draw_networkx_edges(G, pos, alpha=0.5)

    # # Draw labels
    # nx.draw_networkx_labels(G, pos, font_size=6)

    # # Display the plot
    # plt.axis("off")
    # plt.show()

    return essential
