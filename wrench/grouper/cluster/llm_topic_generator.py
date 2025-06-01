from collections import defaultdict

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

    def generate_seed_topics(
        self, clusters: list[Cluster]
    ) -> dict[Topic, list[Device]]:
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

            mappings: dict[Topic, list[Device]] = defaultdict(list)

            for c in clusters:
                for topic in root_topics.topics:
                    if topic.cluster_id.lower() == c.cluster_id:
                        mappings[topic].extend(c._devices)

            return mappings
        else:
            self.logger.warning("LLM did not generate any topics")
            raise ValueError("LLM failed to generate well-structured topics")
