"""
Generic type guard validation system for debugging serialization issues.

This module provides utilities for validating that runtime values match their
expected types, with detailed diagnostics for common serialization issues
like Pydantic models being deserialized as dictionaries.

The system can work with any function by introspecting type hints and
providing clear error messages when types don't match expectations.
"""

import inspect
import logging
from functools import wraps
from typing import (
    Any,
    Dict,
    List,
    Union,
    Callable,
    get_type_hints,
    get_origin,
    get_args,
)
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class TypeValidationError(TypeError):
    """Raised when type validation fails with detailed diagnostics."""


def validate_type(
    value: Any,
    expected_type: Any,
    context_name: str = "value",
    allow_none: bool = False,
) -> None:
    """
    Validate that a value matches the expected type with detailed diagnostics.

    Args:
        value: The actual value to validate
        expected_type: The expected type (from type hints)
        context_name: Name for error messages (e.g., "parameter 'queries'")
        allow_none: Whether None values are acceptable

    Raises:
        TypeValidationError: With detailed diagnosis if type doesn't match
    """
    # Handle None values
    if value is None:
        if allow_none:
            return
        raise TypeValidationError(
            f"{context_name}: Expected {_format_type(expected_type)}, "
            f"got None"
        )

    # Get the origin type for generic types (List[X] -> list, Dict -> dict)
    origin_type = get_origin(expected_type)
    type_args = get_args(expected_type)

    # If no origin, it's a simple type
    if origin_type is None:
        _validate_simple_type(value, expected_type, context_name)
    else:
        _validate_generic_type(
            value, expected_type, origin_type, type_args, context_name
        )


def _validate_simple_type(
    value: Any, expected_type: Any, context_name: str
) -> None:
    """Validate simple (non-generic) types."""
    actual_type = type(value)

    # Check if it's the expected type
    if isinstance(value, expected_type):
        return

    # Special handling for Pydantic models vs dicts (serialization issue)
    if (
        inspect.isclass(expected_type)
        and issubclass(expected_type, BaseModel)
        and isinstance(value, dict)
    ):
        _raise_pydantic_dict_error(value, expected_type, context_name)

    # Generic type mismatch
    raise TypeValidationError(
        f"{context_name}: Type mismatch\n"
        f"  Expected: {_format_type(expected_type)}\n"
        f"  Actual: {actual_type.__name__}\n"
        f"  Value: {_format_value(value)}"
    )


def _validate_generic_type(
    value: Any,
    expected_type: Any,
    origin_type: Any,
    type_args: tuple,
    context_name: str,
) -> None:
    """Validate generic types like List[X], Dict[K,V], etc."""

    # Check the container type first
    if not isinstance(value, origin_type):
        raise TypeValidationError(
            f"{context_name}: Container type mismatch\n"
            f"  Expected container: {origin_type.__name__}\n"
            f"  Actual container: {type(value).__name__}\n"
            f"  Expected full type: {_format_type(expected_type)}\n"
            f"  Value: {_format_value(value)}"
        )

    # Validate contents based on container type
    if origin_type is list:
        _validate_list_contents(value, type_args, context_name)
    elif origin_type is dict:
        _validate_dict_contents(value, type_args, context_name)
    elif origin_type is Union:
        _validate_union_type(value, type_args, context_name)


def _validate_list_contents(
    value: List[Any], type_args: tuple, context_name: str
) -> None:
    """Validate contents of a list."""
    if not type_args:
        return  # List without type args, can't validate contents

    element_type = type_args[0]

    for i, element in enumerate(value):
        try:
            validate_type(element, element_type, f"{context_name}[{i}]")
        except TypeValidationError as e:
            # Re-raise with additional context
            raise TypeValidationError(
                f"List element validation failed:\n{str(e)}"
            ) from e


def _validate_dict_contents(
    value: Dict[Any, Any], type_args: tuple, context_name: str
) -> None:
    """Validate contents of a dictionary."""
    if len(type_args) < 2:
        return  # Dict without full type args, can't validate contents

    key_type, value_type = type_args[0], type_args[1]

    for key, val in value.items():
        # Validate key type
        try:
            validate_type(key, key_type, f"{context_name} key '{key}'")
        except TypeValidationError as e:
            raise TypeValidationError(
                f"Dictionary key validation failed:\n{str(e)}"
            ) from e

        # Validate value type
        try:
            validate_type(val, value_type, f"{context_name}['{key}']")
        except TypeValidationError as e:
            raise TypeValidationError(
                f"Dictionary value validation failed:\n{str(e)}"
            ) from e


def _validate_union_type(
    value: Any, type_args: tuple, context_name: str
) -> None:
    """Validate Union types (including Optional)."""
    # Try each type in the union
    for union_type in type_args:
        try:
            allow_none = union_type is type(None)
            validate_type(
                value, union_type, context_name, allow_none=allow_none
            )
            return  # If any type matches, we're good
        except TypeValidationError:
            continue  # Try the next type

    # None of the union types matched
    type_names = [_format_type(t) for t in type_args]
    raise TypeValidationError(
        f"{context_name}: Value doesn't match any type in Union\n"
        f"  Expected one of: {', '.join(type_names)}\n"
        f"  Actual: {type(value).__name__}\n"
        f"  Value: {_format_value(value)}"
    )


