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
        """
        Initializes the QueryBuilder with the specified property name.

        Args:
            property_name (str): The name of the property to be used in the query.
        """
        self.property_name = property_name

    def eq(self, value) -> "FilterExpression":
        """
        Creates a filter expression for equality comparison.

        Args:
            value: The value to compare against.

        Returns:
            FilterExpression: For the equality comparison.
        """
        return FilterExpression(self.property_name, FilterOperator.EQ, value)

    def ne(self, value) -> "FilterExpression":
        """
        Creates a filter expression for the 'not equal' (NE) operator.

        Args:
            value: The value to compare against.

        Returns:
            FilterExpression: For the 'not equal' condition.
        """
        return FilterExpression(self.property_name, FilterOperator.NE, value)

    def gt(self, value: Union[int, float]) -> "FilterExpression":
        """
        Creates a filter expression for the 'greater than' (GT) operator.

        Args:
            value (Union[int, float]): The value to compare against.

        Returns:
            FilterExpression: For the 'greater than' condition.
        """
        return FilterExpression(self.property_name, FilterOperator.GT, value)

    def ge(self, value: Union[int, float]) -> "FilterExpression":
        """
        Creates a filter expression for the 'greater than or equal to' (>=) comparison.

        Args:
            value (Union[int, float]): The value to compare against.

        Returns:
            FilterExpression: For the 'greater than or equal to' comparison.
        """
        return FilterExpression(self.property_name, FilterOperator.GE, value)

    def lt(self, value: Union[int, float]) -> "FilterExpression":
        """
        Creates a filter expression for the 'less than' comparison.

        Args:
            value (Union[int, float]): The value to compare against.

        Returns:
            FilterExpression: For the 'less than' comparison.
        """
        return FilterExpression(self.property_name, FilterOperator.LT, value)

    def le(self, value: Union[int, float]) -> "FilterExpression":
        """
        Creates a 'less than or equal to' filter expression.

        Args:
            value (Union[int, float]): The value to compare against.

        Returns:
            FilterExpression: For the 'less than or equal to' condition.
        """
        return FilterExpression(self.property_name, FilterOperator.LE, value)

    def contains(self, value: str) -> "FilterExpression":
        """
        Checks if the given value is a substring of the property.

        Args:
            value (str): The substring to check for within the property.

        Returns:
            FilterExpression: A filter expression that represents the substring check.
        """
        return FilterExpression(self.property_name, FilterOperator.SUBSTRINGOF, value)

    def startswith(self, value: str) -> "FilterExpression":
        """
        Checks if the property starts with the given value.

        Args:
            value (str): The value to check if the property starts with.

        Returns:
            FilterExpression: A filter expression representing the startswith condition.
        """
        return FilterExpression(self.property_name, FilterOperator.STARTSWITH, value)

    def endswith(self, value: str) -> "FilterExpression":
        """
        Checks if the property ends with the specified value.

        Args:
            value (str): The substring to check if the property ends with.

        Returns:
            FilterExpression: A new FilterExpression object with the ENDSWITH operator.
        """
        return FilterExpression(self.property_name, FilterOperator.ENDSWITH, value)


class FilterExpression:
    def __init__(self, property_name: str, operator: FilterOperator, value):
        """
        Initializes a QueryBuilder instance.

        Args:
            property_name (str): The name of the property to filter on.
            operator (FilterOperator): The operator to use for filtering.
            value: The value to compare the property against.
        """
        self.property_name = property_name
        self.operator = operator
        self.value = value

    def __and__(self, other: "FilterExpression") -> "FilterExpression":
        """
        Combine this filter with another using AND.

        Args:
            other (FilterExpression): The other filter to combine with.

        Returns:
            FilterExpression: A new filter representing the logical AND of both.
        """
        return CombinedFilter(FilterOperator.AND, [self, other])

    def __or__(self, other: "FilterExpression") -> "FilterExpression":
        """
        Combine the current filter expression with another using the OR operator.

        Args:
            other (FilterExpression): The other filter expression to combine with.

        Returns:
            FilterExpression: A new filter expression representing the combination
            using the OR operator.
        """
        return CombinedFilter(FilterOperator.OR, [self, other])

    def __str__(self) -> str:
        """
        Returns a string representation of the query filter.

        Constructs a string representation of the query filter based on the operator
        and value. Handles function-style operators (SUBSTRINGOF, STARTSWITH, ENDSWITH)
        differently from standard operators.

        Returns:
            str: The string representation of the query filter.
        """
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
        """
        Initializes a QueryBuilder instance.

        Args:
            operator (FilterOperator): The operator to be used in the query.
            expressions (list[FilterExpression]): A list of filter expressions
                                                  to be applied.

        """
        self.operator = operator
        self.expressions = expressions

    def __str__(self) -> str:
        """
        Returns a string representation of the query expression.

        The expressions are joined by the operator's value and enclosed in parentheses.

        Returns:
            str: The string representation of the query expression.
        """
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
    """Options for SensorThings API query."""

    limit: int | None = None
    skip: int | None = None
    orderby: str | None = None
    filter: str | None = None


