import pickle
from pathlib import Path

import numpy as np

from wrench.grouper.teleclass.core.models import Document, EnrichedClass
from wrench.log import logger


class TELEClassCache:
    """Handles caching and loading of TELEClass state and results."""

    def __init__(self, cache_dir: str = ".teleclass_cache"):
        """
        Initializes the cache directory and defines paths for cache components.

        Args:
            cache_dir (str): Directory for cache files. Defaults to ".teleclass_cache".

        Attributes:
            cache_dir (Path): Path to the cache directory.
            class_terms_path (Path): Path to the class terms cache file.
            assignments_path (Path): Path to the assignments cache file.
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

        # Define paths for different cache components
        self.class_terms_path = self.cache_dir / "class_terms.pkl"
        self.assignments_path = self.cache_dir / "assignments.pkl"
        self.embeddings_path = self.cache_dir / "embeddings.npz"

        self.logger = logger.getChild(self.__class__.__name__)

    def save_class_embeddings(self, enriched_classes: list[EnrichedClass]) -> None:
        class_names: list[str] = []
        class_embeddings: list[np.ndarray] = []
        for cls in enriched_classes:
            if cls.embeddings is None:
                raise ValueError("embeddings need to be set before caching")

            class_names.append(cls.class_name)
            class_embeddings.append(cls.embeddings)

        np.savez_compressed(
            self.embeddings_path,
            class_names=class_names,
            embeddings=class_embeddings,
        )

    def load_class_embeddings(self) -> list[EnrichedClass]:
        if not self.embeddings_path.exists():
            raise FileNotFoundError(
                "run the TELEClass classifier to generate embeddings"
            )

        try:
            data = np.load(self.embeddings_path, allow_pickle=True)
            class_names = data["class_names"]
            embeddings = data["embeddings"]

            enriched_classes: list[EnrichedClass] = []
            for name, embedding in zip(class_names, embeddings):
                enriched_class = EnrichedClass(
                    class_name=name,
                    class_description="",
                    terms=set(),
                    embeddings=embedding,
                )
                enriched_classes.append(enriched_class)

            return enriched_classes
        except Exception as e:
            self.logger.error(f"Error loading class embeddings: {e}")
            raise ValueError("failed to load embeddings")

    def save_class_terms(self, class_terms: list[EnrichedClass]) -> None:
        """Save enriched classes using pickle (due to complex objects)."""
        with open(self.class_terms_path, "wb") as f:
            pickle.dump(class_terms, f)

    def load_class_terms(self) -> list[EnrichedClass] | None:
        """Load enriched classes if they exist."""
        if self.class_terms_path.exists():
            with open(self.class_terms_path, "rb") as f:
                return pickle.load(f)
        return None

    def save_assignments(self, assignments: list[Document]) -> None:
        """Save assignments."""
        with open(self.assignments_path, "wb") as f:
            pickle.dump(assignments, f)

    def load_assignments(self) -> list[Document]:
        """Load assignments if they exist, converting lists back to sets."""
        assignments = []

        if self.assignments_path.exists():
            with open(self.assignments_path, "rb") as f:
                assignments = pickle.load(f)

        return assignments
