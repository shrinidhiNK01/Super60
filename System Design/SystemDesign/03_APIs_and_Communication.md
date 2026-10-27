# System Design Notes — Part 3: APIs and Communication

---

## 1. What is an API?

**API = Application Programming Interface**

An API is a way for two pieces of software to talk to each other. It defines:
- What requests can be made
- How to make them (format, rules)
- What responses to expect

**Real-world analogy:** Think of a restaurant menu. The menu is the API — it tells you what you can order (available operations), the format of your order (what information to provide), and what you'll get back (the response).

You don't need to know how the kitchen works. You just place an order through the defined interface (the menu) and get food back.

**In software:**
- Your mobile app (client) uses an API to talk to the backend server
- Weather apps use a weather API to get forecast data
- Payment apps use Stripe's API to process payments

---

## 2. Types of APIs

### 2.1 REST API (Representational State Transfer)

**The most widely used API style today.**

**Core idea:** Every "thing" in your system is a **resource** (a user, a post, a product), and you interact with resources using standard HTTP methods.

**Key characteristics:**
- Uses HTTP (the same protocol as websites)
- **Stateless:** Each request contains all the info needed. The server doesn't remember your previous requests.
- Data usually in **JSON** format
- Each resource has a unique URL

**Example:**
- `GET /users/123` → "Give me user with ID 123"
- `POST /users` → "Create a new user"
- `DELETE /users/123` → "Delete user 123"

**When to use REST:**
- Public APIs
- Web and mobile applications
- When simplicity and broad support matter
- CRUD (Create, Read, Update, Delete) operations

---

### 2.2 SOAP API (Simple Object Access Protocol)

**Older, more rigid standard. Used mostly in enterprise/legacy systems.**

**Key characteristics:**
- Uses XML format (verbose and complex)
- Very strict structure with defined contracts (WSDL files)
- Works over multiple protocols (HTTP, SMTP, etc.)
- Built-in error handling
- Supports advanced security (WS-Security)

**When to use SOAP:**
- Banking and financial systems (where strict contracts matter)
- Legacy enterprise systems that already use it
- When advanced security standards are required

**REST vs SOAP:**

| Feature | REST | SOAP |
|---------|------|------|
| Format | JSON (lightweight) | XML (verbose) |
| Speed | Faster | Slower |
| Complexity | Simple | Complex |
| Flexibility | High | Low |
| Security | Basic (HTTPS) | Advanced (WS-Security) |
| Use today | Very common | Legacy/enterprise |

---

### 2.3 GraphQL

**A query language for APIs created by Facebook in 2015.**

**The problem it solves:**
- With REST, you often get **too much data** (over-fetching) or need **multiple requests** to get related data (under-fetching)

