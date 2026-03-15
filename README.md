# Multi-Tenant Image Hashtag Generator

A FastAPI service that accepts image uploads and returns AI-generated hashtags via Google Gemini. Built to satisfy the **SWE Assignment 1** requirements: multi-tenancy, SQL/NoSQL polyglot persistence, application-level sharding, and primary-replica replication.

---

## Architecture vs. Assignment Requirements

| Assignment Requirement | How It's Implemented |
|---|---|
| **Relational DB for ACID billing** | PostgreSQL `transactions` table — every upload atomically creates a `PENDING` → `COMPLETED` billing record in the same SQLAlchemy session |
| **NoSQL for flexible/fast lookups** | MongoDB (`saas_metadata.image_results`) stores raw hashtag payloads — no rigid schema, easy to extend |
| **Application-level sharding by `tenant_id`** | `sharding.py` → `get_reader_db()` uses `tenant_id % 2` to route reads to Replica 1 or Replica 2 |
| **Primary-replica replication** | `docker-compose.yml` — `postgres-primary` runs with `wal_level=replica`; two replicas run `pg_basebackup` on startup and stream WAL |
| **Writes to primary only** | `get_writer_db()` always connects to `postgres-primary:5432` |
| **Heavy reads to replica** | `GET /history` uses `get_reader_db()` — hits replica, never primary |

### Data Flow for `POST /upload`

```
Client ──► FastAPI
             │
             ├─ 1. Verify Tenant (PostgreSQL PRIMARY - ACID)
             ├─ 2. INSERT Transaction status=PENDING (PRIMARY)
             ├─ 3. Save image file to /uploads/
             ├─ 4. INSERT ImageJob status=PENDING (PRIMARY)
             ├─ 5. Call Gemini Vision API → get 5 hashtags
             ├─ 6. INSERT result doc into MongoDB (NoSQL)
             └─ 7. UPDATE ImageJob + Transaction → COMPLETED (PRIMARY)
```

### Data Flow for `GET /history`

```
Client ──► FastAPI
             │
             ├─ shard = tenant_id % 2
             ├─ 0 → PostgreSQL REPLICA-1 (port 5433)
             ├─ 1 → PostgreSQL REPLICA-2 (port 5434)
             │         (reads job records)
             └─ MongoDB → enriches with hashtags
```

---

## Setup

### Prerequisites
- Docker + Docker Compose
- A `.env` file in the project root:

```env
GEMINI_API_KEY=YOUR_API_KEY_HERE
```

### Start Everything

```bash
docker-compose up --build -d
```

This starts:
- `fastapi-app` → `http://localhost:8000`
- `postgres-primary` → `localhost:5432`
- `postgres-replica-1` → `localhost:5433`
- `postgres-replica-2` → `localhost:5434`
- `mongodb` → `localhost:27017`

The `init.sql` script auto-seeds 4 tenants on first boot:

| Tenant ID | Company |
|---|---|
| 1 | Acme Corp |
| 2 | Globex Corporation |
| 3 | Wayne Enterprises |
| 4 | Stark Industries |

### Check it's running

```bash
curl http://localhost:8000/docs
```

---

## API Reference

All endpoints require the `X-Tenant-ID` header to identify the tenant (simulates JWT-based auth).

### `POST /upload` — Upload an image, get hashtags

```bash
curl -X POST http://localhost:8000/upload \
  -H "X-Tenant-ID: 1" \
  -F "file=@/path/to/your/photo.jpg"
```

**Response:**
```json
{
  "message": "Image processed successfully",
  "job_id": 1,
  "hashtags": [
    "#landscape",
    "#mountains",
    "#sunset",
    "#nature",
    "#travel"
  ]
}
```

> Uses Tenant 1 (Acme Corp). Replace the path with any `.jpg`, `.png`, etc. on your machine.

---

### `GET /history` — Retrieve past jobs for a tenant

```bash
curl "http://localhost:8000/history?limit=5&skip=0" \
  -H "X-Tenant-ID: 1"
```

**Response:**
```json
{
  "tenant_id": 1,
  "results": [
    {
      "job_id": 1,
      "status": "COMPLETED",
      "file_path": "/uploads/3f2a1b4c-....jpg",
      "created_at": "2026-03-15T11:55:00",
      "hashtags": ["#landscape", "#mountains", "#sunset", "#nature", "#travel"]
    }
  ],
  "source": "PostgreSQL Replica & MongoDB"
}
```

> Note: This read is routed to a read replica — Tenant 1 hits Replica 1, Tenant 2 hits Replica 2 (modulo sharding).

---

### Test sharding — use a different tenant

```bash
# Tenant 2 → hits Replica 2 (2 % 2 = 0... wait, 2 % 2 = 0 → Replica 1; 3 % 2 = 1 → Replica 2)
curl "http://localhost:8000/history" \
  -H "X-Tenant-ID: 3"
```

---

## Teardown

```bash
docker-compose down -v
```

The `-v` flag removes volumes (database data). Omit it to preserve data between restarts.
