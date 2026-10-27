# 04 — Data Modeling, Databases, Storage and Scaling

## 1. Model facts before selecting a database

Start with entities, relationships, invariants, and access patterns. An invariant is a fact that must remain true: “an order belongs to exactly one tenant,” “available inventory never goes below zero,” or “an email is unique within an account.” Put an invariant as close as possible to the durable source of truth—usually a constraint or transaction—not only in application code.

### Example relational schema

```sql
CREATE TABLE orders (
  id          UUID PRIMARY KEY,
  tenant_id   UUID NOT NULL,
  customer_id UUID NOT NULL,
  status      TEXT NOT NULL CHECK (status IN ('pending','paid','cancelled')),
  total_cents BIGINT NOT NULL CHECK (total_cents >= 0),
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX orders_tenant_created_idx
  ON orders (tenant_id, created_at DESC, id DESC);
```

Line by line:

1. `id` is the immutable unique order identity; UUIDs allow generation outside a central sequence.
2. `tenant_id` is mandatory so every query can be isolated by tenant.
3. `customer_id` connects the order to its owner; add a foreign key if the referenced table and lifecycle make that correct.
4. `status` has an allowed set; a check prevents typo states from entering the system.
5. Store money in minor integer units, not floating point, and disallow negative totals here.
6. A timezone-aware creation timestamp supports ordering and audits.
7. The composite index matches the common listing filter and sort. `id` makes cursor ordering deterministic.

### Normalization and denormalization

Normalization keeps a fact in one canonical place, reducing update anomalies. Example: product details belong in `products`, not copied into every cart row. Denormalization duplicates or precomputes data to make a dominant query fast, such as storing an `order_total` or a search document. Denormalize only with a defined writer, update mechanism, and repair path; otherwise stale copies become mysterious bugs.

Keys and constraints make rules executable: primary key (unique identity), foreign key (referential link), unique constraint (no duplicate), check constraint (valid domain). Constraints protect against races across application instances.

## 2. Indexes and query plans

An index is a secondary access path that trades write/storage cost for faster reads. Most relational databases use B-tree family indexes for equality, ranges, and ordered scans. A composite index is ordered left-to-right: `(tenant_id, created_at)` is excellent for `WHERE tenant_id=? ORDER BY created_at`; it generally cannot efficiently serve only `WHERE created_at=?`.

| Index type | Main use | Caution |
|---|---|---|
| B-tree | equality, range, sort | default choice in many SQL stores |
| Hash | equality in some engines | no ordered range scan |
| Composite | common filter + sort | column order matters |
| Covering/include | index contains all selected columns | increases index size/write work |
| Clustered | table physically ordered by key (engine-specific) | only one physical order |
| Partial | index a subset, e.g. active rows | query predicate must match |

Use `EXPLAIN`/`EXPLAIN ANALYZE` to inspect actual row counts, scan type, join choice, sort, and time. A slow query is not fixed automatically by “add an index”: first know its filter, cardinality, selected columns, data distribution, and required consistency. Avoid `SELECT *`, unbounded result sets, functions on indexed columns that prevent index use, and accidental N+1 queries.

```sql
-- Cursor page: the index above supports this shape.
SELECT id, status, total_cents, created_at
FROM orders
WHERE tenant_id = $1
  AND (created_at, id) < ($2, $3)
ORDER BY created_at DESC, id DESC
LIMIT 50;
```

## 3. SQL capabilities and transactions

SQL joins combine related tables; aggregation summarizes (`COUNT`, `SUM`, `GROUP BY`); window functions calculate across a related set without collapsing rows.

```sql
SELECT customer_id, id, total_cents,
       ROW_NUMBER() OVER (
         PARTITION BY customer_id ORDER BY created_at DESC
       ) AS order_rank
FROM orders;
```

### ACID in plain English

- **Atomicity:** a transaction’s changes all happen or none do.
- **Consistency:** transactions preserve declared database invariants.
- **Isolation:** concurrent transactions behave according to the chosen isolation rules.
- **Durability:** committed data survives a crash, subject to the configured storage/replication promise.

Isolation anomalies:

| Anomaly | Example | Typical prevention |
|---|---|---|
| Dirty read | read another transaction’s uncommitted price | do not allow read-uncommitted |
| Non-repeatable read | same row changes between two reads | repeatable read / locking where needed |
| Phantom | a predicate returns extra rows on repeat | serializable isolation / predicate protections |
| Lost update | two writers overwrite each other | version check, lock, or atomic update |

**MVCC** lets readers view a consistent version while writers create newer versions, reducing reader/writer blocking. **Optimistic locking** reads a version and updates only if it still matches; it is good when conflicts are rare. **Pessimistic locking** locks before changing; it is useful when conflicts are frequent and the locked work is short.

```sql
-- Optimistic update succeeds for exactly one concurrent editor.
UPDATE documents
SET body = $1, version = version + 1
WHERE id = $2 AND version = $3;
```

If zero rows change, reload and resolve the conflict instead of silently overwriting. Keep transactions short and access rows in a consistent order to reduce deadlocks. A deadlock is normal in concurrent systems: the database detects it, aborts one transaction, and the application retries the whole safe transaction with a small jitter.

Connection pools reuse expensive database connections and cap concurrency. Too many application connections can harm a database through context switching and memory pressure. Pool sizes are capacity settings, not “more is always better.”

