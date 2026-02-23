"""
Quick test script for SLA escalation.

Usage:
    1. Start the SLA monitor worker in one terminal:
           cd app_api
           python -m app.workers.sla_monitor

    2. In another terminal, run this test with a short timer:
           cd app_api
           python test_sla.py

    3. Watch the SLA monitor terminal - you should see the escalation
       happen after the timer expires (2 minutes in this test).
"""
import sys
sys.path.insert(0, ".")

from app.core.config import settings
from app.core.redis_utils import start_sla_timer, get_sla_remaining

# Use a real ticket_id and user_id from your DB
# You can get these from the last auto-assigned ticket
TICKET_ID = input("Enter ticket ID (UUID): ").strip()
USER_ID = input("Enter assigned user ID (UUID): ").strip()
MINUTES = int(input("SLA minutes (e.g. 2 for quick test): ").strip() or "2")

print(f"\nSetting SLA timer: ticket={TICKET_ID}, user={USER_ID}, minutes={MINUTES}")
result = start_sla_timer(TICKET_ID, USER_ID, MINUTES)
print(f"Timer set: {result}")

remaining = get_sla_remaining(TICKET_ID)
print(f"TTL remaining: {remaining} seconds")
print(f"\nTimer will expire in {MINUTES} minute(s).")
print("Make sure 'python -m app.workers.sla_monitor' is running in another terminal!")
