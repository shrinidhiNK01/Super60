# System Design Notes — Part 4: Databases (SQL & NoSQL)

---

## 1. Why Databases?

Before databases, data was stored in text files. Problems:
- No way to query (search) efficiently
- No protection from corruption
- Multiple users accessing the same file = chaos
- No transactions (what if the app crashes mid-write?)

**Databases solve all of this.** They provide:
- Structured storage
- Fast querying
- ACID guarantees (Atomicity, Consistency, Isolation, Durability)
- Concurrent access by multiple users
- Security and access control

---

## 2. SQL Databases (Relational Databases)

### 2.1 What is a Relational Database?

Data is stored in **tables** — like Excel spreadsheets. Tables have **rows** (records) and **columns** (fields).

Tables can be **related** to each other, hence the name "relational."

**Examples:** MySQL, PostgreSQL, SQLite, Microsoft SQL Server, Oracle

---

### 2.2 Tables, Rows, and Columns

**Example: A "users" table:**

| id | name | email | age | created_at |
|----|------|-------|-----|------------|
| 1 | Alice | alice@gmail.com | 25 | 2024-01-01 |
| 2 | Bob | bob@gmail.com | 30 | 2024-01-02 |
| 3 | Charlie | charlie@gmail.com | 22 | 2024-01-03 |

- **Table:** The whole grid — like a spreadsheet tab named "users"
- **Column:** A field type — "name", "email", "age" (all users have these fields)
- **Row:** One record — all info about one specific user

---

### 2.3 Data Types

Each column has a specific data type:

| Type | What it stores | Example |
|------|---------------|---------|
| INT | Whole numbers | age: 25 |
| DECIMAL/FLOAT | Decimal numbers | price: 19.99 |
| VARCHAR(n) | Text up to n characters | name: "Alice" |
| TEXT | Long text | description: "..." |
| BOOLEAN | True or false | is_active: true |
| DATE | Date only | birthday: 1999-05-15 |
| DATETIME/TIMESTAMP | Date and time | created_at: 2024-01-01 10:05:00 |
| JSON | Structured JSON data | metadata: {"key": "value"} |

---

### 2.4 Constraints

**Constraints** are rules that enforce data quality and integrity.

#### NOT NULL
```sql
name VARCHAR(100) NOT NULL
```
This column cannot be empty. Every row must have a name.

#### UNIQUE
```sql
email VARCHAR(255) UNIQUE
```
No two rows can have the same email. Ensures uniqueness.

#### DEFAULT
```sql
is_active BOOLEAN DEFAULT TRUE
```
If no value is provided when inserting, use TRUE as default.

#### CHECK
```sql
age INT CHECK (age >= 0 AND age <= 120)
```
Value must pass this condition. Can't insert age = -5.

#### PRIMARY KEY
```sql
id INT PRIMARY KEY AUTO_INCREMENT
```
The unique identifier for each row. Must be unique and not null. Auto-increments automatically.

#### FOREIGN KEY
```sql
user_id INT REFERENCES users(id)
```
Links this column to another table's primary key. Enforces referential integrity — you can't have a post from a user that doesn't exist.

---

### 2.5 Primary Key and Foreign Key

**Primary Key:** A column (or combination of columns) that uniquely identifies each row.
- Every table should have one
- Must be unique and not null
- Example: `user_id`, `order_id`, `product_id`

**Foreign Key:** A column that references the primary key of another table.
- Creates a relationship between tables
- Enforces referential integrity

**Example:**

**users table:**
| id (PK) | name |
|---------|------|
| 1 | Alice |
| 2 | Bob |

**orders table:**
| id (PK) | user_id (FK → users.id) | product | amount |
|---------|------------------------|---------|--------|
| 101 | 1 | Laptop | 50000 |
| 102 | 1 | Mouse | 500 |
| 103 | 2 | Keyboard | 1500 |

The `user_id` in orders is a foreign key pointing to `id` in users. It means "this order belongs to this user."

If you try to insert an order with `user_id = 99` but user 99 doesn't exist — the database **rejects** it. That's referential integrity.

---

### 2.6 Relationships Between Tables

#### One-to-One (1:1)
Each row in Table A relates to exactly one row in Table B.

**Example:** User and UserProfile
- One user has exactly one profile
- One profile belongs to exactly one user

```
users:         user_profiles:
id | name      user_id | bio | avatar_url
1  | Alice     1       | ... | ...
2  | Bob       2       | ... | ...
```

**Use case:** When you want to split a large table for performance or security (keep sensitive data separate).

---

#### One-to-Many (1:N)
One row in Table A relates to many rows in Table B.

**Example:** User and Posts
- One user can write many posts
- Each post belongs to exactly one user

```
users:         posts:
id | name      id | user_id | title
1  | Alice     1  | 1       | "My first post"
2  | Bob       2  | 1       | "My second post"
               3  | 2       | "Bob's post"
```

**This is the most common relationship in databases.**

---

