from abc import ABC, abstractmethod

import openai
from pydantic import BaseModel

from wrench.log import logger
from wrench.utils.config import LLMConfig
from wrench.utils.prompt_manager import PromptManager


class ConsolidatedTopic(BaseModel):
    """Represents a consolidated topic after merging."""

    name: str
    description: str
    original_topic_ids: list[int]


class TopicConsolidationResult(BaseModel):
    """Result of topic consolidation with merged topics."""

    topics: list[ConsolidatedTopic]


class BaseTopicNamer(ABC):
    """Abstract base class for topic naming strategies."""

    @abstractmethod
    def name_topics(self, topics_data: list[dict]) -> list[dict]:
        """Generate names and descriptions for multiple topics, with merging.

        Args:
            topics_data: List of topic data with id, keywords, and word_distribution

        Returns:
            List of consolidated topic dictionaries with name, description, and
            original_topic_ids
        """
        pass


class KeywordTopicNamer(BaseTopicNamer):
    """Simple topic namer based on top keywords."""

    def name_topics(self, topics_data: list[dict]) -> list[dict]:
        """Generate topic names from top keywords without merging."""
        consolidated_topics = []

        for topic_data in topics_data:
            topic_id = topic_data["id"]
            keywords = topic_data["keywords"]

            if not keywords:
                name = f"Unknown Topic {topic_id}"
                description = "No keywords available"
            else:
                # Use top 3 keywords for naming
                top_keywords = keywords[:3]
                name = " & ".join(top_keywords).title()
                description = f"Topic characterized by: {', '.join(keywords)}"

            consolidated_topics.append(
                {
                    "name": name,
                    "description": description,
                    "original_topic_ids": [topic_id],
                }
            )

        return consolidated_topics


class LLMTopicNamer(BaseTopicNamer):
    """LLM-based topic namer for more semantic naming."""

    def __init__(self, llm_config: LLMConfig, temperature: float = 0.3):
        """Initialize LLM topic namer.

        Args:
            llm_config: LLM configuration
            temperature: Generation temperature
        """
        self.client = openai.OpenAI(
            base_url=llm_config.base_url, api_key=llm_config.api_key
        )
        self.model = llm_config.model
        self.temperature = temperature
        self.logger = logger.getChild(self.__class__.__name__)

    def name_topics(self, topics_data: list[dict]) -> list[dict]:
        """Generate topic names using LLM with merging capability."""
        try:
            # Prepare topics data for the prompt
            topics_text = []
            for topic_data in topics_data:
                topic_id = topic_data["id"]
                keywords = topic_data["keywords"]
                word_distribution = topic_data.get("word_distribution", {})

                # Create weighted keyword string
                weighted_keywords = []
                for word, weight in sorted(
                    word_distribution.items(), key=lambda x: x[1], reverse=True
                )[:10]:
                    weighted_keywords.append(f"{word} ({weight:.3f})")

                topic_text = f"""
Topic ID: {topic_id}
Top Keywords: {", ".join(keywords[:10])}
Weighted Keywords: {"; ".join(weighted_keywords)}
"""
                topics_text.append(topic_text)

            # Load prompts using PromptManager
            system_prompt = PromptManager.get_prompt("lda_topic_naming_system.txt")
            user_prompt = PromptManager.get_prompt("lda_topic_naming_user.txt")

            formatted_user_prompt = user_prompt.format(
                topics_data="\n".join(topics_text)
            )

            response = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": formatted_user_prompt},
                ],
                response_format=TopicConsolidationResult,
                temperature=self.temperature,
            )

            result = response.choices[0].message.parsed
            if not result or not result.topics:
                raise RuntimeError("LLM returned no structured response")

            # Convert to expected format
            consolidated_topics = []
            for topic in result.topics:
                consolidated_topics.append(
                    {
                        "name": topic.name,
                        "description": topic.description,
                        "original_topic_ids": topic.original_topic_ids,
                    }
                )

            return consolidated_topics

        except Exception as e:
            self.logger.warning(
                "LLM topic naming failed: %s. Falling back to keyword naming.", str(e)
            )
            # Fallback to keyword naming
            fallback_namer = KeywordTopicNamer()
            return fallback_namer.name_topics(topics_data)


def create_topic_namer(
    use_llm: bool,
    llm_config: LLMConfig = None,
    temperature: float = 0.3,
) -> BaseTopicNamer:
    """Factory function to create appropriate topic namer.

    Args:
        use_llm: Whether to use LLM for naming
        llm_config: LLM configuration (required if use_llm=True)
        temperature: Temperature for LLM generation

    Returns:
        Topic namer instance
    """
    if use_llm:
        if llm_config is None:
            raise ValueError("LLM config required when use_llm=True")
        return LLMTopicNamer(llm_config, temperature)
    else:
        return KeywordTopicNamer()
