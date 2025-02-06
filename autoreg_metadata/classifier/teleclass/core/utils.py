import numpy as np


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Base cosine similarity between two embeddings"""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def max_cosine_similarity(query: np.ndarray, targets: np.ndarray) -> float:
    """Maximum similarity between query and multiple targets"""
    if targets.ndim == 1:
        targets = targets.reshape(1, -1)
    return np.max([cosine_similarity(query, t) for t in targets])
