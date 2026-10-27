# System Design Notes — Part 5: Caching

---

## 1. Why is Caching Important?

**The problem:** Databases are slow compared to memory.
- Reading from RAM: ~100 nanoseconds
- Reading from SSD: ~100 microseconds (1000x slower)
- Reading from a database (with network): ~10 milliseconds (100,000x slower)
- Fetching data from a remote API: up to 500ms+

**The solution — Caching:** Store frequently-accessed data in a faster storage layer (usually RAM) so you don't need to go to the slow source every time.

**Real-world analogy:**
You're a chef. The recipe book (database) is in the storeroom. Every time you want to make pasta, do you walk to the storeroom to check the recipe? No — you memorize the recipe (cache it in your brain). That's caching.

**What gets cached:**
- Database query results
- Computed results (analytics, recommendations)
- API responses (external weather API, stock prices)
- HTML pages
- Session data
- Images/static files (via CDN)

**Popular caching tools:** Redis, Memcached, Varnish, Cloudflare CDN

---

## 2. Cache Hit and Cache Miss

**Cache Hit:** The data you need is already in the cache. Fast! ✅
- Response time: microseconds

**Cache Miss:** The data is NOT in the cache. You must go to the database (slow).
- Response time: milliseconds
- After fetching from DB, you store the result in cache for next time

**Cache Hit Ratio:**
```
Hit Ratio = Cache Hits / (Cache Hits + Cache Misses)
```

A hit ratio of 90%+ is generally good. It means 90% of requests are served from fast cache.

**Example:**
- 100 requests for "top 10 trending posts"
- 90 served from cache (cache hit)
- 10 go to database (cache miss)
- Hit ratio = 90%

---

## 3. TTL — Time To Live

**What it is:** An expiration time set on cached data. After TTL expires, the cache entry is deleted.

**Why needed:** Cached data can become stale (outdated). If product prices change, you don't want to serve old prices forever.

**Example:**
```
Cache "user_123_profile" with TTL = 300 seconds (5 minutes)
```
- For 5 minutes, all requests for user 123's profile are served from cache
- After 5 minutes, the cache entry expires
- Next request fetches fresh data from DB and stores it in cache again

**TTL trade-offs:**
- **Short TTL (e.g., 10 seconds):** Data is always fresh, but more DB load because cache expires quickly
- **Long TTL (e.g., 24 hours):** Less DB load, but data might be stale for a long time

