from collections import deque

import openai
from pydantic import BaseModel

from wrench.log import logger
from wrench.utils.prompt_manager import PromptManager

SEED_PROMPT = PromptManager.get_prompt("generate_seed_topics.txt")


class Topic(BaseModel):
    name: str
    description: str
    subtopics: list["Topic"]
    keywords: list[str]

    def __hash__(self):
        """Use topic name as unique identifier for hashing."""
        return hash(self.name)

    def __eq__(self, other):
        """Topics are equal if their names as the same."""
        if not isinstance(other, Topic):
            return False
        return self.name == other.name

    def __repr__(self):
        return f"<Topic: {self.name}>"

    def bfs(self) -> list["Topic"]:
        queue: deque[Topic] = deque([self])
        visited = set()  # use set for O(1) lookups
        result: list[Topic] = []
        while queue:
            topic = queue.popleft()
            if topic not in visited:
                visited.add(topic)
                # maintain order
                result.append(topic)

                queue.extend(topic.subtopics)
        return result

    def is_leaf(self) -> bool:
        return not bool(self.subtopics)


class TopicTree(BaseModel):
    topics: list[Topic]

    def visualize(self):
        self.build_graph(self.topics)

    def build_graph(self, topics: list[Topic], indent=""):
        for topic in topics:
            print(indent + topic.name)
            print(indent + topic.description)
            print(indent + " ".join(topic.keywords))
            if topic.subtopics:
                self.build_graph(topic.subtopics, indent + "\t")

    def build_ancestor_map(self):
        pass


class LLMTopicHierarchyGenerator:
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

    def generate_seed_topics(self, keywords: dict[str, list]) -> TopicTree:
        completion = self.llm_client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": SEED_PROMPT,
                },
                {
                    "role": "user",
                    "content": f"{str(keywords)}",
                },
            ],
            response_format=TopicTree,
            temperature=0.1,
        )

        root_topics = completion.choices[0].message.parsed

        if root_topics and root_topics.topics:
            self.logger.info("Generated topics: %s", root_topics.topics)

            return root_topics
        else:
            self.logger.warning("LLM did not generate any topics")
            raise ValueError("LLM failed to generate well-structured topics")
