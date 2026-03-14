import pytest

from wrench.metadataenricher.sensorthings.querybuilder import (
    CombinedFilter,
    DatastreamQuery,
    Filter,
    FilterExpression,
    FilterOperator,
    ThingQuery,
)


class TestFilter:
    @pytest.mark.parametrize(
        "method, operator",
        [
            ("eq", FilterOperator.EQ),
            ("ne", FilterOperator.NE),
            ("gt", FilterOperator.GT),
            ("ge", FilterOperator.GE),
            ("lt", FilterOperator.LT),
            ("le", FilterOperator.LE),
            ("contains", FilterOperator.SUBSTRINGOF),
            ("startswith", FilterOperator.STARTSWITH),
            ("endswith", FilterOperator.ENDSWITH),
        ],
    )
    def test_operator_returns_correct_filter_expression(self, method, operator):
        f = Filter("name")
        expr = getattr(f, method)("test")
        assert isinstance(expr, FilterExpression)
        assert expr.operator == operator
        assert expr.property_name == "name"
        assert expr.value == "test"


class TestFilterExpression:
    @pytest.mark.parametrize(
        "operator, value, expected",
        [
            (FilterOperator.EQ, "hello", "name eq 'hello'"),
            (FilterOperator.NE, "world", "name ne 'world'"),
            (FilterOperator.EQ, 42, "name eq 42"),
            (FilterOperator.GT, 10, "name gt 10"),
            (FilterOperator.GE, 5.5, "name ge 5.5"),
            (FilterOperator.LT, 100, "name lt 100"),
            (FilterOperator.LE, 0, "name le 0"),
        ],
        ids=[
            "eq_string",
            "ne_string",
            "eq_int",
            "gt_int",
            "ge_float",
            "lt_int",
            "le_int",
        ],
    )
    def test_standard_operator_str(self, operator, value, expected):
        expr = FilterExpression("name", operator, value)
        assert str(expr) == expected

    @pytest.mark.parametrize(
        "operator, value, expected",
        [
            (
                FilterOperator.SUBSTRINGOF,
                "temp",
                "substringof(name, 'temp')",
            ),
            (
                FilterOperator.STARTSWITH,
                "Air",
                "startswith(name, 'Air')",
            ),
            (
                FilterOperator.ENDSWITH,
                "Sensor",
                "endswith(name, 'Sensor')",
            ),
            (
                FilterOperator.SUBSTRINGOF,
                42,
                "substringof(name, 42)",
            ),
        ],
        ids=[
            "substringof_string",
            "startswith_string",
            "endswith_string",
            "substringof_int",
        ],
    )
    def test_function_style_operator_str(self, operator, value, expected):
        expr = FilterExpression("name", operator, value)
        assert str(expr) == expected

    def test_and_operator_returns_combined_filter(self):
        left = Filter("a").eq(1)
        right = Filter("b").eq(2)
        combined = left & right
        assert isinstance(combined, CombinedFilter)
        assert combined.operator == FilterOperator.AND

    def test_or_operator_returns_combined_filter(self):
        left = Filter("a").eq(1)
        right = Filter("b").eq(2)
        combined = left | right
        assert isinstance(combined, CombinedFilter)
        assert combined.operator == FilterOperator.OR


class TestCombinedFilter:
    def test_and_str(self):
        left = Filter("a").eq(1)
        right = Filter("b").eq(2)
        combined = CombinedFilter(FilterOperator.AND, [left, right])
        assert str(combined) == "(a eq 1 and b eq 2)"

    def test_or_str(self):
        left = Filter("a").eq("x")
        right = Filter("b").eq("y")
        combined = CombinedFilter(FilterOperator.OR, [left, right])
        assert str(combined) == "(a eq 'x' or b eq 'y')"

    def test_nested_combination(self):
        a = Filter("x").eq(1)
        b = Filter("y").eq(2)
        c = Filter("z").eq(3)
        inner = a & b
        outer = inner | c
        assert str(outer) == "((x eq 1 and y eq 2) or z eq 3)"

    def test_multiple_or_expressions(self):
        exprs = [Filter("@iot.id").eq(str(i)) for i in range(3)]
        combined = CombinedFilter(FilterOperator.OR, exprs)
        result = str(combined)
        assert result == "(@iot.id eq '0' or @iot.id eq '1' or @iot.id eq '2')"


class TestThingQuery:
    def test_resource_name(self):
        assert ThingQuery.RESOURCE_NAME == "Things"

    def test_build_empty_query(self):
        query = ThingQuery()
        result = query.build()
        assert result == "Things?"

    def test_build_with_filter(self):
        query = ThingQuery()
        query.filter(Filter("@iot.id").eq("1"))
        result = query.build()
        assert "Things?" in result
        assert "%40iot.id" in result or "@iot.id" in result

    def test_build_with_limit(self):
        query = ThingQuery()
        query.limit(10)
        result = query.build()
        # urlencode encodes $ as %24
        assert "%24top=10" in result

    def test_build_with_expansion(self):
        query = ThingQuery()
        query.expand("Locations")
        result = query.build()
        assert "Locations" in result
        assert "%24expand" in result

    def test_build_with_nested_expansion(self):
        query = ThingQuery()
        query.expand("Datastreams", {"Sensor"})
        result = query.build()
        assert "Datastreams" in result
        assert "Sensor" in result
        assert "%24expand" in result

    def test_expand_invalid_entity_raises(self):
        query = ThingQuery()
        with pytest.raises(ValueError, match="not a valid expansion"):
            query.expand("InvalidEntity")

    def test_expand_invalid_nested_raises(self):
        query = ThingQuery()
        with pytest.raises(ValueError, match="Invalid nested"):
            query.expand("Datastreams", {"InvalidNested"})

    def test_expand_no_nested_support_raises(self):
        query = ThingQuery()
        with pytest.raises(ValueError, match="does not support nested"):
            query.expand("Locations", {"Something"})

    def test_chaining(self):
        query = ThingQuery()
        result = query.expand("Locations").limit(5).build()
        assert "Locations" in result
        assert "%24top=5" in result

    def test_property_static_method(self):
        f = ThingQuery.property("name")
        assert isinstance(f, Filter)
        assert f.property_name == "name"


class TestDatastreamQuery:
    def test_resource_name(self):
        assert DatastreamQuery.RESOURCE_NAME == "Datastreams"

    def test_valid_expansions(self):
        assert "Sensor" in DatastreamQuery.VALID_EXPANSIONS
        assert "ObservedProperty" in DatastreamQuery.VALID_EXPANSIONS
        assert "Thing" in DatastreamQuery.VALID_EXPANSIONS
        assert "Observations" in DatastreamQuery.VALID_EXPANSIONS

    def test_build_with_nested_expansion(self):
        query = DatastreamQuery()
        query.expand("Thing", {"Locations"})
        result = query.build()
        assert "Thing" in result
        assert "Locations" in result
