# System Design Notes — Part 2: Requirements & DNS

---

## 1. Types of Requirements

Before designing any system, you must understand **what it needs to do** and **how well it needs to do it**.

There are two categories:

---

### 1.1 Functional Requirements

**Definition:** What the system *does* — the features and behaviors visible to the user.

**Examples for a social media app:**
- User can create an account
- User can post photos
- User can follow other users
- User can like and comment on posts
- User can search for other users

**Examples for an e-commerce site:**
- User can browse products
- User can add items to a cart
- User can make a payment
- User can track their order

**Key point:** Functional requirements are about **features**. They answer: "What can the user do?"

---

### 1.2 Non-Functional Requirements

**Definition:** How *well* the system performs — quality attributes that users feel but don't always see explicitly.

These are often more challenging to design for than functional requirements.

---

#### Scalability

**Definition:** The system's ability to handle increasing load (more users, more data, more requests).

**Two types:**

| Type | What it means | Example |
|------|---------------|---------|
| Vertical Scaling (Scale Up) | Make one machine more powerful | Upgrade from 8GB RAM to 64GB RAM server |
| Horizontal Scaling (Scale Out) | Add more machines | Add 10 more servers |

**Why horizontal scaling is usually preferred:**
- There's a limit to how powerful one machine can be
- A single powerful machine is a single point of failure
- Horizontal scaling is more cost-effective at large scale

**Example:** Netflix doesn't run on one super-computer. It runs on tens of thousands of servers spread across the world.

---

#### Availability

**Definition:** The percentage of time the system is up and working.

**Measured in "nines":**

| Availability | Downtime per year | Called |
|--------------|-------------------|--------|
| 99% | ~3.65 days | Two nines |
| 99.9% | ~8.76 hours | Three nines |
| 99.99% | ~52.6 minutes | Four nines |
| 99.999% | ~5.26 minutes | Five nines |

**Why it matters:**
- Amazon loses ~$220,000 per minute of downtime
- If your bank's app is down, you can't pay bills — huge problem
- "High availability" systems aim for 99.99% or higher

**How to achieve it:**
- Redundancy: Have backup servers ready
- No single point of failure: If one component fails, another takes over
- Geographic distribution: Servers in multiple data centers

---

#### Reliability

**Definition:** The system does what it's supposed to do, correctly, every time — without losing data or producing wrong results.

**Difference between availability and reliability:**
- **Available but not reliable:** The system is up, but sometimes gives you someone else's bank balance (that's a bug — it's available but unreliable)
- **Reliable but not always available:** The system is sometimes down for maintenance, but when it's up, it's always correct

**Example:** A banking system must be highly reliable — it cannot lose your transaction data. It's okay if it's briefly unavailable for maintenance, but it must never lose money.

---

#### Performance

**Definition:** How fast the system responds.

**Two key metrics:**

| Metric | Definition | Example |
|--------|------------|---------|
| Latency | Time for one request to complete | "My search results appeared in 200ms" |
| Throughput | Number of requests handled per second | "The server handles 10,000 requests/second" |

**Latency types:**
- **P50 (median):** 50% of requests are faster than this
- **P95:** 95% of requests are faster than this
- **P99:** 99% of requests are faster than this

P99 matters most for user experience — you want to optimize so that even your slowest 1% of requests are acceptable.

**Ways to improve performance:**
- Caching (store frequently-used data in fast memory)
- CDN (serve content from servers near the user)
- Database indexing (find data faster)
- Efficient algorithms

---

#### Security

**Definition:** Protecting the system and its data from unauthorized access, attacks, and misuse.

**Key areas:**

| Area | What it protects | Example measure |
|------|-----------------|-----------------|
| Authentication | Verifying who you are | Username + password, MFA |
| Authorization | What you're allowed to do | "Only admins can delete users" |
| Encryption in transit | Data safe while traveling | HTTPS / TLS |
| Encryption at rest | Data safe while stored | Encrypted hard drives |
| DDoS protection | Preventing attack floods | Rate limiting, firewalls |
| Input validation | Preventing injection attacks | Sanitizing user inputs |

---

#### Maintainability

**Definition:** How easy it is for developers to understand, modify, and fix the system over time.

**Why it matters:**
- Systems live for years and need constant updates
- Bad maintainability = bugs take weeks to fix instead of hours
- Good maintainability = new developers can contribute quickly

**Practices:**
- Clean, readable code with good documentation
- Modular design (small, independent components)
- Good test coverage
- Clear deployment process

---

#### Observability

**Definition:** How well you can understand what's happening inside the system from the outside.

**Three pillars:**

| Pillar | What it is | Example |
|--------|-----------|---------|
| Logs | Text record of events | "Error at 10:05AM: DB timeout" |
| Metrics | Numbers over time | CPU usage, request count |
| Traces | End-to-end request journey | "Request took 500ms: 100ms in API, 400ms in DB" |

**Why it matters:** You can't fix what you can't see. Observability tells you *what* is broken, *where* it's broken, and *why* it's broken.

---

## 2. DNS — Domain Name System

### 2.1 The Problem DNS Solves

Computers on the internet communicate using **IP addresses** — numbers like `142.250.80.46`.

But humans are bad at remembering numbers. We remember names like `google.com`.

**DNS is the internet's phonebook** — it translates human-readable domain names into IP addresses that computers use.

