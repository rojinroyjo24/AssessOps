# Complete Prompt for Assessment Ops Mini Platform

## Context
I need to build a complete Assessment Ops Mini Platform as per the assignment specifications. This is a full-stack application with React frontend, Python backend (FastAPI/Flask), PostgreSQL database, and structured logging.

## Project Overview
Build a mini platform that:
- Ingests student assessment attempts from coaching centres
- Deduplicates noisy/duplicate events intelligently
- Computes scores with negative marking
- Provides analytics via REST APIs
- Displays results in a React dashboard
- Implements comprehensive structured JSON logging

## Technical Stack Requirements
- **Backend**: Python with FastAPI or Flask
- **Database**: PostgreSQL with proper migrations
- **Frontend**: React (simple UI, functionality over design)
- **Logging**: Structured JSON logs (Monolog-style)
- **DevOps**: Docker Compose for all services

## Detailed Implementation Requirements

### 1. DATABASE SCHEMA (PostgreSQL)

Create the following tables with exact specifications:

**students table:**
- id: UUID (Primary Key)
- full_name: TEXT
- email: TEXT (nullable)
- phone: TEXT (nullable)
- created_at: TIMESTAMPTZ

**tests table:**
- id: UUID (Primary Key)
- name: TEXT
- max_marks: INTEGER
- negative_marking: JSONB (format: {"correct": 4, "wrong": -1, "skip": 0})
- created_at: TIMESTAMPTZ

**attempts table:**
- id: UUID (Primary Key)
- student_id: UUID (Foreign Key to students)
- test_id: UUID (Foreign Key to tests)
- source_event_id: TEXT
- started_at: TIMESTAMPTZ
- submitted_at: TIMESTAMPTZ (nullable)
- answers: JSONB (format: question_no -> A/B/C/D/SKIP)
- raw_payload: JSONB
- status: TEXT (INGESTED | DEDUPED | SCORED | FLAGGED)
- duplicate_of_attempt_id: UUID (nullable, Foreign Key to attempts)

**attempt_scores table:**
- attempt_id: UUID (Primary Key, Foreign Key to attempts)
- correct: INTEGER
- wrong: INTEGER
- skipped: INTEGER
- accuracy: NUMERIC
- net_correct: INTEGER
- score: NUMERIC
- computed_at: TIMESTAMPTZ
- explanation: JSONB

**flags table:**
- id: UUID (Primary Key)
- attempt_id: UUID (Foreign Key to attempts)
- reason: TEXT
- created_at: TIMESTAMPTZ

### 2. BACKEND API ENDPOINTS

Implement these REST API endpoints:

**POST /api/ingest/attempts**
- Accept batch of attempt events
- Validate payload structure
- Store raw_payload in attempts table
- Apply deduplication logic
- Return ingestion summary

**POST /api/attempts/{id}/recompute**
- Recalculate score for specific attempt
- Update attempt_scores table
- Log the recomputation

**POST /api/attempts/{id}/flag**
- Create flag entry with reason
- Update attempt status to FLAGGED
- Return flag details

**GET /api/attempts**
- Support filters: test_id, student_id, status, has_duplicates, date_from, date_to
- Implement pagination (page, per_page parameters)
- Return attempts with related student, test, and score data

**GET /api/leaderboard**
- Accept test_id parameter
- Rank students by: total score (best attempt), accuracy, net_correct, earliest submission
- Return ranked list with student details and metrics

### 3. DEDUPLICATION LOGIC (CRITICAL)

Implement smart deduplication with these rules:

**Student Identity Matching:**
- If email exists: normalize to lowercase + handle Gmail aliases (remove everything after '+' before @)
  - Example: john.doe+test@gmail.com → john.doe@gmail.com
- If no email: fallback to normalized phone (digits only, remove spaces/dashes)

**Duplicate Detection Rules:**
Two attempts are duplicates if ALL conditions met:
1. Same student identity (normalized email or phone)
2. Same test_id
3. started_at within 7 minutes of each other
4. Answer similarity >= 92% (or your chosen threshold)

**Answer Similarity Calculation:**
- Implement WITHOUT fuzzy libraries
- Compare answers for common questions
- Formula: matching_answers / total_compared_questions >= 0.92
- Only compare questions present in both attempts

