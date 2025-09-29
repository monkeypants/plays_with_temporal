"""
Runtime validation utilities for ensuring architectural contracts and data
integrity.

This module provides functions to validate:

- Repository implementations against their defined Protocols using @runtime_checkable.
- Dictionary data against Pydantic domain models.
- Pydantic model instances to ensure their internal state is valid.

It leverages Python's built-in `isinstance()` with `@runtime_checkable`
for robust and idiomatic protocol validation, and Pydantic for
comprehensive data validation. The goal is to catch configuration and
data errors early at critical application boundaries.
"""

from typing import Type, TypeVar, Callable, Any
from pydantic import BaseModel, ValidationError
import logging

logger = logging.getLogger(__name__)

P = TypeVar("P")


class RepositoryValidationError(Exception):
    """Raised when repository contract validation fails"""

    pass


class DomainValidationError(Exception):
    """Raised when domain model validation fails"""

    pass


def validate_repository_protocol(
    repository: object, protocol: Type[P]
) -> None:
    """
    Validate that a repository implementation satisfies a protocol contract.

    Uses Python's built-in isinstance() with @runtime_checkable for robust,
    idiomatic protocol validation.

    Args:
        repository: The repository implementation to validate
        protocol: The protocol class to validate against

    Raises:
        RepositoryValidationError: If validation fails

    Example:
        >>> from sample.repos.minio.payment import MinioPaymentRepository
        >>> from sample.repositories import PaymentRepository
        >>> repo = MinioPaymentRepository()
        >>> validate_repository_protocol(repo, PaymentRepository)
    """
    logger.debug(
        "Validating repository protocol",
        extra={
            "repository_type": type(repository).__name__,
            "protocol_name": protocol.__name__,
        },
    )

    if not isinstance(repository, protocol):
        error_message = (
            f"Repository {type(repository).__name__} does not implement "
            f"{protocol.__name__} protocol. Missing or incorrect methods."
        )

        logger.error(
            "Repository protocol validation failed",
            extra={
                "repository_type": type(repository).__name__,
                "protocol_name": protocol.__name__,
            },
        )

        raise RepositoryValidationError(error_message)  # pragma: no cover

    logger.info(
        "Repository protocol validation passed",
        extra={
            "repository_type": type(repository).__name__,
            "protocol_name": protocol.__name__,
        },
    )


def ensure_repository_protocol(repository: object, protocol: Type[P]) -> P:
    """
    Validate and return a repository with proper type annotation.

    This provides both runtime validation and static type checking benefits.

    Args:
        repository: The repository implementation to validate
        protocol: The protocol class to validate against

    Returns:
        The validated repository (type checker knows it satisfies the
        protocol)

    Raises:
        RepositoryValidationError: If validation fails

    Example:
        >>> from sample.repos.minio.payment import MinioPaymentRepository
        >>> from sample.repositories import PaymentRepository
        >>> repo = MinioPaymentRepository()
        >>> validated_repo = ensure_repository_protocol(
        ...     repo, PaymentRepository
        ... )
        >>> # Type checker now knows validated_repo satisfies
        >>> # PaymentRepository
    """
    validate_repository_protocol(repository, protocol)
    return repository  # type: ignore[return-value]