When you type `google.com`:
1. Your computer doesn't know where Google is
2. It asks DNS: "What is the IP address of google.com?"
3. DNS says: "It's 142.250.80.46"
4. Your computer connects to that IP address

---

### 2.2 DNS System Architecture

DNS is not just one server — it's a hierarchical system with four levels.

```
Your Computer
     ↓
Recursive Resolver (your ISP's DNS)
     ↓
Root Name Server
     ↓
TLD Name Server (.com, .org, .in)
     ↓
Authoritative Name Server (for google.com)
     ↓
Returns IP Address
```

---

#### Level 1: Recursive Resolver

**What it is:** The first DNS server your computer contacts. Usually provided by your ISP (Internet Service Provider) or you can use public ones like Google (8.8.8.8) or Cloudflare (1.1.1.1).

**Role:** It does the work of finding the IP address for you. It's like a librarian who searches through different card catalogs on your behalf.

**Caching:** The resolver caches (saves) results so it doesn't need to ask again for the same domain. This is why DNS is fast — most answers are already cached.

---

#### Level 2: Root Name Server

**What it is:** The "top of the tree" in DNS. There are only 13 sets of root servers in the entire world (but each set has many physical machines for redundancy).

**Role:** It doesn't know the IP of `google.com`, but it knows which server handles `.com` domains.

**Analogy:** The root server is like a head librarian who says "I don't know which book you want, but books starting with G are in Section C."

---

#### Level 3: TLD Name Server (Top-Level Domain)

**What it is:** Handles specific domain extensions like `.com`, `.org`, `.net`, `.in`, `.uk`, etc.

**Role:** Knows which **authoritative name server** is responsible for `google.com`.

**Example:** The `.com` TLD server knows that `google.com` is managed by Google's own name servers.

---

#### Level 4: Authoritative Name Server

**What it is:** The final authority for a specific domain. Google manages this for `google.com`.

**Role:** Contains the actual DNS records — it gives the final answer: "google.com = 142.250.80.46"

---

### 2.3 Full DNS Resolution — Step by Step

Let's trace what happens when you type `www.google.com` in your browser for the first time:

**Step 1:** Your browser checks its own cache — "Have I looked this up before?" → No.

**Step 2:** Your OS checks its local cache (`/etc/hosts` file and OS DNS cache) → Not found.

**Step 3:** Your OS sends the query to the **Recursive Resolver** (your ISP's DNS server).

**Step 4:** The Recursive Resolver checks its cache → Not found (first time).

**Step 5:** Recursive Resolver asks a **Root Name Server**: "Who handles `www.google.com`?"
- Root Server replies: "I don't know the IP, but the `.com` TLD server can help. Go ask `192.5.6.30`"

**Step 6:** Recursive Resolver asks the **TLD Name Server** for `.com`: "Who handles `google.com`?"
- TLD Server replies: "Google's authoritative server handles it. Go ask `216.239.32.10`"

**Step 7:** Recursive Resolver asks **Google's Authoritative Name Server**: "What is the IP for `www.google.com`?"
- Authoritative Server replies: "It's `142.250.80.46`"

**Step 8:** Recursive Resolver saves this in its cache (for TTL duration) and returns the IP to your computer.

**Step 9:** Your browser connects to `142.250.80.46` and loads Google.

**Total time:** Usually under 100ms (often much less due to caching).

---

### 2.4 TTL — Time To Live

**What it is:** Every DNS record has a TTL value — a number of seconds that tells resolvers how long to cache the result.

- **Low TTL (e.g., 60 seconds):** DNS changes propagate quickly, but more DNS queries are needed (slower, more load)
- **High TTL (e.g., 86400 = 24 hours):** Fast lookups due to caching, but changes take a long time to propagate

**Practical use:**
- Before migrating a website to a new server, lower the TTL to 60 seconds a few days ahead
- After migration, raise it back to 24 hours

---

### 2.5 DNS Record Types

| Record Type | What it does | Example |
|-------------|-------------|---------|
| A | Maps domain to IPv4 address | `google.com → 142.250.80.46` |
| AAAA | Maps domain to IPv6 address | `google.com → 2607:f8b0::200e` |
| CNAME | Alias — one name points to another name | `www.google.com → google.com` |
| MX | Mail server — where to send email | `gmail.com → mail server` |
| TXT | Text info — used for verification | Used by Google, security records |
| NS | Name Server — which server handles this domain | `google.com → ns1.google.com` |

---

### 2.6 Why DNS Matters for System Design

- **Load distribution:** One domain name can map to multiple IP addresses (round-robin DNS)
- **Failover:** If a server dies, update DNS to point to a backup server
- **Geographic routing:** Route users to the nearest data center based on their location (GeoDNS)
- **Microservices:** Internal DNS lets services find each other by name instead of IP address

---

## 3. Summary

| Concept | Key Point |
|---------|-----------|
| Functional Requirements | What the system does (features) |
| Non-Functional Requirements | How well the system performs |
| Scalability | Handle more load (vertical vs horizontal) |
| Availability | Stay up (measured in "nines") |
| Reliability | Be correct, don't lose data |
| Performance | Latency + Throughput |
| Security | Auth, encryption, protection |
| DNS | Translates domain names to IP addresses |
| Recursive Resolver | Searches DNS on your behalf |
| Root Server | Top of DNS hierarchy |
| TLD Server | Handles .com, .org, .in etc. |
| Authoritative Server | Gives final IP answer |
| TTL | How long to cache DNS answers |

---

*Next: Part 3 — APIs and Communication*
