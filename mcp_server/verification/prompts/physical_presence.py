"""
PHOTINT Category Prompt: Physical Presence

Forensic verification checks for tasks requiring physical presence at a
specific location (store verification, location proof, presence check).

The worker must demonstrate they were physically at the claimed location
at the claimed time. This is the most common and most fraud-prone
category, so checks are especially rigorous.
"""


def get_category_checks(task: dict) -> str:
    """Return category-specific verification instructions for physical presence tasks.

    These instructions are injected into Layer 5 (Task Completion Assessment)
    of the PHOTINT base prompt. The vision model uses them to evaluate whether
    the submitted photo evidence proves the worker was at the location.

    Args:
        task: Task dict with title, description/instructions, category,
              location, deadline, evidence_schema, etc.

    Returns:
        Multi-line string with forensic verification checks.
    """
    title = task.get("title", "Unknown task")
    location = task.get("location", task.get("location_text", "Not specified"))
    instructions = task.get("instructions", task.get("description", ""))

    return f"""### Physical Presence Verification (PHOTINT Category: physical_presence)

**Task context**: "{title}" at location: {location}
{f"**Task instructions**: {instructions}" if instructions else ""}

Perform the following forensic checks. For each check, note your finding
and rate confidence (CONFIRMED / HIGH / MODERATE / LOW). Flag absence of
expected evidence as a negative indicator.

#### A. Location Confirmation
1. **Subject at location**: Is the photographer clearly at the specified location?
   Look for address numbers, building name plates, storefront signage, or
   distinctive architectural features that match the claimed location.
2. **Surrounding infrastructure**: Do street signs, building numbers, utility
   poles, road surface, sidewalk style, and other infrastructure elements
   confirm the geographic area?
3. **Landmark cross-reference**: Are any known landmarks, monuments, or
   distinctive buildings visible in the background that independently confirm
   the location?
4. **Reflective surface analysis**: Check windows, mirrors, puddles, and
   metallic surfaces for reflected context that confirms or contradicts the
   scene.

#### B. Business / Storefront Verification
5. **Business name visible**: Is the business name clearly readable? Does it
   match the task target?
6. **Operating status**: Can you determine if the business is open or closed?
   Look for lit/unlit signs, door position (open/closed/locked), people
   entering or exiting, "OPEN/CLOSED" signs, posted hours.
7. **Hours posted**: Are business hours visible? Do they match the context
   of the photo?
8. **Window displays / merchandise**: Does visible merchandise or signage
   match the type of business expected?

#### C. Live Photo vs. Reproduced Image
9. **Live capture indicators**: A live photo should have natural depth of
   field, consistent perspective, and environmental noise (passers-by,
   vehicles, shadows). Look for these.
10. **Screenshot detection**: Check for device bezels, status bars, browser
    chrome, notification bars, rounded corners, or UI overlays that indicate
    a screenshot of another image.
11. **Screen-of-screen (meta-photography)**: Look for moire patterns, visible
    pixel grids, screen glare, or warped perspective that indicate the
    worker photographed a screen displaying someone else's photo.
12. **Stock photo indicators**: Watermarks, unnaturally perfect composition,
    generic subjects, overly clean environments with no real-world
    imperfections.
13. **Gallery re-upload**: Check EXIF date vs. submission date. A large gap
    suggests an old photo from the gallery, not a fresh capture.

#### D. Temporal Consistency
14. **Shadow direction and length**: Do shadows match the expected solar
    angle for the claimed time and location? Short shadows = near noon.
    Long shadows = early morning or late afternoon.
15. **Lighting quality**: Is the lighting consistent with the claimed time?
    Golden hour warmth, harsh midday light, blue twilight, or artificial
    night lighting should match.
16. **Weather consistency**: Does the visible weather (clear, cloudy, rain,
    snow) match expected conditions for the location and date?
17. **Photographer shadow**: If the photographer's shadow is visible, is it
    consistent with the other shadows in the scene? Inconsistency suggests
    compositing.

#### E. Staging & Fraud Detection
18. **Phone-in-photo trick**: Is the worker holding up a phone or tablet
    displaying Google Maps, a photo, or an address to simulate being at a
    location? This is a common fraud pattern. The actual physical
    surroundings should confirm location, not a device screen.
19. **Props and artificial setup**: Are there signs of temporary staging —
    printed signs placed in frame, objects positioned unnaturally, or
    items that appear out of context for the location?
20. **Perspective consistency**: Do all objects in the scene share a
    consistent vanishing point and perspective? Composited elements often
    have conflicting perspective lines.
21. **Edge analysis**: Look for hard edges, halo artifacts, or resolution
    differences around the subject that might indicate cut-and-paste
    compositing.

#### F. Required task_checks (include in output JSON)
Your `task_checks` object MUST include these boolean fields:
- `subject_at_location`: Worker is demonstrably at the specified location
- `business_verified`: Target business/storefront is identifiable and matches task
- `live_photo`: Image is a genuine live capture (not screenshot, gallery, or stock)
- `lighting_consistent`: Shadows, lighting, and weather are consistent with claimed time
- `no_staging_indicators`: No evidence of props, screen tricks, or artificial setup"""
