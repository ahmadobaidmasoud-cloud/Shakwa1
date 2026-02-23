"""
Redis SLA Timer Utilities

Manages SLA (Service Level Agreement) timers using Redis key expiration.
When a ticket is assigned, a Redis key is set with a TTL.
When the key expires, Redis keyspace notifications trigger escalation.

Key structure:
    ticket:{ticket_id}:sla  ->  value: {user_id}  ->  TTL: sla_minutes * 60

Prerequisites:
    Redis must have keyspace notifications enabled:
        redis-cli CONFIG SET notify-keyspace-events Ex
    Or in redis.conf:
        notify-keyspace-events "Ex"
"""

import logging
import redis
from app.core.config import settings

logger = logging.getLogger(__name__)

# Redis connection pool (singleton)
_redis_pool = None


def _get_redis_connection() -> redis.Redis:
    """Get or create a Redis connection from the pool."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.ConnectionPool(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
    return redis.Redis(connection_pool=_redis_pool)


def get_sla_key(ticket_id: str) -> str:
    """Build the Redis key for a ticket SLA timer."""
    return f"ticket:{ticket_id}:sla"


def start_sla_timer(ticket_id: str, user_id: str, minutes: int = 30) -> bool:
    """
    Start an SLA timer for a ticket assignment.

    When the key expires after `minutes`, the escalation listener will
    pick up the expired event and escalate the ticket.

    Args:
        ticket_id: The ticket UUID string.
        user_id: The currently assigned user UUID string (stored as value).
        minutes: SLA duration in minutes (default 30).

    Returns:
        True if the timer was set successfully, False otherwise.
    """
    try:
        r = _get_redis_connection()
        key = get_sla_key(ticket_id)
        ttl_seconds = minutes * 60
        r.setex(key, ttl_seconds, user_id)
        logger.info(f"SLA timer set: {key} = {user_id} (TTL: {ttl_seconds}s / {minutes}min)")
        return True
    except Exception as e:
        logger.error(f"Failed to set SLA timer for ticket {ticket_id}: {e}")
        return False


def stop_sla_timer(ticket_id: str) -> bool:
    """
    Stop/clear the SLA timer for a ticket.

    Call this when a user moves the ticket to DONE / PROCESSED status,
    or when the ticket is manually reassigned.

    Args:
        ticket_id: The ticket UUID string.

    Returns:
        True if a timer was deleted, False if no timer existed.
    """
    try:
        r = _get_redis_connection()
        key = get_sla_key(ticket_id)
        deleted = r.delete(key)
        if deleted:
            logger.info(f"SLA timer stopped: {key}")
        else:
            logger.debug(f"No SLA timer to stop for: {key}")
        return bool(deleted)
    except Exception as e:
        logger.error(f"Failed to stop SLA timer for ticket {ticket_id}: {e}")
        return False


def get_sla_remaining(ticket_id: str) -> int:
    """
    Get the remaining TTL (in seconds) for a ticket's SLA timer.

    Returns:
        Remaining seconds, or -1 if no timer exists, or -2 if key has no TTL.
    """
    try:
        r = _get_redis_connection()
        key = get_sla_key(ticket_id)
        ttl = r.ttl(key)
        return ttl
    except Exception as e:
        logger.error(f"Failed to get SLA TTL for ticket {ticket_id}: {e}")
        return -1


def get_sla_assigned_user(ticket_id: str) -> str | None:
    """
    Get the user ID stored in the SLA key (the assignee when timer started).

    Returns:
        The user_id string, or None if no timer exists.
    """
    try:
        r = _get_redis_connection()
        key = get_sla_key(ticket_id)
        return r.get(key)
    except Exception as e:
        logger.error(f"Failed to get SLA user for ticket {ticket_id}: {e}")
        return None
