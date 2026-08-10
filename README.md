# DataDoctor

AI-Powered Automated Data Science & Machine Learning Platform.

## Phase 1 — Core Backend Setup

FastAPI backend foundation with environment configuration, database setup,
SQLAlchemy models, JWT security, and a health endpoint.

## Quick Start

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# start PostgreSQL, then:
uvicorn app.main:app --reload
```

## Health Check

```
GET http://localhost:8000/health
```

## API Docs

```
http://localhost:8000/docs
```