class Query(ABC):
    @property
    @abstractmethod
    def RESOURCE_NAME(self) -> str:
        """
        Returns the name of the resource.

        This method should be overridden in subclasses to provide the specific
        resource name.

        Returns:
            str: The name of the resource.
        """
        pass

    @property
    @abstractmethod
    def VALID_EXPANSIONS(self) -> set[str]:
        """
        Returns a set of valid expansions for the SensorThings API query.

        This method should be overridden to provide the specific valid expansions
        for the implementation.

        Returns:
            set[str]: A set of strings representing the valid expansions.
        """
        pass

    @property
    @abstractmethod
    def VALID_NESTED_EXPANSIONS(self) -> dict[str, set[str]]:
        """
        Definition of nested expansions for nested entities.

        Returns a dictionary where the keys are strings representing the names of
        entities, and the values are sets of strings representing the valid nested
        expansions for each entity.

        Returns:
            dict[str, set[str]]: A dictionary mapping entity names to sets of valid
            nested expansions.
        """
        pass

    def __init__(self):
        """
        Initializes the QueryBuilder instance.

        Attributes:
            expansions (set[str]): A set to store expansion options.
            nested_expansions (dict[str, set[str]]): A dictionary to store nested
            expansion options, initialized with keys from VALID_NESTED_EXPANSIONS
            and empty sets as values.
            options (QueryOptions): An instance of QueryOptions to store query options.
        """
        self.expansions: set[str] = set()
        self.nested_expansions: dict[str, set[str]] = {
            k: set() for k in self.VALID_NESTED_EXPANSIONS.keys()
        }
        self.options = QueryOptions()

    def expand(self, entity: str, nested_expansions: set[str] | None = None) -> "Query":
        """
        Add an entity to expand in the query.

        Args:
            entity: Name of entity to expand (e.g. "Locations", "Datastreams")
            nested_expansions: Optional set of nested entities to expand

        Raises:
            ValueError: If entity or nested expansions are invalid
        """
        if entity not in self.VALID_EXPANSIONS:
            raise ValueError(
                f"""'{entity}' is not a valid expansion for Things.
                Valid expansions are: {self.VALID_EXPANSIONS}"""
            )

        self.expansions.add(entity)

        if nested_expansions:
            if entity not in self.VALID_NESTED_EXPANSIONS:
                raise ValueError(f"'{entity}' does not support nested expansions")

            invalid_nested = nested_expansions - self.VALID_NESTED_EXPANSIONS[entity]
            if invalid_nested:
                raise ValueError(
                    f"Invalid nested expansion(s) for {entity}: {invalid_nested}. "
                    f"Valid nested expansions: {self.VALID_NESTED_EXPANSIONS[entity]}"
                )

            self.nested_expansions[entity].update(nested_expansions)

        return self

    def limit(self, n: int) -> "Query":
        """
        Sets the maximum number of records to retrieve in the query.

        Args:
            n (int): The maximum number of records to return.

        Returns:
            Query: The current query instance with the limit applied.
        """
        self.options.limit = n
        return self

    def filter(self, expression: FilterExpression) -> "Query":
        """Add a filter expression to the query."""
        self.options.filter = str(expression)
        return self

    @staticmethod
    def property(name: str) -> Filter:
        """Create a filter for a property."""
        return Filter(name)

    def build(self) -> str:
        """Build the query string."""
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
    """Query builder for Thing entities."""

    RESOURCE_NAME = "Things"
    VALID_EXPANSIONS = {"Locations", "Datastreams"}
    VALID_NESTED_EXPANSIONS = {"Datastreams": {"Sensor", "ObservedProperty"}}


class DatastreamQuery(Query):
    """Query builder for Datastream entities."""

    RESOURCE_NAME = "Datastreams"
    VALID_EXPANSIONS = {"Sensor", "ObservedProperty", "Thing", "Observations"}
    VALID_NESTED_EXPANSIONS = {"Thing": {"Locations"}}
