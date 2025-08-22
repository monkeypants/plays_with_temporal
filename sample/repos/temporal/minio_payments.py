"""
Temporal Activity implementation of PaymentRepository.
Uses clean, consistent activity naming for all methods.

This approach uses a single repository class with consistent activity naming
that follows the pattern: sample.payment_repo.{method_name}

No use case prefixes or implementation details are included in activity names,
providing a clean separation of concerns.
"""

from sample.repos.minio.payment import MinioPaymentRepository
from sample.repos.temporal.decorators import temporal_repository


@temporal_repository("sample.payment_repo")
class TemporalMinioPaymentRepository(MinioPaymentRepository):
    """
    Temporal Activity implementation of PaymentRepository.

    This class inherits from MinioPaymentRepository and automatically wraps
    all async methods as Temporal activities using the @temporal_repository
    decorator.

    The decorator creates activities with clean, consistent names:
    - process_payment -> "sample.payment_repo.process_payment"
    - get_payment -> "sample.payment_repo.get_payment"
    - refund_payment -> "sample.payment_repo.refund_payment"

    This approach provides:
    - Single repository for all use cases
    - Clean naming without use case mixing
    - No implementation details leaked (.minio removed)
    - True inheritance rather than delegation
    - Significant reduction in boilerplate code
    """

    # That's it! The @temporal_repository decorator automatically wraps
    # all async methods as Temporal activities:
    # - process_payment -> "sample.payment_repo.process_payment"
    # - get_payment -> "sample.payment_repo.get_payment"
    # - refund_payment -> "sample.payment_repo.refund_payment"
    pass
