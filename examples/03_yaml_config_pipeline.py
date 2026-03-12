"""
Example: YAML-configured pipeline
Demonstrates: How to define a complete pipeline in a YAML file and run it with
              PipelineRunner.from_config_file(). Environment variables are
              substituted automatically using ${VAR_NAME} syntax.
Prerequisites: pip install 'auto-wrench[sensorthings,kinetic]'
               Copy pipeline_config.example.yaml to pipeline_config.yaml,
               fill in your values (or export the listed env vars), then run
               this script.
"""

import asyncio
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# The YAML config below is written to disk so this example is self-contained.
# In real usage, maintain your YAML file separately and call
# PipelineRunner.from_config_file("path/to/pipeline_config.yaml").
# ---------------------------------------------------------------------------

YAML_CONTENT = """\
# pipeline_config.yaml
#
# template_ selects the built-in SensorPipeline template which wires
# harvester → grouper → metadataenricher → cataloger automatically.
template_: SensorPipeline

harvester:
  sensorthings:
    base_url: "${STA_BASE_URL}"
    pagination_config:
      page_delay: 0.1
      timeout: 60
      batch_size: 100

grouper:
  kinetic:
    llm_config:
      model: "${OLLAMA_MODEL}"
      base_url: "${OLLAMA_URL}"
      api_key: "${OLLAMA_API_KEY}"
    # Optional KINETIC parameters (shown with defaults):
    # embedder: "intfloat/multilingual-e5-large-instruct"
    # lang: "de"
    # resolution: 1

metadataenricher:
  sensorthings:
    base_url: "${STA_BASE_URL}"
    title: "City Sensor Network"
    description: "Urban sensor network providing environmental and mobility data."
    llm_config:
      model: "${OLLAMA_MODEL}"
      base_url: "${OLLAMA_URL}"
      api_key: "${OLLAMA_API_KEY}"

# Use noop to test the pipeline without connecting to a real catalog.
# Replace with the sddi section below when you have catalog credentials.
cataloger:
  noop: {}

# cataloger:
#   sddi:
#     base_url: "${CATALOG_BASE_URL}"
#     api_key: "${CATALOG_API_KEY}"
#     owner_org: "${CATALOG_OWNER_ORG}"
"""


def write_example_config(path: Path) -> None:
    """Write the example YAML config to disk if it does not already exist."""
    if not path.exists():
        path.write_text(YAML_CONTENT)
        print(f"Wrote example config to {path}")
    else:
        print(f"Using existing config at {path}")


async def main() -> None:
    # Set minimal env vars so ConfigReader can resolve ${...} placeholders.
    # In production these would come from your shell environment or a .env file.
    os.environ.setdefault("STA_BASE_URL", "https://example.org/v1.1")
    os.environ.setdefault("OLLAMA_URL", "http://localhost:11434/v1")
    os.environ.setdefault("OLLAMA_MODEL", "llama3.3:70b-instruct-q4_K_M")
    os.environ.setdefault("OLLAMA_API_KEY", "ollama")

    config_path = Path(__file__).parent / "pipeline_config.yaml"
    write_example_config(config_path)

    # PipelineRunner reads, validates, and assembles the pipeline from YAML.
    from wrench.pipeline.config import PipelineRunner

    runner = PipelineRunner.from_config_file(str(config_path))
    result = await runner.run({})

    print(f"Pipeline succeeded: {result.success}")
    print(f"Run ID: {result.run_id}")


if __name__ == "__main__":
    asyncio.run(main())
