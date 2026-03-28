"""
PHOTINT Category Prompt: Social

Forensic verification checks for social interaction tasks (conduct interview,
make introduction, attend social gathering). These tasks involve human-to-human
interaction, so checks focus on evidence of genuine engagement, participant
presence, venue verification, and outcome documentation while respecting
privacy considerations.
"""


def get_category_checks(task: dict) -> str:
    """Return category-specific verification instructions for social tasks.

    These instructions are injected into Layer 5 (Task Completion Assessment)
    of the PHOTINT base prompt. The vision model uses them to evaluate whether
    the submitted photo evidence proves the worker participated in the
    requested social interaction.

    Args:
        task: Task dict with title, description/instructions, category,
              location, deadline, evidence_schema, etc.

    Returns:
        Multi-line string with forensic verification checks.
    """
    title = task.get("title", "Unknown task")
    location = task.get("location", task.get("location_text", "Not specified"))
    instructions = task.get("instructions", task.get("description", ""))

    return f"""### Social Interaction Verification (PHOTINT Category: social)

**Task context**: "{title}" at location: {location}
{f"**Task instructions**: {instructions}" if instructions else ""}

**Privacy note**: Social tasks involve real people. Faces may be intentionally
blurred, obscured, or out of frame to protect privacy. This is acceptable and
expected. Focus on contextual evidence of interaction rather than facial
identification.

Perform the following forensic checks. For each check, note your finding
and rate confidence (CONFIRMED / HIGH / MODERATE / LOW). Flag absence of
expected evidence as a negative indicator.

#### A. Evidence of Social Interaction
1. **Interaction occurring**: Is there visible evidence that a social
   interaction is taking place or has taken place? Look for body language
   indicating conversation (facing each other, gesturing), shared
   activity, or collaborative engagement.
2. **Not a solo photo**: Does the photo show more than one person, or
   clear evidence that multiple people were present (multiple drinks,
   place settings, seats occupied, belongings of others)?
3. **Authentic interaction vs. staged pose**: Does the scene look like a
   genuine interaction or a staged photograph? Authentic interactions
   show natural body positioning, mid-conversation gestures, and
   environmental engagement. Stiff posing with eye contact toward the
   camera suggests staging.
4. **Same person in multiple roles**: If multiple people are visible,
   do they appear to be genuinely different individuals? Same clothing,
   build, or accessories appearing in different "roles" suggests the
   worker staged the interaction alone.

#### B. Participant Presence
5. **Multiple participants**: Are the expected number of participants
   present or evidenced? For an interview, at least two people (or
   evidence of two — e.g., two microphones, two cups). For a gathering,
   a group.
6. **Participant engagement**: Are participants actively engaged (talking,
   listening, taking notes, exchanging materials) rather than passive or
   clearly disinterested?
7. **Appropriate participants**: If the task specifies a particular type
   of participant (e.g., store manager, community leader), is there any
   contextual evidence supporting that role (name badge, behind a counter,
   at a podium)?

#### C. Venue Verification
8. **Correct meeting location**: Does the venue match the location
   specified in the task? Look for venue signage, recognizable interior
   or exterior features, or location-specific context.
9. **Appropriate venue type**: Is the venue appropriate for the type of
   social interaction? A job interview in a professional setting, a
   community meeting in a public space, etc.
10. **Indoor/outdoor consistency**: Does the environment match what the
    task implies? An "outdoor market visit" should not show an office
    interior.

#### D. Temporal Evidence
11. **Within task window**: Is there evidence the interaction happened
    within the task's time window? Clock visible, daylight conditions,
    event-specific signage with dates, or timestamped materials.
12. **Duration evidence**: For tasks requiring a minimum interaction
    duration, is there evidence of sustained engagement (multiple photos
    from different moments, progression of activity, notes accumulation)?

#### E. Outcome Documentation
13. **Notes or recording evidence**: If the task requires documenting the
    interaction, are notes, a recording device, forms, or written
    materials visible?
14. **Materials exchanged**: If the task involves exchanging materials
    (business cards, documents, products), is there evidence of the
    exchange or the received materials?
15. **Outcome deliverables**: Does the submission include any deliverables
    the task requested (interview transcript summary, contact information
    collected, meeting minutes, feedback gathered)?

#### F. Required task_checks (include in output JSON)
Your `task_checks` object MUST include these boolean fields:
- `interaction_occurred`: There is clear evidence of a social interaction taking place
- `participants_present`: The expected number and type of participants are evidenced
- `venue_correct`: The venue matches the specified meeting location
- `activity_authentic`: The interaction appears genuine, not staged or faked
- `outcome_documented`: Required deliverables (notes, materials, outcomes) are evidenced"""
