"""
PHOTINT Category Prompt: Social Proof

Forensic verification checks for social proof tasks such as event
attendance, community participation, public posting verification,
and social media engagement.

These tasks require the worker to demonstrate authentic participation
in a social or public activity. The key challenge is distinguishing
current, genuine participation from recycled, staged, or fabricated
evidence.
"""


def get_category_checks(task: dict) -> str:
    """Return category-specific verification instructions for social proof tasks.

    These instructions are injected into Layer 5 (Task Completion Assessment)
    of the PHOTINT base prompt. The vision model uses them to evaluate whether
    the submitted photo evidence proves authentic social participation.

    Args:
        task: Task dict with title, description/instructions, category,
              location, deadline, evidence_schema, etc.

    Returns:
        Multi-line string with forensic verification checks.
    """
    title = task.get("title", "Unknown task")
    location = task.get("location", task.get("location_text", "Not specified"))
    instructions = task.get("instructions", task.get("description", ""))

    return f"""### Social Proof Verification (PHOTINT Category: social_proof)

**Task context**: "{title}" at: {location}
{f"**Task instructions**: {instructions}" if instructions else ""}

Perform the following forensic checks. For each check, note your finding
and rate confidence (CONFIRMED / HIGH / MODERATE / LOW). Social proof
tasks are vulnerable to recycled evidence from past events — temporal
verification is critical.

#### A. Event / Venue Verification
1. **Venue identification**: Is the event venue identifiable? Look for
   venue name on signage, banners, projection screens, or physical
   markers (entrance arches, branded stages, sponsor logos).
2. **Event-specific materials**: Are there event-specific items visible
   that could not easily be fabricated or reused? Examples: dated
   programs, unique stage setups, event-branded backdrops, sponsor
   arrangements specific to this edition.
3. **Crowd and activity**: Does the scene show an active event with
   attendees? An empty venue or suspiciously sparse crowd (relative to
   the event's expected size) should be noted.
4. **Event type match**: Does the visible activity match the type of
   event described in the task (conference, concert, meetup, workshop,
   protest, market, etc.)?

#### B. Attendance Proof
5. **Personal attendance artifacts**: Are attendance-proving items
   visible? Look for name badges, lanyards, wristbands, stamps
   (hand/wrist), ticket stubs, or printed programs with the worker
   visible alongside them.
6. **Stage / presentation context**: If the task involves attending a
   talk or presentation, is a speaker, stage, or screen with
   presentation content visible? The content should be consistent
   with the claimed event.
7. **Selfie or inclusion**: Is the worker visibly present in the photo
   (selfie, group photo) rather than submitting a generic venue shot
   that anyone could have taken from the internet?

#### C. Community Participation
8. **Active participation evidence**: Does the photo show the worker
   actively participating (interacting with others, performing an
   activity, holding event materials) rather than passively observing
   from a distance?
9. **Group context**: In group photos, does the setting and composition
   appear natural and spontaneous, or staged and artificial?
10. **Venue context alignment**: Does the interior/exterior setting match
    a venue where the claimed community activity would plausibly occur?

#### D. Temporal Currency (Current vs. Recycled)
11. **Date indicators**: Are there visible dates on banners, screens,
    programs, or digital displays that confirm the event is current
    (matches the task's time window)?
12. **Seasonal consistency**: Does vegetation, clothing, weather, and
    lighting match the expected season for the task's date? Winter
    coats at a June event, or summer foliage for a December submission,
    are strong fraud indicators.
13. **Technology anachronisms**: Are visible devices (phones, laptops,
    displays) consistent with current technology? Outdated devices or
    software interfaces may indicate an old photo.
14. **News / media cross-reference**: If the event is notable, do
    visible details (speaker, stage design, sponsor lineup) match what
    is known about the current edition vs. past editions?
15. **Recycled content detection**: Search for indicators that this exact
    photo has been used before — watermarks, social media overlays from
    past posts, EXIF dates far in the past.

#### E. Social Media Post Verification (if applicable)
16. **Platform UI authenticity**: If the evidence includes a screenshot
    of a social media post, does the UI match the current version of
    that platform? Outdated UI elements suggest an old screenshot.
17. **Timestamp visibility**: Is the post timestamp visible and readable
    in the screenshot? Does it fall within the task's time window?
18. **Profile consistency**: Does the visible profile name/photo match
    the worker's claimed identity? Look for inconsistencies.
19. **Engagement plausibility**: Are visible engagement metrics (likes,
    comments, shares) plausible, or do they suggest a fabricated or
    purchased-engagement post?
20. **Screenshot authenticity**: Is this a genuine device screenshot
    (consistent resolution, device-appropriate status bar, no warping)
    or a photo of a screen / digitally fabricated image?

#### F. Required task_checks (include in output JSON)
Your `task_checks` object MUST include these boolean fields:
- `event_verified`: The event/venue is identifiable and matches the task description
- `attendance_proven`: The worker demonstrably attended (not just a generic venue photo)
- `activity_authentic`: The social activity shown is genuine and matches what was requested
- `temporal_current`: Evidence is from the correct time period (not recycled from a past event)
- `not_recycled`: No indicators that the photo is reused from a previous occasion"""
