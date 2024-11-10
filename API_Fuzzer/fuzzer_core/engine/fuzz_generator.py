"""
Responsible for generating Fuzz values to test the API
"""
import re
import base64
from enum import Enum
import random
from typing import Optional, List, Literal, Any
import hypothesis.strategies as st


# TODO:
#  - FIX STRING GENERATION + returning strategies ( maybe return lists instead)   (done)
#  - Number generation (int and other formats) (exlusivemin /max) (multiple of)    (done)
#  - Take oneOf, anyOf, allOf, not into consideration (done)
#  - Arrays (don't forget mixed types) (done)
#  - Objects (done)


class ValuesIncluded(Enum):
    VALID_ONLY = "valid"
    INVALID_ONLY = "invalid"
    BOTH = "both"


class BaseFuzzGenerator:
    def __init__(self, include_values: ValuesIncluded):
        self.include_values = include_values

    @staticmethod
    def convert_js_regex(js_pattern: str) -> re.Pattern:
        """

        :param js_pattern:
        :return:
        """

        # Map of JavaScript regex flags to Python regex flags
        flag_map = {
            'i': re.IGNORECASE,  # Case-insensitive
            'm': re.MULTILINE,  # Multiline mode
            's': re.DOTALL  # Dot matches all (including newlines)
        }

        flags = 0
        pattern = js_pattern

        # Check for inline flags like (?i) and extract them
        match = re.match(r'^\(\?([ims]+)\)', pattern)
        if match:
            for flag in match.group(1):
                flags |= flag_map.get(flag, 0)
            pattern = pattern[match.end():]  # Remove the inline flag part from the pattern

        # Return the compiled pattern with appropriate flags
        return re.compile(pattern, flags)

    ################### INTEGERS & NUMBERS ####################

    def _generate_numeric_valid_values(self, strategy, minimum, maximum, multiple_of):
        if minimum is not None:
            strategy = strategy.filter(lambda x: x >= minimum)
        if maximum is not None:
            strategy = strategy.filter(lambda x: x <= maximum)
        if multiple_of is not None:
            strategy = strategy.filter(lambda x: x % multiple_of == 0.0)
        return strategy

    def _generate_numeric_invalid_values(self, strategy, minimum=None, maximum=None, multiple_of=None):
        invalid_strategies = []
        if minimum is not None:
            invalid_strategies.append(strategy.filter(lambda x: x < minimum))
        if maximum is not None:
            invalid_strategies.append(strategy.filter(lambda x: x > maximum))
        if multiple_of is not None:
            invalid_strategies.append(strategy.filter(lambda x: x % multiple_of != 0.0))
        return st.one_of(*invalid_strategies) if invalid_strategies else st.nothing()

    def _generate_numeric_values(self, strategy, minimum, maximum, multiple_of):
        if self.include_values == ValuesIncluded.VALID_ONLY:
            return self._generate_numeric_valid_values(strategy, minimum, maximum, multiple_of)
        elif self.include_values == ValuesIncluded.INVALID_ONLY:
            return self._generate_numeric_invalid_values(strategy, minimum, maximum, multiple_of)
        else:
            return st.one_of(self._generate_numeric_valid_values(strategy, minimum, maximum, multiple_of),
                             self._generate_numeric_invalid_values(strategy, minimum, maximum, multiple_of))

    def generate_number(self, minimum=None, maximum=None, multiple_of=None):
        strategy = st.one_of(
            st.integers(),
            st.floats(allow_nan=False, allow_infinity=False)
        )
        return self._generate_numeric_values(strategy, minimum, maximum, multiple_of)

    def generate_float(self, minimum=None, maximum=None, multiple_of=None):
        strategy = st.floats(allow_nan=False, allow_infinity=False, width=32)
        return self._generate_numeric_values(strategy, minimum, maximum, multiple_of)

    def generate_double(self, minimum=None, maximum=None, multiple_of=None):
        strategy = st.floats(allow_nan=False, allow_infinity=False, width=64)
        return self._generate_numeric_values(strategy, minimum, maximum, multiple_of)

    def generate_integer(self, minimum=None, maximum=None, multiple_of=None):
        strategy = st.integers()
        return self._generate_numeric_values(strategy, minimum, maximum, multiple_of)

    def generate_int32(self, minimum=None, maximum=None, multiple_of=None):
        min_val = max(minimum, -2 ** 31) if minimum is not None else -2 ** 31
        max_val = min(maximum, 2 ** 31 - 1) if maximum is not None else 2 ** 31 - 1
        strategy = st.integers(min_value=min_val, max_value=max_val)
        return self._generate_numeric_values(strategy, min_val, max_val, multiple_of)

    def generate_int64(self, minimum=None, maximum=None, multiple_of=None):
        min_val = max(minimum, -2 ** 63) if minimum is not None else -2 ** 63
        max_val = min(maximum, 2 ** 63 - 1) if maximum is not None else 2 ** 63 - 1
        strategy = st.integers(min_value=min_val, max_value=max_val)
        return self._generate_numeric_values(strategy, min_val, max_val, multiple_of)

    ################################################################################

    # ##################################### STRINGS ################################
    def _generate_valid_string(self, min_length=None, max_length=None, string_format=None, pattern=None, enum=None):

        if enum:
            return random.choice(enum)

        strategy = st.text(min_size=min_length, max_size=max_length)

        if string_format:
            strategy = self._apply_string_format(strategy, string_format)

        if pattern:
            strategy = strategy.filter(lambda x: re.match(pattern, x))

        return strategy

    def _apply_string_format(self, strategy, string_format):
        format_strategy = self._get_string_format_strategy(string_format)
        return st.one_of(strategy, format_strategy)

    def _get_string_format_strategy(self, string_format):
        match string_format:
            case "date":
                return st.dates().map(str)
            case "date-time":
                return st.datetimes().map(lambda dt: dt.isoformat())
            case "password":
                return st.text()
            case "byte":
                return st.binary().map(lambda b: b.decode('utf-8', errors='ignore'))
            case "binary":
                return st.binary()
            case "email":
                return st.emails()
            case "uuid":
                return st.uuids().map(str)
            case "hostname":
                return st.from_regex(
                    r"^(([a-zA-Z]|[a-zA-Z][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z]|[A-Za-z][A-Za-z0-9\-]*[A-Za-z0-9])$")
            case "ipv4":
                return st.ip_addresses(v=4).map(str)
            case "ipv6":
                return st.ip_addresses(v=6).map(str)
            case _:
                return st.text()

    def _generate_invalid_string(self, min_length=None, max_length=None, string_format=None, pattern=None, enum=None):
        invalid_strategy = st.text()

        if enum is not None:
            invalid_strategy.filter(lambda x: x not in enum)

        if min_length is not None:
            invalid_strategy.filter(lambda x: len(x) < min_length)
        if max_length is not None:
            invalid_strategy.filter(lambda x: len(x) > max_length)
        if string_format:
            invalid_strategy.filter(lambda x: not re.match(self._get_invalid_format_regex(string_format), x))
        if pattern:
            invalid_strategy.filter(lambda x: not re.match(pattern, x))

        return invalid_strategy

    def _get_invalid_format_regex(self, string_format):
        # TODO: check if the regexes work

        match string_format:
            case "date":
                return r"^\d{4}-\d{2}-\d{2}$"  # YYYY-MM-DD
            case "date-time":
                return r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"  # YYYY-MM-DDTHH:MM:SSZ
            case "email":
                return r"^[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*@(?:[a-z0-9](?:[a-z0-9-]*[" \
                       r"a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$ "
            case "uuid":
                return r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
            case "uri":
                return
            case "hostname":
                return r"^(([a-zA-Z]|[a-zA-Z][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z]|[A-Za-z][A-Za-z0-9\-]*[A-Za-z0-9])$"
            case "ipv4":
                return r"(?:\b|^)((?:(?:(?:\d)|(?:\d{2})|(?:1\d{2})|(?:2[0-4]\d)|(?:25[0-5]))\.){3}(?:(?:(?:\d)|(?:\d{2})|(" \
                       r"?:1\d{2})|(?:2[0-4]\d)|(?:25[0-5]))))(?:\b|$)"
            case "ipv6":
                return r"^(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1," \
                       r"6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1," \
                       r"4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1," \
                       r"2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1," \
                       r"7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0," \
                       r"1}[0-9]){0,1}[0-9])\\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1," \
                       r"4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))$ "
            case _:
                return r".*"  # Match any string

    def generate_string(self, min_length=3, max_length=20, string_format=None, pattern=None, enum=None):
        valid_strategy = self._generate_valid_string(min_length=min_length, max_length=max_length, string_format=string_format,
                                                     pattern=pattern, enum=enum)

        if self.include_values == ValuesIncluded.VALID_ONLY:
            return valid_strategy
        elif self.include_values == ValuesIncluded.INVALID_ONLY:
            return self._generate_invalid_string(min_length=min_length, max_length=max_length, string_format=string_format,
                                                 pattern=pattern, enum=enum)
        else:  # Both valid and invalid values
            invalid_strategy = self._generate_invalid_string(min_length=min_length, max_length=max_length,
                                                             string_format=string_format, pattern=pattern, enum=enum)
            return st.one_of(valid_strategy, invalid_strategy)

    ################################################################################

    # ################################## BOOLEAN ###################################
    def generate_bool(self, default: bool = None):
        if default:
            if self.include_values == ValuesIncluded.VALID_ONLY:
                return st.just(default)
            if self.include_values == ValuesIncluded.INVALID_ONLY:
                return st.just(not default)
        return st.booleans()

    ################################################################################

    # ################################### OBJECT ###################################
    def generate_random_strategy(self):
        return st.one_of(
            self.generate_string(), self.generate_number(), self.generate_bool(),
            self.generate_integer(), self.generate_int32(), self.generate_int64(),
            st.lists(st.text(), min_size=1),
            st.dictionaries(st.text(min_size=1), st.text(), min_size=1)
        )

    def generate_object(self, props_strategies, additional_props: bool, min_properties: int = None, max_properties: int = None,
                        req_props: list = None):
        valid_strategy = self._generate_valid_object(min_properties=min_properties, max_properties=max_properties,
                                                     props_strategies=props_strategies, req_props=req_props,
                                                     additional_props=additional_props
                                                     )

        invalid_strategy = self._generate_invalid_object(min_properties=min_properties, max_properties=max_properties,
                                                         props_strategies=props_strategies, req_props=req_props,
                                                         additional_props=additional_props
                                                         )

        if self.include_values == ValuesIncluded.VALID_ONLY:
            return valid_strategy
        elif self.include_values == ValuesIncluded.INVALID_ONLY:
            return invalid_strategy
        else:
            return st.one_of(valid_strategy, invalid_strategy)

    def _generate_valid_object(self, props_strategies, additional_props: bool, min_properties: int = None,
                               max_properties: int = None, req_props: list = None):
        req_props = req_props or []
        required_props_strategy = {prop: props_strategies[prop] for prop in req_props}
        optional_props_strategy = {prop: props_strategies[prop] for prop in props_strategies if prop not in req_props}
        optional_props_keys = list(optional_props_strategy.keys())

        def build_object(required, optional):
            obj = {**required, **optional}
            if additional_props:
                additional_keys = [key for key in props_strategies if key not in obj]
                for key in additional_keys:
                    obj[key] = self.generate_random_strategy()
            return obj

        base_strategy = st.fixed_dictionaries(required_props_strategy).flatmap(
            lambda required: st.dictionaries(
                keys=st.sampled_from(optional_props_keys),
                values=st.sampled_from(list(optional_props_strategy.values())),
                min_size=max(0, min_properties - len(req_props)) if min_properties is not None else 0,
                max_size=max_properties - len(req_props) if max_properties is not None else None
            ).map(lambda optional: build_object(required, optional))
        )

        return base_strategy

    def _generate_invalid_object(self, props_strategies: dict, additional_props: bool, min_properties: int = None,
                                 max_properties: int = None, req_props: list = None):
        req_props = req_props or []
        invalid_strategies = []

        def add_additional_props(obj):
            additional_props_strategy = st.dictionaries(
                keys=st.text(min_size=1),
                values=self.generate_random_strategy(),
                min_size=1,
                max_size=max_properties - len(obj) if max_properties is not None else None
            )
            return additional_props_strategy.map(lambda additional: {**obj, **additional})

        for prop in req_props:
            required_props_strategy = {k: v for k, v in props_strategies.items() if k != prop}
            missing_prop_strategy = st.fixed_dictionaries(required_props_strategy).flatmap(add_additional_props)
            invalid_strategies.append(missing_prop_strategy)

        if min_properties is not None and min_properties > 0:
            fewer_props_strategy = st.fixed_dictionaries(
                {k: props_strategies[k] for k in list(props_strategies.keys())[:min_properties - 1]}
            ).flatmap(add_additional_props)
            invalid_strategies.append(fewer_props_strategy)

        if max_properties is not None and max_properties > len(req_props):
            extra_props_strategy = st.fixed_dictionaries(
                {k: props_strategies[k] for k in list(props_strategies.keys())[:max_properties + 1]}
            ).flatmap(add_additional_props)
            invalid_strategies.append(extra_props_strategy)

        return st.one_of(invalid_strategies)

    def generate_array(self, min_items=None, max_items=None, unique_items=None, items_strategies=None):
        if self.include_values == ValuesIncluded.VALID_ONLY:
            return self._generate_valid_array(min_items, max_items, unique_items, items_strategies)
        elif self.include_values == ValuesIncluded.INVALID_ONLY:
            return self._generate_invalid_array(min_items, max_items, unique_items, items_strategies)
        else:
            return st.one_of

    def _generate_valid_array(self, items_strategies, min_items=None, max_items=None, unique_items=None):

        # Ensure we have a valid strategy for the items
        if not items_strategies or not all(isinstance(strategy, st.SearchStrategy) for strategy in items_strategies):
            raise ValueError("items_strategies must be provided and hypothesis strategies")


        # Generate the base array strategy
        base_strategy = st.lists(
            elements=st.one_of(*items_strategies),
            min_size=min_items,
            max_size=max_items,
            unique=unique_items
        )

        return base_strategy

    def _generate_invalid_array(self, items_strategies: list[st.SearchStrategy], min_items=None, max_items=None,
                                unique_items=None):
        if not items_strategies:
            raise ValueError("items_strategies must be provided")

        invalid_strategies = []

        # Invalid due to fewer items than min_items
        if min_items is not None and min_items > 0:
            invalid_strategies.append(
                st.lists(elements=st.one_of(*items_strategies), min_size=0, max_size=min_items - 1)
            )

        # Invalid due to more items than max_items
        if max_items is not None:
            invalid_strategies.append(
                st.lists(elements=st.one_of(*items_strategies), min_size=max_items + 1)
            )

        # Invalid due to duplicate items when unique_items is True
        if unique_items:
            invalid_strategies.append(
                st.lists(elements=st.one_of(*items_strategies), min_size=min_items or 0, max_size=max_items, unique=False).filter(
                    lambda x: len(x) != len(set(x)))
            )

        return st.one_of(*invalid_strategies)


