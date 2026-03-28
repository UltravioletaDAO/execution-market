"""
PHOTINT Category Prompt: Emergency

Forensic verification checks for urgent, time-critical tasks such as
emergency repairs, immediate physical assistance, or situations that
require a rapid human response. Speed of response and resolution are
key evaluation factors alongside standard evidence quality.

The worker must demonstrate that the emergency was addressed promptly,
handled safely, and resolved (or appropriately escalated). Before/during/
after documentation is ideal but the urgency context means evidence may
be less polished than in non-emergency categories.
"""


def get_category_checks(task: dict) -> str:
    """Return category-specific verification instructions for emergency tasks.

    These instructions are injected into Layer 5 (Task Completion Assessment)
    of the PHOTINT base prompt. The vision model uses them to evaluate whether
    the submitted photo evidence proves the worker responded to the emergency
    promptly, handled it safely, and resolved the situation.

    Args:
        task: Task dict with title, description/instructions, category,
              location, deadline, evidence_schema, etc.

    Returns:
        Multi-line string with forensic verification checks.
    """
    title = task.get("title", "Unknown task")
    location = task.get("location", task.get("location_text", "Not specified"))
    instructions = task.get("instructions", task.get("description", ""))
    deadline = task.get("deadline", "Not specified")

    return f"""### Emergency Response Verification (PHOTINT Category: emergency)

**Task context**: "{title}" at location: {location}
{f"**Task instructions**: {instructions}" if instructions else ""}
**Deadline**: {deadline}

NOTE: Emergency tasks are time-critical. Evidence quality may be lower
than in non-urgent categories (shaky photos, poor lighting, incomplete
framing) due to the stress of the situation. Evaluate substance over
polish -- a blurry photo of a fixed pipe is better evidence than a
perfectly composed photo that does not show the repair.

Perform the following forensic checks. For each check, note your finding
and rate confidence (CONFIRMED / HIGH / MODERATE / LOW). Flag absence of
expected evidence as a negative indicator.

#### A. Situation Documentation
1. **Emergency visible**: Is the emergency situation or its aftermath
   visible in the evidence? This could be the problem (leak, broken
   equipment, blocked access) or the resolution scene.
2. **Context consistency**: Does the scene in the photo match the
   described emergency? A task describing a burst pipe should show
   water damage, plumbing, tools -- not an unrelated environment.
3. **Severity indicators**: Does the evidence show the scale of the
   emergency consistent with the task description? An "urgent" repair
   of a major leak should show evidence proportional to that severity.
4. **Before/during/after documentation**: Ideally the worker captured
   the state before intervention, during the work, and after resolution.
   Even partial documentation (before + after, or during + after) is
   valuable. Only "after" requires higher scrutiny to confirm the
   problem existed in the first place.

#### B. Response Timing
5. **Prompt response**: Does the evidence timeline suggest the worker
   responded promptly? Compare the task publication time, the
   submission timestamp, and any visible time indicators (clocks,
   device timestamps, ambient lighting changes between photos).
6. **Location-time alignment**: Did the worker arrive at the right
   place at an appropriate time given the emergency? A response
   submitted hours after the deadline for an urgent task is suspect.
7. **Urgency corroboration**: Are there visual indicators that the
   situation was treated as urgent -- tools deployed quickly, temporary
   fixes applied before permanent ones, protective measures taken
   immediately?

#### C. Resolution Evidence
8. **Problem resolved**: Is there clear visual evidence that the
   emergency has been addressed? A fixed pipe, restored power,
   cleared obstruction, or stabilized situation should be visible.
9. **Resolution completeness**: Was the emergency fully resolved, or
   only partially mitigated? A temporary patch may be acceptable if
   the task instructions allow it, but full resolution is the default
   expectation.
10. **Functional state**: After the response, does the affected system
    or area appear functional? Running water without leaks, lights on,
    equipment operating, pathway cleared.
11. **No new damage**: Did the response itself cause additional damage?
    The fix should not have created new problems visible in the
    evidence.

#### D. Safety Assessment
12. **Safe response**: Was the emergency handled safely? Look for
    appropriate protective equipment (gloves, goggles, masks) if
    applicable, safe use of tools, and no visible hazards created by
    the response.
13. **Area secured**: After the emergency response, is the area safe?
    No exposed wires, no standing water near electrical components,
    no unstable structures left unaddressed.
14. **Appropriate escalation**: If the emergency was beyond the
    worker's capability, is there evidence of appropriate escalation
    (professional called, area cordoned off, authorities notified)?
    This counts as a valid response for tasks that may exceed a
    single worker's capacity.

#### E. Location and Scene Verification
15. **Correct location**: Does the evidence confirm the worker
    responded at the right location? Address numbers, building
    features, or distinctive environmental markers should match
    the task location.
16. **Scene continuity**: If multiple photos are submitted, do they
    show the same location? Background elements, wall colors,
    flooring, and fixtures should be consistent across all photos.
17. **Environmental conditions**: Do weather, lighting, and ambient
    conditions in the photos match what would be expected at the
    claimed location and time?

#### F. Staging & Fraud Detection
18. **Fabricated emergency**: Could the worker have staged the "before"
    photo to make it appear as if a problem existed? Look for evidence
    that the problem was real -- water stains from an actual leak,
    wear patterns on broken equipment, dust accumulation suggesting
    the scene was not recently arranged.
19. **Unrelated photos**: Are the before and after photos clearly from
    the same location and timeframe? Different wall colors, flooring,
    or fixtures between photos suggest they depict different places.
20. **Disproportionate response**: Is the "fix" shown consistent with
    the problem described? A photo showing a new faucet installed
    when the task was about a roof leak does not constitute relevant
    evidence.

#### G. Required task_checks (include in output JSON)
Your `task_checks` object MUST include these boolean fields:
- `situation_documented`: The emergency situation or its aftermath is visible in evidence
- `response_adequate`: The worker's response appropriately addressed the emergency
- `resolution_visible`: The problem has been fixed or the emergency is demonstrably handled
- `safety_maintained`: The response was conducted safely with no new hazards created
- `timing_appropriate`: Evidence supports that the worker responded at the right place and time"""
