from app.db.session import engine
from sqlalchemy import text, inspect

inspector = inspect(engine)

# Check ticket_assignments table
print("=" * 60)
print("ticket_assignments table columns:")
print("=" * 60)
cols = inspector.get_columns('ticket_assignments')
for col in cols:
    print(f"  - {col['name']}: {col['type']}")

# Check ticket_escalations table
print("\n" + "=" * 60)
print("ticket_escalations table columns:")
print("=" * 60)
cols = inspector.get_columns('ticket_escalations')
for col in cols:
    print(f"  - {col['name']}: {col['type']}")

# Check indexes on ticket_assignments
print("\n" + "=" * 60)
print("ticket_assignments indexes:")
print("=" * 60)
indexes = inspector.get_indexes('ticket_assignments')
for idx in indexes:
    print(f"  - {idx['name']}: {idx['column_names']}")

# Check foreign keys
print("\n" + "=" * 60)
print("ticket_assignments foreign keys:")
print("=" * 60)
fks = inspector.get_foreign_keys('ticket_assignments')
for fk in fks:
    print(f"  - {fk['name']}: {fk['constrained_columns']} → {fk['referred_table']}.{fk['referred_columns']}")
