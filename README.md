# Assessment Ops Mini Platform

A full-stack platform for ingesting student assessment attempts from coaching centres, deduplicating noisy/duplicate events intelligently, computing scores with negative marking, and providing analytics via REST APIs with a React dashboard.

## 🛠 Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Backend** | Python + FastAPI | REST API server with async support |
| **Database** | PostgreSQL 15 | Persistent storage with JSONB support |
| **ORM** | SQLAlchemy 2.0 | Object-relational mapping |
| **Migrations** | Alembic | Database schema versioning |
| **Frontend** | React 18 | Interactive dashboard UI |
| **HTTP Client** | Axios | Frontend API communication |
| **Logging** | Custom structured JSON | Monolog-style observability |
| **DevOps** | Docker Compose | Container orchestration |

## 📋 Prerequisites

- **Docker** (v20.10+)
- **Docker Compose** (v2.0+)

That's it! Everything else runs inside containers.

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd assessment-ops-platform
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env if you need to change any defaults
```

### 3. Start All Services

```bash
docker-compose up --build
```

This will:
- Start PostgreSQL on port **5432**
- Run Alembic migrations automatically
- Start the FastAPI backend on port **8000**
- Start the React frontend on port **3000**

### 4. Load Sample Data

Once services are running, load the sample assessment events:

```bash
# Using curl
curl -X POST http://localhost:8000/api/ingest/attempts \
  -H "Content-Type: application/json" \
  -d @attempt_events.json

# Or use the Swagger UI at http://localhost:8000/docs
```

### 5. Access the Application

| Service | URL |
|---------|-----|
| **Frontend Dashboard** | http://localhost:3000 |
| **Backend API** | http://localhost:8000 |
| **API Documentation (Swagger)** | http://localhost:8000/docs |
| **API Documentation (ReDoc)** | http://localhost:8000/redoc |

## 📡 API Endpoints

### Ingestion
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/ingest/attempts` | Batch ingest assessment attempt events |

### Attempts
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/attempts` | List attempts with filters and pagination |
| `GET` | `/api/attempts/{id}` | Get detailed attempt information |
| `POST` | `/api/attempts/{id}/recompute` | Recompute score for an attempt |
| `POST` | `/api/attempts/{id}/flag` | Flag an attempt with a reason |

### Analytics
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/leaderboard` | Get ranked leaderboard for a test |

### Query Parameters for `/api/attempts`

| Parameter | Type | Description |
|-----------|------|-------------|
| `test_id` | UUID | Filter by test ID |
| `student_id` | UUID | Filter by student ID |
| `status` | string | Filter by status (INGESTED, DEDUPED, SCORED, FLAGGED) |
| `has_duplicates` | boolean | Show only attempts with duplicates |
| `date_from` | ISO date | Filter by start date |
| `date_to` | ISO date | Filter by end date |
| `search` | string | Search by student name/email/phone |
| `page` | integer | Page number (default: 1) |
| `per_page` | integer | Results per page (default: 20, max: 100) |

## 🔍 Deduplication Logic

The platform uses smart deduplication with four criteria (ALL must match):

1. **Student Identity**: Normalized email (Gmail alias handling) or phone fallback
2. **Same Test**: Attempts must be for the same test
3. **Time Window**: `started_at` within 7 minutes of each other
4. **Answer Similarity**: ≥ 92% matching answers (computed without fuzzy libraries)

### Gmail Alias Normalization
```
john.doe+coaching@gmail.com → john.doe@gmail.com
```

### Phone Normalization
```
91-7654-321098 → 917654321098
91 7654 321098 → 917654321098
```

## 📊 Scoring Formula

```
correct_points = correct_count × marking.correct (default: +4)
wrong_points   = wrong_count × marking.wrong   (default: -1)
skip_points    = skip_count × marking.skip     (default: 0)
total_score    = correct_points + wrong_points + skip_points

accuracy       = (correct / (correct + wrong)) × 100
net_correct    = correct - wrong
```