class OpenAPIFuzzGenerator(BaseFuzzGenerator):
    def __init__(self, include_values: ValuesIncluded):
        super().__init__(include_values=include_values)
        pass

    @staticmethod
    def find_bounds_string(definition: dict[str, Any]) -> tuple:
        """

        :param definition:
        :return:
        """
        return definition.get('minLength', None), definition.get('maxLength', None)

    @staticmethod
    def find_bounds_number(definition: dict[str, Any]) -> tuple:
        """
        If the schema specifies a maximum and minimum for the numeric value,
        record it.
        By default, maximums and minimums in OpenAPI are not exclusive

        :param definition: dict containing the definition
        :return:
        """

        min_value, max_value = None, None
        if 'minimum' in definition:
            min_value = definition['minimum']
            if definition.get('exclusiveMinimum'):
                min_value += 1.0

        if 'maximum' in definition:
            max_value = definition['maximum']
            if definition.get('exclusiveMaximum'):
                max_value -= 1.0
        return min_value, max_value

    def parse_and_generate_strategy(self, definition):
        if "type" in definition:
            match definition["type"]:
                case "string":
                    string_format = definition.get("format", None)
                    min_length, max_length = self.find_bounds_string(definition=definition)
                    enum = definition.get("enum", None)
                    pattern = OpenAPIFuzzGenerator.convert_js_regex(js_pattern=definition["pattern"]) if \
                        definition.get("pattern", None) else None
                    return self.generate_string(min_length=min_length, max_length=max_length, string_format=string_format,
                                                pattern=pattern, enum=enum)

                case "number":
                    min_value, max_value = self.find_bounds_number(definition=definition)
                    multiple_of = definition.get("multipleOf", None)
                    if definition.get("format", None):
                        if definition["format"] == "float":
                            return self.generate_float(minimum=min_value, maximum=max_value, multiple_of=multiple_of)
                        if definition["format"] == "double":
                            return self.generate_double(minimum=min_value, maximum=max_value, multiple_of=multiple_of)
                    return self.generate_number(minimum=min_value, maximum=max_value, multiple_of=multiple_of)

                case "integer":
                    min_value, max_value = self.find_bounds_number(definition=definition)
                    multiple_of = definition.get("multipleOf", None)
                    if definition.get("format", None):
                        if definition["format"] == "int32":
                            return self.generate_int32(minimum=min_value, maximum=max_value, multiple_of=multiple_of)
                        if definition["format"] == "int64":
                            return self.generate_int64(minimum=min_value, maximum=max_value, multiple_of=multiple_of)
                    return self.generate_integer(minimum=min_value, maximum=max_value, multiple_of=multiple_of)
                case "boolean":
                    default = definition.get("default", None)
                    return self.generate_bool(default=default)
                case "array":
                    min_items = definition.get("minItems", None)
                    max_items = definition.get("maxItems", None)
                    unique_items = definition.get("uniqueItems", None)
                    if definition.get("items", {}) == {}:
                        return self.generate_random_strategy()
                    items_strategies = self.parse_and_generate_strategy(definition=definition.get("items", {}))
                    return self.generate_array(min_items=min_items, max_items=max_items, unique_items=unique_items,
                                               items_strategies=items_strategies)

                case "object":
                    min_properties = definition.get("minProperties", None)
                    max_properties = definition.get("maxProperties", None)
                    props_strategies = {}
                    if definition.get("properties", None):
                        for prop_key, prop_value in definition["properties"].items():
                            props_strategies[prop_key] = self.parse_and_generate_strategy(definition=prop_value)

                    return self.generate_object(min_properties=min_properties, max_properties=max_properties,
                                                props_strategies=props_strategies,
                                                req_props=definition.get("required", None),
                                                additional_props=definition.get("additionalProperties", False))

        elif "oneOf" in definition:
            types_strategies = []
            for data_type in definition["oneOf"]:
                types_strategies.append(self.parse_and_generate_strategy(data_type))
            return st.one_of(types_strategies)

        elif "anyOf" in definition:
            return self.parse_and_generate_strategy(self.choose_random_objects(definition["anyOf"]))

        elif "allOf" in definition:
            merged_objects_def = self.merge_objects_def(definition["allOf"])
            return self.parse_and_generate_strategy(merged_objects_def)

        elif "not" in definition:
            if isinstance(definition["not"], list):
                return st.one_of()
            if isinstance(definition["not"], dict):
                invalid_strat = self.parse_and_generate_strategy(definition["not"])
                # valid_strat=
                if self.include_values == ValuesIncluded.INVALID_ONLY:
                    return invalid_strat
                elif self.include_values == ValuesIncluded.VALID_ONLY:
                    pass

    def handle_not(self, definition):
        constraints = {
            'integer': ['forma', 'minimum', 'maximum', 'exclusiveMinimum', 'exclusiveMaximum', 'multipleOf'],
            'number': ['forma', 'minimum', 'maximum', 'exclusiveMinimum', 'exclusiveMaximum', 'multipleOf'],
            'string': ['minLength', 'maxLength', 'pattern', 'format'],
            'array': ['minItems', 'maxItems', 'uniqueItems', 'items'],
            'object': ['minProperties', 'maxProperties', 'required', 'properties', 'additionalProperties']
        }
        type_strats = {
            'number': self.generate_number(), "integer": self.generate_integer, 'string': self.generate_string,
            'array': st.lists(st.text(), min_size=1), 'object': st.dictionaries(st.text(min_size=1), st.text(), min_size=1)

        }

        invalid_strats = []
        for defn in definition or [definition]:
            invalid_strats.append(self.parse_and_generate_strategy(defn))

        if self.include_values == ValuesIncluded.INVALID_ONLY:
            return st.one_of(invalid_strats)

        valid_strats = []
        types_constraints = {}

        # Extracting the valid types for "not" type specification
        for type_def in definition or [definition]:
            if type_def["type"]:
                type_strats.pop(type_def["type"])
                if type_def["type"] in constraints:
                    types_constraints[type_def["type"]] = {key: type_def[key] for key in constraints[type_def["type"]] if
                                                           key in type_def}
        # generating valid type strategies
        for key, value in type_strats.items():
            valid_strats.append(value)
        for type_constraints in types_constraints:
            match type_constraints:
                case "integer", "number":
                    strat = None
                    if type_constraints.get("format", None):
                        if type_constraints["format"] == "int32":
                            strat = self.generate_int32()
                        if type_constraints["format"] == "int64":
                            strat = self.generate_int64()
                    else:
                        strat = st.integers()
                    minimum, maximum = self.find_bounds_number(type_constraints)
                    valid_strats.append(
                        self._generate_numeric_invalid_values(strategy=strat, minimum=minimum,
                                                              maximum=maximum,
                                                              multiple_of=type_constraints.get("multipleOf", None)))
                case "number":
                    strat = None
                    if type_constraints.get("format", None):
                        if type_constraints["format"] == "float":
                            strat = self.generate_float()
                        if type_constraints["format"] == "double":
                            strat = self.generate_double()
                    else:
                        strat = st.one_of(st.integers(), st.floats(allow_nan=False, allow_infinity=False))

                    minimum, maximum = self.find_bounds_number(type_constraints)
                    valid_strats.append(
                        self._generate_numeric_invalid_values(strategy=strat, minimum=type_constraints.get("minimum", None),
                                                              maximum=type_constraints.get("maximum", None),
                                                              multiple_of=type_constraints.get("multipleOf", None)))
                case "string":
                    pattern = OpenAPIFuzzGenerator.convert_js_regex(js_pattern=definition["pattern"]) if \
                        definition.get("pattern", None) else None

                    valid_strats.append(self._generate_invalid_string(min_length=type_constraints.get("minLength"),
                                                                      max_length=type_constraints.get("maxLength"),
                                                                      string_format=type_constraints.get("format"),
                                                                      pattern=pattern))
                case "array":
                    if definition.get("items", {}) == {}:
                        return self.generate_random_strategy()
                    items_strategies = self.parse_and_generate_strategy(definition=definition.get("items", {}))
                    valid_strats.append(self.generate_array(min_items=definition.get("minItems", None),
                                                            max_items=definition.get("maxItems", None),
                                                            unique_items=definition.get("uniqueItems", None),
                                                            items_strategies=items_strategies)
                                        )
                case "object":
                    props_strategies = {}
                    if definition.get("properties", None):
                        for prop_key, prop_value in definition["properties"].items():
                            props_strategies[prop_key] = self.parse_and_generate_strategy(definition=prop_value)

                    return self.generate_object(min_properties=definition.get("minProperties", None),
                                                max_properties=definition.get("maxProperties", None),
                                                props_strategies=props_strategies,
                                                req_props=definition.get("required", None),
                                                additional_props=definition.get("additionalProperties", False))

            if self.include_values == ValuesIncluded.VALID_ONLY:
                return st.one_of(valid_strats)

            if self.include_values == ValuesIncluded.BOTH:
                return st.one_of([*invalid_strats, *valid_strats])

    def merge_objects_def(self, objects_defs):
        merged_def = {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": True
        }

        for obj_def in objects_defs:
            # Merge properties
            if "properties" in obj_def:
                merged_def["properties"].update(obj_def["properties"])

            # Merge required fields
            if "required" in obj_def:
                merged_def["required"].extend(obj_def["required"])

            # Handle additionalProperties
            if "additionalProperties" in obj_def and not obj_def["additionalProperties"]:
                merged_def["additionalProperties"] = False

        # Remove duplicate required fields
        if merged_def["required"]:
            merged_def["required"] = list(set(merged_def["required"]))

        return merged_def

    def choose_random_objects(self, object_defs):
        num_objects = len(object_defs)
        # Randomly choose a number between 0 and num_objects
        num_to_choose = random.randint(0, num_objects)
        # Randomly select the specified number of objects from the list
        chosen_objects = random.sample(object_defs, num_to_choose)
        return chosen_objects





