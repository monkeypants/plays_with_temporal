"""
Custom Temporal data converter with support for temporal_validation context.

This module provides a custom Pydantic data converter that automatically
adds temporal_validation=True context when deserializing Pydantic models.
This allows domain models to implement context-aware validation that can
be more permissive during Temporal serialization/deserialization.
"""

from typing import Any, Optional, Type

from pydantic import TypeAdapter
from temporalio.contrib.pydantic import (
    PydanticJSONPlainPayloadConverter,
    ToJsonOptions,
)
from temporalio.converter import (
    DataConverter,
    CompositePayloadConverter,
    DefaultPayloadConverter,
    JSONPlainPayloadConverter,
)
import temporalio.api.common.v1


class TemporalValidationPydanticConverter(PydanticJSONPlainPayloadConverter):
    """Custom Pydantic JSON converter that adds temporal_validation context.

    This converter extends the standard PydanticJSONPlainPayloadConverter
    to automatically add temporal_validation=True context when deserializing
    Pydantic models. This allows domain models to implement more permissive
    validation during Temporal operations while maintaining strict validation
    for direct instantiation.
    """

    def from_payload(
        self,
        payload: temporalio.api.common.v1.Payload,
        type_hint: Optional[Type] = None,
    ) -> Any:
        """Deserialize payload with temporal_validation context.

        This method overrides the base implementation to always add
        temporal_validation=True to the validation context. This allows
        Pydantic models to detect when they're being deserialized by
        Temporal and apply appropriate validation rules.

        Args:
            payload: The Temporal payload to deserialize
            type_hint: Optional type hint for the expected return type

        Returns:
            Deserialized object with temporal validation context applied
        """
        # Convert Optional[Type] to Type, defaulting to Any (same as original)
        _type_hint = type_hint if type_hint is not None else Any

        # Always add temporal_validation context for Pydantic model validation
        return TypeAdapter(_type_hint).validate_json(
            payload.data, context={"temporal_validation": True}
        )


class TemporalValidationPayloadConverter(CompositePayloadConverter):
    """Custom payload converter that uses temporal validation context.

    This payload converter extends CompositePayloadConverter to use our
    custom TemporalValidationPydanticConverter for JSON serialization,
    ensuring all Pydantic models get temporal_validation context.
    """

    def __init__(
        self, to_json_options: Optional[ToJsonOptions] = None
    ) -> None:
        """Initialize with custom JSON converter adding temporal context."""
        # Create our custom JSON converter with temporal validation
        json_payload_converter = TemporalValidationPydanticConverter(
            to_json_options
        )

        # Initialize CompositePayloadConverter, replacing JSON converter

        super().__init__(
            *(
                (
                    c
                    if not isinstance(c, JSONPlainPayloadConverter)
                    else json_payload_converter
                )
                for c in (
                    DefaultPayloadConverter.default_encoding_payload_converters
                )
            )
        )


def create_temporal_data_converter(
    to_json_options: Optional[ToJsonOptions] = None,
) -> DataConverter:
    """Create a data converter with temporal validation support.

    This factory function creates a DataConverter that uses our custom
    TemporalValidationPayloadConverter for serialization. This
    ensures that all Pydantic models are deserialized with the
    temporal_validation context.

    Args:
        to_json_options: Optional configuration for JSON serialization

    Returns:
        DataConverter configured with temporal validation support
    """
    return DataConverter(
        payload_converter_class=TemporalValidationPayloadConverter
    )


# Default temporal data converter with validation context support
temporal_data_converter = create_temporal_data_converter()
"""Default Temporal data converter with temporal_validation context support.

This data converter automatically adds temporal_validation=True context
when deserializing Pydantic models, allowing domain models to implement
context-aware validation rules.

Usage:
    client = Client(
        data_converter=temporal_data_converter,
        ...
    )
"""