def _raise_pydantic_dict_error(
    value: dict, expected_type: type, context_name: str
) -> None:
    """Raise a detailed error for Pydantic model vs dict issues."""
    dict_keys = list(value.keys())

    # Try to identify if this looks like a serialized Pydantic model
    model_fields = []
    if hasattr(expected_type, "model_fields"):
        model_fields = list(expected_type.model_fields.keys())

    matching_fields = [k for k in dict_keys if k in model_fields]

    error_msg = (
        f"SERIALIZATION ISSUE DETECTED: {context_name} is dict instead of "
        f"{expected_type.__name__}!\n"
        f"  Expected Type: {expected_type.__name__}\n"
        f"  Expected Module: {expected_type.__module__}\n"
        f"  Actual Type: dict\n"
        f"  Dict Keys: {dict_keys}\n"
    )

    if model_fields:
        error_msg += (
            f"  Expected Model Fields: {model_fields}\n"
            f"  Matching Fields: {matching_fields}\n"
            f"  Missing Fields: "
            f"{[f for f in model_fields if f not in dict_keys]}\n"
            f"  Extra Fields: "
            f"{[k for k in dict_keys if k not in model_fields]}\n"
        )

    error_msg += (
        f"  Sample Dict Content: {_format_value(value, max_items=3)}\n"
        f"  This indicates a Temporal/serialization issue where a Pydantic "
        f"model\n"
        f"  was serialized correctly but deserialized as a plain "
        f"dictionary.\n"
        f"  Check your data converter configuration and type hints."
    )

    logger.error(
        "Pydantic serialization issue detected",
        extra={
            "context_name": context_name,
            "expected_type": expected_type.__name__,
            "expected_module": expected_type.__module__,
            "actual_type": "dict",
            "dict_keys": dict_keys,
            "model_fields": model_fields,
            "matching_fields": matching_fields,
            "dict_sample": {k: v for k, v in list(value.items())[:3]},
        },
    )

    raise TypeValidationError(error_msg)


def _format_type(type_hint: Any) -> str:
    """Format a type hint for display in error messages."""
    if hasattr(type_hint, "__name__"):
        return str(type_hint.__name__)
    return str(type_hint)


def _format_value(value: Any, max_items: int = 5) -> str:
    """Format a value for display in error messages."""
    if isinstance(value, dict):
        if len(value) <= max_items:
            return str(value)
        else:
            items = list(value.items())[:max_items]
            return f"{dict(items)}... ({len(value)} total items)"
    elif isinstance(value, (list, tuple)):
        if len(value) <= max_items:
            return str(value)
        else:
            return f"{value[:max_items]}... ({len(value)} total items)"
    else:
        return repr(value)


def validate_parameter_types(
    **expected_types: Any,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to validate function parameters against their expected types.

    Usage:
        @validate_parameter_types(queries=Dict[str, KnowledgeServiceQuery])
        def my_function(self, queries):
            # parameters are validated before function runs
            pass

    Or automatically from type hints:
        @validate_parameter_types()
        def my_function(self, queries: Dict[str, KnowledgeServiceQuery]):
            # type hints are used automatically
            pass
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get type hints if no explicit types provided
            types_to_check = expected_types
            if not types_to_check:
                try:
                    types_to_check = get_type_hints(func)
                except Exception as e:
                    logger.warning(
                        f"Could not get type hints for {func.__name__}: {e}"
                    )
                    return func(*args, **kwargs)

            # Get parameter names
            sig = inspect.signature(func)
            param_names = list(sig.parameters.keys())

            # Validate positional arguments
            for i, (param_name, arg_value) in enumerate(
                zip(param_names, args)
            ):
                if param_name in types_to_check and param_name != "self":
                    try:
                        validate_type(
                            arg_value,
                            types_to_check[param_name],
                            f"parameter '{param_name}'",
                        )
                    except TypeValidationError:
                        logger.error(
                            f"Parameter validation failed in {func.__name__}",
                            extra={
                                "function": func.__name__,
                                "parameter": param_name,
                                "parameter_index": i,
                            },
                        )
                        raise

            # Validate keyword arguments
            for param_name, arg_value in kwargs.items():
                if param_name in types_to_check:
                    try:
                        validate_type(
                            arg_value,
                            types_to_check[param_name],
                            f"parameter '{param_name}'",
                        )
                    except TypeValidationError:
                        logger.error(
                            f"Parameter validation failed in {func.__name__}",
                            extra={
                                "function": func.__name__,
                                "parameter": param_name,
                            },
                        )
                        raise

            return func(*args, **kwargs)

        return wrapper

    return decorator


def guard_check(
    value: Any, expected_type: Any, context_name: str = "value"
) -> None:
    """
    Simple guard check function for manual validation.

    Usage:
        guard_check(queries, Dict[str, KnowledgeServiceQuery], "queries")
        guard_check(document, Document, "document")
    """
    try:
        validate_type(value, expected_type, context_name)
        logger.debug(f"Type validation passed for {context_name}")
    except TypeValidationError:
        logger.error(f"Guard check failed for {context_name}")
        raise
