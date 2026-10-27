# System Design Notes — Part 9: Monitoring, Observability & Final Case Study

---

## Part A: Monitoring and Observability

### 1. Why Monitoring Matters

**Without monitoring:** You're flying blind. You find out about problems only when users complain. By then, thousands are affected.

**With monitoring:** You detect problems the moment they start. Often you fix them before users even notice.

**Real scenario:**
- 2AM: Database query time spikes from 50ms to 5000ms
- Without monitoring: Support emails flood in at 8AM when users start their workday
- With monitoring: Alert fires at 2:01AM, on-call engineer wakes up, fixes it by 2:30AM before any user notices

---

### 2. The Three Pillars of Observability

#### Logs
Text records of discrete events that happened in your system.

```
2024-01-15 10:05:23 INFO  User 12345 logged in successfully
2024-01-15 10:05:45 ERROR Failed to charge card: card_declined for order 789
2024-01-15 10:06:01 WARN  Database query took 3.2s (threshold: 1s)
```

**Log levels:**
- **DEBUG:** Detailed developer info (disabled in production)
- **INFO:** Normal operational events
- **WARN:** Something unexpected, but not breaking
- **ERROR:** Something failed, needs attention
- **FATAL:** System is crashing

**Structured logs (JSON):**
```json
{
  "timestamp": "2024-01-15T10:05:45Z",
  "level": "ERROR",
  "service": "payment-service",
  "user_id": 12345,
  "order_id": 789,
  "error": "card_declined",
  "message": "Payment failed"
}
```

Structured logs are **searchable** — you can filter by user_id, service, error type.

**Log aggregation tools:** Elasticsearch + Kibana (ELK stack), Grafana Loki, Splunk, Datadog

---

#### Metrics
Numerical measurements over time. Unlike logs (individual events), metrics show trends.

```
CPU usage:    [10%, 12%, 15%, 45%, 80%, 95%, 60%, 20%]
Request/sec:  [100, 120, 140, 800, 900, 200, 150, 130]
Error rate:   [0%, 0%, 0%, 5%, 12%, 2%, 0%, 0%]
```

Metrics answer questions like:
- "Is CPU trending up over time?"
- "At what time does traffic peak?"
- "When did error rate spike?"

**Tools:** Prometheus + Grafana (most popular), Datadog, CloudWatch, InfluxDB

---

#### Traces (Distributed Tracing)
Track the complete journey of a request through multiple services.

```
User Request (total: 350ms)
    ├── API Gateway (5ms)
    ├── Auth Service (15ms)
    ├── Product Service (280ms)
    │       ├── Database query (250ms) ← BOTTLENECK
    │       └── Cache check (5ms)
    └── Response serialization (10ms)
```

Without tracing: "The request is slow, but which service is slow?"
With tracing: "Product Service is slow because of a database query."

**Tools:** Jaeger, Zipkin, Datadog APM, AWS X-Ray

---

### 3. API Monitoring Metrics

#### Throughput
**Definition:** Number of requests the system handles per unit of time.

```
Throughput = Requests per second (RPS) or Requests per minute (RPM)
```

**Why it matters:**
- Low throughput → system can't keep up with demand (capacity problem)
- Sudden drop in throughput → something might be wrong (fewer users or service down)
- Spike in throughput → traffic spike, might overwhelm system

**Example:**
- Normal: 1,000 requests/second
- Flash sale starts: 50,000 requests/second
- Alert fires: throughput exceeded threshold → scale up

---

#### Latency

**Definition:** Time from when a request is sent to when a response is received.

```
Latency = Response time = Time for one request to complete
```

**Percentile latency (how you should measure it):**

Don't use average — it hides outliers.

```
100 requests with response times:
10ms, 12ms, 15ms, 15ms, 20ms, 22ms, 25ms, 30ms, 35ms, 5000ms

Average: ~518ms (misleading — 9 requests were fine!)
P50: 20ms (50% of requests finish in 20ms or less)
P95: 35ms (95% finish in 35ms or less)
P99: 5000ms (99% finish in 5000ms or less)
```

P99 exposes that 1% of users have a terrible 5-second experience. Average would hide this.

**Standard targets:**
- API response time P99 < 500ms for good user experience
- <200ms P50 is excellent
- >1000ms P99 → investigate

---

#### Error Rate

**Definition:** Percentage of requests that return an error (5xx responses).

```
Error Rate = (Errors / Total Requests) × 100%
```

**What to alert on:**
- Error rate > 1% → Warning
- Error rate > 5% → Critical