## 📝 Structured Logging

Every log entry is valid JSON with:
```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "message": "Human-readable message",
  "channel": "http|db|dedup|scoring",
  "context": { "request_id": "uuid", "attempt_id": "uuid" },
  "extra": { "duration_ms": 123, "ip": "127.0.0.1" }
}
```

**Channels**: `http` (request/response), `db` (database operations), `dedup` (deduplication), `scoring` (score computation)

## 🧪 Testing

### Manual Testing with Swagger UI

1. Open http://localhost:8000/docs
2. Use the "Try it out" button on each endpoint
3. Load sample data via POST `/api/ingest/attempts`

### Test Scenarios

1. **Ingestion**: POST sample events → verify ingestion summary
2. **Deduplication**: Events with Gmail aliases should be detected as duplicates
3. **Scoring**: Verify score calculations match expected values
4. **Leaderboard**: Only best attempt per student, correct ranking
5. **Flagging**: Flag an attempt, verify status changes to FLAGGED
6. **Recompute**: Recompute a score, verify values update

### API Testing with curl

```bash
# Health check
curl http://localhost:8000/health

# List all attempts
curl http://localhost:8000/api/attempts

# Get leaderboard
curl http://localhost:8000/api/leaderboard

# Flag an attempt
curl -X POST http://localhost:8000/api/attempts/{attempt-id}/flag \
  -H "Content-Type: application/json" \
  -d '{"reason": "Suspicious submission pattern"}'
```

## 📁 Project Structure

```
assessment-ops-platform/
├── backend/
│   ├── app/
│   │   ├── __init__.py          # App package
│   │   ├── main.py              # FastAPI app, middleware, routes
│   │   ├── database.py          # DB engine, session, dependency
│   │   ├── logging_config.py    # Structured JSON logging
│   │   ├── models/
│   │   │   ├── student.py       # Student ORM model
│   │   │   ├── test.py          # Test ORM model
│   │   │   ├── attempt.py       # Attempt ORM model
│   │   │   ├── attempt_score.py # AttemptScore ORM model
│   │   │   └── flag.py          # Flag ORM model
│   │   ├── routes/
│   │   │   ├── ingest.py        # POST /api/ingest/attempts
│   │   │   ├── attempts.py      # GET/POST /api/attempts/*
│   │   │   └── leaderboard.py   # GET /api/leaderboard
│   │   └── services/
│   │       ├── deduplication.py  # Dedup logic, identity matching
│   │       └── scoring.py       # Score computation, neg marking
│   ├── migrations/
│   │   ├── env.py               # Alembic environment config
│   │   ├── script.py.mako       # Migration template
│   │   └── versions/
│   │       └── 001_initial.py   # Initial schema migration
│   ├── requirements.txt         # Python dependencies
│   ├── Dockerfile               # Backend container image
│   └── alembic.ini              # Alembic configuration
├── frontend/
│   ├── public/
│   │   └── index.html           # HTML template
│   ├── src/
│   │   ├── index.js             # React entry point
│   │   ├── index.css            # Global styles (dark theme)
│   │   ├── App.js               # Router + navigation
│   │   ├── pages/
│   │   │   ├── AttemptsList.js   # Filterable attempts table
│   │   │   ├── AttemptDetail.js  # Attempt detail view
│   │   │   └── Leaderboard.js   # Ranked leaderboard
│   │   └── services/
│   │       └── api.js           # API client (axios)
│   ├── package.json             # Node dependencies
│   └── Dockerfile               # Frontend container image
├── docker-compose.yml           # Docker Compose orchestration
├── .env.example                 # Environment variables template
├── attempt_events.json          # Sample assessment data
├── README.md                    # This file
└── DECISIONS.md                 # Architecture decisions
```

## 🛑 Stopping the Application

```bash
docker-compose down          # Stop services
docker-compose down -v       # Stop services and remove data volumes
```

## 📄 License

This project is created as an assessment submission.
