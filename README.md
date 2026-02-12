# Shakwa Multi-Tenant API

FastAPI backend server for multi-tenant SaaS application with user authentication and role-based access control.

## Features

✅ **FastAPI Framework**
- Modern, fast (up to 3x faster than Flask/Django)
- Automatic Swagger/OpenAPI documentation
- Type hints throughout the codebase

✅ **Database**
- PostgreSQL database
- SQLAlchemy ORM
- Auto table creation on startup

✅ **Authentication**
- JWT token-based authentication
- Secure password hashing with bcrypt
- Login with username or email
- User registration

✅ **Authorization**
- Role-based access control (RBAC)
- Roles: super-admin, admin, tenant-admin, user
- Protected endpoints with role verification

✅ **API Documentation**
- Automatic Swagger UI at `/api/docs`
- ReDoc documentation at `/api/redoc`
- Clear request/response schemas

## Project Structure

```
app_api/
├── app/
│   ├── api/
│   │   ├── api_v1/
│   │   │   └── endpoints/
│   │   │       └── auth.py          # Auth endpoints
│   │   ├── deps.py                   # Dependency injection (auth)
│   │   └── __init__.py
│   ├── core/
│   │   ├── config.py                 # Configuration from env
│   │   ├── security.py               # Password & JWT functions
│   │   └── __init__.py
│   ├── crud/
│   │   ├── user.py                   # User database operations
│   │   └── __init__.py
│   ├── db/
│   │   ├── session.py                # Database setup
│   │   └── __init__.py
│   ├── models/
│   │   ├── user.py                   # SQLAlchemy User model
│   │   └── __init__.py
│   ├── schemas/
│   │   ├── user.py                   # Pydantic request/response models
│   │   └── __init__.py
│   ├── main.py                        # FastAPI application
│   └── __init__.py
├── seed_db.py                         # Database seeding script
├── requirements.txt                   # Python dependencies
├── .env.example                       # Environment variables template
├── .gitignore
├── run.ps1                            # PowerShell startup script
└── README.md
```

## Quick Start

### 1. Prerequisites

- Python 3.9+
- PostgreSQL 12+

### 2. Install Dependencies

```bash
cd app_api
pip install -r requirements.txt
```

### 3. Setup Environment

```bash
cp .env.example .env
# Edit .env with your PostgreSQL credentials
```

### 4. Create PostgreSQL Database

```bash
createdb shakwa_db
```

Or using pgAdmin GUI.

### 5. Seed Database

```bash
python seed_db.py
```

### 6. Run Server

```bash
python -m app.main
```

Or use the convenience script:
```bash
powershell -ExecutionPolicy Bypass -File run.ps1
```

Server will start on `http://localhost:8000`

## API Endpoints

### Authentication

#### Login
```
POST /api/v1/auth/login

Request:
{
  "login": "admin@example.com",
  "password": "password123"
}

Response:
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "admin",
    "email": "admin@example.com",
    "first_name": "Admin",
    "last_name": "User",
    "role": "super-admin",
    "is_active": true,
    "created_at": "2024-02-10T10:00:00",
    "updated_at": "2024-02-10T10:00:00"
  }
}
```

#### Register
```
POST /api/v1/auth/register

Request:
{
  "username": "johndoe",
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "password": "password123",
  "role": "user"
}

Response:
(Same as login response)
```

#### Health Check
```
GET /api/v1/auth/health

Response:
{
  "message": "API is running"
}
```

### Root

```
GET /                    # Welcome message
GET /api                 # API information
GET /api/docs           # Swagger UI
GET /api/redoc          # ReDoc documentation
```

## Database Models

### User Table

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| username | String(50) | Unique username |
| email | String(100) | Unique email |
| first_name | String(100) | First name |
| last_name | String(100) | Last name |
| hashed_password | String(255) | Bcrypt hashed password |
| role | Enum | User role (super-admin, admin, tenant-admin, user) |
| is_active | Boolean | Account active status |
| created_at | DateTime | Creation timestamp |
| updated_at | DateTime | Last update timestamp |

## Test Credentials

Created by `seed_db.py`:
```
Username: admin
Email: admin@example.com
Password: password123
Role: super-admin
```

## Authentication Flow

1. User sends credentials to `/api/v1/auth/login`
2. Server validates credentials
3. JWT token is generated
4. Token is returned to client
5. Client stores token and includes in Authorization header
6. Server validates token for protected routes

### Using Token

```javascript
// In Authorization header
Authorization: Bearer <access_token>
```

## Configuration

All configuration is managed through environment variables in `.env`:

```
# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/shakwa_db

# JWT
SECRET_KEY=your-secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# App
PROJECT_NAME=Shakwa Multi-Tenant API
PROJECT_VERSION=1.0.0
```

## Error Handling

All errors return appropriate HTTP status codes:

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request (validation error) |
| 401 | Unauthorized (invalid credentials) |
| 403 | Forbidden (insufficient permissions) |
| 404 | Not Found |
| 500 | Internal Server Error |

## Frontend Integration

### Login Example (JavaScript/React)

```javascript
const response = await fetch('http://localhost:8000/api/v1/auth/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    login: 'admin@example.com',
    password: 'password123'
  })
});

const data = await response.json();

// Store token and user
localStorage.setItem('token', data.access_token);
localStorage.setItem('user', JSON.stringify(data.user));

// Use token for protected requests
fetch('http://localhost:8000/api/v1/protected-endpoint', {
  headers: {
    'Authorization': `Bearer ${data.access_token}`
  }
});
```

## Development

### Adding New Routes

1. Create endpoint file in `app/api/api_v1/endpoints/`
2. Define router with `APIRouter()`
3. Add endpoints with proper docstrings
4. Include router in `app/main.py`

### Adding New Models

1. Create model class in `app/models/`
2. Create corresponding Pydantic schemas in `app/schemas/`
3. Create CRUD functions in `app/crud/`
4. Tables auto-created on startup

## Troubleshooting

### PostgreSQL Connection Error

```
Error: could not connect to server
```

**Solution**: Check if PostgreSQL is running and DATABASE_URL is correct.

### Module Not Found

```
ModuleNotFoundError: No module named 'fastapi'
```

**Solution**: Install dependencies:
```bash
pip install -r requirements.txt
```

### Port Already in Use

```
ERROR: Address already in use
```

**Solution**: Use different port:
```bash
python -m uvicorn app.main:app --port 8001
```

### Database Errors

Clear tables and re-seed:
```bash
# In psql:
DROP DATABASE shakwa_db;
CREATE DATABASE shakwa_db;
```

Then run `python seed_db.py` again.

## Production Deployment

For production:

1. Set `SECRET_KEY` to a strong random value
2. Update `DATABASE_URL` to production database
3. Set `DEBUG=False`
4. Use production-grade server:

```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## Documentation

- **FastAPI**: https://fastapi.tiangolo.com/
- **SQLAlchemy**: https://www.sqlalchemy.org/
- **Pydantic**: https://docs.pydantic.dev/
- **PostgreSQL**: https://www.postgresql.org/docs/

## License

MIT
