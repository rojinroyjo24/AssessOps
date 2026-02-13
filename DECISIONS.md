# DECISIONS.md - Architecture & Design Decisions

This document explains the key technical decisions made during the development of the Assessment Ops Mini Platform, including rationale, trade-offs, and assumptions.

---

## 1. Framework Choice: FastAPI over Flask

**Decision**: FastAPI

**Reasoning**:
- **Automatic API documentation**: FastAPI generates Swagger UI and ReDoc out of the box, which is invaluable for testing and demonstrating the API.
- **Pydantic validation**: Built-in request/response validation with Pydantic models eliminates boilerplate validation code and provides clear error messages.
- **Async support**: Native async/await support allows better handling of concurrent requests, especially important during batch ingestion.
- **Type hints**: Python type hints are first-class citizens, making the code self-documenting and easier to understand.
- **Performance**: FastAPI is one of the fastest Python frameworks, comparable to Node.js and Go for most workloads.

**Trade-offs**:
- Flask has a larger ecosystem of extensions, but FastAPI's built-in features cover our needs.
- FastAPI's middleware pattern is slightly different from Flask's, requiring adaptation for request ID tracking.

---

## 2. ORM Decision: SQLAlchemy 2.0

**Decision**: SQLAlchemy 2.0 with declarative ORM models

**Reasoning**:
- **Industry standard**: SQLAlchemy is the most mature and widely-used Python ORM, with extensive documentation and community support.
- **Alembic integration**: Alembic (by the same author) provides seamless database migration management.
- **JSONB support**: Native support for PostgreSQL JSONB columns, critical for storing answers, raw payloads, and scoring explanations.
- **Relationship management**: Built-in relationship loading strategies (joinedload, lazy loading) prevent N+1 query problems.
- **Raw SQL escape hatch**: When ORM queries become complex, we can drop down to raw SQL without switching tools.

**Alternatives considered**:
- **Raw SQL (psycopg2)**: Maximum control but requires more boilerplate and manual query construction. Chosen against for maintainability.
- **Tortoise ORM**: Async-native ORM but less mature and smaller community.

---

## 3. Deduplication Threshold: 92%

**Decision**: Answer similarity threshold of 92%

**Reasoning**:
- **Why not 100%?**: Network retries and UI glitches can cause re-submissions where a student accidentally changes 1-2 answers (mis-tap, page reload after selection change). Requiring exact match would miss these true duplicates.
- **Why not lower (80-85%)?**: Too many false positives. Students in the same coaching centre taking the same test will naturally have some answer overlap (taught the same material). A lower threshold would incorrectly mark different students' legitimate attempts as duplicates.
- **Why 92%?**: For a 50-question test, 92% means up to 4 answers can differ and still be flagged as duplicate. For a 100-question test, up to 8. This covers typical UI glitch scenarios (1-3 changed answers) while staying well above random similarity.
- **Configurable**: The threshold is defined as a constant (`ANSWER_SIMILARITY_THRESHOLD = 0.92`) in `deduplication.py` and can be easily adjusted without code changes.

**The 7-minute time window** was chosen because:
- Test re-submissions from network issues typically happen within seconds to minutes.
- A student starting the same test 10+ minutes later is likely a deliberate re-attempt.
- 7 minutes provides a generous buffer for slow network conditions.

---

## 4. Data Cleanup: Accept and Document vs Skip

**Decision**: Accept partial/imperfect data with logging, skip only truly unprocessable events.

**Approach**:
- **Missing email**: Use phone as identity fallback. Log the fallback at DEBUG level.
- **Gmail aliases**: Automatically normalize (remove +alias). Log the normalization.
- **Phone format variations**: Strip all non-digit characters. Handles any format.
- **Missing submitted_at**: Accept as partial submission (submitted_at = NULL). The attempt is still valid.
- **Malformed timestamps**: Attempt flexible parsing (ISO formats with/without timezone). Skip and log as WARNING only if completely unparseable.
- **Unknown answer values**: Accept as-is. The scoring system treats any non-matching answer as wrong.

**Rationale**: In an ops platform, data loss is worse than imperfect data. By accepting everything we can and logging decisions, operators can review the logs and make corrections via the recompute/flag endpoints.

---

## 5. Logging Implementation

**Decision**: Custom structured JSON logging to stdout

