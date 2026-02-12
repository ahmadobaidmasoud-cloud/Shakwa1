# Alembic Database Migrations Setup

## Overview
Alembic has been successfully initialized and configured for your FastAPI application. This allows you to manage database schema changes version-controlled migrations.

## Migration Applied
✅ **001_add_manager_role** - Added 'manager' value to the userrole enum type in PostgreSQL

## Common Alembic Commands

### Apply pending migrations to the database
```bash
cd app_api
python -m alembic upgrade head
```

### Check current migration status
```bash
python -m alembic current
```

### View migration history
```bash
python -m alembic history
```

### Create a new migration (automatic detection)
```bash
python -m alembic revision --autogenerate -m "Description of changes"
```

### Create a new blank migration
```bash
python -m alembic revision -m "Description of changes"
```

### Downgrade to a specific migration
```bash
python -m alembic downgrade <revision_id>
```

### Show SQL for a migration without applying it
```bash
python -m alembic upgrade head --sql
```

## Structure
- `alembic/` - Migration scripts directory
  - `versions/` - Contains all migration files
  - `env.py` - Alembic environment configuration (configured to use app settings)
  - `script.py.mako` - Template for new migrations
- `alembic.ini` - Alembic configuration file

## Configuration
The Alembic environment (`env.py`) is already configured to:
- Use the database URL from `app.core.config.settings`
- Import all models from `app.models` for autogenerate support
- Use the SQLAlchemy declarative base from your app

## For Future Enum Changes
When adding new enum values to PostgreSQL enums:
1. Update the enum class in your model
2. Create a migration: `python -m alembic revision -m "Add new enum value"`
3. In the migration file, use: `op.execute("ALTER TYPE enum_name ADD VALUE 'new_value'")`
4. Apply the migration: `python -m alembic upgrade head`

## Notes
- PostgreSQL doesn't support removing enum values, so downgrades with enum changes are limited
- Always test migrations on a development database first
- Keep migration files in version control
