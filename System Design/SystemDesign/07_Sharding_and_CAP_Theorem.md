# System Design Notes — Part 7: Partitioning (Sharding) & CAP Theorem

---

## Part A: Partitioning (Sharding)

### 1. What is Partitioning?

**The problem:** Even with replication, if you have 100TB of data, every replica must store all 100TB. You can't add more replicas to increase storage capacity.

**Partitioning (Sharding):** Split the dataset across multiple machines. Each machine (shard) stores only a **portion** of the total data.

```
Without Sharding:
Server 1: [ALL 100TB of data]
Server 2: [copy of ALL 100TB] ← replication

With Sharding:
Shard 1: [Users A-H, 25TB]
Shard 2: [Users I-P, 25TB]
Shard 3: [Users Q-Z, 25TB]
Shard 4: [Recently added, 25TB]
```

**Benefits:**
- Store more data than any single machine can hold
- Distribute write load across multiple machines
- Higher throughput — queries on different shards can run in parallel

**Used by:** Cassandra, MongoDB, DynamoDB, MySQL (manual sharding), PostgreSQL (with extensions)

---

### 2. Partition Strategies

#### 2.1 Partition by Key Range (Range-Based Partitioning)

**How it works:** Assign each shard a range of key values.

**Example — Partitioning users by last name:**
```
Shard 1: A - G
Shard 2: H - N
Shard 3: O - Z
```

Or partitioning by date:
```
Shard 1: January 2024
Shard 2: February 2024
Shard 3: March 2024
```

**Pros:**
- Range queries are efficient: "Get all orders from Jan 2024" → only hits Shard 1
- Data is sorted — easy to do range scans

**Cons:**
- **Hotspots:** If most users have last names starting with A-G, Shard 1 gets far more traffic than others. Uneven load.
- **Temporal hotspots:** Most recent data is always newest shard → all current writes go to one shard

---

#### 2.2 Partition by Hash (Hash-Based Partitioning)

**How it works:** Apply a hash function to the partition key. The hash output determines which shard stores the data.

```
shard = hash(user_id) % number_of_shards
```

**Example (4 shards):**
```
user_id=1001: hash(1001) % 4 = 1 → Shard 1
user_id=1002: hash(1002) % 4 = 2 → Shard 2
user_id=1003: hash(1003) % 4 = 3 → Shard 3
user_id=1004: hash(1004) % 4 = 0 → Shard 0
user_id=1005: hash(1005) % 4 = 1 → Shard 1
```

**Pros:**
- ✅ Even distribution — hash functions spread data uniformly
- ✅ Eliminates range hotspots

**Cons:**
- ❌ Range queries are broken: "Get all orders from Jan 2024" must check ALL shards (scatter-gather)
- ❌ **Resharding problem:** If you add a 5th shard, `hash(key) % 5` gives completely different assignments. Almost all data must move to new shards. Very expensive.

**Solution to resharding: Consistent Hashing**

Instead of `hash(key) % N`, use a hash ring:
- All shards are placed on a circle (hash ring)
- Each key hashes to a point on the ring and goes to the next shard clockwise
- Adding a new shard only moves a small portion of keys (not all of them)

Used by: Cassandra, DynamoDB, Riak, Amazon's internal systems

---

#### 2.3 Secondary Index Partitioning

**The problem:** With sharding, how do you handle queries that don't use the partition key?

**Example:** User data is partitioned by `user_id`. But you want to query "Find all users in Mumbai." The city isn't the partition key — you'd have to check all shards.

**Two approaches:**

