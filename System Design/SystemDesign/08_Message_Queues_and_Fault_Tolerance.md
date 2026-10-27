# System Design Notes — Part 8: Message Queues & Fault Tolerance

---

## Part A: Message Queues

### 1. The Problem — Synchronous Processing

In a **synchronous** system, when you make a request, you wait for it to complete before moving on.

**Example — Synchronous order processing:**
1. User places an order → API receives it
2. API saves to database (waits)
3. API sends confirmation email (waits for email service)
4. API charges the payment (waits for payment service)
5. API updates inventory (waits)
6. API sends SMS notification (waits)
7. API returns "success" to user

**Total time:** All steps added together. If email service is slow (2 seconds), user waits 2 seconds just for email.

**Problems with synchronous:**
- **Slow:** User waits for every step, including ones they don't need to wait for
- **Tight coupling:** If email service is down, the entire order fails
- **Can't handle spikes:** If 10,000 orders arrive at once, every service must handle 10,000 simultaneously
- **No retry on failure:** If a step fails, the whole thing fails

---

### 2. The Solution — Asynchronous Processing with Message Queues

A **Message Queue** is a buffer — a middleman that holds messages (tasks) until a worker is ready to process them.

**How it works:**
1. Producer puts a message in the queue ("Process this order")
2. Producer continues immediately — doesn't wait
3. Consumer picks up the message from the queue when ready
4. Consumer processes it independently

```
Producer → [Message Queue] → Consumer
           [  Order 1    ]
           [  Order 2    ]
           [  Order 3    ]
                ↓
         Workers pick up orders
         at their own pace
```

**Async order processing:**
1. User places order → API saves to DB → puts "new order" message in queue → returns "Success" to user **immediately**
2. (Asynchronously) Email worker picks up message → sends email
3. (Asynchronously) Payment worker picks up message → charges card
4. (Asynchronously) SMS worker picks up message → sends SMS