if __name__=='__main__':

    # Initialize the FuzzGenerator object
    fuzz = BaseFuzzGenerator(include_values=ValuesIncluded.VALID_ONLY)

    # Expanded test cases for each function
    test_cases = [
        # No constraints (should generate any number within the data type's range)
        {"minimum": None, "maximum": None, "multiple_of": None},

        # Range limits
        {"minimum": 10, "maximum": 100, "multiple_of": None},
        {"minimum": -100, "maximum": 100, "multiple_of": None},
        {"minimum": 1, "maximum": 1, "multiple_of": None},  # Edge case: single value range

        # Only multiple_of defined
        {"minimum": None, "maximum": None, "multiple_of": 5},
        {"minimum": None, "maximum": None, "multiple_of": 0.1},  # Edge case: decimal multiples

        # All constraints defined with integers
        {"minimum": 10, "maximum": 100, "multiple_of": 10},
        {"minimum": -50, "maximum": 50, "multiple_of": 7},

        # All constraints defined with decimals
        {"minimum": -10.5, "maximum": 10.5, "multiple_of": 0.5},

        # Edge case: minimum greater than maximum (should ideally handle gracefully or skip)
        {"minimum": 100, "maximum": 10, "multiple_of": None},
    ]


    # Function to run and display results for each test case
    def run_test_cases():
        print("Testing FuzzGenerator methods with expanded test cases:")

        # Each function will iterate through each test case
        for case in test_cases:
            print(f"\nTesting with parameters: {case}")

            try:
                print("generate_number:", fuzz.generate_number(**case).example())
            except Exception as e:
                print("generate_number raised an exception:", e)

            try:
                print("generate_float:", fuzz.generate_float(**case).example())
            except Exception as e:
                print("generate_float raised an exception:", e)

            try:
                print("generate_double:", fuzz.generate_double(**case).example())
            except Exception as e:
                print("generate_double raised an exception:", e)

            try:
                print("generate_integer:", fuzz.generate_integer(**case).example())
            except Exception as e:
                print("generate_integer raised an exception:", e)

            try:
                print("generate_int32:", fuzz.generate_int32(**case).example())
            except Exception as e:
                print("generate_int32 raised an exception:", e)

            try:
                print("generate_int64:", fuzz.generate_int64(**case).example())
            except Exception as e:
                print("generate_int64 raised an exception:", e)


    # Run all tests
    run_test_cases()