# System Design Notes — Part 6: Load Balancers & Replication

---

## Part A: Load Balancers

### 1. Why Load Balancers Are Needed

Imagine your app has one server. It handles 1,000 requests/second fine. But now you have 1 million users. That one server will crash.

**Solution:** Add more servers (horizontal scaling). But now: how do you decide which server handles which request?

**That's the load balancer's job.**

A **Load Balancer** sits in front of your servers and distributes incoming requests across multiple servers.

```
                     ┌─ Server 1 (healthy)
Users → Load Balancer─┤─ Server 2 (healthy)
                     └─ Server 3 (healthy)
```

**Benefits:**
- **No single point of failure** — if one server dies, others keep working
- **Scalability** — add more servers without changing anything for users
- **Better performance** — no one server gets overwhelmed
- **Health monitoring** — automatically stops sending to unhealthy servers

**Types of load balancers:**
- **Hardware load balancers** — Physical devices, expensive, used by banks/telecom
- **Software load balancers** — Nginx, HAProxy (common in modern apps)
- **Cloud load balancers** — AWS ALB, Google Cloud Load Balancing, Azure LB

---

### 2. Load Balancing Algorithms

Different rules for deciding which server gets the next request.

---

#### 2.1 Round Robin

**How it works:** Send requests to servers in order, cycling through them.

```
Request 1 → Server 1
Request 2 → Server 2
Request 3 → Server 3
Request 4 → Server 1  (back to start)
Request 5 → Server 2
...
```

**Pros:**
- Extremely simple
- Distributes load evenly (in theory)

**Cons:**
- Doesn't account for server capacity (Server 1 might be more powerful than Server 3)
- Doesn't account for current load (Server 2 might already be handling 100 heavy requests while Server 3 is idle)

**Best for:** When all servers are identical and requests are roughly similar in complexity.

---

#### 2.2 Weighted Round Robin

**How it works:** Like Round Robin, but servers get different weights based on their capacity. More powerful servers get more requests.

**Example:**
- Server 1: weight 3 (most powerful)
- Server 2: weight 2
- Server 3: weight 1 (least powerful)

```
Request 1 → Server 1
Request 2 → Server 1
Request 3 → Server 1
Request 4 → Server 2
Request 5 → Server 2
Request 6 → Server 3
Request 7 → Server 1  (cycle restarts)
```

**Best for:** When servers have different capacities (e.g., you added a new powerful server alongside older smaller ones).

---

#### 2.3 Least Connections

**How it works:** Send each new request to the server with the fewest active connections (least busy).

**Example:**
```
Server 1: 50 active connections
Server 2: 30 active connections ← New request goes here
Server 3: 45 active connections
```

**Pros:**
- Smarter than Round Robin — accounts for current load
- Works well when requests take varying amounts of time

**Cons:**
- Requires tracking connection count in real-time
- Slightly more complex

**Best for:** Applications where some requests are much heavier than others (file processing, long API calls).

---

#### 2.4 IP Hash (Sticky Sessions)

**How it works:** Hash the client's IP address to always route them to the same server.

```
IP: 192.168.1.1 → hash → Server 2 (always)
IP: 10.0.0.5    → hash → Server 1 (always)
IP: 172.16.0.3  → hash → Server 3 (always)
```

**Why this matters — Stateful sessions:**
- Some apps store session data in memory on the server (old approach)
- If request 1 (login) goes to Server 1 and request 2 (dashboard) goes to Server 2, Server 2 has no session → user gets logged out

**IP Hash solves this:** Same user always goes to same server, so their session is always available.

**Pros:** Solves session affinity (sticky sessions)

**Cons:**
- If a server goes down, users on that server lose their sessions
- Uneven distribution if many users share the same IP (NAT/VPN scenarios)

**Modern alternative:** Use a distributed cache (Redis) for sessions instead of in-memory on the server. Then you don't need sticky sessions.

---

#### 2.5 GEO-Based Routing

**How it works:** Route users to the nearest data center based on their geographic location.

```
User in India    → Route to Asia-Pacific servers
User in Germany  → Route to European servers
User in USA      → Route to US servers
```

**Why it matters:**
- Network latency increases with distance (speed of light is a real constraint)
- India to USA = ~200-300ms latency
- India to India = ~10-20ms latency
- Serving users from nearby data centers dramatically reduces latency

**How it works technically:**
- DNS-based routing: Return different IP addresses based on where the DNS query came from
- Anycast routing: Same IP address, but network routes you to the nearest server

