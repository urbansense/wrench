"""
Example: Full pipeline with KINETIC grouper, metadata enricher, and SDDI cataloger
Demonstrates: A production-style pipeline that harvests from a SensorThings API,
              groups devices using the KINETIC algorithm, enriches metadata with an
              LLM, and registers the result to an SDDI/CKAN catalog.
Prerequisites: pip install 'auto-wrench[sensorthings,kinetic]'
               A reachable SensorThings endpoint, an LLM service, and an SDDI
               catalog with a valid API key.
"""

import asyncio

from wrench.cataloger.sddi import SDDICataloger
from wrench.grouper.kinetic import KINETIC
from wrench.harvester.sensorthings import SensorThingsHarvester
from wrench.metadataenricher.sensorthings import SensorThingsMetadataEnricher
from wrench.pipeline.sensor_pipeline import SensorRegistrationPipeline
from wrench.utils.config import LLMConfig

# ---------------------------------------------------------------------------
# Configuration — replace all placeholder values before running.
# ---------------------------------------------------------------------------
STA_BASE_URL = "https://example.org/v1.1"

LLM_BASE_URL = "http://localhost:11434/v1"  # Ollama or any OpenAI-compatible URL
LLM_MODEL = "llama3.3:70b-instruct-q4_K_M"
LLM_API_KEY = "ollama"  # "ollama" for local Ollama; use a real
# key for OpenAI

CATALOG_BASE_URL = "https://catalog.example.org"
CATALOG_API_KEY = "your-ckan-api-key"
CATALOG_OWNER_ORG = "your-organization"
# ---------------------------------------------------------------------------


def build_pipeline() -> SensorRegistrationPipeline:
    """Assemble the full pipeline."""
    harvester = SensorThingsHarvester(
        base_url=STA_BASE_URL,
        pagination_config={
            "page_delay": 0.2,
            "timeout": 60,
            "batch_size": 100,
        },
    )

    llm_config = LLMConfig(
        base_url=LLM_BASE_URL,
        model=LLM_MODEL,
        api_key=LLM_API_KEY,
    )

    # KINETIC uses keyword extraction and a co-occurrence network to build a
    # topic hierarchy, then classifies devices into that hierarchy.
    grouper = KINETIC(
        llm_config=llm_config,
        # SentenceTransformers model used for keyword extraction and classification.
        # Use "all-MiniLM-L12-v2" for English-only data.
        embedder="intfloat/multilingual-e5-large-instruct",
        lang="de",  # "de" for German sensor names, "en" for English
        resolution=1,  # Higher values → smaller, more specific groups
    )

    metadata_enricher = SensorThingsMetadataEnricher(
        base_url=STA_BASE_URL,
        title="City Sensor Network",
        description="Environmental and mobility sensors deployed across the city.",
        llm_config=llm_config,
    )

    cataloger = SDDICataloger(
        base_url=CATALOG_BASE_URL,
        api_key=CATALOG_API_KEY,
        owner_org=CATALOG_OWNER_ORG,
    )

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
    print(f"Stopped early: {result.stopped_early}")


if __name__ == "__main__":
    asyncio.run(main())
