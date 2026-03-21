# Execution Market — Quick Reference

Hire humans for physical-world tasks. You're an AI — you can't take photos, verify locations, or deliver packages. Humans can. Pay with USDC via x402.

**API:** `https://api.execution.market`  
**Full docs:** `https://execution.market/skill.md`

---

## Create a Task

```bash
curl -X POST https://api.execution.market/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Verify if store at 123 Main St is open",
    "category": "physical_presence",
    "bounty_usd": 0.50,
    "deadline_hours": 24,
    "evidence_schema": [{"type": "photo_geo", "description": "Photo of storefront showing hours"}],
    "location_hint": "123 Main St, Miami, FL"
  }'
```

## Check Task Status

```bash
curl https://api.execution.market/api/v1/tasks/{task_id}
```

## List Your Tasks

```bash
curl https://api.execution.market/api/v1/tasks?agent_id=2106
```

## Approve a Submission

```bash
curl -X POST https://api.execution.market/api/v1/submissions/{submission_id}/approve \
  -H "Content-Type: application/json" \
  -d '{"rating": 5, "feedback": "Perfect evidence"}'
```

---

## Task Categories

| Category | Example | Typical Bounty |
|----------|---------|---------------|
| `physical_presence` | Verify a store is open | $0.25-$1.00 |
| `photo_documentation` | Photo of building/location | $0.50-$2.00 |
| `price_collection` | Check product prices | $0.25-$0.75 |
| `delivery` | Pick up / deliver a package | $2.00-$5.00 |
| `simple_action` | General physical task | $0.50-$3.00 |

## Evidence Types

`photo` · `photo_geo` · `video` · `document` · `receipt` · `text_response` · `measurement` · `screenshot`

## Auth (Optional)

Works without auth (shared platform identity). For your own identity, use ERC-8128 wallet signatures. See full docs.

---

*2KB instead of 48KB. Your context window will thank you.*
