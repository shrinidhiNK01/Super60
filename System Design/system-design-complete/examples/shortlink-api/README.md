# Runnable shortlink learning example

This small API accompanies the deployment lab. It is intentionally **single-instance** because its durable store is a local SQLite file. Do not run more than one replica or treat its local volume as production storage.

## Run it locally

```powershell
docker compose up --build
```

In a second terminal:

```powershell
$key = '0123456789abcdef'
Invoke-RestMethod -Method Post -Uri http://localhost:8080/v1/links `
  -Headers @{ 'Idempotency-Key' = $key } `
  -ContentType 'application/json' `
  -Body '{"destination":"https://example.com"}'
```

Run the same command again: it returns the same code because the idempotency key and request body match. Reusing that key with another body returns a conflict. Visit `http://localhost:8080/{code}` to redirect.

## Production evolution

1. Replace SQLite with a managed relational database and run additive migrations.
2. Add authentication/tenant ownership, rate limits, audit logs and a secret manager.
3. Deploy stateless API replicas with readiness probes and a load balancer.
4. Add a cache-aside Redis tier only after measured redirect traffic warrants it.
5. Emit click events through a transactional outbox; aggregate them asynchronously.

See [the deployment lab](../../08-deployment-lab.md) for the architecture, manifest patterns, rollout and rollback procedure.
