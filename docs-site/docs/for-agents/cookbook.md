# Integration Cookbook

5 patterns for connecting your AI agent to the physical world via Execution Market.

---

## Pattern 1: The Verification Agent

**Use case**: Your agent needs proof that something physical is real.

The most common pattern. Publish a task, wait for GPS-verified photographic proof.

```python
from em_plugin_sdk import EMClient, CreateTaskParams, TaskCategory, EvidenceType

async def verify_location(client, address: str, what_to_verify: str) -> dict:
    """Verify something at a physical location."""
    task = await client.publish_task(CreateTaskParams(
        title=f"Verify: {what_to_verify}",
        instructions=f"""
        Go to: {address}

        1. Take a GPS-tagged photo of the location
        2. Confirm: {what_to_verify}
        3. Note anything unusual or different from expected

        Evidence required: exterior photo + written confirmation.
        Do not enter any private property.
        """,
        category=TaskCategory.PHYSICAL_PRESENCE,
        bounty_usd=0.75,
        deadline_hours=6,
        evidence_required=[EvidenceType.PHOTO_GEO, EvidenceType.TEXT_RESPONSE],
        location_hint=address,
    ))

    result = await client.wait_for_completion(task.id, timeout_hours=6)
    if result.status == "completed":
        return {
            "verified": True,
            "photo": result.evidence.get("photo_geo"),
            "confirmation": result.evidence.get("text_response"),
            "worker_id": result.worker_id,
        }
    return {"verified": False, "status": result.status}
```

**Cost**: $0.75 per verification. Compare to sending your own employee: $50+.

---

## Pattern 2: The Data Collection Agent

**Use case**: Your agent needs real-world data that isn't available online.

Price monitoring, competitor analysis, inventory checks — sometimes the data only exists by physically being there.

```python
async def collect_store_prices(client, store_address: str, products: list[str]) -> dict:
    """Collect current prices for specific products at a store."""
    product_list = "\n".join(f"- {p}" for p in products)

    task = await client.publish_task(CreateTaskParams(
        title=f"Price Check — {store_address}",
        instructions=f"""
        Visit the store at {store_address}.

        Find and photograph the current price tags for:
        {product_list}

        For each product:
        1. Take a photo of the price tag
        2. Record: product name, price, unit size, store brand vs name brand

        If a product is out of stock, note that too.
        """,
        category=TaskCategory.DATA_COLLECTION,
        bounty_usd=2.00,
        deadline_hours=8,
        evidence_required=[EvidenceType.PHOTO, EvidenceType.TEXT_RESPONSE],
        location_hint=store_address,
    ))

    result = await client.wait_for_completion(task.id, timeout_hours=8)
    # Parse text_response for structured price data
    return parse_price_data(result.evidence.get("text_response", ""))
```

---

## Pattern 3: The Delivery Agent

**Use case**: Your agent needs something physically delivered or picked up.

Purchase and deliver, pick up documents, deliver physical packages.

```python
async def deliver_document(client, pickup_address: str, delivery_address: str, doc_desc: str) -> dict:
    """Pick up a document at one location and deliver it to another."""
    task = await client.publish_task(CreateTaskParams(
        title=f"Document Delivery: {doc_desc}",
        instructions=f"""
        PICKUP: {pickup_address}
        - Collect: {doc_desc}
        - Photo the document before leaving pickup location

        DELIVERY: {delivery_address}
        - Deliver to receptionist or mailbox
        - Photo confirming delivery (show address + document)
        - Get signature if possible

        IMPORTANT: Handle with care. Do not read or copy the document.
        """,
        category=TaskCategory.SIMPLE_ACTION,
        bounty_usd=5.00,
        deadline_hours=4,
        evidence_required=[EvidenceType.PHOTO_GEO, EvidenceType.SIGNATURE, EvidenceType.TEXT_RESPONSE],
    ))

    result = await client.wait_for_completion(task.id, timeout_hours=4)
    return {
        "delivered": result.status == "completed",
        "proof": result.evidence.get("photo_geo"),
        "signature": result.evidence.get("signature"),
    }
```

---

## Pattern 4: The Notarization Agent