def validate_file_upload_security(
    data: bytes, declared_content_type: str, filename: str
) -> None:
    """
    Validate file upload security constraints.

    This function provides additional security validation beyond
    what's enforced in the FileUploadArgs domain model.

    Args:
        data: File content bytes
        declared_content_type: Content type declared by client
        filename: Original filename

    Raises:
        ValueError: If security validation fails
    """
    # Additional filename security checks
    if filename.startswith("."):
        raise ValueError("Hidden files (starting with '.') are not allowed")

    # Check for executable file extensions
    dangerous_extensions = {
        ".exe",
        ".bat",
        ".cmd",
        ".com",
        ".scr",
        ".pif",
        ".vbs",
        ".js",
        ".jar",
        ".sh",
        ".ps1",
        ".msi",
        ".deb",
        ".rpm",
        ".dmg",
    }

    file_ext = filename.lower().split(".")[-1] if "." in filename else ""
    if f".{file_ext}" in dangerous_extensions:
        raise ValueError(
            f"File extension '.{file_ext}' is not allowed for security "
            f"reasons"
        )

    # Check for suspicious file content patterns
    if len(data) > 0:
        # Check for executable signatures
        executable_signatures = [
            b"MZ",  # Windows PE
            b"\x7fELF",  # Linux ELF
            b"\xca\xfe\xba\xbe",  # Java class file
            b"PK\x03\x04",  # ZIP (could contain executables)
        ]

        for sig in executable_signatures:
            if data.startswith(sig) and declared_content_type not in [
                "application/zip",
                "application/octet-stream",
            ]:
                raise ValueError(
                    f"File appears to be executable but declared as "
                    f"{declared_content_type}"
                )


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe storage.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename safe for storage
    """
    import os
    import re

    # Remove path components
    sanitized = os.path.basename(filename.strip())

    # Replace dangerous characters with underscores
    sanitized = re.sub(r'[<>:"/\\|?*]', "_", sanitized)

    # Remove control characters
    sanitized = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", sanitized)

    # Ensure reasonable length
    if len(sanitized) > 255:
        name, ext = os.path.splitext(sanitized)
        max_name_len = 255 - len(ext)
        sanitized = name[:max_name_len] + ext

    # Ensure not empty
    if not sanitized:
        sanitized = "unnamed_file"

    return sanitized


def validate_domain_model(
    data: dict, model_class: Type[BaseModel]
) -> BaseModel:
    """
    Validate and convert dictionary data to a domain model using Pydantic.

    This provides runtime validation that complements static type checking,
    ensuring data integrity at critical boundaries.

    Args:
        data: Dictionary data to validate
        model_class: Pydantic model class to validate against

    Returns:
        Validated domain model instance

    Raises:
        DomainValidationError: If validation fails

    Example:
        >>> from sample.domain import Order
        >>> data = {"order_id": "123", "customer_id": "cust1", ...}
        >>> order = validate_domain_model(data, Order)
    """
    logger.debug(
        "Validating domain model",
        extra={
            "model_class": model_class.__name__,
            "data_keys": (
                list(data.keys()) if isinstance(data, dict) else "not_dict"
            ),
        },
    )

    try:
        validated_model = model_class(**data)

        logger.debug(
            "Domain model validation passed",
            extra={
                "model_class": model_class.__name__,
                "validated_fields": list(
                    model_class.model_fields.keys()
                ),  # Use class attribute instead of instance
            },
        )

        return validated_model

    except ValidationError as e:
        error_message = (
            f"Domain model validation failed for {model_class.__name__}: {e}"
        )

        logger.error(
            "Domain model validation failed",
            extra={
                "model_class": model_class.__name__,
                "validation_errors": e.errors(),
                "input_data": data,
            },
        )

        raise DomainValidationError(error_message) from e
    except Exception as e:
        error_message = (
            f"Unexpected error validating {model_class.__name__}: {e}"
        )

        logger.error(
            "Unexpected domain validation error",
            extra={
                "model_class": model_class.__name__,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
        )

        raise DomainValidationError(error_message) from e


def validate_pydantic_response(
    obj: object, expected_type: Type[BaseModel]
) -> BaseModel:
    """
    Validate that an object is a valid Pydantic model of the expected type.

    This is useful for validating responses from repositories or use cases
    to ensure they return properly validated domain objects.

    Args:
        obj: Object to validate
        expected_type: Expected Pydantic model type

    Returns:
        The validated object (unchanged if valid)

    Raises:
        DomainValidationError: If validation fails

    Example:
        >>> from sample.domain import Payment
        >>> payment = some_repository_method()
        >>> validated = validate_pydantic_response(payment, Payment)
    """
    logger.debug(
        "Validating Pydantic response",
        extra={
            "object_type": type(obj).__name__,
            "expected_type": expected_type.__name__,
        },
    )

    # Check if object is an instance of the expected type
    if not isinstance(obj, expected_type):
        error_message = (
            f"Expected {expected_type.__name__}, got {type(obj).__name__}"
        )

        logger.error(
            "Pydantic response type validation failed",
            extra={
                "object_type": type(obj).__name__,
                "expected_type": expected_type.__name__,
            },
        )

        raise DomainValidationError(error_message)

    # If it's a Pydantic model, we can also validate its current state
    if isinstance(obj, BaseModel):
        try:
            # This will re-validate the model's current field values
            obj.model_validate(obj.model_dump())

            logger.debug(
                "Pydantic response validation passed",
                extra={
                    "object_type": type(obj).__name__,
                    "expected_type": expected_type.__name__,
                },
            )

            return obj

        except ValidationError as e:
            error_message = (
                f"Pydantic model {expected_type.__name__} has invalid "
                f"state: {e}"
            )

            logger.error(
                "Pydantic response state validation failed",
                extra={
                    "object_type": type(obj).__name__,
                    "expected_type": expected_type.__name__,
                    "validation_errors": e.errors(),
                },
            )

            raise DomainValidationError(error_message) from e


def create_validated_repository_factory(
    protocol: Type[P], implementation_class: Type
) -> Callable[..., Any]:
    """
    Create a factory function that validates repository implementations at
    creation time.

    This provides a clean way to ensure repository implementations are valid
    when they're instantiated, catching configuration errors early.

    Args:
        protocol: The protocol the implementation should satisfy
        implementation_class: The concrete implementation class

    Returns:
        Factory function that creates validated repository instances

    Example:
        >>> from sample.repositories import PaymentRepository
        >>> from sample.repos.minio.payment import MinioPaymentRepository
        >>> factory = create_validated_repository_factory(
        ...     PaymentRepository, MinioPaymentRepository
        ... )
        >>> repo = factory()  # Will validate on creation
    """

    def factory(*args: Any, **kwargs: Any) -> Any:
        logger.debug(
            "Creating validated repository",
            extra={
                "protocol_name": protocol.__name__,
                "implementation_class": implementation_class.__name__,
            },
        )

        # Create the repository instance
        repository = implementation_class(*args, **kwargs)

        # Validate it satisfies the protocol
        validate_repository_protocol(repository, protocol)

        logger.info(
            "Validated repository created",
            extra={
                "protocol_name": protocol.__name__,
                "implementation_class": implementation_class.__name__,
            },
        )

        return repository

    factory.__name__ = f"create_validated_{implementation_class.__name__}"
    factory.__doc__ = (
        f"Create and validate {implementation_class.__name__} against "
        f"{protocol.__name__}"
    )

    return factory


# Convenience functions for common validation patterns
def ensure_payment_repository(repo: object) -> Any:
    """Ensure an object satisfies the PaymentRepository protocol"""
    from sample.repositories import PaymentRepository

    return ensure_repository_protocol(repo, PaymentRepository)  # type: ignore[type-abstract]


def ensure_inventory_repository(repo: object) -> Any:
    """Ensure an object satisfies the InventoryRepository protocol"""
    from sample.repositories import InventoryRepository

    return ensure_repository_protocol(repo, InventoryRepository)  # type: ignore[type-abstract]


def ensure_order_repository(repo: object) -> Any:
    """Ensure an object satisfies the OrderRepository protocol"""
    from sample.repositories import OrderRepository

    return ensure_repository_protocol(repo, OrderRepository)  # type: ignore[type-abstract]


def ensure_order_request_repository(repo: object) -> Any:
    """Ensure an object satisfies the OrderRequestRepository protocol"""
    from sample.repositories import OrderRequestRepository

    return ensure_repository_protocol(repo, OrderRequestRepository)  # type: ignore[type-abstract]
