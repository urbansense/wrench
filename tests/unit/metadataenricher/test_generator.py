from unittest.mock import MagicMock, patch

import pytest

from wrench.metadataenricher.generator import Content, ContentGenerator
from wrench.models import CommonMetadata, Group
from wrench.utils.config import LLMConfig


@pytest.fixture()
def mock_openai():
    with patch("wrench.metadataenricher.generator.OpenAI") as MockOpenAI:
        mock_client = MagicMock()
        MockOpenAI.return_value = mock_client
        yield mock_client


@pytest.fixture()
def generator(mock_openai):
    config = LLMConfig(
        base_url="https://api.example.com/v1",
        api_key="test-key",
        model="gpt-4",
    )
    return ContentGenerator(config)


@pytest.fixture()
def sample_group(make_device):
    d1 = make_device(id="d-1", name="Temp Sensor", datastreams={"Temperature"})
    d2 = make_device(id="d-2", name="Humidity Sensor", datastreams={"Humidity"})
    return Group(name="Weather", devices=[d1, d2])


@pytest.fixture()
def service_metadata():
    return CommonMetadata(
        identifier="test-service",
        title="Test Service",
        description="A test service",
        endpoint_urls=["https://api.example.com"],
        source_type="sensorthings",
    )


class TestContentModel:
    def test_content_creation(self):
        content = Content(name="Weather Group", description="Monitors weather")
        assert content.name == "Weather Group"
        assert content.description == "Monitors weather"

    def test_content_serialization(self):
        content = Content(name="Test", description="Desc")
        data = content.model_dump()
        assert data == {"name": "Test", "description": "Desc"}


class TestGenerateGroupContent:
    def test_returns_content_object(
        self, generator, mock_openai, sample_group, service_metadata
    ):
        # Set up mock response
        mock_parsed = Content(name="Weather Monitoring", description="Weather sensors")
        mock_message = MagicMock()
        mock_message.parsed = mock_parsed
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_openai.beta.chat.completions.parse.return_value = mock_response

        result = generator.generate_group_content(
            group=sample_group,
            context={"service_metadata": service_metadata},
        )
        assert isinstance(result, Content)
        assert result.name == "Weather Monitoring"
        assert result.description == "Weather sensors"

    def test_calls_openai_with_correct_model(
        self, generator, mock_openai, sample_group, service_metadata
    ):
        mock_parsed = Content(name="Test", description="Test")
        mock_message = MagicMock()
        mock_message.parsed = mock_parsed
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_openai.beta.chat.completions.parse.return_value = mock_response

        generator.generate_group_content(
            group=sample_group,
            context={"service_metadata": service_metadata},
        )

        call_kwargs = mock_openai.beta.chat.completions.parse.call_args
        assert call_kwargs.kwargs["model"] == "gpt-4"
        assert call_kwargs.kwargs["temperature"] == 0

    def test_missing_service_metadata_raises(self, generator, sample_group):
        with pytest.raises(ValueError, match="service_metadata is required"):
            generator.generate_group_content(
                group=sample_group,
                context={},
            )

    def test_llm_returns_none_raises(
        self, generator, mock_openai, sample_group, service_metadata
    ):
        mock_message = MagicMock()
        mock_message.parsed = None
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_openai.beta.chat.completions.parse.return_value = mock_response

        with pytest.raises(RuntimeError, match="LLM returned no messages"):
            generator.generate_group_content(
                group=sample_group,
                context={"service_metadata": service_metadata},
            )

    def test_prompt_contains_group_info(
        self, generator, mock_openai, sample_group, service_metadata
    ):
        mock_parsed = Content(name="Test", description="Test")
        mock_message = MagicMock()
        mock_message.parsed = mock_parsed
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_openai.beta.chat.completions.parse.return_value = mock_response

        generator.generate_group_content(
            group=sample_group,
            context={"service_metadata": service_metadata},
        )

        call_kwargs = mock_openai.beta.chat.completions.parse.call_args
        messages = call_kwargs.kwargs["messages"]
        user_message = messages[1]["content"]
        assert "Weather" in user_message
        assert "Test Service" in user_message