**Example problem with REST:**
- You want to display a user's name and their last 3 posts
- REST: Call `/users/123` (gets name + 20 other fields you don't need) + Call `/users/123/posts` (gets all posts, you only need 3)
- GraphQL: One request, you specify exactly what you want

**GraphQL request:**
```graphql
query {
  user(id: "123") {
    name
    posts(last: 3) {
      title
      date
    }
  }
}
```

**Response:**
```json
{
  "user": {
    "name": "Alice",
    "posts": [
      {"title": "Post 1", "date": "2024-01-01"},
      {"title": "Post 2", "date": "2024-01-02"},
      {"title": "Post 3", "date": "2024-01-03"}
    ]
  }
}
```

**When to use GraphQL:**
- Mobile apps (bandwidth is precious — only fetch what you need)
- Complex data with many relationships
- When frontend teams need flexibility to define their own data needs
- Rapid product development

**Downsides:**
- More complex to set up
- Caching is harder than REST
- Can be over-engineered for simple use cases

---

### 2.4 gRPC (Google Remote Procedure Call)

**A high-performance communication framework created by Google.**

**Core idea:** Instead of thinking about HTTP requests, you think about calling functions (procedures) on a remote server.

**Key characteristics:**
- Uses **Protocol Buffers (Protobuf)** — binary format, much smaller and faster than JSON
- Supports **streaming** in both directions
- Strongly typed — both sides agree on the data format
- HTTP/2 underneath — supports multiplexing (multiple requests in one connection)
- Auto-generates client code from API definition

**Speed comparison:**
- REST with JSON: Parse text, flexible but slower
- gRPC with Protobuf: Binary format, ~5-10x faster for same data

**When to use gRPC:**
- **Microservices talking to each other** internally (not for end-users)
- Real-time bidirectional streaming
- When performance is critical (gaming, IoT, financial services)
- Polyglot environments (different services in different languages)

**Downsides:**
- Not human-readable (binary format)
- Not supported by browsers natively (you need a proxy)
- More complex setup than REST

---

### 2.5 WebSockets

**A protocol for real-time, two-way communication between client and server.**

**The problem with HTTP:** Normal HTTP is request-response. The client asks, the server answers. The server **cannot proactively push** data to the client.

**Problem example:** You're building a live chat app.
- With HTTP: Client must ask "any new messages?" every second (called polling) — wasteful and laggy
- With WebSockets: The server can push new messages the instant they arrive

**How WebSockets work:**
1. Client sends a special HTTP request: "I want to upgrade to WebSocket"
2. Server agrees
3. A persistent connection is established — now both can send data anytime
4. Connection stays open until one side closes it

**When to use WebSockets:**
- Live chat applications (WhatsApp, Slack)
- Real-time notifications
- Live sports scores
- Collaborative editing (Google Docs)
- Online multiplayer games
- Live trading dashboards

**Downside:**
- Maintaining open connections at scale is expensive (one connection per user)
- More complex than REST

---

### 2.6 When to Use Which API

| Situation | Best Choice |
|-----------|-------------|
| Standard web/mobile app | REST |
| Legacy enterprise system | SOAP |
| Mobile app with complex data needs | GraphQL |
| Internal microservice communication | gRPC |
| Real-time features (chat, live data) | WebSockets |

---

## 3. REST API Deep Dive

Since REST is the most common, let's go deep on how it works.

### 3.1 HTTP Methods

HTTP methods define what **action** you want to perform on a resource.

| Method | Action | Example | Idempotent? |
|--------|--------|---------|-------------|
| GET | Read/retrieve data | `GET /products` | Yes |
| POST | Create new resource | `POST /products` | No |
| PUT | Replace entire resource | `PUT /products/5` | Yes |
| PATCH | Update part of resource | `PATCH /products/5` | Yes |
| DELETE | Delete resource | `DELETE /products/5` | Yes |

**Idempotent:** Doing the same request multiple times gives the same result.
- `GET /users/1` — No matter how many times you call it, it just reads data. No side effects.
- `DELETE /users/1` — First call deletes user. All subsequent calls: "user not found." Same end state.
- `POST /users` — Each call creates a NEW user. Not idempotent.

**PUT vs PATCH:**
- `PUT /users/1` with `{"name": "Alice", "email": "alice@example.com"}` — Replaces the entire user record
- `PATCH /users/1` with `{"name": "Alice"}` — Updates only the name field, email stays unchanged

---

### 3.2 Endpoints

**What it is:** The URL that identifies a specific resource or collection of resources.

**Good REST endpoint design:**
- Use **nouns, not verbs** (the HTTP method already says the action)
- Use **plural** for collections

```
✅ Good:
GET    /users          → Get all users
GET    /users/123      → Get user 123
POST   /users          → Create a user
PUT    /users/123      → Update user 123
DELETE /users/123      → Delete user 123
GET    /users/123/posts → Get all posts by user 123

❌ Bad:
GET  /getUsers
POST /createUser
GET  /deleteUser?id=123
```

---

### 3.3 JSON (JavaScript Object Notation)

**The standard data format for REST APIs.**

```json
{
  "id": 123,
  "name": "Alice Johnson",
  "email": "alice@example.com",
  "age": 28,
  "address": {
    "city": "Bangalore",
    "country": "India"
  },
  "hobbies": ["reading", "coding", "hiking"]
}
```

**Why JSON?**
- Human-readable
- Lightweight (smaller than XML)
- Supported natively by JavaScript
- Easy to parse in all languages

---

### 3.4 Query Parameters

**Used to filter, sort, or paginate data without changing the endpoint.**

```
GET /products?category=electronics&maxPrice=5000&sort=price&order=asc
```

Breaking it down:
- `?` — Start of query parameters
- `category=electronics` — Filter by electronics
- `&` — Separator between parameters
- `maxPrice=5000` — Only products under ₹5000
- `sort=price` — Sort by price
- `order=asc` — Ascending order

**Pagination example:**
```
GET /posts?page=2&limit=10
```
→ Get 10 posts, starting from page 2 (posts 11-20)

---

### 3.5 Request Body

**Used with POST, PUT, PATCH to send data to the server.**

```http
POST /users
Content-Type: application/json

{
  "name": "Bob Smith",
  "email": "bob@example.com",
  "password": "securepassword123"
}
```

---

### 3.6 HTTP Status Codes

Status codes tell the client what happened with their request.

**2xx — Success:**
| Code | Meaning | When |
|------|---------|------|
| 200 OK | Request succeeded | GET, PUT, PATCH |
| 201 Created | New resource created | POST |
| 204 No Content | Success, no data to return | DELETE |

**3xx — Redirection:**
| Code | Meaning | When |
|------|---------|------|
| 301 Moved Permanently | Resource has a new URL forever | Site migration |
| 302 Found | Temporary redirect | Login redirects |
| 304 Not Modified | Cached version is still valid | Browser caching |

**4xx — Client Errors (you did something wrong):**
| Code | Meaning | When |
|------|---------|------|
| 400 Bad Request | Invalid input/format | Malformed JSON |
| 401 Unauthorized | Not authenticated | No login token |
| 403 Forbidden | Authenticated but not allowed | No permission |
| 404 Not Found | Resource doesn't exist | Wrong URL |
| 409 Conflict | Resource conflict | Duplicate email |
| 422 Unprocessable | Validation failed | Email format wrong |
| 429 Too Many Requests | Rate limited | Too many API calls |

**5xx — Server Errors (the server did something wrong):**
| Code | Meaning | When |
|------|---------|------|
| 500 Internal Server Error | Generic server crash | Unhandled exception |
| 502 Bad Gateway | Upstream server failed | Load balancer issue |
| 503 Service Unavailable | Server is down/overloaded | Maintenance |
| 504 Gateway Timeout | Upstream server too slow | Database timeout |

---

### 3.7 Request and Response Headers

**Headers** provide metadata about the request or response.

**Common request headers:**
```
Content-Type: application/json     → "I'm sending JSON"
Authorization: Bearer <token>      → "Here's my auth token"
Accept: application/json           → "I want JSON back"
Accept-Language: en-US             → "I prefer English"
```

**Common response headers:**
```
Content-Type: application/json     → "I'm returning JSON"
Cache-Control: max-age=3600        → "Cache this for 1 hour"
X-Rate-Limit-Remaining: 95        → "You have 95 API calls left"
```

---

### 3.8 API Design Best Practices

1. **Use proper HTTP methods** — GET for reading, POST for creating, etc.
2. **Use correct status codes** — 404 for not found, 201 for created, etc.
3. **Version your API** — `/v1/users`, `/v2/users` so you can change without breaking existing clients
4. **Be consistent** — Same naming convention throughout (camelCase or snake_case, not both)
5. **Return useful error messages** — Tell the client *why* it failed
   ```json
   {
     "error": "validation_failed",
     "message": "Email is not in a valid format",
     "field": "email"
   }
   ```
6. **Pagination** — Never return 10 million records at once; use `page` and `limit`
7. **Security** — Always use HTTPS, validate all inputs, authenticate sensitive endpoints
8. **Rate limiting** — Limit how many calls a client can make (e.g., 100 requests/minute)
9. **Documentation** — A good API needs clear documentation (Swagger/OpenAPI)

---

## 4. Summary

| API Type | Best For | Format |
|----------|---------|--------|
| REST | Standard web/mobile apps | JSON over HTTP |
| SOAP | Enterprise/legacy systems | XML |
| GraphQL | Flexible data fetching | JSON, custom query |
| gRPC | Fast internal microservices | Binary (Protobuf) |
| WebSockets | Real-time, bidirectional | Any |

**HTTP Methods:**
- GET → Read, POST → Create, PUT → Replace, PATCH → Update, DELETE → Delete

**Status Codes:**
- 2xx = Success, 4xx = Client error, 5xx = Server error

---

*Next: Part 4 — SQL Databases*
