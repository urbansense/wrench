import pytest

from wrench.utils.sanitization import sanitize_ckan_name, validate_ckan_name


class TestSanitizeCkanName:
    @pytest.mark.parametrize(
        "input_name, expected",
        [
            ("Air Quality Sensors", "air_quality_sensors"),
            ("Temperature & Humidity", "temperature_humidity"),
            ("simple", "simple"),
            ("already_valid", "already_valid"),
            ("hyphen-name", "hyphen_name"),
        ],
        ids=[
            "spaces_to_underscores",
            "ampersand_removed",
            "lowercase_passthrough",
            "underscore_passthrough",
            "hyphen_to_underscore",
        ],
    )
    def test_basic_sanitization(self, input_name, expected):
        assert sanitize_ckan_name(input_name) == expected

    @pytest.mark.parametrize(
        "input_name, expected",
        [
            ("Hello World!!", "hello_world"),
            ("test@email.com", "test_email_com"),
            ("price $100", "price_100"),
            ("a/b/c", "a_b_c"),
            ("key=value", "key_value"),
            ("data (raw)", "data_raw"),
            ("<tag>", "tag"),
            ("a+b", "a_b"),
        ],
        ids=[
            "exclamation_marks",
            "at_sign_and_dots",
            "dollar_sign",
            "slashes",
            "equals",
            "parentheses",
            "angle_brackets",
            "plus_sign",
        ],
    )
    def test_special_characters(self, input_name, expected):
        assert sanitize_ckan_name(input_name) == expected

    @pytest.mark.parametrize(
        "input_name, expected",
        [
            ("", "unnamed_item"),
            (None, "unnamed_item"),
            (123, "unnamed_item"),
            ("!!!@@@", "unnamed_item"),
        ],
        ids=[
            "empty_string",
            "none_value",
            "non_string",
            "only_special_chars",
        ],
    )
    def test_fallback_on_empty(self, input_name, expected):
        assert sanitize_ckan_name(input_name) == expected

    def test_custom_fallback_prefix(self):
        assert sanitize_ckan_name("", fallback_prefix="service") == "service_item"
        assert sanitize_ckan_name("@@@", fallback_prefix="group") == "group_item"

    @pytest.mark.parametrize(
        "input_name",
        [
            "multiple   spaces",
            "tabs\there",
            "newlines\nhere",
        ],
        ids=["multiple_spaces", "tabs", "newlines"],
    )
    def test_whitespace_collapsed(self, input_name):
        result = sanitize_ckan_name(input_name)
        assert "  " not in result
        assert "\t" not in result
        assert "\n" not in result

    def test_unicode_stripped(self):
        result = sanitize_ckan_name("sensors_group_1")
        assert result == "sensors_group_1"

        result = sanitize_ckan_name("\u6e2c\u8a66 Sensors (Group #1)")
        assert result == "sensors_group_1"

    @pytest.mark.parametrize(
        "input_name, expected",
        [
            ("1_starts_with_number", "unnamed_1_starts_with_number"),
            ("42things", "unnamed_42things"),
        ],
        ids=["numeric_prefix_with_underscore", "numeric_prefix_direct"],
    )
    def test_numeric_start_gets_prefix(self, input_name, expected):
        assert sanitize_ckan_name(input_name) == expected

    def test_max_length_truncation(self):
        long_name = "a" * 200
        result = sanitize_ckan_name(long_name, max_length=50)
        assert len(result) <= 50

    def test_truncation_strips_trailing_separators(self):
        name = "a" * 49 + "_b"
        result = sanitize_ckan_name(name, max_length=50)
        assert not result.endswith("_")
        assert not result.endswith("-")

    def test_consecutive_underscores_collapsed(self):
        assert sanitize_ckan_name("a___b") == "a_b"
        assert sanitize_ckan_name("a---b") == "a_b"
        assert sanitize_ckan_name("a_-_b") == "a_b"

    def test_leading_trailing_separators_stripped(self):
        assert sanitize_ckan_name("_leading") == "leading"
        assert sanitize_ckan_name("trailing_") == "trailing"
        assert sanitize_ckan_name("-both-") == "both"

    def test_docstring_examples(self):
        assert sanitize_ckan_name("Air Quality Sensors") == "air_quality_sensors"
        assert sanitize_ckan_name("Temperature & Humidity") == "temperature_humidity"
        assert sanitize_ckan_name("!!!@@@") == "unnamed_item"


class TestValidateCkanName:
    @pytest.mark.parametrize(
        "name",
        [
            "air_quality_sensors",
            "simple",
            "with-hyphens",
            "mixed_and-both",
            "abc123",
        ],
        ids=[
            "underscores",
            "plain_alpha",
            "hyphens",
            "mixed_separators",
            "alphanumeric",
        ],
    )
    def test_valid_names(self, name):
        is_valid, error = validate_ckan_name(name)
        assert is_valid is True
        assert error is None

    @pytest.mark.parametrize(
        "name, expected_substring",
        [
            ("", "empty"),
            (None, "empty"),
        ],
        ids=["empty_string", "none_value"],
    )
    def test_empty_or_none(self, name, expected_substring):
        is_valid, error = validate_ckan_name(name)
        assert is_valid is False
        assert expected_substring in error.lower()

    def test_uppercase_invalid(self):
        is_valid, error = validate_ckan_name("HasUpperCase")
        assert is_valid is False
        assert "invalid characters" in error.lower()

    def test_special_chars_invalid(self):
        is_valid, error = validate_ckan_name("has spaces")
        assert is_valid is False

    def test_numeric_start_invalid(self):
        is_valid, error = validate_ckan_name("123abc")
        assert is_valid is False
        assert "number" in error.lower()

    @pytest.mark.parametrize(
        "name",
        ["_leading", "trailing_", "-leading", "trailing-"],
        ids=[
            "leading_underscore",
            "trailing_underscore",
            "leading_hyphen",
            "trailing_hyphen",
        ],
    )
    def test_leading_trailing_separators_invalid(self, name):
        is_valid, error = validate_ckan_name(name)
        assert is_valid is False
        assert "start or end" in error.lower()
