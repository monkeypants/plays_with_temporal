"""
The execution context is bound to way execution works.
In this case, we are using a temporal.io execution method,
so we need to use the temporal repositories.
"""

from temporalio import workflow

from sample.domain import (
    CreateOrderRequest,
)
from sample.api.responses import (
    OrderStatusResponse,
)
from sample.repos.temporal.proxies import (
    WorkflowOrderRepositoryProxy,
    WorkflowPaymentRepositoryProxy,
    WorkflowInventoryRepositoryProxy,
    WorkflowOrderRequestRepositoryProxy,
)
from util.repos.temporal.proxies.file_storage import (
    WorkflowFileStorageRepositoryProxy,
)
from sample.usecase import (
    OrderFulfillmentUseCase,
    CancelOrderUseCase,
)  # Added CancelOrderUseCase


@workflow.defn
class OrderFulfillmentWorkflow:
    def __init__(self) -> None:
        self.current_step = "initialized"

    @workflow.query
    def get_current_step(self) -> str:
        """Query method to get the current workflow step"""
        return str(self.current_step)

    @workflow.run
    async def run(self, request_dict: dict) -> OrderStatusResponse:
        """
        Run the order fulfillment workflow.
        This is just a thin wrapper around the use case.

        The workflow accepts a dict containing request data.
        All conversion between Pydantic and domain models happens in the
        use case. The workflow returns the Pydantic response object
        directly - let the data converter handle serialization.
        """
        # Extract request_id from workflow ID (format: "req-{hash}")
        request_id = workflow.info().workflow_id

        workflow.logger.debug(
            "Starting order fulfillment workflow",
            extra={
                "request_id": request_id,
                "workflow_run_id": workflow.info().run_id,
                "debug_step": "workflow_entry",
            },
        )

        workflow.logger.debug(
            "Workflow input received",
            extra={
                "request_id": request_id,
                "request_dict_keys": (
                    list(request_dict.keys())
                    if isinstance(request_dict, dict)
                    else []
                ),
                "customer_id": (
                    request_dict.get("customer_id")
                    if isinstance(request_dict, dict)
                    else None
                ),
                "debug_step": "before_pydantic_model_creation",
            },
        )

        try:
            # Recreate the Pydantic model from the request dict
            request = CreateOrderRequest(**request_dict)
            workflow.logger.debug(
                "Pydantic request model created successfully",
                extra={
                    "request_id": request_id,
                    "customer_id": request.customer_id,
                    "item_count": len(request.items),
                    "total_amount": str(request.total_amount),
                    "debug_step": "pydantic_model_created",
                },
            )
            workflow.logger.debug(
                "Successfully created Pydantic request model",
                extra={
                    "request_id": request_id,
                    "debug_step": "pydantic_model_created",
                },
            )
        except Exception as e:
            workflow.logger.error(
                "Failed to create Pydantic request model",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                    "debug_step": "pydantic_model_failed",
                },
            )
            raise

        try:
            # Create repository stubs
            # These stubs delegate to Temporal activities, ensuring
            # determinism
            # for the workflow.
            # The use case receives these stubs and remains unaware of
            # Temporal.
            # The use case itself will perform runtime validation of these
            # repositories.
            workflow.logger.debug(
                "Creating workflow repository stubs",
                extra={
                    "request_id": request_id,
                    "debug_step": "before_repo_stubs_creation",
                },
            )

            order_repo = WorkflowOrderRepositoryProxy()  # type: ignore[abstract]
            payment_repo = WorkflowPaymentRepositoryProxy()  # type: ignore[abstract]
            inventory_repo = WorkflowInventoryRepositoryProxy()  # type: ignore[abstract]
            request_repo = WorkflowOrderRequestRepositoryProxy()  # type: ignore[abstract]
            file_storage_repo = WorkflowFileStorageRepositoryProxy()

            workflow.logger.debug(
                "Workflow repository stubs created successfully",
                extra={
                    "request_id": request_id,
                    "order_repo_type": type(order_repo).__name__,
                    "payment_repo_type": type(payment_repo).__name__,
                    "inventory_repo_type": type(inventory_repo).__name__,
                    "request_repo_type": type(request_repo).__name__,
                    "file_storage_repo_type": type(
                        file_storage_repo
                    ).__name__,
                    "debug_step": "repo_stubs_created",
                },
            )
        except Exception as e:
            workflow.logger.error(
                "Failed to create repository stubs",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                    "debug_step": "repo_stubs_failed",
                },
            )
            raise

        try:
            # Create use case with the activity stubs
            workflow.logger.debug(
                "Creating OrderFulfillmentUseCase",
                extra={
                    "request_id": request_id,
                    "debug_step": "creating_use_case",
                },
            )

            use_case = OrderFulfillmentUseCase(
                payment_repo=payment_repo,
                inventory_repo=inventory_repo,
                order_repo=order_repo,
                order_request_repo=request_repo,
                file_storage_repo=file_storage_repo,
            )

            workflow.logger.debug(
                "OrderFulfillmentUseCase created successfully",
                extra={
                    "request_id": request_id,
                    "debug_step": "use_case_instance_created",
                },
            )
        except Exception as e:
            workflow.logger.error(
                "Failed to create OrderFulfillmentUseCase",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                    "debug_step": "use_case_creation_failed",
                },
            )
            raise

        # Execute the use case with the generated order ID
        self.current_step = "processing"
        workflow.logger.debug(
            "About to execute order fulfillment use case",
            extra={
                "request_id": request_id,
                "debug_step": "before_fulfill_order_call",
            },
        )

        try:
            result = await use_case.fulfill_order(request, request_id)

            workflow.logger.debug(
                "Order fulfillment use case completed successfully",
                extra={
                    "request_id": request_id,
                    "order_id": (
                        result.order_id
                        if hasattr(result, "order_id")
                        else "N/A"
                    ),
                    "final_status": (
                        result.status
                        if hasattr(result, "status")
                        else "unknown"
                    ),
                    "debug_step": "fulfill_order_completed",
                },
            )
        except Exception as e:
            workflow.logger.error(
                "Order fulfillment use case failed with exception",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "debug_step": "fulfill_order_failed",
                },
            )
            raise

        workflow.logger.debug(
            "Order fulfillment workflow completed successfully",
            extra={
                "request_id": request_id,
                "order_id": (
                    result.order_id if hasattr(result, "order_id") else "N/A"
                ),
                "final_status": (
                    result.status if hasattr(result, "status") else "unknown"
                ),
                "debug_step": "workflow_completed",
            },
        )

        workflow.logger.debug(
            "Order fulfillment workflow exiting",
            extra={
                "request_id": request_id,
                "order_id": (
                    result.order_id if hasattr(result, "order_id") else "N/A"
                ),
                "final_status": (
                    result.status if hasattr(result, "status") else "unknown"
                ),
                "debug_step": "workflow_exit",
            },
        )
        self.current_step = "completed"

        # Return the Pydantic object directly - let the data converter
        # handle serialization
        return result


