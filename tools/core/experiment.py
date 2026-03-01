"""Experiment tracking for grouper evaluation."""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


class ExperimentTracker:
    """Track and compare grouper experiments."""

    def __init__(self, experiments_dir: str = ".experiments"):
        self.experiments_dir = Path(experiments_dir)
        self.experiments_dir.mkdir(exist_ok=True)

    def save_experiment(
        self,
        name: str,
        source: str,
        grouper: str,
        results: dict[str, list[str]],
        config: dict[str, Any] | None = None,
        metrics: dict[str, float] | None = None,
        similarity_scores: dict | None = None,
        trace: dict | None = None,
    ) -> Path:
        """
        Save an experiment with its results and metadata.

        Args:
            name: Experiment name (e.g., "osnabrueck_kinetic_v1")
            source: Data source name
            grouper: Grouper type used (kinetic, embedding, lda)
            results: Topic -> device IDs mapping
            config: Grouper configuration used
            metrics: Evaluation metrics (if ground truth available)

        Returns:
            Path to the experiment directory
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        exp_id = f"{name}_{timestamp}"
        exp_dir = self.experiments_dir / exp_id
        exp_dir.mkdir(parents=True, exist_ok=True)

        # Save results
        with open(exp_dir / "results.json", "w") as f:
            json.dump(results, f, indent=2)

        # Save metadata
        metadata = {
            "name": name,
            "source": source,
            "grouper": grouper,
            "timestamp": timestamp,
            "num_topics": len(results),
            "num_devices": sum(len(ids) for ids in results.values()),
        }
        if config:
            metadata["config"] = config
        if metrics:
            metadata["metrics"] = metrics
        if similarity_scores:
            metadata["similarity_scores"] = similarity_scores

        with open(exp_dir / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        if trace:
            from wrench.grouper.kinetic.tracer import _json_default

            with open(exp_dir / "trace.json", "w") as f:
                json.dump(trace, f, indent=2, ensure_ascii=False, default=_json_default)

        return exp_dir

    def list_experiments(self, source: str | None = None) -> list[dict]:
        """List all experiments, optionally filtered by source."""
        experiments = []

        for exp_dir in sorted(self.experiments_dir.iterdir(), reverse=True):
            if not exp_dir.is_dir():
                continue

            metadata_file = exp_dir / "metadata.json"
            if not metadata_file.exists():
                continue

            with open(metadata_file) as f:
                metadata = json.load(f)
                metadata["id"] = exp_dir.name
                metadata["path"] = str(exp_dir)

            if source is None or metadata.get("source") == source:
                experiments.append(metadata)

        return experiments

    def get_experiment(self, exp_id: str) -> tuple[dict, dict]:
        """
        Get experiment metadata and results.

        Returns:
            Tuple of (metadata, results)
        """
        exp_dir = self.experiments_dir / exp_id

        if not exp_dir.exists():
            raise FileNotFoundError(f"Experiment {exp_id} not found")

        with open(exp_dir / "metadata.json") as f:
            metadata = json.load(f)

        with open(exp_dir / "results.json") as f:
            results = json.load(f)

        return metadata, results

    def get_results_path(self, exp_id: str) -> Path:
        """Get path to results.json for an experiment."""
        return self.experiments_dir / exp_id / "results.json"

    def delete_experiment(self, exp_id: str):
        """Delete an experiment."""
        exp_dir = self.experiments_dir / exp_id
        if exp_dir.exists():
            shutil.rmtree(exp_dir)

    def compare_experiments(
        self, exp_id1: str, exp_id2: str
    ) -> dict[str, dict[str, Any]]:
        """Compare two experiments."""
        meta1, results1 = self.get_experiment(exp_id1)
        meta2, results2 = self.get_experiment(exp_id2)

        comparison = {
            "experiment_1": {
                "id": exp_id1,
                "name": meta1.get("name"),
                "grouper": meta1.get("grouper"),
                "num_topics": meta1.get("num_topics"),
                "num_devices": meta1.get("num_devices"),
                "metrics": meta1.get("metrics", {}),
            },
            "experiment_2": {
                "id": exp_id2,
                "name": meta2.get("name"),
                "grouper": meta2.get("grouper"),
                "num_topics": meta2.get("num_topics"),
                "num_devices": meta2.get("num_devices"),
                "metrics": meta2.get("metrics", {}),
            },
        }

        # Compare topics
        topics1 = set(results1.keys())
        topics2 = set(results2.keys())

        comparison["topics"] = {
            "common": list(topics1 & topics2),
            "only_in_1": list(topics1 - topics2),
            "only_in_2": list(topics2 - topics1),
        }

        return comparison
