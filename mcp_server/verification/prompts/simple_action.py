"""
PHOTINT Category Prompt: Simple Action

Forensic verification checks for straightforward action tasks such as
buying a specific item, delivering a package, or performing a discrete
physical action on behalf of an AI agent.

The worker must demonstrate that the requested action was completed
in full, with correct items, acceptable condition, and supporting
proof (receipts, photos of delivered goods, etc.).
"""


def get_category_checks(task: dict) -> str:
    title = task.get("title", "Unknown task")
    location = task.get("location", task.get("location_text", "Not specified"))
    instructions = task.get("instructions", task.get("description", ""))

    return f"""### Simple Action Verification (PHOTINT Category: simple_action)

**Task context**: "{title}" at location: {location}
{f"**Task instructions**: {instructions}" if instructions else ""}

Perform the following forensic checks. For each check, note your finding
and rate confidence (CONFIRMED / HIGH / MODERATE / LOW). Flag absence of
expected evidence as a negative indicator.

#### A. Item / Action Visibility
1. **Requested item or action visible**: Is the item the task asked for
   clearly visible in the photo? If the task requested an action (e.g.,
   "drop off package"), is there visual proof the action was performed?
2. **Correct product identification**: Does the item match the request
   in terms of brand, model, color, size, variant, and any other
   distinguishing attributes specified in the instructions?
3. **Quantity verification**: If the task requested multiple items, are
   all items visible and countable? A single item shown when three were
   requested is incomplete.
4. **Item condition**: Is the item undamaged, sealed (if applicable), and
   in the expected condition? Look for dents, tears, broken seals,
   missing components, or signs of prior use.
5. **Packaging**: Is the item in its original packaging, or in a bag
   from the correct store? Are labels, barcodes, or brand markings
   visible and consistent with the claimed product?

#### B. Receipt Verification
6. **Receipt present**: Is a receipt included in the evidence? For
   purchase tasks, a receipt is a critical proof element.
7. **Store name on receipt**: Does the store name printed on the receipt
   match the store where the purchase was supposed to be made?
8. **Date and time on receipt**: Is the receipt date current (matches the
   task window)? A receipt from days or weeks ago is a red flag.
9. **Items listed on receipt**: Do the line items on the receipt match
   the items requested in the task? Look for product names, SKUs, or
   descriptions that correspond to the task instructions.
10. **Total visible**: Is the total amount on the receipt visible and
    reasonable for the items purchased?
11. **Temporal consistency**: Does the receipt date/time align with the
    submission timestamp? A receipt timestamped hours after the deadline
    or days before the task was published suggests recycled evidence.

#### C. Delivery Proof
12. **Package at location**: If the task involves delivery, is the
    package visible at the specified drop-off location (doorstep,
    mailbox, reception desk)?
13. **Address or location identifiable**: Can the delivery location be
    confirmed from visible address numbers, building name plates,
    apartment signage, or other identifiers?
14. **Package integrity**: Is the package intact and placed appropriately,
    not tossed or damaged?

#### D. Purchase Proof Chain
15. **Complete proof chain**: A fully proven purchase includes three
    independent elements: receipt + item + location. All three
    converging on the same story = HIGH confidence. Missing any one
    element lowers confidence proportionally.
16. **Cross-reference receipt to item**: Do the items physically shown
    match what the receipt lists? Mismatches between receipt line items
    and visible products indicate potential fraud.
17. **Cross-reference receipt to store**: Does the store name on the
    receipt match any visible storefront signage or bags in the photo?

#### E. Staging & Fraud Detection
18. **Recycled evidence**: Could this photo have been taken for a
    different purpose or a previous task? Check for mismatches between
    evidence elements and the current task specifics.
19. **Stock photo indicators**: Watermarks, unnaturally perfect
    composition, or generic product photography suggest non-authentic
    evidence.
20. **Receipt manipulation**: Look for signs of digital editing on the
    receipt (font inconsistencies, alignment issues, color differences
    between text and background).

#### F. Required task_checks (include in output JSON)
Your `task_checks` object MUST include these boolean fields:
- `item_visible`: The requested item or action result is clearly shown
- `receipt_valid`: Receipt is present, current, and matches the task
- `correct_product`: Item matches the requested brand, model, color, size
- `condition_acceptable`: Item is undamaged and in expected condition
- `delivery_confirmed`: Delivery location is confirmed (set true if task is not a delivery)"""