**Benefits:**
- User gets instant response (doesn't wait for email, SMS, etc.)
- Each service is decoupled — if email service is down, order still succeeds
- Workers process at their own pace — handles traffic spikes
- Failed tasks stay in queue and can be retried

**Popular message queue systems:** RabbitMQ, Apache Kafka, Amazon SQS, Google Pub/Sub, Azure Service Bus

---

### 3. Core Concepts

#### Producer and Consumer
- **Producer:** The service that sends messages to the queue
- **Consumer:** The service that reads and processes messages from the queue
- One queue can have multiple producers and multiple consumers

#### Queue
The actual buffer that holds messages waiting to be processed. Messages persist even if all consumers are temporarily offline.

#### Broker
The server that manages the queue — receives from producers, stores messages, delivers to consumers.

---

### 4. Types of Queues

#### 4.1 FIFO Queue (First In, First Out)

**How it works:** Messages are processed in the order they were received.

```
Queue: [Message 1 (first)] [Message 2] [Message 3] [Message 4 (latest)]
Consumer processes: Message 1 first → Message 2 → Message 3 → Message 4
```

**Pros:** Maintains order — important when order matters (process payment before shipping)

**Cons:** If Message 1 takes a long time, Messages 2, 3, 4 must wait (head-of-line blocking)

**Use cases:**
- Order processing (payment must happen before shipping)
- Database migrations (apply changes in sequence)
- Any workflow where order matters

---

#### 4.2 Priority Queue

**How it works:** Messages are assigned a priority. Higher priority messages are processed first, regardless of when they were added.

```
Queue:
Priority 1 (Urgent): [VIP customer complaint]
Priority 2 (High):   [Failed payment retry]
Priority 3 (Normal): [Send marketing email]
Priority 4 (Low):    [Generate weekly report]
```

Consumer always picks highest priority message next.

**Use cases:**
- Customer support (VIP customers get faster service)
- Emergency alerts (critical system alerts before info messages)
- Fraud detection (process suspicious transactions immediately)

---

### 5. Pub/Sub Model (Publish-Subscribe)

**Standard queue:** One producer → one queue → one consumer (or competing consumers processing from same queue)

**Pub/Sub:** One producer → one "topic" → **multiple independent consumers** all receive a copy

```
Payment Service publishes "order.completed" event to topic
        ↓
Topic: "order.completed"
        ├→ Email Service (sends confirmation email)
        ├→ Inventory Service (reduces stock)
        ├→ Analytics Service (records sale)
        └→ Loyalty Service (adds points)
```

**Key difference from a regular queue:**
- Regular queue: Message is consumed by ONE consumer. When picked up, it's gone.
- Pub/Sub: Message is received by ALL subscribers. Each gets their own copy.

**How it works:**
- Publisher publishes messages to a **topic**
- Subscribers subscribe to a topic they care about
- Every subscriber gets every message published to that topic
- Publishers and subscribers don't know about each other — loose coupling

**Examples:** Apache Kafka, Google Pub/Sub, Amazon SNS, Redis Pub/Sub

---

### 6. Push vs Pull Model

#### Push Model
The broker **pushes** messages to consumers as they arrive.
- Consumer registers with the broker: "Send me messages when they arrive"
- Broker delivers immediately
- Consumer must be always online and ready

**Pros:** Low latency — messages delivered the instant they arrive
**Cons:** Can overwhelm slow consumers — what if they can't keep up?

**Examples:** Amazon SQS with push, webhooks

---

#### Pull Model
The consumer **pulls** (polls) messages from the queue at its own pace.
- Consumer asks: "Do you have any messages for me?"
- Broker responds: "Yes, here are 10 messages"
- Consumer processes them, asks again

**Pros:** Consumer controls its own rate. Can't be overwhelmed.
**Cons:** Latency — consumer might not pull immediately when a message arrives. Polling adds overhead.

**Examples:** Apache Kafka (pull-based), most consumers poll

**Kafka's approach:** Consumers poll at high frequency. New messages are available almost instantly. Consumers maintain their own "offset" (position in the queue).

---

### 7. Poison Messages

**What is a poison message?** A message that consistently causes the consumer to fail and crash.

**Example:**
- Consumer tries to process a message
- Message has a malformed format or invalid data
- Consumer throws an exception and crashes
- Queue retries the message
- Consumer crashes again
- Message goes back to queue... infinite loop

**Solution — Dead Letter Queue (DLQ):**
- After a message fails N times (e.g., 3 times), move it to a separate "Dead Letter Queue"
- Main processing continues with other messages
- Operations team investigates messages in the DLQ later
- Option to replay fixed messages or discard them

```
Main Queue → Consumer crashes (3 attempts) → Dead Letter Queue
                                               ↑
                                   Ops team investigates
```

---

### 8. Duplicate Messages (At-Least-Once Delivery)

**The problem:** In distributed systems, it's hard to guarantee exactly-once delivery.

**Why duplicates happen:**
1. Consumer processes a message
2. Consumer sends "acknowledgment" (ACK) to queue
3. ACK is lost due to network failure
4. Queue thinks message wasn't processed
5. Queue resends the message
6. Consumer processes it again → duplicate processing

**Delivery guarantees:**

| Guarantee | Description | Risk |
|-----------|-------------|------|
| At-Most-Once | Message delivered 0 or 1 times | Data loss (if message lost, not retried) |
| At-Least-Once | Message delivered 1 or more times | Duplicates (processed multiple times) |
| Exactly-Once | Message delivered exactly 1 time | Hardest to achieve, highest overhead |

**Handling duplicates — Idempotency:**
Design your consumer to be **idempotent** — processing the same message multiple times produces the same result as processing it once.

**Examples:**
- Sending an email for order #123: Before sending, check "Have I already sent an email for order #123?" → If yes, skip.
- Charging a payment: Use a unique transaction ID. Database constraint prevents charging twice for the same ID.
- Updating a balance: "Set balance to $500" is idempotent. "Add $50 to balance" is NOT (would add $50 twice if processed twice).

---

### 9. Real-World Message Queue Architecture

**YouTube video upload flow:**
```
User uploads video
       ↓
Upload Service → [Queue] → Transcoding Service (converts to multiple resolutions)
                        → Thumbnail Service (generates thumbnails)
                        → Metadata Service (extracts tags, duration)
                        → Notification Service (alerts subscribers)
```

All of these happen asynchronously. YouTube immediately says "Your video is uploading" without waiting for transcoding.

---

## Part B: Fault Tolerance

### 10. Types of Failures

No system is perfect. Failures happen. The question is: how does your system handle them?

#### Hardware Failures

**Examples:**
- Hard drive failure (most common: enterprise drives fail ~2% per year)
- Memory (RAM) corruption
- CPU overheating
- Power supply failure
- Network interface card failure
- Entire server dying
- Data center power outage

**Solutions:**
- **RAID storage:** Redundant hard drives. Data written to multiple disks. One fails, others have the data.
- **Redundant power supplies:** Two power supplies per server
- **UPS (Uninterruptible Power Supply):** Battery backup for brief power outages
- **Hot standby servers:** Identical server ready to take over if primary fails
- **Multi-AZ deployment:** Servers in multiple Availability Zones (different physical buildings with independent power, network, cooling)

---

#### Software Failures

**Examples:**
- Memory leaks (app gradually uses more RAM until it crashes)
- Infinite loops
- Unhandled exceptions causing crashes
- Deadlocks (two processes each waiting for the other to release a lock)
- Cascading failures (one service failure causes a chain of failures in dependent services)

**Solutions:**

**Circuit Breaker Pattern:**
- Monitor calls to a downstream service
- If too many calls fail, "open" the circuit — stop calling the failing service
- Return a fallback response immediately
- Periodically test if the service has recovered; if yes, "close" the circuit

```
Normal → [API calls Service B] → Success
Degraded → [Service B failing] → Circuit OPENS
Protected → [Reject calls immediately, return fallback] → Don't overwhelm Service B
Recovery → [Try Service B again] → Success → Circuit CLOSES
```

**Bulkhead Pattern:**
- Isolate components so one failure doesn't cascade to everything
- Like watertight bulkheads in a ship — one compartment floods, others stay dry
- Example: Use separate thread pools for different downstream services. Service A slowdown doesn't exhaust threads for Service B.

**Retry with Exponential Backoff:**
- When a call fails, retry automatically
- But don't retry immediately (might make it worse)
- Wait 1s, then 2s, then 4s, then 8s... (exponential backoff)
- Add jitter (randomness) to prevent all clients retrying simultaneously

---

#### Human Errors

**The most common cause of production outages.**

**Examples:**
- Wrong deployment (deployed bad code)
- Accidental deletion of data or database
- Misconfigured infrastructure
- Incorrect configuration changes

**Solutions:**

**Infrastructure as Code (IaC):** Define infrastructure in code (Terraform, CloudFormation). Changes go through code review. Reduces misconfiguration.

**Blue-Green Deployments:** Run two identical environments (Blue = current, Green = new). Deploy to Green, test, then switch traffic. If something's wrong, switch back to Blue instantly.

**Canary Deployments:** Roll out changes to 1% of users first. Monitor for errors. If good, gradually increase to 5%, 10%, 100%.

**Feature Flags:** Deploy new code but keep it turned off. Turn on for specific users/regions. Turn off immediately if problems.

**Database Backups:**
- Regular automated backups (daily full, hourly incremental)
- Test backup restoration regularly ("a backup you've never tested is not a backup")
- Point-in-time recovery capability

---

### 11. Recovery Strategies

#### RTO and RPO — Critical Concepts for Business

**RTO — Recovery Time Objective:**
Maximum acceptable time for a system to be down.
- "We can be down for at most 4 hours before business impact is unacceptable."

**RPO — Recovery Point Objective:**
Maximum acceptable data loss measured in time.
- "We can afford to lose at most 1 hour of data."

These define what backup/recovery solution you need:

| RTO | RPO | Solution |
|-----|-----|---------|
| 24 hours | 24 hours | Daily backup to tape/cloud |
| 4 hours | 1 hour | Hot standby + hourly backups |
| 15 minutes | 5 minutes | Active-passive failover + frequent snapshots |
| 30 seconds | Near-zero | Active-active with synchronous replication |

---

### 12. Reliability Best Practices

1. **Eliminate single points of failure (SPOF):** Every component should have at least one backup.
2. **Design for failure:** Assume everything will fail. How does your system behave?
3. **Graceful degradation:** When a component fails, the rest of the system keeps working at reduced capacity. Don't fail completely.
   - YouTube recommendation service down → Still show videos, just not personalized
4. **Test failure scenarios:** Netflix uses "Chaos Monkey" — a tool that randomly kills servers in production to ensure systems can handle failures.
5. **Rate limiting:** Prevent any one client from overwhelming the system.
6. **Timeout everything:** Every external call should have a timeout. Don't wait forever.
7. **Monitor and alert:** Can't fix what you don't know is broken.

---

## 13. Summary

### Message Queues

| Concept | Key Point |
|---------|-----------|
| Message Queue | Buffer between producers and consumers |
| FIFO Queue | Process in order |
| Priority Queue | High priority first |
| Pub/Sub | One message → multiple consumers |
| Push | Broker sends to consumer |
| Pull | Consumer fetches from broker |
| Poison Message | Message that always fails → Dead Letter Queue |
| At-Least-Once | May get duplicates → use idempotent consumers |
| Exactly-Once | Hardest, most overhead |

### Fault Tolerance

| Type | Solutions |
|------|-----------|
| Hardware failure | Redundancy, RAID, multi-AZ |
| Software failure | Circuit breaker, bulkhead, retry |
| Human error | IaC, canary deploys, feature flags, backups |
| Recovery | RTO (downtime), RPO (data loss), active-passive, active-active |

---

*Next: Part 9 — Monitoring, Observability & Final Case Study*
