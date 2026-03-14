"""
Example: Minimal pipeline
Demonstrates: The smallest runnable Wrench pipeline using a NoopCataloger so no
              external catalog is needed. Harvests devices from a public SensorThings
              API and prints the result without registering anything.
Prerequisites: pip install 'auto-wrench[sensorthings]'
               A reachable SensorThings endpoint (edit BASE_URL below).
"""

import asyncio

from wrench.cataloger.noop import NoopCataloger
from wrench.grouper.lda import LDAGrouper
from wrench.grouper.lda.models import LDAConfig
from wrench.harvester.sensorthings import SensorThingsHarvester
from wrench.metadataenricher.sensorthings import SensorThingsMetadataEnricher
from wrench.pipeline.sensor_pipeline import SensorRegistrationPipeline
from wrench.utils.config import LLMConfig

# ---------------------------------------------------------------------------
# Configuration — edit these values to point at a real endpoint.
# ---------------------------------------------------------------------------
BASE_URL = "https://example.org/v1.1"

# SensorThingsMetadataEnricher requires an LLM to generate group descriptions.
# Point this at any OpenAI-compatible endpoint (e.g. a local Ollama instance).
LLM_BASE_URL = "http://localhost:11434/v1"
LLM_MODEL = "llama3.3:70b-instruct-q4_K_M"
# ---------------------------------------------------------------------------


def build_pipeline() -> SensorRegistrationPipeline:
    """Assemble a minimal pipeline."""
    harvester = SensorThingsHarvester(
        base_url=BASE_URL,
        pagination_config={
            "page_delay": 0.1,
            "timeout": 60,
            "batch_size": 100,
        },
    )

    # LDAGrouper groups devices by topic modelling — no ML extras needed.
    grouper = LDAGrouper(
        config=LDAConfig(
            n_topics=5,
            use_llm_naming=False,  # disable LLM naming to avoid a second network call
        )
    )

    llm_config = LLMConfig(base_url=LLM_BASE_URL, model=LLM_MODEL)

    metadata_enricher = SensorThingsMetadataEnricher(
        base_url=BASE_URL,
        title="Example Sensor Network",
        description="A minimal example sensor network.",
        llm_config=llm_config,
    )

    # NoopCataloger discards results — no catalog credentials needed.
    cataloger = NoopCataloger()

    return SensorRegistrationPipeline(
        harvester=harvester,
        grouper=grouper,
        metadataenricher=metadata_enricher,
        cataloger=cataloger,
    )


async def main() -> None:
    pipeline = build_pipeline()
    result = await pipeline.run_async()

    print(f"Pipeline succeeded: {result.success}")
    print(f"Run ID: {result.run_id}")
    if result.results:
        for component, data in result.results.items():
            print(f"  [{component}] → {data}")


if __name__ == "__main__":
    asyncio.run(main())