**Best for:** Global applications (Netflix, Google, Cloudflare all do this)

---

### 3. Load Balancer Layers

Load balancers work at different levels of the network stack:

| Layer | Type | What it routes on | Example |
|-------|------|------------------|---------|
| Layer 4 | Transport | IP + TCP/UDP port | Simple TCP routing |
| Layer 7 | Application | HTTP content, headers, URL | Smart routing by path, cookie |

**Layer 7 load balancers can do smart things like:**
- Route `/api/*` requests to API servers and `/static/*` to CDN
- Route based on cookie (for sticky sessions)
- Add/remove HTTP headers
- SSL termination (decrypt HTTPS here, pass plain HTTP to servers)

---

### 4. Health Checks

**The problem:** A server might crash, run out of memory, or slow down. You don't want to send traffic to a dead server.

**Health checks:** The load balancer periodically tests each server to see if it's working.

**Two types:**

**Passive health checks:** Monitor real traffic. If a server returns too many errors or times out, mark it as unhealthy.

**Active health checks:** Load balancer actively sends a test request to each server every few seconds.
```
Load Balancer → GET /health → Server 1
             ← 200 OK (Server 1 is healthy)
Load Balancer → GET /health → Server 2
             ← 500 Error (Server 2 is unhealthy!)
```

When a server fails health checks:
1. Load balancer stops routing to it
2. Alerts are triggered
3. When the server recovers and passes health checks, it's added back automatically

**Health check endpoint example (what the server returns):**
```json
{
  "status": "healthy",
  "database": "connected",
  "cache": "connected",
  "memory_usage": "45%",
  "uptime": "5 days, 3 hours"
}
```

---

## Part B: Replication

### 5. What is Replication?

**Replication** is keeping copies of your data on multiple database servers simultaneously.

**Why?**
- **Availability:** If one database server crashes, another copy is still there
- **Read scalability:** Multiple replicas can handle read queries simultaneously
- **Disaster recovery:** Data center fire? Your replica in another city still has all the data
- **Geographic distribution:** Serve reads from a nearby replica

---

### 6. Replication Algorithms

#### 6.1 Single Leader Replication (Primary-Replica)

**How it works:**
- One server is the **leader** (also called primary or master) — all **writes** go here
- Multiple **followers** (replicas, slaves) — copies of the leader's data
- Followers can serve **reads** (but not writes)
- Leader sends all changes to followers to keep them in sync

```
           Writes → [Leader] → Replicates changes to...
Reads ←    [Replica 1]
Reads ←    [Replica 2]
Reads ←    [Replica 3]
```

**Flow:**
1. App writes to Leader: "Update user 123's email"
2. Leader saves the change
3. Leader sends the change to all Replicas (replication log)
4. Replicas apply the change

**Pros:**
- Simple to understand
- Reads can be scaled by adding replicas
- Replicas are ready for failover if leader dies

**Cons:**
- All writes go to one server (write bottleneck)
- If leader fails, you need to elect a new leader (brief downtime)
- Replicas might have slightly stale data (replication lag)

**Used by:** MySQL, PostgreSQL, MongoDB (in replica set mode)

---

#### 6.2 Multi-Leader Replication

**How it works:** Multiple servers can accept writes. Each leader replicates its changes to all other leaders.

```
[Leader 1] ↔ replicates with ↔ [Leader 2] ↔ replicates with ↔ [Leader 3]
```

**When it's useful:**
- **Multi-datacenter setup:** Leader in each data center. Local writes are fast (no cross-continent write latency). Each data center syncs with others.
- **Offline apps:** Google Docs mobile works offline. Changes sync when you reconnect.

**Big problem — Conflicts:**
If two leaders accept different writes to the same data at the same time:
- Leader 1 updates user email to alice@gmail.com
- Leader 2 updates same user email to alice@yahoo.com
- Which one wins?

**Conflict resolution strategies:**
- **Last Write Wins (LWW):** The write with the later timestamp wins. Simple but can lose data.
- **Application-level resolution:** App code decides how to merge (Google Docs does this for text)
- **CRDT (Conflict-free Replicated Data Types):** Mathematical structures that always merge correctly

**Best for:** Multi-datacenter setups, collaborative apps (Google Docs, Notion)

---

#### 6.3 Leaderless Replication

**How it works:** There is no single leader. Clients write to multiple replicas directly. Reads are also done from multiple replicas.

```
Client writes to: Replica 1, Replica 2, Replica 3 (all at once)
Write succeeds if at least W replicas acknowledge
Client reads from: Replica 1, Replica 2, Replica 3
Read succeeds with latest value if at least R replicas respond
```

