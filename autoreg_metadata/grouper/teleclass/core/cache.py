import pickle
from pathlib import Path

from autoreg_metadata.grouper.teleclass.core.models.enrichment_models import (
    EnrichedClass,
)
from autoreg_metadata.grouper.teleclass.core.models.models import DocumentMeta


class TELEClassCache:
    """Handles caching and loading of TELEClass state and results"""

    def __init__(self, cache_dir: str = ".teleclass_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

        # Define paths for different cache components
        self.class_terms_path = self.cache_dir / "class_terms.pkl"
        self.assignments_path = self.cache_dir / "assignments.pkl"

    def save_class_terms(self, class_terms: dict[str, EnrichedClass]) -> None:
        """Save enriched classes using pickle (due to complex objects)"""
        with open(self.class_terms_path, "wb") as f:
            pickle.dump(class_terms, f)

    def load_class_terms(self) -> dict[str, EnrichedClass] | None:
        """Load enriched classes if they exist"""
        if self.class_terms_path.exists():
            with open(self.class_terms_path, "rb") as f:
                return pickle.load(f)
        return None

    def save_assignments(self, assignments: list[DocumentMeta]) -> None:
        """Save assignments"""
        with open(self.assignments_path, "wb") as f:
            pickle.dump(assignments, f)

    def load_assignments(self) -> list[DocumentMeta]:
        """Load assignments if they exist, converting lists back to sets"""
        assignments = []

        if self.assignments_path.exists():
            with open(self.assignments_path, "rb") as f:
                assignments = pickle.load(f)

        return assignments