@workflow.defn
class CancelOrderWorkflow:
    def __init__(self) -> None:
        self.current_step = "initialized"

    @workflow.query
    def get_current_step(self) -> str:
        """Query method to get the current workflow step for cancellation"""
        return str(self.current_step)

    @workflow.run
    async def run(self, args_dict: dict) -> OrderStatusResponse:
        """
        Run the order cancellation workflow.
        This is a thin wrapper around the CancelOrderUseCase.
        """
        order_id = args_dict["order_id"]
        reason = args_dict.get("reason")

        workflow.logger.info(
            "Starting order cancellation workflow",
            extra={
                "order_id": order_id,
                "reason": reason,
                "workflow_run_id": workflow.info().run_id,
            },
        )

        # Create repository stubs for cancellation use case
        order_repo = WorkflowOrderRepositoryProxy()  # type: ignore[abstract]
        payment_repo = WorkflowPaymentRepositoryProxy()  # type: ignore[abstract]
        inventory_repo = WorkflowInventoryRepositoryProxy()  # type: ignore[abstract]

        workflow.logger.debug(
            "Workflow repository stubs created for cancellation",
            extra={
                "order_id": order_id,
                "order_repo_type": type(order_repo).__name__,
                "payment_repo_type": type(payment_repo).__name__,
                "inventory_repo_type": type(inventory_repo).__name__,
            },
        )

        # Create cancellation use case with activity stubs
        cancel_use_case = CancelOrderUseCase(
            order_repo=order_repo,
            payment_repo=payment_repo,
            inventory_repo=inventory_repo,
        )

        self.current_step = "cancelling"
        workflow.logger.info(
            "Executing order cancellation use case",
            extra={
                "order_id": order_id,
            },
        )

        result = await cancel_use_case.cancel_order(order_id, reason)

        workflow.logger.info(
            "Order cancellation workflow completed",
            extra={
                "order_id": order_id,
                "final_status": (
                    result.status if hasattr(result, "status") else "unknown"
                ),
            },
        )

        self.current_step = "completed"
        return result
