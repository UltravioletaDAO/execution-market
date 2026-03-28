"""
PHOTINT Category Prompt: Proxy

Forensic verification checks for proxy tasks where the worker acts on
behalf of the AI agent or another party -- purchasing items, attending
meetings, representing at events, collecting documents, or performing
actions that require a human stand-in.

The worker must demonstrate that the proxy action was fully performed,
not merely that they were present. Outcomes, acquired items, and
documentation of what was achieved are critical.
"""


def get_category_checks(task: dict) -> str:
    """Return category-specific verification instructions for proxy tasks.

    These instructions are injected into Layer 5 (Task Completion Assessment)
    of the PHOTINT base prompt. The vision model uses them to evaluate whether
    the submitted photo evidence proves the worker performed the proxy action
    in full and documented the outcomes.

    Args:
        task: Task dict with title, description/instructions, category,
              location, deadline, evidence_schema, etc.

    Returns:
        Multi-line string with forensic verification checks.
    """
    title = task.get("title", "Unknown task")
    location = task.get("location", task.get("location_text", "Not specified"))
    instructions = task.get("instructions", task.get("description", ""))

    return f"""### Proxy Action Verification (PHOTINT Category: proxy)

**Task context**: "{title}" at location: {location}
{f"**Task instructions**: {instructions}" if instructions else ""}

Perform the following forensic checks. For each check, note your finding
and rate confidence (CONFIRMED / HIGH / MODERATE / LOW). Flag absence of
expected evidence as a negative indicator.

#### A. Proxy Action Performed
1. **Evidence of action**: Is there clear photographic evidence that the
   proxy action was actually performed, not just planned or attempted?
   The worker must show outcomes, not only presence.
2. **Action specificity**: Does the evidence match the specific proxy
   action requested? A generic photo of a building does not prove
   that a meeting was attended or a purchase was made inside.
3. **Worker role clarity**: Is the worker's role in the proxy action
   identifiable from the evidence? For a purchase proxy, the worker
   should be the buyer. For a meeting proxy, the worker should have
   been an active participant or observer as specified.

#### B. Purchase Proxy
4. **Receipt with correct items**: If the task was a purchase proxy, is
   a receipt present showing the correct items were purchased?
5. **Store identification**: Is the store or vendor identifiable in the
   evidence (storefront signage, receipt header, branded bag)?
6. **Payment proof**: Is there evidence of payment (receipt total,
   transaction confirmation, payment terminal display)?
7. **Items acquired**: Are the purchased items visible in the evidence,
   matching the task requirements in type, quantity, and specification?

#### C. Meeting / Event Proxy
8. **Venue confirmed**: If the task was a meeting or event proxy, is the
   venue identifiable (building name, room number, event banner, venue
   signage)?
9. **Attendance evidence**: Is there evidence of active attendance, such
   as meeting materials (agenda, handouts, badge), other attendees
   visible, presentation slides, or the meeting room setup?
10. **Notes or documentation**: Did the worker document the outcomes of
    the meeting -- decisions made, key points discussed, action items?
    This can be handwritten notes, a typed summary, or photos of a
    whiteboard/presentation.

#### D. Representation & Document Collection
11. **Forms or documents**: If the proxy task involved signing forms,
    collecting documents, or submitting paperwork, are the relevant
    documents visible in the evidence?
12. **Representation adequacy**: Does the evidence show the worker
    completed the full scope of the representation, not just a partial
    step? Picking up a form is not the same as filling it out and
    submitting it, if submission was required.
13. **Document authenticity**: Do visible documents appear genuine
    (official letterhead, stamps, signatures, correct formatting)?
    Generic or blank forms do not constitute completion evidence.

#### E. Outcome Documentation
14. **Outcomes clearly documented**: What was achieved through the proxy
    action? The evidence should show results: items purchased, notes
    from a meeting, documents collected, decisions recorded.
15. **Completeness of proxy action**: Was the full proxy action
    completed, or only a portion? If the task asked the worker to
    attend a meeting and report back, both attendance and the report
    must be evidenced.
16. **Task-specific deliverables**: Does the evidence include all
    deliverables specified in the task instructions? Cross-reference
    each requirement against the submitted evidence.

#### F. Staging & Fraud Detection
17. **Presence without action**: The worker shows they were at a
    location but provides no evidence of the proxy action itself. This
    is the most common fraud pattern for proxy tasks -- showing up is
    not completing.
18. **Recycled meeting photos**: Are meeting materials, badges, or venue
    photos generic enough to have been reused from a different event?
    Look for date-specific details (event banners with dates, agenda
    items matching the task).
19. **Fabricated documents**: Do collected documents or notes appear
    fabricated? Check for inconsistent handwriting, digital text on
    supposedly handwritten notes, or documents that lack official
    markings.

#### G. Required task_checks (include in output JSON)
Your `task_checks` object MUST include these boolean fields:
- `proxy_action_performed`: Worker demonstrably performed the requested proxy action
- `venue_confirmed`: Location or venue where the action took place is identifiable
- `outcomes_documented`: Results, decisions, or deliverables are documented in evidence
- `items_acquired`: Any items to be purchased or collected are present (set true if not applicable)
- `representation_adequate`: The full scope of the proxy action was completed, not partial"""
