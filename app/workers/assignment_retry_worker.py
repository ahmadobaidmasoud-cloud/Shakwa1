"""
Assignment Retry Worker

A standalone background worker that periodically polls for tickets that are
still in QUEUED status (i.e., auto-assignment failed because no agent was
available) and retries assigning them.

Flow:
    1. Every ASSIGNMENT_RETRY_INTERVAL_SECONDS, query all QUEUED tickets.
    2. For each one, call auto_assign_ticket() — if an agent is now free,
       assignment proceeds normally (creates assignment, sends notification,
       starts SLA timer).
    3. If still no agent available, the ticket stays QUEUED and will be
       retried on the next cycle.

Usage:
    python -m app.workers.assignment_retry_worker

Run this alongside the SLA monitor:
    python -m app.workers.sla_monitor
    python -m app.workers.assignment_retry_worker
"""

import sys
import time
import logging
from datetime import datetime

# Ensure the app package is importable when running as __main__
sys.path.insert(0, ".")

from app.core.config import settings
from app.db.session import SessionLocal

# Import ALL models so SQLAlchemy relationships resolve correctly
from app.models.tenant import Tenant          # noqa: F401
from app.models.category import Category      # noqa: F401
from app.models.configuration import Configuration  # noqa: F401
from app.models.ticket_submission import TicketSubmission  # noqa: F401
from app.models.notification import Notification  # noqa: F401
from app.models.ticket_assignment import TicketAssignment, TicketEscalation, AssignmentType  # noqa: F401
from app.models.ticket import Ticket, TicketStatus
from app.models.user import User              # noqa: F401

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("assignment_retry_worker")


def retry_unassigned_tickets() -> int:
    """
    Find all QUEUED tickets and attempt to auto-assign each one.

    Returns the number of tickets successfully assigned in this cycle.
    """
    from app.services.assignment import auto_assign_ticket

    db = SessionLocal()
    assigned_count = 0

    try:
        queued_tickets = (
            db.query(Ticket)
            .filter(Ticket.status == TicketStatus.QUEUED)
            .all()
        )

        if not queued_tickets:
            logger.debug("No queued tickets found — nothing to retry.")
            return 0

        logger.info(f"Found {len(queued_tickets)} queued ticket(s) — attempting assignment...")

        for ticket in queued_tickets:
            try:
                assignment = auto_assign_ticket(
                    db=db,
                    ticket_id=ticket.id,
                    tenant_id=ticket.tenant_id,
                )
                if assignment:
                    logger.info(
                        f"Ticket {ticket.id} assigned to user "
                        f"{assignment.assigned_to_user_id} on retry."
                    )
                    assigned_count += 1
                else:
                    logger.debug(
                        f"Ticket {ticket.id} still has no eligible agent — will retry next cycle."
                    )
            except Exception as e:
                logger.error(f"Error retrying assignment for ticket {ticket.id}: {e}")
                db.rollback()  # Roll back this ticket's transaction, continue with others

    except Exception as e:
        logger.exception(f"Unexpected error during retry cycle: {e}")
    finally:
        db.close()

    return assigned_count


def run_retry_worker():
    """Main loop: poll for unassigned tickets every ASSIGNMENT_RETRY_INTERVAL_SECONDS."""
    interval = settings.ASSIGNMENT_RETRY_INTERVAL_SECONDS

    logger.info("=" * 60)
    logger.info("Assignment Retry Worker starting...")
    logger.info(f"Retry interval: {interval} seconds")
    logger.info("=" * 60)

    while True:
        cycle_start = datetime.utcnow()
        logger.info(f"[{cycle_start.strftime('%H:%M:%S')}] Starting assignment retry cycle...")

        try:
            assigned = retry_unassigned_tickets()
            logger.info(
                f"Retry cycle complete — {assigned} ticket(s) newly assigned. "
                f"Next check in {interval}s."
            )
        except Exception as e:
            logger.exception(f"Retry cycle failed: {e}")

        time.sleep(interval)


if __name__ == "__main__":
    run_retry_worker()