**Used by:** Amazon DynamoDB, Apache Cassandra, Riak

**Key insight (Quorum):** For consistency, you need W + R > N where:
- N = total replicas
- W = write quorum (how many must acknowledge write)
- R = read quorum (how many must respond to read)

With N=3, W=2, R=2: W + R = 4 > 3 → guaranteed to see latest write

**Pros:**
- No single point of failure
- Highly available
- Writes can proceed even if some replicas are down

**Cons:**
- Potential for conflicting writes
- More complex consistency model
- Reads might return stale data if quorum not configured correctly

---

### 7. Sync vs Async Replication

This defines when the leader sends data to replicas.

#### Synchronous Replication
```
Client → Leader writes → Waits for ALL replicas to confirm → Responds "Success" to client
```

- **Pros:** Replicas always have latest data. No data loss on leader failure.
- **Cons:** Write is slow (must wait for all replicas to respond). If any replica is slow or down, the write stalls.

**Use case:** When data loss is absolutely unacceptable (financial transactions).

---

#### Asynchronous Replication
```
Client → Leader writes → Responds "Success" to client immediately
         → (In background) Leader replicates to followers
```

- **Pros:** Very fast writes. Leader doesn't wait for replicas.
- **Cons:** If leader crashes before replicating, data can be lost. Replicas might be slightly behind (replication lag).

**Use case:** When performance matters more than perfect consistency (social media posts, logs).

---

#### Semi-Synchronous (Common in practice)
```
Leader must get acknowledgment from at least ONE replica before responding.
Other replicas replicate asynchronously.
```

This balances safety (at least one copy is safe) with performance (don't wait for all replicas).

---

### 8. Quorum

**What it is:** The minimum number of nodes that must agree for an operation to be considered successful.

**In a system with N replicas:**
- **Write Quorum (W):** At least W nodes must confirm the write
- **Read Quorum (R):** At least R nodes must respond to the read

**The Quorum rule for consistency:** `W + R > N`

| N | W | R | W+R | Consistent? |
|---|---|---|-----|-------------|
| 3 | 2 | 2 | 4 | ✅ Yes (4 > 3) |
| 3 | 1 | 1 | 2 | ❌ No (2 ≤ 3) |
| 3 | 3 | 1 | 4 | ✅ Yes |
| 5 | 3 | 3 | 6 | ✅ Yes (6 > 5) |

**Tuning quorum for different needs:**

- **W=N, R=1:** All replicas must confirm writes. Reads from any one replica. → Slow writes, fast reads
- **W=1, R=N:** Write to one replica. Read from all replicas. → Fast writes, slow reads
- **W=N/2+1, R=N/2+1:** Balanced. Most common Cassandra configuration.

---

## 9. Failover — What Happens When the Leader Dies

When the leader crashes:

1. **Detect failure:** Followers notice the leader hasn't sent a heartbeat in X seconds
2. **Elect new leader:** Followers vote to elect one of themselves as the new leader (usually the most up-to-date one)
3. **Reconfigure clients:** Clients are redirected to the new leader
4. **Old leader returns:** Old leader must recognize it's no longer leader and become a follower

**Challenges:**
- **Split Brain:** Two servers both think they're the leader. Both accept writes. Data diverges. Very dangerous — especially for databases.
- **Data loss:** If old leader had writes that hadn't replicated yet
- **Election time:** Brief unavailability while new leader is elected

**Tools that manage this automatically:** ZooKeeper, Raft consensus algorithm (used by etcd, Consul), Paxos

---

## 10. Summary

### Load Balancer Algorithms

| Algorithm | How | Best For |
|-----------|-----|----------|
| Round Robin | Cycle through servers | Equal servers, similar requests |
| Weighted Round Robin | More weight = more requests | Servers with different capacities |
| Least Connections | Route to least busy server | Variable request complexity |
| IP Hash | Same IP = same server | Session affinity |
| GEO-Based | Route to nearest data center | Global apps |

### Replication

| Type | Writes | Pros | Cons |
|------|--------|------|------|
| Single Leader | Leader only | Simple | Write bottleneck |
| Multi Leader | Multiple leaders | Multi-datacenter | Conflict resolution complex |
| Leaderless | Any node | Highly available | Complex consistency |
| Sync replication | Wait for all replicas | No data loss | Slow |
| Async replication | Don't wait | Fast | Potential data loss |

---

*Next: Part 7 — Partitioning (Sharding) & CAP Theorem*
