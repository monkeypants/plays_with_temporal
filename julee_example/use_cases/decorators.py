"""
Decorators for use case step error handling and logging.

This module provides decorators that implement consistent error handling
and logging patterns across all use cases in the julee_example domain,
following the patterns established in the sample use cases.
"""

import logging
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar, Awaitable

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


def try_use_case_step(
    step_name: str,
    extra_context: Optional[Dict[str, Any]] = None,
) -> Callable[[F], F]:
    """
    Decorator that wraps use case steps with consistent error handling and
    logging.

    This decorator provides the same error handling and logging pattern used
    in the sample use cases, eliminating boilerplate and ensuring consistency
    across all use case implementations.

    Args:
        step_name: Name of the step (e.g., "assembly_id_generation")
        extra_context: Optional additional context to include in all log
            messages

    Returns:
        Decorated function with consistent error handling and logging

    Example:
        >>> @try_use_case_step(
        ...     "assembly_id_generation", {"document_id": "doc-123"}
        ... )
        >>> async def generate_assembly_id(self) -> str:
        ...     return await self.assembly_repo.generate_id()
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Build base logging context
            log_context = {
                "debug_step": f"before_{step_name}",
            }
            if extra_context:
                log_context.update(extra_context)

            # Pre-step logging
            logger.debug(
                f"About to {step_name}",
                extra=log_context,
            )

            try:
                # Execute the wrapped function
                result = await func(*args, **kwargs)

                # Success logging with result information
                success_context = {
                    "debug_step": f"{step_name}_success",
                }
                if extra_context:
                    success_context.update(extra_context)

                # Add result to logging context if it's a simple type
                if isinstance(result, str):
                    success_context["result"] = result
                elif hasattr(result, "id"):
                    success_context["result_id"] = result.id
                elif hasattr(result, "__dict__"):
                    # For complex objects, just log the type
                    success_context["result_type"] = type(result).__name__

                logger.debug(
                    f"{step_name} completed successfully",
                    extra=success_context,
                )

                return result

            except Exception as e:
                # Error logging
                error_context = {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "debug_step": f"{step_name}_failed",
                }
                if extra_context:
                    error_context.update(extra_context)

                logger.error(
                    f"Failed to {step_name}",
                    extra=error_context,
                )
                raise

        return wrapper  # type: ignore[return-value]

    return decorator
