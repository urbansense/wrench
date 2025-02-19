from abc import ABC, abstractmethod
from enum import Enum
from typing import Union
from urllib.parse import urlencode

from pydantic import BaseModel


class FilterOperator(Enum):
    EQ = "eq"  # equals
    NE = "ne"  # not equals
    GT = "gt"  # greater than
    GE = "ge"  # greater than or equals
    LT = "lt"  # less than
    LE = "le"  # less than or equals
    AND = "and"
    OR = "or"
    NOT = "not"
    SUBSTRINGOF = "substringof"  # text contains
    STARTSWITH = "startswith"
    ENDSWITH = "endswith"


class Filter:
    def __init__(self, property_name: str):
        self.property_name = property_name

    def eq(self, value) -> "FilterExpression":
        return FilterExpression(self.property_name, FilterOperator.EQ, value)

    def ne(self, value) -> "FilterExpression":
        return FilterExpression(self.property_name, FilterOperator.NE, value)

    def gt(self, value: Union[int, float]) -> "FilterExpression":
        return FilterExpression(self.property_name, FilterOperator.GT, value)

    def ge(self, value: Union[int, float]) -> "FilterExpression":
        return FilterExpression(self.property_name, FilterOperator.GE, value)

    def lt(self, value: Union[int, float]) -> "FilterExpression":
        return FilterExpression(self.property_name, FilterOperator.LT, value)

    def le(self, value: Union[int, float]) -> "FilterExpression":
        return FilterExpression(self.property_name, FilterOperator.LE, value)

    def contains(self, value: str) -> "FilterExpression":
        return FilterExpression(self.property_name, FilterOperator.SUBSTRINGOF, value)

    def startswith(self, value: str) -> "FilterExpression":
        return FilterExpression(self.property_name, FilterOperator.STARTSWITH, value)

    def endswith(self, value: str) -> "FilterExpression":
        return FilterExpression(self.property_name, FilterOperator.ENDSWITH, value)


class FilterExpression:
    def __init__(self, property_name: str, operator: FilterOperator, value):
        self.property_name = property_name
        self.operator = operator
        self.value = value

    def __and__(self, other: "FilterExpression") -> "FilterExpression":
        return CombinedFilter(FilterOperator.AND, [self, other])

    def __or__(self, other: "FilterExpression") -> "FilterExpression":
        return CombinedFilter(FilterOperator.OR, [self, other])

    def __str__(self) -> str:
        # Handle function-style operators differently
        if self.operator in {
            FilterOperator.SUBSTRINGOF,
            FilterOperator.STARTSWITH,
            FilterOperator.ENDSWITH,
        }:
            if isinstance(self.value, str):
                return f"{self.operator.value}({self.property_name}, '{self.value}')"
            return f"{self.operator.value}({self.property_name}, {self.value})"

        # Standard operators
        if isinstance(self.value, str):
            return f"{self.property_name} {self.operator.value} '{self.value}'"
        return f"{self.property_name} {self.operator.value} {self.value}"


class CombinedFilter(FilterExpression):
    def __init__(self, operator: FilterOperator, expressions: list[FilterExpression]):
        self.operator = operator
        self.expressions = expressions

    def __str__(self) -> str:
        joined = f" {self.operator.value} ".join(str(exp) for exp in self.expressions)
        return f"({joined})"


class EntityType(Enum):
    THING = "Things"
    DATASTREAM = "Datastreams"
    LOCATION = "Locations"
    HISTORICAL_LOCATION = "HistoricalLocations"
    SENSOR = "Sensors"
    OBSERVATION = "Observations"
    OBSERVED_PROPERTY = "ObservedProperties"
    FEATURES_OF_INTEREST = "FeaturesOfInterest"


class QueryOptions(BaseModel):
    """Options for SensorThings API query"""

    limit: int | None = None
    skip: int | None = None
    orderby: str | None = None
    filter: str | None = None


class Query(ABC):
    @property
    @abstractmethod
    def RESOURCE_NAME(self) -> str:
        pass

    @property
    @abstractmethod
    def VALID_EXPANSIONS(self) -> set[str]:
        pass

    @property
    @abstractmethod
    def VALID_NESTED_EXPANSIONS(self) -> dict[str, set[str]]:
        pass

    def __init__(self):
        self.expansions: set[str] = set()
        self.nested_expansions: dict[str, set[str]] = {
            k: set() for k in self.VALID_NESTED_EXPANSIONS.keys()
        }
        self.options = QueryOptions()

    def expand(self, entity: str, nested_expansions: set[str] | None = None) -> "Query":
        """
        Add an entity to expand in the query

        Args:
            entity: Name of entity to expand (e.g. "Locations", "Datastreams")
            nested_expansions: Optional set of nested entities to expand

        Raises:
            ValueError: If entity or nested expansions are invalid
        """
        if entity not in self.VALID_EXPANSIONS:
            raise ValueError(
                f"'{entity}' is not a valid expansion for Things. Valid expansions are: {self.VALID_EXPANSIONS}"
            )

        self.expansions.add(entity)

        if nested_expansions:
            if entity not in self.VALID_NESTED_EXPANSIONS:
                raise ValueError(f"'{entity}' does not support nested expansions")

            invalid_nested = nested_expansions - self.VALID_NESTED_EXPANSIONS[entity]
            if invalid_nested:
                raise ValueError(
                    f"Invalid nested expansion(s) for {entity}: {invalid_nested}. "
                    f"Valid nested expansions are: {self.VALID_NESTED_EXPANSIONS[entity]}"
                )

            self.nested_expansions[entity].update(nested_expansions)

        return self

    def limit(self, n: int) -> "Query":
        self.options.limit = n
        return self

    def filter(self, expression: FilterExpression) -> "Query":
        """Add a filter expression to the query"""
        self.options.filter = str(expression)
        return self

    @staticmethod
    def property(name: str) -> Filter:
        """Create a filter for a property"""
        return Filter(name)

    def build(self) -> str:
        """Build the query string"""
        params = {}

        # Handle expansions
        if self.expansions:
            expand_parts = []
            for exp in self.expansions:
                if exp in self.nested_expansions and self.nested_expansions[exp]:
                    nested = f"{exp}($expand={','.join(self.nested_expansions[exp])})"
                    expand_parts.append(nested)
                else:
                    expand_parts.append(exp)
            params["$expand"] = ",".join(expand_parts)

        # Add other query options
        if self.options.limit:
            params["$top"] = self.options.limit
        if self.options.skip:
            params["$skip"] = self.options.skip
        if self.options.orderby:
            params["$orderby"] = self.options.orderby
        if self.options.filter:
            params["$filter"] = self.options.filter

        param_url = urlencode(params)

        return "{resource_name}?{param_url}".format(
            resource_name=self.RESOURCE_NAME, param_url=param_url
        )


class ThingQuery(Query):
    """Query builder for Thing entities"""

    RESOURCE_NAME = "Things"
    VALID_EXPANSIONS = {"Locations", "Datastreams"}
    VALID_NESTED_EXPANSIONS = {"Datastreams": {"Sensor", "ObservedProperty"}}


class DatastreamQuery(Query):
    """Query builder for Datastream entities"""

    RESOURCE_NAME = "Datastreams"
    VALID_EXPANSIONS = {"Sensor", "ObservedProperty", "Thing", "Observations"}
    VALID_NESTED_EXPANSIONS = {"Thing": {"Locations"}}