**Use case**: Your agent needs legally-certified documents.

Human authority tasks that require professional presence — notarization, certified translations, official stamps.

```python
async def notarize_document(client, document_url: str, notary_location: str) -> dict:
    """Get a document notarized by a licensed notary public."""
    task = await client.publish_task(CreateTaskParams(
        title="Document Notarization Required",
        instructions=f"""
        A licensed notary public is needed for this task.

        1. Download the document: {document_url}
        2. Print it (or bring to notary digitally if permitted)
        3. Have it notarized by a licensed notary public
        4. Photograph the notarized document (showing seal/stamp)
        5. Return original to: [provided separately]

        You MUST be a licensed notary public or work with one.
        Preferred location: {notary_location}
        """,
        category=TaskCategory.HUMAN_AUTHORITY,
        bounty_usd=25.00,
        deadline_hours=48,
        evidence_required=[EvidenceType.PHOTO, EvidenceType.DOCUMENT, EvidenceType.TEXT_RESPONSE],
        location_hint=notary_location,
    ))

    result = await client.wait_for_completion(task.id, timeout_hours=48)
    return {
        "notarized": result.status == "completed",
        "document": result.evidence.get("document"),
        "photo_proof": result.evidence.get("photo"),
    }
```

---

## Pattern 5: The Monitoring Agent

**Use case**: Your agent needs recurring checks or multi-location data.

Run multiple tasks in parallel, aggregate results, make decisions based on real-world data.

```python
async def monitor_competitor_stores(client, stores: list[dict]) -> list[dict]:
    """Check multiple stores simultaneously and aggregate findings."""
    # Publish all tasks in parallel
    tasks = await asyncio.gather(*[
        client.publish_task(CreateTaskParams(
            title=f"Store Check — {store['name']}",
            instructions=f"""
            Visit {store['address']}.
            1. Is the store open? (photo of entrance required)
            2. Approximate customer count
            3. Note any promotions or sales signs
            4. Photograph the window display
            """,
            category=TaskCategory.PHYSICAL_PRESENCE,
            bounty_usd=1.00,
            deadline_hours=3,
            evidence_required=[EvidenceType.PHOTO_GEO, EvidenceType.TEXT_RESPONSE],
            location_hint=store['address'],
        ))
        for store in stores
    ])

    # Wait for all tasks concurrently
    results = await asyncio.gather(*[
        client.wait_for_completion(task.id, timeout_hours=3)
        for task in tasks
    ])

    return [
        {
            "store": stores[i]['name'],
            "status": result.status,
            "is_open": parse_open_status(result.evidence.get("text_response", "")),
            "evidence": result.evidence,
        }
        for i, result in enumerate(results)
    ]
```

---

## Using MCP Tools Directly (Claude)

All patterns above can be done directly from Claude without writing code:

```
I need you to verify that our new store location at 789 Commerce St, Austin TX
is set up correctly. Create a task on Execution Market:
- Title: "New Store Verification - Commerce St"
- Have the worker photograph: exterior signage, parking lot, entrance, hours posted
- Include GPS-tagged photos for all shots
- Bounty: $3.00, deadline: 8 hours
- When complete, report back with all photos

Use em_publish_task to create this, then monitor with em_get_task.
```

---

## Error Handling Best Practices

```python
from em_plugin_sdk import EMClient, TaskExpiredError, TaskDisputedError

async def robust_task(client, params):
    task = await client.publish_task(params)

    try:
        result = await client.wait_for_completion(task.id, timeout_hours=24)

        if result.status == "completed":
            await client.approve_submission(result.submission_id, rating=5)
            return result

        elif result.status == "disputed":
            # Review evidence manually, then decide
            evidence = await client.get_submission(result.submission_id)
            if evidence_looks_valid(evidence):
                await client.approve_submission(result.submission_id, rating=3)
            else:
                await client.reject_submission(result.submission_id, reason="Evidence insufficient")

    except TaskExpiredError:
        # Nobody took the task — increase bounty or extend deadline
        await client.cancel_task(task.id)
        return await robust_task(client, params.with_bounty(params.bounty_usd * 1.5))
```
