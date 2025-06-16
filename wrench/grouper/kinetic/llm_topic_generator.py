import json
import os
from collections import defaultdict
from pathlib import Path

import openai

from wrench.log import logger
from wrench.models import Device
from wrench.utils.prompt_manager import PromptManager

from .models import Cluster, Topic, TopicList

SEED_PROMPT = PromptManager.get_prompt("generate_seed_topics.txt")
USER_PROMPT = PromptManager.get_prompt("user_prompt.txt")


class LLMTopicGenerator:
    def __init__(
        self,
        llm_client: openai.OpenAI,
        model: str,
    ):
        self.llm_client = llm_client
        self.model = model
        self.topic_model = None
        self.merged_topics: list[int] = []
        self.logger = logger.getChild(self.__class__.__name__)
        self.cache_dir = Path(".kineticache")
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_topics = self.cache_dir / "topics.json"

    def generate_seed_topics(
        self, clusters: list[Cluster]
    ) -> dict[Topic, list[Device]]:
        topics = self._check_cache(clusters)

        mappings: dict[Topic, list[Device]] = defaultdict(list)

        for c in clusters:
            for topic in topics:
                if topic.cluster_id.lower() == c.cluster_id:
                    mappings[topic].extend(c._devices)

        return mappings

    def _check_cache(self, clusters: list[Cluster]) -> list[Topic]:
        if self.is_cached():
            return self._load_topics()

        user_prompts = USER_PROMPT.format(
            keywords_and_docs="\n\n".join([str(c) for c in clusters])
        )

        completion = self.llm_client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": SEED_PROMPT,
                },
                {
                    "role": "user",
                    "content": user_prompts,
                },
            ],
            response_format=TopicList,
            temperature=0.1,
        )

        root_topics = completion.choices[0].message.parsed
        if root_topics and root_topics.topics:
            self.logger.info("Generated topics: %s", root_topics.topics)

            self._save_topics(root_topics.topics)

            return root_topics.topics

    def _save_topics(self, topics: list[Topic]):
        with open(self.cache_topics, "w") as f:
            json.dump([t.model_dump(mode="json") for t in topics], f)

    def _load_topics(self):
        with open(self.cache_topics, "r") as f:
            topics: dict = json.load(f)

        return [Topic.model_validate(t) for t in topics]

    def is_cached(self) -> bool:
        return os.path.isfile(self.cache_topics)
