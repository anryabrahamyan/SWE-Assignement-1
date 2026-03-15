# Multi-Tenant Image Hashtag Generator

A FastAPI service that accepts image uploads and returns AI-generated hashtags via Google Gemini. 

**Relevance to SWE Assignment 1**: This project directly implements the "Multi-Tenant User Directory" requirements by combining strict **ACID-compliant PostgreSQL** for tenant billing transactions with a **flexible MongoDB NoSQL** document store for the image processing metadata. To ensure the database handles the required horizontal scale, the application implements **layer-7 sharding**, routing tenant-specific queries to dedicated shards (`tenant_id % 2`). Finally, to protect the primary node's performance, a **primary-replica replication** system is configured via streaming WAL, forcing all heavy analytical reads (the `/history` endpoint) exclusively to the read-replicas.

---

## Setup & Execution

### 1. Prerequisites
- Docker + Docker Compose
- Add your `.env` file to the root directory containing your API key:
```env
GEMINI_API_KEY=YOUR_API_KEY_HERE
```

### 2. Start the Stack
```bash
docker-compose up --build -d
```
*(Starting this runs: FastAPI backend, Postgres Primary, 2 Postgres Replicas, and MongoDB. The system auto-seeds 4 mock tenants on boot).*

### 3. Testing the Application
A sample test image (`test_image.jpg`) has been included in the repository for validation. You can quickly verify the entire assignment's data flow using these commands:

```bash
# 1. Test POST /upload (Tenant 1 - Writes to Primary & Mongo)
curl -s -X POST http://localhost:8000/upload \
  -H "X-Tenant-ID: 1" \
  -F "file=@./test_image.jpg" | jq .

# 2. Test GET /history (Tenant 1 - Reads from Sharded Replica)
curl -s "http://localhost:8000/history?limit=5" \
  -H "X-Tenant-ID: 1" | jq .
```

---

## Teardown
```bash
docker-compose down -v
```
*(The `-v` flag removes the persistent database volumes for a clean slate).*
