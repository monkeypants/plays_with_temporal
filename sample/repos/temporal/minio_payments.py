"""
Temporal Activity implementation of PaymentRepository.
Uses clean, consistent activity naming for all methods.

This approach uses a single repository class with consistent activity naming
that follows the pattern: sample.payment_repo.{method_name}

No use case prefixes or implementation details are included in activity names,
providing a clean separation of concerns.
"""

import logging
from sample.repos.minio.payment import MinioPaymentRepository
from sample.repos.temporal.decorators import temporal_repository

logger = logging.getLogger(__name__)


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

    def __init__(self, endpoint: str):
        """
        Initialize the Temporal wrapper with Minio connection details.

        Args:
            endpoint: Minio endpoint URL (e.g., "localhost:9000")
        """
        super().__init__(endpoint)
        logger.debug("Initialized TemporalMinioPaymentRepository")

    # That's it! No method definitions needed.
    # The @temporal_repository decorator automatically wraps all async methods
    # from the parent MinioPaymentRepository class as Temporal activities:
    #
    # - async def process_payment(self, order: Order) -> PaymentOutcome
    #   becomes activity "sample.payment_repo.process_payment"
    #
    # - async def get_payment(self, payment_id: str) -> Optional[Payment]
    #   becomes activity "sample.payment_repo.get_payment"
    #
    # - async def refund_payment(self, args: RefundPaymentArgs) ->
    # RefundPaymentOutcome becomes activity
    # "sample.payment_repo.refund_payment"
    #
    # All methods maintain their original signatures and behavior while being
    # wrapped as Temporal activities for use in workflows.