**Types to track:**
- 4xx errors: Client errors (bad requests, auth failures) — usually not your fault
- 5xx errors: Server errors (your bugs, crashes) — always investigate

---

### 4. Machine Monitoring

#### CPU Usage
**What it measures:** How much of the processor's capacity is being used.

```
0-70%: Normal
70-85%: Watch closely
85%+:  Investigation needed — scale up or find bottleneck
100%:  System struggling, requests queuing up
```

**High CPU causes:**
- CPU-intensive code (complex algorithms, encryption)
- Infinite loop
- Too many concurrent requests
- Lack of caching (computing the same thing repeatedly)

---

#### Memory Usage

**What it measures:** How much RAM is being used.

**Problems:**
- **Memory leak:** Application continuously allocates memory and never frees it. Usage grows until the system runs out → crash.
- **Out of Memory (OOM) kill:** OS kills the process to reclaim memory

```
Normal: Memory stays relatively flat over time
Memory leak: Memory grows steadily over hours/days
```

---

#### Disk I/O

**What it measures:** How fast data is being read from / written to storage.

**Why it matters:**
- Databases are I/O intensive — slow disk = slow queries
- Log files filling up disk = crash

**Alert when:**
- Disk usage > 80% (add more storage or clean up)
- Disk I/O wait high (storage is the bottleneck)

---

#### Network I/O

**What it measures:** Data flowing in and out of a server.

**Why it matters:**
- Bandwidth saturation → network bottleneck, requests time out
- Unusual outbound traffic → possible data exfiltration (security concern)

---

### 5. Alerts and SLAs

#### Setting Alerts
Alerts notify engineers when metrics cross thresholds.

**Good alert:** Specific, actionable, not too noisy.
```
ALERT: Payment service error rate > 2% for 5 minutes
ALERT: Database CPU > 90% for 10 minutes
ALERT: API P99 latency > 2000ms
ALERT: Disk usage > 85%
```

**Bad alert:** Too sensitive → alert fatigue (engineers ignore alerts)
```
BAD: Alert if any request takes > 100ms  (fires constantly)
BAD: Alert if CPU > 50%  (normal operation)
```

---

#### SLA, SLO, SLI

**SLI (Service Level Indicator):** The actual metric you measure.
- "99.8% of requests returned successful response last month"

**SLO (Service Level Objective):** Your internal goal.
- "We want 99.9% successful requests"

**SLA (Service Level Agreement):** The external promise to customers.
- "We guarantee 99.5% uptime. If we miss, you get credits."

SLA is always less strict than SLO (you want internal buffer before breaching customer commitment).

---

### 6. Monitoring Tools Summary

| Tool | Primary Use |
|------|------------|
| Prometheus | Metrics collection and storage |
| Grafana | Metrics visualization and dashboards |
| Elasticsearch + Kibana | Log aggregation and search |
| Jaeger / Zipkin | Distributed tracing |
| PagerDuty / OpsGenie | Alert management and on-call scheduling |
| Datadog | All-in-one (metrics, logs, traces) |
| New Relic | Full-stack observability |
| AWS CloudWatch | Cloud infrastructure monitoring |

---

## Part B: Final Case Study — Designing a Video Streaming Application

### 7. Requirements

**Functional:**
- Users can upload videos
- Users can watch videos (streaming, not full download)
- Videos are available in multiple resolutions (360p, 720p, 1080p, 4K)
- Videos have titles, descriptions, thumbnails
- Users have feeds, recommendations
- Search for videos

**Non-Functional:**
- Scale to 1 billion users
- Videos must start playing quickly (<2 seconds buffering)
- 99.99% availability for watching (people can always watch)
- High durability for videos (never lose a video)
- Ingestion: Support millions of video uploads per day

---

### 8. System Design Thinking Process

**Step 1: Clarify requirements** — Ask questions before designing anything.
- How long are typical videos? (YouTube: minutes to hours. TikTok: seconds)
- Expected DAU (daily active users)?
- Read-heavy or write-heavy? (Video platforms: much more reads/views than uploads)
- What's the monetization model? (Affects what data we track)