**Reasoning**:
- **Container-native**: Logging to stdout is the standard practice for Docker containers. Container orchestrators (Docker, K8s) capture stdout and route to log aggregation.
- **Monolog-style structure**: The JSON format with timestamp, level, message, channel, context, and extra fields matches the monitoring industry standard.
- **Request ID tracking**: Using Python's `contextvars.ContextVar` for request-scoped tracking. This is thread-safe and works with async/await.
- **Channel separation**: Separating logs by channel (http, db, dedup, scoring) allows selective filtering in log aggregation tools.

**Alternatives considered**:
- **python-json-logger**: A library for JSON logging. We included it in requirements but implemented our own formatter for complete control over the output format and Monolog compatibility.
- **structlog**: Excellent library but adds a dependency. Our custom formatter is simple enough to not warrant an additional dependency.
- **File-based logging**: Not container-friendly. Would require volume mounts and rotation configuration.

---

## 6. Scoring Without Answer Key

**Decision**: Use a deterministic default answer key pattern for demonstration

**Reasoning**:
- The assignment specifies scoring with negative marking but doesn't provide an actual answer key for the sample data.
- In production, the answer key would be stored in the `tests` table or provided via a separate API.
- For demonstration, we generate expected answers using a deterministic pattern: `["A", "B", "C", "D"]` cycling with question number. This ensures:
  - Consistent scores across recomputations
  - A mix of correct and wrong answers (demonstrating negative marking)
  - The scoring pipeline is fully exercised

**The recompute endpoint** allows updating scores if an answer key is later provided.

---

## 7. UUID Primary Keys

**Decision**: UUID v4 for all primary keys

**Reasoning**:
- **Distributed ingestion**: UUIDs allow multiple systems to generate IDs without coordination. Critical for coaching centres submitting data independently.
- **Security**: UUIDs don't expose record counts or creation order (unlike auto-increment integers).
- **Merge-friendly**: No ID conflicts when merging data from different sources.

**Trade-off**: UUIDs are larger (16 bytes vs 4 bytes for integers) and slightly slower for indexing. For this scale, the impact is negligible.

---

## 8. Frontend Architecture

**Decision**: Simple React with hooks, no state management library

**Reasoning**:
- **Simplicity**: The assignment specifies "functionality over design" and "basic UI". React hooks (useState, useEffect) are sufficient for this scope.
- **No Redux/Zustand**: With only 3 pages and no complex shared state, adding a state management library would be over-engineering.
- **Axios over fetch**: Axios provides better error handling, interceptors (for request ID logging), and a cleaner API than native fetch.
- **React Router**: Standard routing library for multi-page navigation.

---

## 9. Docker Compose Design

**Decision**: Three services with health checks and proper dependency ordering

**Key decisions**:
- **Health check on PostgreSQL**: The backend waits for PostgreSQL to be ready (via `pg_isready`) before starting. This prevents migration failures on first boot.
- **Volume mounts for code**: In development mode, source code is mounted into containers for hot-reload (backend via uvicorn --reload, frontend via react-scripts).
- **Separate network**: All services communicate on `app-network`, isolating them from the host network except for exposed ports.
- **Migration in startup**: `alembic upgrade head` runs before the backend server starts, ensuring the schema is always up to date.

---

## 10. Assumptions

1. **No authentication required**: The platform is assumed to be for internal ops use, running behind a VPN or firewall.
2. **Single-node deployment**: The platform runs on a single machine via Docker Compose. For production, we'd add load balancing, replicas, and managed database.
3. **Answer values are uppercase**: We normalize answers to uppercase for comparison (e.g., "a" becomes "A").
4. **One test has one marking scheme**: The marking scheme is per-test and doesn't vary by question.
5. **Canonical attempt is the earliest**: When duplicates are detected, the attempt with the earliest `started_at` is kept as canonical.
6. **Sample data is representative**: The `attempt_events.json` demonstrates all edge cases (duplicates, missing email, Gmail aliases, partial submissions, different phone formats).

---

## 11. Performance Considerations

1. **Database indexes**: Created on `student_id`, `test_id`, `status`, `started_at`, and `source_event_id` for fast filtering.
2. **Eager loading**: API queries use `joinedload` to fetch related data in a single query, avoiding N+1 problems.
3. **Connection pooling**: SQLAlchemy engine configured with pool_size=10 and max_overflow=20.
4. **Pagination**: All list endpoints support pagination to prevent loading entire datasets.

---

## 12. Security Considerations

1. **Input validation**: All API inputs validated via Pydantic models.
2. **SQL injection prevention**: SQLAlchemy parameterized queries prevent SQL injection.
3. **CORS**: Configured for development (allow all origins). Must be restricted for production.
4. **No sensitive data exposure**: Raw SQL queries are not logged by default.
