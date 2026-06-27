# Customer Support Ticket Management API

A modular Flask API for customer support tickets with JWT authentication, PostgreSQL, SQLAlchemy, Alembic migrations, Redis token blacklisting with memory fallback, Swagger docs, email notifications, role-based authorization, and Render deployment files.

## Features

- Customer registration, login, refresh tokens, logout, forgot password, and reset password.
- Roles: `admin`, `agent`, and `customer`.
- Customers create tickets, view their own tickets, and reply.
- Agents view assigned tickets, reply, and move tickets through the workflow.
- Admins manage users, assign tickets, close/reopen tickets, view all tickets, and access dashboard stats.
- Ticket workflow: `open -> in_progress -> resolved -> closed`.
- Ticket filters: title, status, priority, customer name, agent id, and date.
- Redis-backed JWT revocation with an in-memory fallback when Redis is unavailable.
- Simple per-IP, per-endpoint rate limiting.
- Flask-Mail SMTP notifications with failure-safe delivery.
- Swagger UI at `/apidocs`.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

For local beginner-friendly development, the default config uses SQLite. For PostgreSQL, set:

```bash
set APP_CONFIG=app.config.production.ProductionConfig
set DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/support_api
```

## Run

```bash
flask --app app.py run
```

Open:

- API health: `http://127.0.0.1:5000/`
- Swagger: `http://127.0.0.1:5000/apidocs`

## Rate Limiting

The API includes a simple in-memory rate limiter. By default, each IP address can call the same endpoint 100 times per 60 seconds. When the limit is exceeded, the API returns `429 Too Many Requests` with a `Retry-After` header.

Configure it with:

```bash
set RATE_LIMIT_ENABLED=true
set RATE_LIMIT_REQUESTS=100
set RATE_LIMIT_WINDOW_SECONDS=60
```

## Migrations

```bash
flask --app app.py db init
flask --app app.py db migrate -m "initial"
flask --app app.py db upgrade
```

No raw SQL is required.

## First Admin User

Create an admin in a Flask shell:

```bash
flask --app app.py shell
```

```python
from app.extensions.db import db
from app.models.user import User
from app.auth.utils import hash_password

admin = User(
    name="Admin",
    email="admin@example.com",
    password_hash=hash_password("Admin@123"),
    role="admin",
)
db.session.add(admin)
db.session.commit()
```

## Main Endpoints

### Authentication

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/refresh`
- `POST /auth/logout`
- `POST /auth/forgot-password`
- `POST /auth/reset-password`

### Users

- `POST /users/agents` admin only
- `GET /users` admin only
- `GET /users/<id>` admin only
- `PUT /users/<id>` admin only
- `DELETE /users/<id>` admin only

### Tickets

- `POST /tickets` customer only
- `GET /tickets/my-tickets` customer only
- `GET /tickets/<id>` customer owner, assigned agent, or admin
- `GET /tickets` admin only, supports filters
- `PATCH /tickets/<id>/assign` admin only
- `PATCH /tickets/<id>/status` agent/admin
- `PATCH /tickets/<id>/close` admin only
- `PATCH /tickets/<id>/reopen` admin only

### Replies

- `POST /tickets/<id>/replies`
- `GET /tickets/<id>/replies`

### Dashboard

- `GET /dashboard/stats` admin only

## Example Bodies

Register:

```json
{
  "name": "Jane Customer",
  "email": "jane@example.com",
  "password": "Password@123",
  "phone_number": "+2348012345678"
}
```

Create ticket:

```json
{
  "title": "Cannot login",
  "description": "Login keeps failing",
  "priority": "high"
}
```

Assign ticket:

```json
{
  "agent_id": 5
}
```

Change status:

```json
{
  "status": "resolved"
}
```

Add reply:

```json
{
  "message": "We are investigating this issue."
}
```

## Tests

```bash
pytest
```

## Render Deployment

This project includes `Procfile` and `render.yaml`.

On Render:

1. Create a PostgreSQL database.
2. Create a web service from the GitHub repository.
3. Set `APP_CONFIG=app.config.production.ProductionConfig`.
4. Set `DATABASE_URL`, `SECRET_KEY`, `JWT_SECRET_KEY`, optional `REDIS_URL`, and SMTP variables.
5. Run migrations from the Render shell:

```bash
flask --app app.py db upgrade
```

Deployment placeholders:

- Live URL: add your Render service URL here.
- Swagger URL: add `<live-url>/apidocs` here.
- GitHub URL: add your repository URL here.