## 4. Schema evolution and analytical systems

Use expand–migrate–contract for zero-downtime change:

1. Add a nullable/new column or a new table/index (expand).
2. Deploy code that writes both old and new forms, then backfill in small restartable batches.
3. Verify reads use the new form and all writers are upgraded.
4. Stop old writes, then later remove old code/column (contract).

Avoid a deployment that requires old code to understand a new non-null field immediately. Test migration time and lock behavior on production-like data; indexes may need online/concurrent creation.

**OLTP** serves many small transactional reads/writes (orders, accounts). **OLAP** scans and aggregates large history (reports). A warehouse/lakehouse normally receives copies/events rather than being the database that checkout uses. This separation protects operational latency and enables columnar, large scans.

## 5. NoSQL and storage choices

Choose a store based on access patterns, consistency, scale, and query needs—never just data shape.

| Family | Core model | Good fit | Common trap |
|---|---|---|---|
| Key-value | key → opaque value | session, cache, simple lookup | trying to query unindexed value fields |
| Document | nested JSON documents | flexible aggregates, content | unbounded documents/weak relationship design |
| Wide-column | partition key + sorted columns | very high write scale, known queries | bad partition key/hot partitions |
| Graph | nodes + relationships | multi-hop relation queries | using it for simple key lookup |
| Time-series | timestamped measurements | metrics, sensors | unbounded high-cardinality labels |
| Search engine | inverted text index | full text/filter/ranking | treating index as transactional source of truth |
| Vector DB | embedding nearest-neighbor index | semantic retrieval | ignoring filters, evaluation, freshness |

### Object, block, and file storage

Object storage keeps blobs under keys in buckets; it scales well for images, media, backups, and documents. It supports metadata, multipart upload, lifecycle tiers, versioning, and signed access. A relational row should reference an object key and checksum rather than contain a large video blob.

Block storage exposes raw volumes, usually attached to a VM/database. A filesystem organizes files/directories on a volume or a network filesystem. Each has different latency, durability, sharing, and backup semantics.

### Search and vector basics

An inverted index maps terms to documents, enabling full-text retrieval; analyzers tokenize/normalize text. Search engines are often asynchronously updated from a primary database, so document visibility can lag. For vector search, text/images become embedding vectors. Approximate nearest-neighbor structures such as HNSW/IVF trade exactness, memory, and latency for speed. Filter by tenant/permissions before or during vector retrieval; semantic relevance never bypasses access control.

## 6. Database internals and replication

### B-trees and LSM trees

A B/B+ tree maintains sorted pages, making point lookups and ranges efficient. Writes can modify pages in place. LSM-based stores first append writes to a log and memory table, flush immutable sorted files (SSTables), then compact files later. LSMs often excel at write-heavy workloads but require compaction, tombstone, and read-amplification management. Bloom filters quickly say “this SSTable definitely does not contain this key,” avoiding many disk reads.

A **write-ahead log (WAL)/commit log** records intended changes before reporting commit. On restart, the database replays it to recover durable state. An append-only log also underpins event streams; retention and compaction determine how long history remains.

### Replication and read consistency

Leader-follower replication accepts writes at a leader and copies changes to followers. Synchronous replication can improve acknowledged-write durability but raises latency/availability coupling. Asynchronous replication improves write availability/latency but creates lag: a user may write then read a stale replica.

Solve read-after-write needs with leader reads for a short session window, a replication-position token, sticky routing, or a store offering session consistency. State the guarantee; do not promise “eventual consistency” where a balance or booking needs immediate correctness.

Multi-leader accepts writes in multiple places and requires conflict resolution. Leaderless systems use replicas and quorum reads/writes. With `N` replicas, `W` write acknowledgements and `R` read responses, `R + W > N` creates quorum overlap under assumptions, but real semantics still depend on versioning, failures, and repair.

## 7. Partitioning (sharding) and hot spots

Sharding spreads data across nodes. Common keys:

- **Range:** contiguous IDs/time ranges. Great range scans; prone to newest-range hot spot.
- **Hash:** hash key distributes uniformly; ranges are hard.
- **Directory:** mapping service chooses shard; flexible, mapping becomes critical.
- **Geo/tenant/time:** useful locality/isolation, can create uneven traffic.

**Consistent hashing** places nodes and keys on a ring; adding/removing a node moves only a fraction of keys. Virtual nodes give each physical machine multiple ring positions, improving balance. Consistent hashing reduces movement; it does not fix a single celebrity key. Mitigate hot keys using cache replication, request coalescing, key splitting/counter sharding, rate limits, or a different data model.

Resharding needs dual routing or a routing layer, copy/checkpoint, change capture, verification, cutover, and rollback. Plan it before the last shard is full.

## 8. Backups and recovery

Replication is not backup: it can replicate deletion, corruption, or a malicious change. Backups need independent retention, encryption, access control, integrity checks, and restore drills. Point-in-time recovery combines a base backup with WAL/log history to restore to a chosen moment. Define:

- **RPO (recovery point objective):** maximum tolerable data loss window.
- **RTO (recovery time objective):** maximum tolerable recovery duration.

Measure restore time against realistic data, credentials, networking, DNS, and application migration steps. A backup that cannot be restored is only stored hope.