#### Many-to-Many (M:N)
Many rows in Table A relate to many rows in Table B.

**Example:** Students and Courses
- One student can enroll in many courses
- One course can have many students

**You cannot store this directly.** You need a **junction table** (also called a join table or pivot table):

```
students:           courses:
id | name           id | title
1  | Alice          10 | Math
2  | Bob            11 | Science
3  | Charlie        12 | History

enrollments (junction table):
student_id | course_id
1          | 10         (Alice takes Math)
1          | 11         (Alice takes Science)
2          | 11         (Bob takes Science)
2          | 12         (Bob takes History)
3          | 10         (Charlie takes Math)
```

---

### 2.7 SQL Joins

Joins combine data from multiple tables in a single query.

**Example tables:**

**users:**
| id | name |
|----|------|
| 1 | Alice |
| 2 | Bob |
| 3 | Charlie |

**orders:**
| id | user_id | product |
|----|---------|---------|
| 1 | 1 | Laptop |
| 2 | 1 | Mouse |
| 3 | 4 | Tablet |

---

#### INNER JOIN
Returns only rows that have matching values in **both** tables.

```sql
SELECT users.name, orders.product
FROM users
INNER JOIN orders ON users.id = orders.user_id;
```

**Result:**
| name | product |
|------|---------|
| Alice | Laptop |
| Alice | Mouse |