**Duplicate Handling:**
- Keep earliest attempt as canonical (status: SCORED)
- Mark later duplicates with duplicate_of_attempt_id
- Set duplicate status to DEDUPED
- Don't compute scores for duplicates

### 4. SCORING LOGIC

Implement scoring with these formulas:

**Score Calculation:**
```
1. Count correct, wrong, skipped answers
2. accuracy = (correct / (correct + wrong)) * 100
3. net_correct = correct - wrong
4. score = (correct * marking.correct) + (wrong * marking.wrong) + (skipped * marking.skip)
```

**Explanation JSON:**
Store in attempt_scores.explanation:
```json
{
  "marking_scheme": {"correct": 4, "wrong": -1, "skip": 0},
  "counts": {"correct": 85, "wrong": 10, "skipped": 5},
  "breakdown": {
    "correct_points": 340,
    "wrong_points": -10,
    "skip_points": 0,
    "total": 330
  }
}
```

### 5. STRUCTURED LOGGING (MANDATORY)

Implement Monolog-style JSON logging:

**Log Structure:**
Every log entry must include:
```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO|WARNING|ERROR|DEBUG",
  "message": "Human-readable message",
  "channel": "http|db|dedup|scoring",
  "context": {
    "request_id": "uuid-here",
    "attempt_id": "uuid-here",
    "student_id": "uuid-here",
    "test_id": "uuid-here"
  },
  "extra": {
    "ip": "192.168.1.1",
    "user_agent": "...",
    "query_params": {},
    "duration_ms": 123
  }
}
```

**Required Logging Points:**
1. **HTTP Channel**: Log request start/end with latency
2. **DB Channel**: Log queries, connection events
3. **Dedup Channel**: Log similarity calculations, canonical attempt selection
4. **Scoring Channel**: Log score computation with duration

**Request ID:**
- Generate UUID per request (middleware)
- Pass through all log entries in that request
- Include in API responses (X-Request-ID header)

### 6. FRONTEND (React)

Build these pages with basic, functional UI:

**Page 1: Attempts List**
- Table showing: student name, test name, status, score, duplicate count
- Filters: test dropdown, status dropdown, has_duplicates checkbox
- Search: student name/email/phone
- Pagination controls
- Click row to go to detail page

**Page 2: Attempt Detail**
- Student and test information
- Status badge
- Collapsible raw payload JSON viewer
- Score breakdown card (correct, wrong, skipped, accuracy, score)
- Duplicate thread (if any) showing related attempts
- Action buttons: "Recompute Score", "Flag Attempt"
- Flag form with reason textarea

**Page 3: Leaderboard**
- Test selector dropdown
- Ranked table: rank, student name, score, accuracy, net_correct, submission time
- Highlight top 3 performers
- Show only best attempt per student

**Technical Requirements:**
- Use React hooks (useState, useEffect)
- API calls with fetch or axios
- Basic error handling and loading states
- Responsive table design (scrollable on mobile)
- No fancy styling needed (basic CSS or Tailwind is fine)

### 7. DOCKER COMPOSE SETUP

Create docker-compose.yml with:

**Services:**
1. **postgres**: PostgreSQL 15+
   - Volume for data persistence
   - Environment: POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD

2. **backend**: Python API
   - Depends on postgres
   - Environment: DATABASE_URL, LOG_LEVEL
   - Port mapping: 8000:8000
   - Volume mount for code (development)

3. **frontend**: React app
   - Depends on backend
   - Environment: REACT_APP_API_URL
   - Port mapping: 3000:3000
   - Volume mount for code (development)

**Networks:**
- Create app-network for service communication

### 8. DATABASE MIGRATIONS

Implement proper migrations:
- Use Alembic (for SQLAlchemy) or similar
- Create initial migration with all tables
- Include indexes on foreign keys
- Add indexes for common queries (test_id, student_id, status, started_at)

### 9. DATA HANDLING

Handle the provided attempt_events.json with:
- **Duplicates**: Apply dedup logic
- **Gmail aliases**: Normalize (remove +alias)
- **Missing emails**: Use phone as fallback
- **Malformed timestamps**: Parse flexibly or skip with logging
- **Partial submissions**: Accept with submitted_at as NULL

Document all decisions in DECISIONS.md

### 10. PROJECT STRUCTURE