**Choosing TTL:**
- User profile: 5-15 minutes (doesn't change often)
- Product price: 1-5 minutes (can change)
- Live sports score: 10-30 seconds (changes frequently)
- Static config data: 1 hour or more (rarely changes)

---

## 4. Cache Strategies

Different strategies for how/when you read from and write to the cache.

---

### 4.1 Read-Through Cache

**How it works:**
1. Application always reads from cache
2. On cache hit → return data immediately
3. On cache miss → cache itself fetches data from DB, stores it, returns it

```
App → Cache → (cache miss) → Cache fetches from DB → Cache stores → Returns to App
```

**Diagram:**
```
Request → Cache
              ↓ Miss
              → DB
              ← Data
              Store in Cache
              ← Return to App
```

**Pros:**
- Application code is simple — just always talk to the cache
- Cache is always populated with data that's actually used

**Cons:**
- First request is always slow (cache miss, called cold start)
- Cache and DB must stay in sync

**Best for:** Read-heavy applications where the same data is requested multiple times.

---

### 4.2 Write-Through Cache

**How it works:**
1. Application writes to the cache
2. Cache immediately writes to the database too
3. Both cache and DB are updated together

```
App → Write to Cache → Cache writes to DB (synchronously)
```

**Pros:**
- ✅ Cache is always consistent with DB (no stale data)
- ✅ Read-through works perfectly alongside this

**Cons:**
- ❌ Writes are slower (must write to both cache and DB)
- ❌ Cache fills up with data that might never be read again

**Best for:** When you can't afford stale reads — financial data, user account data.

---

### 4.3 Write-Around Cache

**How it works:**
- Writes go directly to the database, **bypassing the cache**
- Cache is only populated on reads (cache miss → fetch from DB → store in cache)

```
App → Write directly to DB (cache not updated)
App → Read → Cache miss → Fetch from DB → Store in Cache
```

**Pros:**
- ✅ Cache isn't polluted with data that's written but rarely read

**Cons:**
- ❌ First read after a write is always a cache miss (slower)

**Best for:** Data that is written once and read infrequently. Example: Log data, audit trails, one-time reports.

---

### 4.4 Write-Back Cache (Write-Behind)

**How it works:**
1. Application writes to cache only
2. Cache acknowledges the write immediately
3. Cache writes to DB **asynchronously** (in the background, after a delay)

```
App → Write to Cache → App gets "success" immediately
                    → (Later, asynchronously) Cache writes to DB
```

**Pros:**
- ✅ Extremely fast writes — no waiting for DB
- ✅ Can batch multiple writes into fewer DB operations (efficient)

**Cons:**
- ❌ **Risk of data loss** — If the cache crashes before writing to DB, data is lost
- ❌ More complex to implement

**Best for:** Write-heavy applications where some data loss is acceptable. Example: Analytics counters, game leaderboards, activity tracking.

---

### 4.5 Cache Strategy Comparison

| Strategy | Write Destination | Read Source | Consistency | Write Speed |
|----------|------------------|-------------|-------------|-------------|
| Read-Through | DB directly | Cache (miss → DB) | Good | Normal |
| Write-Through | Cache + DB together | Cache | Excellent | Slow |
| Write-Around | DB directly | Cache (miss → DB) | Good | Normal |
| Write-Back | Cache first, DB later | Cache | Risk of loss | Very Fast |

---

## 5. Cache Eviction Policies

**The problem:** Cache has limited size (RAM is expensive). When the cache is full and you need to store new data, what do you remove?

**Eviction policies** define the rules for choosing what to remove.

---

### 5.1 LRU — Least Recently Used

**Rule:** Remove the item that was **accessed least recently** (has gone the longest without being used).

**Logic:** If data hasn't been used in a while, it's probably not needed.

**Example:**
```
Cache has: [A (used 10min ago), B (used 5min ago), C (used 1min ago)]
Cache is full. Need to add D.
LRU removes A (least recently used).
Cache becomes: [B, C, D]
```

**Use case:** General-purpose caching. Most popular eviction policy.

**How it's implemented:** Linked list + hashmap (O(1) get and put)

---

### 5.2 LFU — Least Frequently Used

**Rule:** Remove the item that has been **accessed the fewest times**.

**Logic:** If data is rarely used, it's probably not important.

**Example:**
```
Cache:
- A: accessed 100 times
- B: accessed 3 times
- C: accessed 50 times
Cache full, adding D.
LFU removes B (fewest accesses).
```

**Pros:** Better for items that are always popular (will never be evicted despite not being recent)

**Cons:** New items have low counts and get evicted before they get a chance to become popular — "cache pollution" with hot items that were popular only temporarily

**Use case:** When long-term popularity matters (music streaming: top charts)

---

### 5.3 FIFO — First In, First Out

**Rule:** Remove the item that was **added to the cache first** (oldest entry by insertion time).

**Logic:** Like a queue — first in, first out.

**Example:**
```
Items added in order: A, B, C, D, E
Cache full. Adding F.
FIFO removes A (added first).
```

**Pros:** Simple to implement

**Cons:** Doesn't consider usage. A very popular item added early will be evicted even if still frequently used.

**Use case:** Simple systems, or when all cached items have roughly equal lifetime (like network packets)

---

### 5.4 MRU — Most Recently Used

**Rule:** Remove the item that was **accessed most recently**.

This sounds counterintuitive — why evict what's being used?

**Logic:** In some patterns, once you've accessed an item, you won't need it again for a long time.

**Example use case:** Media player playlist. After you watch a video, you're unlikely to watch it again immediately. The most recently watched video can be evicted.

**Use case:** Scanning large datasets sequentially where you'll never look at the same data twice.

---

### 5.5 LIFO — Last In, First Out

**Rule:** Remove the item that was **most recently added** (like a stack — last in, first out).

**Example:**
```
Items added: A, B, C
Cache full. Adding D.
LIFO removes C (most recently added).
```

**Use case:** Rare. Useful in undo systems and specific task scheduling scenarios.

---

### 5.6 Eviction Policy Comparison

| Policy | Evicts | Best For |
|--------|--------|----------|
| LRU | Least recently used | General purpose |
| LFU | Least frequently used | Long-term popularity matters |
| FIFO | Oldest insertion time | Simple use cases |
| MRU | Most recently used | Sequential scan workloads |
| LIFO | Most recently added | Stack-like patterns |

**90% of the time, LRU is the right choice.** Redis uses LRU by default.

---

## 6. Cache Design Considerations

### Where to Place the Cache

**1. In-process cache (local):**
- Cache lives inside the application process (in-memory HashMap)
- Extremely fast (no network)
- Problem: Each server has its own cache. Server 1's cache ≠ Server 2's cache. Inconsistency.
- Good for: Single-server apps, configuration data, lookup tables

**2. Distributed cache (external):**
- Shared cache server (like Redis, Memcached) that all app servers connect to
- Slightly slower (network hop), but all servers see the same cache
- Can be scaled independently
- Good for: Multi-server apps, session storage, shared data

```
App Server 1 ↘
App Server 2 → Redis Cache → Database
App Server 3 ↗
```

---

### Cache Invalidation — The Hard Problem

**"There are only two hard problems in computer science: naming things and cache invalidation."**

**The problem:** When the database is updated, the cache might still have the old value.

**Solutions:**

1. **TTL expiry:** Just let the cache expire naturally. Accept some stale data.
2. **Active invalidation:** When you update DB, also delete the cache entry so the next read forces a fresh fetch.
3. **Cache-aside + delete:** Pattern where the app manages cache explicitly:
   - Read: Check cache → miss → read DB → store in cache
   - Write: Write to DB → delete from cache (don't update, just delete)

---

### Thundering Herd Problem

**The problem:** A popular cache entry expires. Suddenly 1,000 requests all miss the cache at the same time. All 1,000 hit the database simultaneously. Database overloads.

**Solutions:**
1. **Mutex/Lock:** First request that misses gets a lock to fetch from DB. Others wait. Only one DB call is made.
2. **Probabilistic early expiration:** Randomly refresh cache slightly before TTL expires, so it never goes cold for everyone at once.
3. **Background refresh:** Before TTL expires, a background job refreshes the cache proactively.

---

## 7. Real-World Caching Example: Twitter

**What Twitter caches:**
- **Timeline cache (Redis):** When you open Twitter, your timeline is pre-computed and cached. You don't wait for a fresh DB query.
- **User profile cache:** Profile data cached for 15 minutes
- **Trending topics cache (Redis):** Updated every few minutes, served to millions
- **CDN cache:** Images, videos, JavaScript files cached at edge servers near users

**Without caching:**
- Opening Twitter = 1 database query per user per visit
- 100 million active users = 100 million DB queries simultaneously
- Database would collapse

---

## 8. Summary

| Concept | Key Point |
|---------|-----------|
| Cache Hit | Data found in cache → fast |
| Cache Miss | Data not in cache → go to DB → slow |
| TTL | Expiry time for cache entries |
| Read-Through | Cache fetches from DB on miss |
| Write-Through | Writes go to cache AND DB together |
| Write-Around | Writes go directly to DB, bypassing cache |
| Write-Back | Writes to cache first, DB later (async) — fast but risky |
| LRU | Evict least recently used — most common policy |
| LFU | Evict least frequently used |
| FIFO | Evict oldest inserted entry |

---

*Next: Part 6 — Load Balancers*
