"""
PostgreSQL implementation of ScheduleRepository.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from asyncpg import Pool

from cal.domain import Schedule
from cal.repositories import ScheduleRepository

logger = logging.getLogger(__name__)


class PostgreSQLScheduleRepository(ScheduleRepository):
    """
    PostgreSQL implementation of ScheduleRepository.
    Uses PostgreSQL for persistence of schedules.
    """

    def __init__(self, pool: Pool):
        """
        Initialize with an asyncpg connection pool.

        Args:
            pool: asyncpg connection pool for database operations
        """
        self.pool = pool
        logger.debug("Initialized PostgreSQLScheduleRepository")

    async def generate_schedule_id(self) -> str:
        """Generate a unique schedule ID using uuid4"""
        return str(uuid.uuid4())

    async def save_schedule(self, schedule: Schedule) -> None:
        """Saves a schedule object to PostgreSQL."""
        async with self.pool.acquire() as conn:
            # Set timestamps if not present
            now = datetime.now(timezone.utc)
            if schedule.created_at is None:
                schedule.created_at = now
            schedule.last_updated_at = now

            # Update time block timestamps
            for block in schedule.time_blocks:
                if block.created_at is None:
                    block.created_at = now
                block.last_updated_at = now

            query = """
                INSERT INTO schedules (
                    schedule_id, start_date, end_date, status,
                    schedule_data, created_at, last_updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (schedule_id)
                DO UPDATE SET
                    start_date = EXCLUDED.start_date,
                    end_date = EXCLUDED.end_date,
                    status = EXCLUDED.status,
                    schedule_data = EXCLUDED.schedule_data,
                    last_updated_at = EXCLUDED.last_updated_at
            """

            await conn.execute(
                query,
                schedule.schedule_id,
                schedule.start_date,
                schedule.end_date,
                schedule.status.value,
                schedule.model_dump_json(),
                schedule.created_at,
                schedule.last_updated_at,
            )

        logger.info(
            "Saved schedule to PostgreSQL",
            extra={
                "schedule_id": schedule.schedule_id,
                "time_blocks": len(schedule.time_blocks),
            },
        )

    async def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        """Retrieves a schedule object from PostgreSQL."""
        async with self.pool.acquire() as conn:
            query = """
                SELECT schedule_data
                FROM schedules
                WHERE schedule_id = $1
            """
            row = await conn.fetchrow(query, schedule_id)

        if row:
            try:
                schedule = Schedule.model_validate_json(row["schedule_data"])
                logger.debug(
                    "Retrieved schedule from PostgreSQL",
                    extra={"schedule_id": schedule_id},
                )
                return schedule
            except Exception as e:
                logger.error(
                    f"Failed to parse schedule data: {e}",
                    extra={"schedule_id": schedule_id},
                )

        return None
