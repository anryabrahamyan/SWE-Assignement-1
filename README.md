# Multi-Tenant Image Hashtag Generator

A FastAPI service that accepts image uploads and returns AI-generated hashtags via Google Gemini. 

**Relevance to SWE Assignment 1**: This project implements the requirements of a fast-growing B2B SaaS platform handling multiple enterprise clients. 
* **Data Modeling (SQL vs NoSQL):** Combines **ACID-compliant PostgreSQL** for strict user billing/job tracking with a **flexible MongoDB NoSQL** document store for the raw, dynamic hashtag payloads.
* **Multi-Tenancy & Sharding:** A "Tenant" represents an enterprise client (B2B company) onboarded into the SaaS platform. The application uses **Application-Level Sharding**, partitioning user data based on the `X-Tenant-ID` header. This ensures queries for a specific company only hit a specific database shard.
* **Primary-Replica Replication:** The database uses a primary-replica architecture. The Primary node enforces strict transactional updates (ACID compliance) for user uploads and billing. All heavy read/analytical operations (like generating history) are independently routed strictly to the Read-Replicas to protect the Primary node's performance.

---

## Example

![Test Image](./test_image.jpg)

**1. The Upload Endpoint (Writes to Primary Database):**
When an enterprise client uploads an image, the application strictly processes the transaction in the PostgreSQL Primary Node to ensure ACID compliance for billing, and saves the metadata into MongoDB.

```bash
curl -s -X POST http://localhost:8000/upload \
  -H "X-Tenant-ID: 1" \
  -F "file=@./test_image.jpg" | jq .
```

*Response:*
```json
{
  "message": "Image processed successfully",
  "job_id": 14,
  "hashtags": [
    "#solitude #reflection #nature #peace #stillness"
  ]
}
```

**2. The Analytics Endpoint (Reads exclusively from Replicas):**
A separate endpoint is used to generate analytical reports and historical lookups. When a client requests their history, the application uses modulo math (`tenant_id % 2`) to perform Application-Level Sharding. It seamlessly offloads the heavy read workload by routing the query to `postgres-replica-1` or `postgres-replica-2`, physically protecting the Primary database.

```bash
curl -s "http://localhost:8000/history?limit=5" \
  -H "X-Tenant-ID: 1" | jq .
```

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
*(Starting this runs: FastAPI backend, Postgres Primary, 2 Postgres Replicas, and MongoDB. The system auto-seeds 4 mock enterprise tenants on boot).*

### 3. Testing the Application
A sample test image (`test_image.jpg`) has been included in the repository for validation. You can quickly verify the entire assignment's data flow using these commands:

```bash
# 1. Test POST /upload (Tenant 1 - Writes to Primary & Mongo)
curl -s -X POST http://localhost:8000/upload \
  -H "X-Tenant-ID: 1" \
  -F "file=@./test_image.jpg" | jq .

# 2. Test GET /history (Tenant 1 - Routes to Replica 1 via Shard 0)
curl -s "http://localhost:8000/history?limit=5" \
  -H "X-Tenant-ID: 1" | jq .

# 3. Test GET /history for another tenant (Tenant 2 - Routes to Replica 2 via Shard 1)
curl -s "http://localhost:8000/history?limit=5" \
  -H "X-Tenant-ID: 2" | jq .
```

---

## Teardown
```bash
docker-compose down -v
```
*(The `-v` flag removes the persistent database volumes for a clean slate).*