Organize code as:
```
assessment-ops-platform/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── models/
│   │   ├── routes/
│   │   ├── services/
│   │   │   ├── deduplication.py
│   │   │   ├── scoring.py
│   │   ├── database.py
│   │   ├── logging_config.py
│   ├── migrations/
│   ├── requirements.txt
│   ├── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── App.js
│   ├── package.json
│   ├── Dockerfile
├── docker-compose.yml
├── README.md
├── DECISIONS.md
├── .env.example
└── attempt_events.json
```

### 11. DOCUMENTATION REQUIREMENTS

**README.md must include:**
1. Project overview
2. Prerequisites (Docker, Docker Compose)
3. Setup instructions:
   - Clone repository
   - Copy .env.example to .env
   - Run docker-compose up
   - Run migrations
   - Load sample data
4. API endpoints documentation
5. Testing instructions
6. Technology stack details

**DECISIONS.md must document:**
1. Framework choice (FastAPI vs Flask) - with reasoning
2. ORM decision (SQLAlchemy, raw SQL, or other)
3. Deduplication threshold rationale (why 92% or other)
4. Data cleanup decisions (skip vs repair)
5. Logging implementation choices
6. Any assumptions made
7. Trade-offs considered

**.env.example must include:**
```
DATABASE_URL=postgresql://user:password@postgres:5432/assessment_ops
LOG_LEVEL=INFO
SECRET_KEY=your-secret-key
REACT_APP_API_URL=http://localhost:8000
```

## Implementation Instructions

**Step-by-step approach:**

1. **Setup project structure** - Create all directories and basic files

2. **Setup database** - Create Docker Compose with PostgreSQL, design schema, create migrations

3. **Build backend API** - Implement models, routes, deduplication logic, scoring logic, structured logging

4. **Test backend** - Test each endpoint with sample data, verify deduplication, verify scoring

5. **Build frontend** - Create React components, pages, API integration

6. **Integration testing** - Test full flow from ingestion to leaderboard

7. **Documentation** - Write README, DECISIONS.md, add comments

8. **Final testing** - Load attempt_events.json, verify all features work

## Quality Checklist

Before submission, verify:
- [ ] All database tables created with correct schema
- [ ] All API endpoints working and tested
- [ ] Deduplication logic correctly identifies duplicates
- [ ] Scoring calculations are accurate
- [ ] Structured logging outputs valid JSON to stdout
- [ ] Request IDs generated and tracked
- [ ] Frontend displays all required pages
- [ ] Docker Compose brings up all services
- [ ] Migrations run automatically or with simple command
- [ ] README has clear setup instructions
- [ ] DECISIONS.md explains key choices
- [ ] Code is clean, commented, and understandable
- [ ] Can explain every line of code if asked

## Deliverables Checklist

Ensure repository contains:
- [ ] docker-compose.yml
- [ ] backend/ directory with complete API
- [ ] frontend/ directory with React app
- [ ] migrations/ directory with database migrations
- [ ] README.md with setup instructions
- [ ] DECISIONS.md with assumptions and choices
- [ ] .env.example with all required variables
- [ ] Sample data or loader script

## Expected Output

When running the application:
1. `docker-compose up` starts all services
2. Backend API runs on http://localhost:8000
3. Frontend runs on http://localhost:3000
4. PostgreSQL accessible on port 5432
5. Structured logs output to console in JSON format
6. Can ingest attempt_events.json via API
7. Can view attempts list, details, and leaderboard
8. Can recompute scores and flag attempts

## Additional Notes

- **Code Quality**: Write clean, modular, well-commented code
- **Error Handling**: Implement proper try-catch blocks and return meaningful errors
- **Validation**: Validate all API inputs
- **Testing**: Manual testing is fine, but document test scenarios
- **Performance**: Consider indexing for common queries
- **Security**: Basic security (no SQL injection, validate inputs)

## Final Reminder

The evaluation focuses on:
- Correctness (45%): Does it work as specified?
- Code Quality (25%): Is it clean, maintainable, well-structured?
- Logging & Observability (20%): Are logs comprehensive and useful?
- UX (10%): Is the frontend functional and usable?

You must be able to explain and defend every line of code, even if using AI assistance.

---

## START IMPLEMENTATION

Please implement the complete Assessment Ops Mini Platform following all specifications above. Create all necessary files, implement all features, and ensure the application is fully functional and production-ready.
