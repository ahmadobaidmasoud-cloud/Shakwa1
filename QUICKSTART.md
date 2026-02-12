# Quick Start Guide

Get the API running in 5 minutes!

## Step 1: Install PostgreSQL

### Windows
1. Download from https://www.postgresql.org/download/windows/
2. Run installer and follow setup
3. Remember the password for `postgres` user

### macOS
```bash
brew install postgresql
brew services start postgresql
```

### Linux
```bash
sudo apt-get install postgresql postgresql-contrib
sudo service postgresql start
```

## Step 2: Create Database

Open PostgreSQL terminal:
```bash
psql -U postgres
```

In psql:
```sql
CREATE DATABASE shakwa_db;
\q
```

## Step 3: Setup Python

```bash
cd app_api

# Create virtual environment (recommended)
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Step 4: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your PostgreSQL credentials:
```
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/shakwa_db
SECRET_KEY=any-random-string-here
```

## Step 5: Seed Database

```bash
python seed_db.py
```

You should see:
```
Creating database tables...
✓ Tables created successfully

✓ Super-admin user created successfully

Test Credentials:
  Username: admin
  Email: admin@example.com
  Password: password123
  Role: super-admin
```

## Step 6: Run Server

```bash
python -m app.main
```

You should see:
```
INFO:     Started server process [1234]
INFO:     Waiting for application startup.
INFO:     Application startup complete
INFO:     Uvicorn running on http://127.0.0.1:8000
```

## Step 7: Test It

Visit in browser:
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

### In Swagger UI:

1. Click "POST /api/v1/auth/login"
2. Click "Try it out"
3. Enter:
   ```json
   {
     "login": "admin@example.com",
     "password": "password123"
   }
   ```
4. Click "Execute"
5. You should get a token and user info!

## Common Issues

### "Could not connect to server"

PostgreSQL is not running:
- **Windows**: Start PostgreSQL service
- **macOS**: `brew services start postgresql`
- **Linux**: `sudo service postgresql start`

### "ModuleNotFoundError: No module named 'fastapi'"

Install dependencies:
```bash
pip install -r requirements.txt
```

### "Database shakwa_db does not exist"

Create it:
```bash
psql -U postgres -c "CREATE DATABASE shakwa_db;"
```

### Port 8000 already in use

Use different port:
```bash
python -m uvicorn app.main:app --port 8001
```

## Next Steps

1. ✅ API is running
2. ✅ You have test user
3. → Connect React frontend to login endpoint
4. → Add more API endpoints as needed
5. → Deploy to production

## Integration with React

In your React app:

```javascript
// Login
const response = await fetch('http://localhost:8000/api/v1/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    login: 'admin@example.com',
    password: 'password123'
  })
});

const data = await response.json();
localStorage.setItem('token', data.access_token);
localStorage.setItem('user', JSON.stringify(data.user));
```

## File Structure

```
app_api/
├── app/                          # Application code
│   ├── api/                      # API routes and dependencies
│   ├── core/                     # Configuration and security
│   ├── crud/                     # Database operations
│   ├── db/                       # Database setup
│   ├── models/                   # Database models
│   ├── schemas/                  # Request/response schemas
│   └── main.py                   # FastAPI app
├── seed_db.py                    # Create test data
├── requirements.txt              # Python packages
├── .env                          # Configuration (create from .env.example)
└── README.md                     # Full documentation
```

## Key Commands

```bash
# Activate virtual environment
source venv/bin/activate              # macOS/Linux
venv\Scripts\activate                 # Windows

# Install packages
pip install -r requirements.txt

# Seed database
python seed_db.py

# Start API server
python -m app.main

# Run Swagger docs
# Open browser to: http://localhost:8000/api/docs

# Stop server
# Press Ctrl+C

# Deactivate virtual environment
deactivate
```

## Environment Variables

Create `.env` file with:

```
# Database connection
DATABASE_URL=postgresql://postgres:password@localhost:5432/shakwa_db

# JWT secret (change for production!)
SECRET_KEY=your-secret-key-here

# JWT algorithm and expiration
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# App info
PROJECT_NAME=Shakwa Multi-Tenant API
PROJECT_VERSION=1.0.0
```

## Testing Endpoints

### With curl

```bash
# Login
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"login":"admin@example.com","password":"password123"}'

# Health check
curl -X GET "http://localhost:8000/api/v1/auth/health"
```

### With Postman

1. Import collection (coming soon)
2. Set variables
3. Test endpoints

## Getting Help

1. Check README.md for detailed documentation
2. Use Swagger UI at `/api/docs` to test endpoints
3. Check console output for error messages
4. Review `.env` file for misconfigurations

---

**You're ready to build! 🚀**
