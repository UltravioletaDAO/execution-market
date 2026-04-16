"""
PHOTINT Category Prompt: Verification

Forensic verification checks for general verification tasks such as
confirming existence of something, status checks, condition reports,
and inspection documentation.

These tasks require the worker to document the current state of a
subject (object, property, equipment, infrastructure) with enough
detail and authenticity for a remote party to make decisions based on
the evidence.
"""


def get_category_checks(task: dict) -> str:
    title = task.get("title", "Unknown task")
    location = task.get("location", task.get("location_text", "Not specified"))
    instructions = task.get("instructions", task.get("description", ""))

    return f"""### General Verification (PHOTINT Category: verification)

**Task context**: "{title}" at: {location}
{f"**Task instructions**: {instructions}" if instructions else ""}

Perform the following forensic checks. For each check, note your finding
and rate confidence (CONFIRMED / HIGH / MODERATE / LOW). Verification
tasks demand clarity and completeness — if the subject cannot be
positively identified, the verification fails.

#### A. Subject Identification
1. **Subject clearly visible**: Is the subject of verification (object,
   property, equipment, infrastructure, document, etc.) clearly visible
   and in focus? The subject should occupy a significant portion of the
   frame and be unambiguous.
2. **Identifiability**: Can the specific subject be positively identified
   from the photo? Look for serial numbers, model numbers, labels,
   addresses, distinctive markings, or other unique identifiers that
   tie this photo to the exact subject described in the task.
3. **Correct subject**: Does the visible subject match what the task asked
   to verify? Confirming the wrong item (e.g., photographing Building A
   when the task asked about Building B) is a failure even if the photo
   is technically excellent.
4. **Context confirmation**: Does the surrounding environment support
   that this is the correct subject? A furnace photographed in a
   basement is consistent; the same furnace model in an outdoor market
   is suspicious.

#### B. Condition Documentation
5. **Current state assessment**: Is the current condition of the subject
   visible? Look for indicators of: functionality (lights on, displays
   active, moving parts in motion), damage (cracks, dents, rust,
   discoloration, missing parts), wear (patina, scratches, fading),
   or pristine condition.
6. **Damage documentation**: If the task asks about damage or defects,
   are they clearly photographed with sufficient detail to assess
   severity? Close-up shots of damage areas are expected. Distance-only
   shots that obscure defects are insufficient.
7. **Functional indicators**: For equipment or systems, are there visible
   indicators of operational status? LED lights, display readouts,
   gauge readings, output products, or running sounds (if video) all
   contribute. Their absence when expected should be noted.
8. **Comparison to expected state**: If the task provides a reference
   state (e.g., "verify this was repaired"), does the current state
   match the expected post-condition? Look for fresh repair indicators
   (new materials, paint, sealant) or remaining defects.

#### C. Thoroughness of Documentation
9. **Multiple angles**: Does the evidence include views from multiple
   angles when the subject's geometry warrants it? A single flat-on
   shot may miss damage on sides, back, or top. Complex subjects need
   multiple perspectives.
10. **Scale reference**: Is there an object of known size in the frame
    that provides scale? This is important for assessing dimensions,
    extent of damage, or size of the subject. Common references:
    hands, coins, rulers, standard-sized objects (doors, bricks, etc.).
11. **Detail resolution**: Are critical details readable? Text on labels,
    gauge readings, serial numbers, small defects — these should be
    sharp enough to read. Blurry evidence that obscures critical details
    is insufficient.
12. **Completeness**: Does the evidence cover all aspects the task asked
    to verify? If the task asks to check "front and back," both must be
    present. Partial documentation leaves the verification incomplete.

#### D. Scene Authenticity
13. **Environmental context**: Does the surrounding environment match
    where the subject is expected to be? An indoor appliance should be
    in a building, outdoor infrastructure should be in an outdoor
    setting with appropriate surroundings.
14. **Lighting and visibility**: Is the photo taken with adequate lighting
    to see the subject clearly? Dark, underexposed photos that hide
    details may be intentional obfuscation. Flash artifacts should not
    obscure critical areas.
15. **Temporal indicators**: Are there visible indicators of when the
    photo was taken? Dated newspapers, digital displays with timestamps,
    seasonal cues, or changing conditions (construction progress,
    seasonal merchandise) help establish currency.
16. **Manipulation detection**: Look for signs the photo was altered to
    change the apparent condition: cloned regions, color adjustments
    limited to specific areas, resolution inconsistencies between the
    subject and its surroundings, or unnatural edge artifacts.

#### E. Evidence Sufficiency Assessment
17. **Would a reasonable person be convinced?** Step back from individual
    checks: does the totality of the evidence give a clear, convincing
    picture of the subject and its condition? If you were making a
    business decision based on this evidence, would you feel confident?
18. **Information gaps**: List any information the task requested that is
    NOT visible in the submitted evidence. Each gap weakens the
    verification. Multiple gaps together may warrant rejection or
    NEEDS_HUMAN.
19. **Ambiguity assessment**: Is there any aspect of the evidence that
    could reasonably be interpreted in two contradictory ways? If so,
    flag for human review.

#### F. Required task_checks (include in output JSON)
Your `task_checks` object MUST include these boolean fields:
- `subject_identified`: The subject of verification is clearly visible and positively identifiable
- `condition_documented`: The current condition/state is adequately captured in the evidence
- `evidence_sufficient`: The quantity and quality of evidence is enough to support a verification decision
- `authenticity_confirmed`: The photo appears authentic with no manipulation indicators
- `details_readable`: Critical details (text, numbers, labels, defects) are sharp and legible"""