**Local Secondary Index (Document-based partitioning):**
- Each shard maintains its own index for the records it holds
- Query all shards in parallel, merge results (scatter-gather)
- Writes are fast (only update local shard's index)
- Reads require querying all shards

**Global Secondary Index (Term-based partitioning):**
- A separate index is created that's itself partitioned
- "City: Mumbai → [user_ids: 1, 5, 8, 23, 101, ...]" stored on a specific shard
- Reads are fast (query the index shard → get IDs → fetch records)
- Writes are slow (must update potentially many index shards)

**Examples:**
- DynamoDB: Supports both local and global secondary indexes
- Elasticsearch: Optimized for this use case (search across sharded data)

---

### 3. Hotspots and Challenges

#### What is a Hotspot?

A **hotspot** is when one shard receives disproportionately more requests than others.

**Examples:**
- Celebrity user: Justin Bieber has 100 million followers. Any activity from his account causes massive traffic to his data's shard.
- Time-based: All writes for today go to today's shard.
- Sequential IDs: If you partition by ID range and always insert new records, the "last" shard gets all inserts.

**Solutions to hotspots:**

1. **Add random prefix to hot keys:**
   ```
   Instead of key: "user_bieber"
   Use: "user_bieber_0", "user_bieber_1", ..., "user_bieber_9"
   Spread data across 10 sub-shards
   ```
   (Read must combine from all 10 sub-keys — trade-off)

2. **Dedicated shards for hot data:** Isolate celebrities/hot data to their own dedicated shards with more resources.

3. **Caching:** Cache hot data heavily so it rarely hits the database shard at all.

---

#### Other Sharding Challenges

**Cross-shard joins:** If a query needs data from multiple shards, you must query all relevant shards and join in application code. Database-level joins are not possible across shards.

**Cross-shard transactions:** ACID transactions across shards require distributed transaction protocols (2-phase commit, Saga pattern) — complex and slow.

**Rebalancing:** When adding/removing shards, data must be moved. This is expensive and must be done carefully without downtime.

**Determining the right shard:** Application or a routing layer must know which shard has the data. This logic must be consistent and correct.

---

## Part B: CAP Theorem

### 4. What is the CAP Theorem?

**CAP Theorem** states that in a **distributed system**, you can only guarantee **2 out of 3** of these properties simultaneously:

```
         C
        /|\
       / | \
      /  |  \
     A---+---P
```

- **C = Consistency**
- **A = Availability**
- **P = Partition Tolerance**

**Proven by Eric Brewer in 2000.** One of the most important theorems in distributed systems.

---

### 5. Understanding Each Property

#### Consistency (C)
**Definition:** Every read receives the most recent write (or an error). All nodes see the same data at the same time.

**Think of it as:** If you write "balance = $500" to one node, anyone reading from any node immediately sees $500. Not $450 (old value), not different values on different nodes.

**Example of violation:** You transfer money from account A to B. Bank system debits A immediately. A split-second later you check your balance — it shows you still have money that was already debited (inconsistency).

---

#### Availability (A)
**Definition:** Every request receives a response (not necessarily the most recent data), even if some nodes are down.

**Think of it as:** The system never says "I'm too busy" or "I don't know." It always responds — even if the response might be slightly outdated.

**Example:** Amazon's shopping cart. Even if some nodes are down, you can always add items to your cart. The cart might show slightly inconsistent state briefly, but you're never blocked.

---

#### Partition Tolerance (P)
**Definition:** The system continues to operate even when network communication between nodes fails (a "network partition").

**Network partition:** Node A and Node B can't communicate with each other (network cable cut, router failure, etc.).

**Why P is not optional in distributed systems:** Networks are unreliable. Packets get dropped. Routers fail. Network partitions will happen. If your system can't tolerate them, it's not a distributed system. **Therefore, partition tolerance is essentially mandatory.** You must choose between C and A when a partition occurs.

---

### 6. The Real Choice: CP vs AP

Since P is always required, the real choice during a network partition is:

**CP Systems (Consistency + Partition Tolerance):**
Choose to **stop responding** (sacrifice availability) rather than serve potentially incorrect data.

```
Node A and B can't communicate.
Node A refuses to respond to reads/writes.
"Better to be unavailable than wrong."
```

**Examples:** HBase, Zookeeper, MongoDB (with certain settings), traditional SQL databases

**Good for:** Banks, financial systems, anywhere data accuracy is critical.

---

**AP Systems (Availability + Partition Tolerance):**
Choose to **keep responding** (sacrifice consistency) even if it might serve stale data.

```
Node A and B can't communicate.
Both keep accepting reads and writes.
When partition heals, they reconcile (eventually consistent).
"Better to respond with possibly stale data than not respond at all."
```

**Examples:** Cassandra, DynamoDB, CouchDB

**Good for:** Shopping carts, social media feeds, DNS — where availability matters more than perfect freshness.

---

### 7. Consistency Models (Going Deeper)

"Consistency" isn't binary — there are different levels.

#### Strong Consistency
After a write, all subsequent reads from any node will see that write.
- The gold standard, hardest to achieve
- Example: "I updated my profile picture. Everyone sees the new picture immediately."

#### Eventual Consistency
After a write, given enough time (no more writes), all replicas will converge to the same value.
- Most distributed systems use this
- Example: DNS — after you update your DNS record, it might take 24 hours to propagate everywhere. But eventually, all DNS servers see the same value.

#### Read-Your-Own-Writes Consistency
After you write data, you will always see your own writes.
- Others might not see it immediately, but you will.
- Example: After posting on Facebook, you always see your own post. Others might see it slightly later.

#### Monotonic Read Consistency
Once you read a value, you will never read an older value.
- You won't see a post, refresh, and see it disappear.

#### Causal Consistency
Operations that are causally related are seen in the correct order by all nodes.
- If you comment on a post, no one sees your comment before the post.

---

### 8. PACELC Theorem — Going Beyond CAP

CAP Theorem only describes behavior during a partition. But what about when there is **no partition** (normal operation)?

**PACELC Theorem** (proposed by Daniel Abadi):

> If there is a **P**artition: choose between **A**vailability and **C**onsistency
> **E**lse (no partition): choose between **L**atency and **C**onsistency

During normal operation (no partition), you still face a trade-off:
- **Low latency:** Return data quickly, possibly from a nearby but slightly stale replica
- **Strong consistency:** Wait for all replicas to confirm → higher latency

| System | During Partition | During Normal Ops |
|--------|-----------------|-------------------|
| Cassandra | Availability | Latency |
| ZooKeeper | Consistency | Consistency |
| DynamoDB | Availability | Latency |
| PostgreSQL | Consistency | Consistency |

---

### 9. Practical Examples

**Banking system:** Must be CP.
- When the network partitions, it's better for your bank to temporarily go offline than to accept a withdrawal and not properly debit the account.
- Inconsistency here means someone could double-spend money.

**Amazon Shopping Cart:** AP.
- When network partitions, Amazon still lets you add to cart (availability).
- Two partitioned nodes might have different cart states.
- When partition heals, they merge: "You had 2 items on Node A, 1 item on Node B → cart now has 3 items." (Eventual consistency)
- It's okay to have a slightly inconsistent cart for a moment. It's not okay to be unable to shop.

**DNS:** AP.
- DNS servers are eventually consistent. A record change propagates over time.
- But DNS always responds to queries (high availability).

**Google Search Index:** AP-ish.
- The search index might be slightly out of date (new pages take time to be indexed).
- But Google always returns results (never says "unavailable").

---

## 10. Summary

### Sharding

| Strategy | Based On | Pros | Cons |
|----------|----------|------|------|
| Range Partitioning | Key ranges | Good for range queries | Hotspots |
| Hash Partitioning | Hash of key | Uniform distribution | Bad range queries, resharding hard |
| Secondary Indexes | Non-partition key | Query flexibility | Complex |

### CAP Theorem

| Property | Meaning | Trade-off |
|----------|---------|-----------|
| Consistency | All nodes see same data | May sacrifice availability |
| Availability | Always responds | May serve stale data |
| Partition Tolerance | Works despite network failure | Required in distributed systems |

**CP systems:** Banks, financial data, strong consistency required
**AP systems:** Social media, shopping carts, DNS — availability matters more

---

*Next: Part 8 — Message Queues & Fault Tolerance*