(Bob and Charlie have no orders. Order 3 has user_id=4 which doesn't exist. Neither appears.)

---

#### LEFT JOIN (LEFT OUTER JOIN)
Returns all rows from the **left** table, and matching rows from the right (or NULL if no match).

```sql
SELECT users.name, orders.product
FROM users
LEFT JOIN orders ON users.id = orders.user_id;
```

**Result:**
| name | product |
|------|---------|
| Alice | Laptop |
| Alice | Mouse |
| Bob | NULL |
| Charlie | NULL |

---

#### RIGHT JOIN
Returns all rows from the **right** table, and matching rows from the left.

---

#### FULL OUTER JOIN
Returns all rows from both tables, with NULLs where there's no match.

---

### 2.8 Indexing

**Problem:** Without indexes, finding a specific row requires scanning the entire table (millions of rows).

**Index:** A data structure (usually a B-Tree) that lets the database find rows much faster.

```sql
CREATE INDEX idx_users_email ON users(email);
```

Now `WHERE email = 'alice@gmail.com'` is fast — like a book index that lets you jump directly to the right page instead of reading the whole book.

**Trade-off:**
- ✅ Faster reads
- ❌ Slower writes (index must be updated on every insert/update)
- ❌ Uses extra storage

---

### 2.9 ACID Properties

Every relational database guarantees ACID:

**A — Atomicity:** A transaction either completes entirely or not at all.
- Example: Transfer ₹1000 from Alice to Bob. Either both the debit AND credit happen, or neither does. You can't debit Alice without crediting Bob.

**C — Consistency:** The database always moves from one valid state to another. Constraints are never violated.

**I — Isolation:** Concurrent transactions don't interfere with each other. Each transaction sees a consistent snapshot of the data.

**D — Durability:** Once a transaction is committed (saved), it persists even if the system crashes immediately after.

---

## 3. NoSQL Databases

### 3.1 Why NoSQL?

Relational databases are excellent, but they have limitations at extreme scale:

**Problem 1 — Rigid Schema:** Every row must have the same columns. What if different products have completely different attributes?
- A book has: author, ISBN, pages
- A laptop has: RAM, processor, screen size
- Forcing these into the same table is messy

**Problem 2 — Scaling:** Relational databases scale vertically well but horizontally scaling (sharding) is complex. NoSQL databases are designed for horizontal scaling.

**Problem 3 — Performance for specific use cases:** 
- For a session store (user login data), a simple key-value lookup is much faster than SQL
- For a social graph (who follows whom), graph relationships are complex in SQL

**NoSQL** = "Not Only SQL" — a collection of database types that don't follow the relational model.

---

### 3.2 Key-Value Databases

**Structure:** Like a dictionary or hashmap — a key paired with a value.

```
"user:123:session" → "eyJhbGciOiJIUzI1NiJ9..."
"product:456:price" → "29.99"
"user:123:cart" → "[{item:1, qty:2}, {item:5, qty:1}]"
```

**Examples:** Redis, Amazon DynamoDB, Memcached

**Characteristics:**
- Extremely fast (O(1) lookup)
- Simple data model — no complex queries
- No relationships between records
- Often stored in memory (RAM) for ultra-fast access

**Best for:**
- **Session storage** — Store user login sessions
- **Caching** — Store computed results to avoid recalculating
- **Rate limiting** — Count requests per user
- **Leaderboards** — Sorted rankings (Redis Sorted Sets)
- **Real-time counters** — Page views, likes

**Not good for:**
- Complex queries
- Structured relational data
- Queries across multiple records

---

### 3.3 Document Databases

**Structure:** Stores data as self-contained JSON-like documents. Each document can have different fields.

```json
{
  "_id": "usr_123",
  "name": "Alice",
  "email": "alice@gmail.com",
  "address": {
    "city": "Mumbai",
    "zip": "400001"
  },
  "orders": [
    {"product": "Laptop", "amount": 50000, "date": "2024-01-01"},
    {"product": "Mouse", "amount": 500, "date": "2024-01-15"}
  ]
}
```

**Examples:** MongoDB, Firestore, CouchDB, Amazon DocumentDB

**Characteristics:**
- Schema-flexible — different documents in the same collection can have different fields
- Good for nested, hierarchical data
- Can query on any field
- Scales horizontally well

**Best for:**
- **Content management** — Blog posts, articles (different post types have different fields)
- **User profiles** — Complex nested data
- **Product catalogs** — Products with varying attributes
- **Event logging** — Events with different structures
- **Rapid prototyping** — Schema can evolve without migrations

**Not good for:**
- Data with complex relationships requiring joins
- Financial transactions requiring strong ACID guarantees
- When data consistency across multiple documents is critical

---

### 3.4 Graph Databases

**Structure:** Data stored as **nodes** (entities) and **edges** (relationships between them).

```
(Alice) --[FOLLOWS]--> (Bob)
(Alice) --[LIKES]--> (Post: "Hello World")
(Bob) --[POSTED]--> (Post: "Hello World")
(Alice) --[FRIENDS_WITH]--> (Charlie)
```

**Examples:** Neo4j, Amazon Neptune, ArangoDB

**Characteristics:**
- Designed for highly connected data
- Queries that traverse relationships are extremely fast
- Natural representation of networks

**Best for:**
- **Social networks** — Friend recommendations, mutual connections
- **Fraud detection** — Finding suspicious patterns in transaction graphs
- **Recommendation engines** — "People who liked X also liked Y"
- **Knowledge graphs** — Google's Knowledge Graph
- **Network analysis** — Computer networks, supply chains

**Not good for:**
- Simple CRUD with no relationships
- Large amounts of non-relational data

---

### 3.5 Columnar Databases (Wide-Column Stores)

**Structure:** Data stored by columns rather than rows. Optimized for reading/writing specific columns across millions of rows.

**Examples:** Apache Cassandra, HBase, Google Bigtable, Amazon Redshift (analytical)

**Think of it this way:**

Traditional (row store) — stores each row together:
```
[Alice, alice@gmail.com, 25, Mumbai]
[Bob, bob@gmail.com, 30, Delhi]
```

Column store — stores each column together:
```
Names:  [Alice, Bob, Charlie, ...]
Emails: [alice@gmail.com, bob@gmail.com, ...]
Ages:   [25, 30, 22, ...]
```

**Why columnar is faster for analytics:**
- "What's the average age of all users?" — Column store reads only the Age column
- Row store would read every entire row even though you only need one field

**Best for:**
- **Time-series data** — Sensor readings, server metrics, stock prices
- **Analytics/Data warehousing** — Aggregations over millions of rows
- **Write-heavy, globally distributed apps** — Cassandra handles huge write throughput
- **IoT data** — Billions of small writes from devices

**Cassandra strengths:**
- Masterless — no single point of failure
- Extremely write-optimized
- Designed for geographic distribution
- Tunable consistency

---

### 3.6 SQL vs NoSQL — When to Use Which

| Factor | SQL | NoSQL |
|--------|-----|-------|
| Data structure | Structured, consistent | Flexible, variable |
| Relationships | Many complex relationships | Few or simple relationships |
| Consistency | Strong (ACID) | Eventual (usually) |
| Scale | Vertical (mostly) | Horizontal |
| Transactions | Excellent | Limited (improving) |
| Schema changes | Painful (migrations needed) | Easy |
| Query flexibility | High (SQL is powerful) | Varies by type |
| Examples | Banking, ERP, e-commerce | Social media, IoT, caching |

**Rule of thumb:**
- If your data is structured and you need strong consistency → **SQL**
- If you need horizontal scale, flexible schema, or specific data models → **NoSQL**
- Most large systems use **both** (polyglot persistence)

**Example: Instagram uses both:**
- **PostgreSQL (SQL):** User accounts, follower relationships (require consistency)
- **Cassandra (NoSQL):** User activity feed (massive write throughput needed)
- **Redis (NoSQL):** Caching user sessions and feed data (speed)

---

## 4. Summary

| Database Type | Structure | Best For | Examples |
|---------------|-----------|----------|---------|
| SQL/Relational | Tables with rows & columns | Structured data, complex queries, ACID | PostgreSQL, MySQL |
| Key-Value | Key → Value | Caching, sessions, fast lookups | Redis, DynamoDB |
| Document | JSON-like documents | Flexible schema, nested data | MongoDB, Firestore |
| Graph | Nodes and edges | Relationships, social networks | Neo4j, Neptune |
| Columnar | Columns grouped together | Analytics, time-series, IoT | Cassandra, HBase |

---

*Next: Part 5 — Caching*
