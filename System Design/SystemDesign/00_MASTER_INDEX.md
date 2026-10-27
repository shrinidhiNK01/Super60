# Complete System Design Notes — Master Index

> Beginner to Advanced | Everything Explained Simply

---

## Files in This Series

| File | Topics Covered |
|------|---------------|
| `01_Introduction_and_Components.md` | What is System Design, Alien Bank example, Core Components, Data-Intensive vs Compute-Intensive Apps |
| `02_Requirements_and_DNS.md` | Functional & Non-Functional Requirements, Scalability, Availability, Reliability, Performance, Security, DNS Architecture |
| `03_APIs_and_Communication.md` | REST, SOAP, GraphQL, gRPC, WebSockets, HTTP Methods, Status Codes, API Design Best Practices |
| `04_Databases_SQL_NoSQL.md` | SQL Tables/Joins/Constraints/Relationships, NoSQL Key-Value/Document/Graph/Columnar, ACID, When to use which |
| `05_Caching.md` | Cache Hit/Miss, TTL, Read-Through, Write-Through, Write-Around, Write-Back, LRU/LFU/FIFO eviction policies |
| `06_Load_Balancers_and_Replication.md` | Round Robin, Weighted, Least Connections, IP Hash, Geo Routing, Health Checks, Single/Multi/Leaderless Replication, Sync/Async, Quorum |
| `07_Sharding_and_CAP_Theorem.md` | Range/Hash Partitioning, Consistent Hashing, Hotspots, CAP Theorem, CP vs AP, Eventual Consistency |
| `08_Message_Queues_and_Fault_Tolerance.md` | FIFO/Priority Queues, Pub/Sub, Push/Pull, Poison Messages, Duplicates, Hardware/Software/Human failures, Circuit Breaker |
| `09_Monitoring_and_Case_Study.md` | Logs/Metrics/Traces, Throughput, Latency, Error Rate, SLA/SLO/SLI, Streaming App Design from scratch |

---

## Quick Reference: Key Concepts

### Non-Functional Requirements (SARPSOM)
- **S**calability — Handle more users
- **A**vailability — Stay up (99.99%)
- **R**eliability — Be correct, don't lose data
- **P**erformance — Low latency + high throughput
- **S**ecurity — Auth, encryption, protection
- **O**bservability — Logs, metrics, traces
- **M**aintainability — Easy to change and fix

### Choosing a Database
- Need ACID transactions, complex queries → **SQL (PostgreSQL, MySQL)**
- Need fast key lookups, caching, sessions → **Key-Value (Redis)**
- Need flexible schema, nested documents → **Document DB (MongoDB)**
- Need relationship traversal, social graphs → **Graph DB (Neo4j)**
- Need time-series, huge write throughput → **Columnar (Cassandra)**

### Choosing an API Type
- Standard web/mobile app → **REST**
- Internal microservice communication → **gRPC**
- Real-time features (chat, live data) → **WebSockets**
- Flexible data fetching for complex frontend → **GraphQL**
- Legacy enterprise → **SOAP**

### CAP Theorem
- Network partition is unavoidable → always choose P
- Real choice: **CP** (consistent, may be unavailable) vs **AP** (always available, may be stale)
- Banks → CP | Social media, DNS → AP

### Cache Eviction
- **LRU** (Least Recently Used) → General purpose (most common)
- **LFU** (Least Frequently Used) → Long-term popular content
- **FIFO** → Simple time-based expiry

### Load Balancing
- All servers equal → **Round Robin**
- Servers differ in power → **Weighted Round Robin**
- Requests vary in complexity → **Least Connections**
- Need session affinity → **IP Hash**
- Global app → **Geo-Based Routing**

---

## How to Study This

**Beginner path (first pass):**
Read files 01 → 02 → 03 → 04 in order. Focus on understanding concepts, not memorizing.

**Intermediate path:**
Read files 05 → 06 → 07. These get into distributed systems. Take notes on trade-offs.

**Advanced path:**
Files 07 (CAP) → 08 (Queues) → 09 (Case Study). Try to design the streaming app yourself before reading the solution.

**Interview prep:**
Review the Master Index → Go back to each file for weak areas → Practice drawing architecture diagrams.

---

*These notes cover the complete System Design course from beginner to advanced. Every concept explained with examples, analogies, and trade-offs.*