**Step 2: Estimate scale**
- 1 billion users, 100 million daily active users
- Upload: 100 hours of video uploaded per minute (YouTube's real stat)
- Watch: 500 million video views per day
- Storage: 1 hour of 1080p video ≈ 1GB → 100 hours/min × 60min × 1GB × 365 days/year = petabytes

**Step 3: Design the components**

---

### 9. Video Processing Architecture

**Upload flow:**

```
User → Upload Service → Raw Video Storage (S3)
                              ↓
                      Message Queue (Kafka)
                              ↓
              ┌───────────────────────────────┐
              ↓           ↓           ↓       ↓
         Transcoding  Thumbnail  Metadata  Subtitle
          Service     Service   Service   Service
              ↓           ↓           ↓
         Processed    CDN Upload  Database
          Videos
```

**Detailed upload steps:**

1. **User uploads raw video file** to an Upload Service
2. Upload Service stores raw video in **object storage (S3/GCS)**
3. Upload Service publishes event to **message queue**: "New video uploaded: video_id=ABC"
4. **Transcoding workers** pick up the job:
   - Convert original video to multiple formats (MP4, WebM)
   - Create multiple resolutions (360p, 720p, 1080p, 4K)
   - This is compute-intensive — uses GPU instances
5. **Thumbnail service** extracts frames, generates thumbnails
6. **Metadata service** extracts duration, aspect ratio, audio tracks
7. Processed videos are uploaded to **CDN (Content Delivery Network)**
8. Video status updated in database: "Video is ready to watch"
9. User gets a notification: "Your video is live!"

---

### 10. Video Playback Architecture (The Most Critical Path)

**Watch flow — must be fast and reliable:**

```
User → CDN (nearest PoP) → Video chunks delivered
```

**Adaptive Bitrate Streaming (ABR):**

The video is NOT streamed as one huge file. It's delivered in small chunks (2-10 seconds each). The player switches quality based on network speed.

```
Network fast → Player requests 1080p chunk
Network slows → Player automatically switches to 720p
Network degrades more → Player drops to 480p
Network improves → Player gradually goes back to 1080p
```

**This is why Netflix/YouTube rarely buffers.** The quality adapts instead of buffering.

**Standards used:** HLS (HTTP Live Streaming), MPEG-DASH

**CDN (Content Delivery Network):**
- Videos are cached at hundreds of edge locations worldwide
- User in Mumbai gets video from Mumbai CDN node, not US servers
- Dramatically reduces latency and load on origin servers
- CDN providers: Cloudflare, Akamai, Amazon CloudFront, Fastly

**CDN cache hit ratio for popular videos:**
- Top 1% of videos (viral content) might have 99% cache hit rate
- Users watch from CDN, origin server barely touched

---

### 11. Database Design for the Streaming App

**What to store where:**

| Data | Database Choice | Why |
|------|----------------|-----|
| User accounts | PostgreSQL | Structured, ACID needed |
| Video metadata (title, tags, description) | PostgreSQL + Elasticsearch | Structured + Search |
| Video view counts | Redis (cache) + async DB write | Very high frequency updates |
| Comments | Cassandra | High write throughput, time-ordered |
| Subscriptions/followers | Cassandra or Neo4j | High volume, graph-like |
| Watch history | Cassandra | High volume, time-series |
| Recommendations | Separate ML service | Computation, not just storage |
| Video files | Object Storage (S3) | Binary blob storage |

---

### 12. Recommendations and Search

**Search (How users find videos):**
- Videos indexed in **Elasticsearch** with title, tags, description, transcript
- Full-text search, filtering by category, duration, date
- Search service separate from main app

**Recommendations:**
- Not simple database queries — requires ML models
- Inputs: What you watched, what similar users watched, video engagement data
- Recommendation engine runs offline/periodically (not real-time)
- Results stored in fast cache (Redis)
- When you open homepage, recommendations are already computed and ready

---

### 13. Handling Scale — Key Decisions

#### Microservices Architecture
Instead of one monolithic app, split into independent services:

```
[Upload Service] [Transcoding Service] [Streaming Service]
[User Service] [Auth Service] [Search Service]
[Recommendation Service] [Notification Service] [Analytics Service]
```

**Why:**
- Each service scales independently (transcoding needs more compute, streaming needs more bandwidth)
- Teams can work on different services independently
- One service failing doesn't bring down everything

---

#### Sharding the Database

User data sharded by `user_id`:
```
Users 1-1M → Shard 1
Users 1M-2M → Shard 2
...
```

Video data sharded by `video_id`:
```
Videos by hash(video_id) % N shards
```

---

#### Handling Hot Videos (Viral Content)

When a video goes viral, millions of people watch simultaneously.

**Solutions:**
1. **CDN:** 99% of requests served by CDN, never touch origin
2. **Multi-CDN:** Use multiple CDN providers for redundancy
3. **Pre-warming cache:** When a video starts trending, proactively push it to more CDN nodes
4. **Rate limiting uploads:** Prevent abuse while maintaining good user experience

---

#### Eventual Consistency for View Counts

**Problem:** A viral video gets 1,000 views per second. Writing "views + 1" to database 1,000 times/second would kill the database.

**Solution:**
1. Increment counter in Redis (in-memory, very fast): `INCR video:ABC:views`
2. Every 60 seconds, a background job writes the count from Redis to the database
3. Users see approximate count — "1.2M views" not exactly "1,234,567 views"
4. Eventual consistency is acceptable for view counts

---

### 14. Complete Architecture Diagram

```
                         ┌─────────────────────────────────┐
                         │         USERS                    │
                         └──────────────┬──────────────────┘
                                        │
                         ┌──────────────▼──────────────────┐
                         │      CDN (Cloudflare/Akamai)     │
                         │  (Serves cached videos globally) │
                         └──────────────┬──────────────────┘
                                        │ (cache miss)
                         ┌──────────────▼──────────────────┐
                         │        Load Balancer             │
                         └────────┬────────┬───────────────┘
                                  │        │
              ┌───────────────────▼─┐   ┌──▼─────────────────────┐
              │   API Gateway        │   │    Streaming Service    │
              │  (Auth, Rate limit)  │   │  (Video delivery)      │
              └──────────┬──────────┘   └────────────────────────┘
                         │
         ┌───────────────┴─────────────────────────┐
         │               │              │           │
    ┌────▼──────┐   ┌────▼──────┐ ┌───▼──────┐ ┌─▼────────────┐
    │  Upload   │   │  User     │ │  Search  │ │ Recommend.   │
    │  Service  │   │  Service  │ │  Service │ │ Service      │
    └────┬──────┘   └────┬──────┘ └───┬──────┘ └─┬────────────┘
         │               │            │           │
         ▼               │        Elasticsearch  Redis
    [Kafka Queue]    PostgreSQL       │
         │           (sharded)    ML Models
    ┌────▼──────────────────────────────┐
    │        Transcoding Workers        │
    │    (Multiple GPU instances)       │
    └────────────────┬──────────────────┘
                     │
              Object Storage (S3)
                     │
              CDN Origin Push
```

---

### 15. Trade-offs Made in This Design

| Decision | Trade-off |
|----------|-----------|
| Eventual consistency for view counts | Accuracy vs Performance |
| Async video processing | Slower time-to-live vs Better user experience (no waiting) |
| Multiple video resolutions | Storage cost vs User experience |
| CDN for delivery | Cost vs Performance and scale |
| Microservices | Complexity vs Scalability |
| Cassandra for comments | No ACID vs High write throughput |
| Redis for hot data | Cost (RAM expensive) vs Speed |

---

## 16. Summary: How to Think About System Design

**The mindset:**

1. **Clarify before designing** — Ask questions. Understand scale, constraints, and priorities.

2. **Estimate scale** — Numbers matter. 1,000 users vs 1 billion users need completely different designs.

3. **Start simple, add complexity only when needed** — A monolith is fine for early stages. Add microservices when you actually need them.

4. **Know your trade-offs** — Every decision has pros and cons. Know what you're giving up.

5. **Design for failure** — Assume everything will fail. Add redundancy.

6. **Use the right tool for the job** — Don't use SQL when you need high-speed caching. Don't use NoSQL when you need ACID transactions.

7. **Think about the data flow** — Where does data come from? Where does it go? What transforms it?

8. **Consider consistency vs availability** — Does this need to be perfectly consistent, or is eventual consistency okay?

9. **Monitor everything** — You can't improve what you don't measure.

10. **Iterate** — No design is perfect the first time. Build, measure, learn, improve.

---

## 17. Complete Course Summary

| Topic | Key Concepts |
|-------|-------------|
| System Design Basics | Components, trade-offs, mindset |
| Requirements | Functional vs Non-Functional (SARPSOM) |
| DNS | Root → TLD → Authoritative, TTL |
| APIs | REST, SOAP, GraphQL, gRPC, WebSockets |
| SQL | Tables, joins, constraints, ACID |
| NoSQL | Key-value, document, graph, columnar |
| Caching | Hit/miss, TTL, read/write strategies, LRU |
| Load Balancers | Round Robin, Least Connections, IP Hash, Geo |
| Replication | Single/Multi/Leaderless, Sync/Async, Quorum |
| Sharding | Range, Hash, Consistent Hashing, Hotspots |
| CAP Theorem | CP vs AP, Eventual Consistency |
| Message Queues | FIFO, Priority, Pub/Sub, Poison Messages |
| Fault Tolerance | Hardware/Software/Human failures, Circuit Breaker |
| Monitoring | Metrics, Logs, Traces, SLA/SLO/SLI |
| Streaming Design | CDN, ABR, Transcoding, Microservices |

---

*End of Complete System Design Notes*
