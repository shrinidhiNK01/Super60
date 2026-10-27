# System Design Notes — Part 1: Introduction & Core Components

> **Goal of this course:** Build the *mindset* to design scalable systems — not just memorize definitions.

---

## 1. What is System Design?

System Design is the process of **planning how to build an application** — deciding what parts it needs, how those parts talk to each other, and what trade-offs you are willing to make.

Think of it like designing a building:
- Before you lay a single brick, you draw blueprints
- You decide: How many floors? Where are the exits? What if there's a fire?

In software, system design answers:
- How will millions of users use my app at the same time?
- What happens if one server crashes?
- Where do I store the data?
- How fast must the app respond?

---

## 2. The Alien Bank Example (Why Design Matters)

Imagine you are building a bank for aliens. You don't know:
- How many aliens will use it (10? 10 billion?)
- What currency they use
- How often they make transactions

**Bad approach:** Just start coding and "figure it out later"

**Good approach (System Design mindset):**
1. Ask questions first (requirements)
2. Estimate scale (how many users, how much data)
3. Choose the right components
4. Think about what can go wrong
5. Make conscious trade-offs

**The lesson:** Every design decision is a trade-off. There is no perfect design — only designs that fit your requirements better or worse.

---

## 3. Core Components of System Design

Every large application is built from a handful of building blocks. Let's understand each one.

---

### 3.1 Client Applications

**What it is:** The part the user directly interacts with.

**Examples:**
- A website in a browser (Chrome, Firefox)
- A mobile app (Instagram on your phone)
- A desktop app (VS Code on your laptop)

**How it works:**
- The client sends a **request** to the server ("Give me the latest posts")
- The server sends back a **response** ("Here are the posts: ...")
- The client displays the result to the user

**Key point:** Clients are "thin" — they don't store much data themselves. They rely on servers.

---

### 3.2 Backend Servers

**What it is:** The "brain" of the application. It processes requests, applies business logic, and talks to databases.

**Example:** When you search on Google:
1. Your browser (client) sends "search for cats" to Google's server
2. The server finds relevant pages (business logic)
3. The server sends back search results
4. Your browser shows them

**Why multiple servers?**
- One server can only handle so many requests at once
- If that one server crashes, your whole app is down
- Solution: Use many servers and a **Load Balancer** (covered later)

---

### 3.3 Databases

**What it is:** Persistent storage — data that survives even if the server restarts.

**Two main types** (covered in detail later):
- **SQL (Relational):** Data in tables with rows and columns, like a spreadsheet. Example: MySQL, PostgreSQL
- **NoSQL:** Flexible data formats. Example: MongoDB, Redis, Cassandra

**Why not just store data in the server's memory (RAM)?**
- RAM is lost when the server restarts
- RAM is limited and expensive
- Databases are designed for safe, reliable, long-term storage

---

### 3.4 Load Balancers

**What it is:** A "traffic cop" that sits in front of your servers and distributes incoming requests evenly.

```
Users → Load Balancer → Server 1
                     → Server 2
                     → Server 3
```

**Why needed:**
- Without it, one server gets overwhelmed while others sit idle
- If a server crashes, the load balancer stops sending traffic to it
- You can add/remove servers without users noticing

**Simple analogy:** Like a cashier manager at a supermarket who directs customers to the shortest checkout line.

---

### 3.5 Message Queues

**What it is:** A waiting room for tasks that don't need to happen immediately.

**Example:** You upload a video to YouTube.
- You don't wait 10 minutes for YouTube to process it
- Instead, a task ("process this video") is put in a queue
- Background workers pick up tasks from the queue and process them
- You get a notification when done

**Why needed:**
- Handles spikes in traffic without crashing
- Decouples the sender and the worker (they don't need to be available at the same time)
- Provides reliability (if a worker crashes, the task stays in the queue)

---

### 3.6 Monitoring and Logs

**What it is:** Tools to watch your system and record what's happening.

**Monitoring:** Real-time dashboards showing:
- Is the server running? (Health)
- How many requests per second? (Throughput)
- How long do requests take? (Latency)
- How many errors? (Error rate)

**Logs:** A written record of everything that happened, like a diary:
- "User 123 logged in at 10:05 AM"
- "Error: Database connection failed at 10:06 AM"

**Why needed:**
- Without monitoring, you're flying blind
- When something breaks, logs help you find out why
- Helps you catch problems before users notice

---

## 4. Types of Applications

### 4.1 Data-Intensive Applications

**Definition:** Applications where the main challenge is **handling large amounts of data** — storing it, reading it, writing it, and transforming it.

**Examples:**
- **Instagram:** Stores billions of photos and videos. The challenge isn't complex math — it's storing and serving huge files fast.
- **Twitter:** Stores billions of tweets and serves timelines to millions of users simultaneously.
- **Netflix:** Stores thousands of movies and streams them reliably.

**Characteristics:**
- Large storage requirements (terabytes to petabytes)
- High read/write operations on databases
- Bottleneck is usually I/O (Input/Output) — reading from disk or network
- Solution focuses on: databases, caching, CDNs, replication

**Instagram Architecture Example:**
- When you post a photo → it gets stored in an **object storage** (like Amazon S3)
- When your followers open the app → their feed is read from a **fast cache** (like Redis)
- The actual heavy processing (image resizing, filters) happens in **background workers**

---

### 4.2 Compute-Intensive Applications

**Definition:** Applications where the main challenge is **performing complex calculations** — the CPU or GPU is the bottleneck, not data storage.

**Examples:**
- **Machine Learning model training:** Training a large AI model requires trillions of math operations
- **Video rendering:** Converting raw footage to a final video requires massive computation
- **Weather prediction:** Simulating the atmosphere requires complex physics calculations
- **Cryptocurrency mining:** Requires solving complex math problems

**CPU-bound vs GPU-bound:**

| Type | Best For | Example |
|------|----------|---------|
| CPU-bound | General logic, sequential tasks | Web servers, databases |
| GPU-bound | Parallel math operations | ML training, graphics rendering |

**Why GPUs for ML?**
- A CPU has ~16 cores (does 16 things at once)
- A GPU has thousands of cores (does thousands of things at once)
- ML training is basically millions of matrix multiplications — perfect for GPUs

**Characteristics:**
- High CPU or GPU usage
- Less data, more computation
- Bottleneck is processing power
- Solution: specialized hardware, distributed computing (split work across many machines)

---

## 5. Summary Table

| Component | Role | Simple Analogy |
|-----------|------|----------------|
| Client | User-facing interface | Customer at a restaurant |
| Backend Server | Processes requests | Kitchen in a restaurant |
| Database | Stores data permanently | Recipe book / pantry |
| Load Balancer | Distributes traffic | Restaurant host/manager |
| Message Queue | Holds tasks for later processing | Order tickets in a kitchen |
| Monitoring & Logs | Watches system health | Restaurant security cameras + logbook |

---

## 6. Key Mindset Principles

1. **Start with requirements** — Don't design before you know what you're building
2. **Scale matters** — A design for 100 users is different from one for 100 million users
3. **Everything fails** — Design assuming servers will crash, networks will drop
4. **Trade-offs are real** — Faster response times might mean more cost. Higher availability might mean some consistency trade-offs.
5. **Keep it simple first** — Start simple, add complexity only when needed

---

*Next: Part 2 — Functional vs Non-Functional Requirements & DNS*
