"""
PHOTINT Category Prompt: Bureaucratic

Forensic verification checks for tasks involving government offices,
administrative procedures, paperwork, queues, and institutional interactions --
filing permits, paying fines, registering documents, obtaining certificates,
waiting in government queues, and similar bureaucratic errands.

The core adversarial concern: workers may submit old photos of government
buildings, fabricate queue tickets or receipts, or claim to have completed
an interaction without actually visiting the institution. The vision model must
verify genuine institutional interaction with temporal and spatial consistency.
"""


def get_category_checks(task: dict) -> str:
    """Return category-specific verification instructions for bureaucratic tasks.

    Args:
        task: Task dict with title, description, evidence requirements, etc.

    Returns:
        Multi-line string of forensic checks for injection into Layer 5.
    """
    title = task.get("title", "Unknown")
    description = task.get("instructions", task.get("description", ""))
    location = task.get("location", task.get("location_text", ""))

    return f"""### Bureaucratic Task Verification

**Task context**: "{title}" -- {description or "No description provided."}
**Expected institution/location**: {location or "Not specified"}

Evaluate the submitted photo evidence against these forensic checks:

#### A. Institution Verification
- Is the government office, agency, or institution identifiable in the photos?
- Look for:
  - Official signage with the institution's full name
  - Government logos, coat of arms, or official emblems
  - Building exterior or interior that matches known government architecture
    (security checkpoints, service windows, waiting areas)
  - Institutional branding on walls, doors, reception desks
- Does the identified institution match the one required by the task?
- If the task specifies a particular branch or office (e.g., "DMV on 5th Ave"),
  is there evidence of THAT specific location, not just any branch?

#### B. Interaction Documentation
- Is there photographic evidence of actual interaction with the institution?
- Look for evidence such as:
  - Service counter or window where the interaction occurred
  - Staff members (faces may be blurred for privacy -- that is acceptable)
  - Documents being handed over or received
  - Computer screens at service points showing transaction details
  - The worker's perspective from inside the building (not just exterior)
- A photo of only the building exterior from across the street is insufficient
  for most bureaucratic tasks -- it proves proximity but not interaction.

#### C. Queue and Waiting Evidence
- If the task involves waiting in a queue or line:
  - Is there a queue ticket, turn number, or waiting number visible?
  - Is a digital queue display board visible showing current numbers?
  - Is the waiting area visible with other people waiting (consistent with
    a real government office)?
  - Is there a sequence of photos showing progression (ticket received,
    waiting, number called, at the window)?
- Queue ticket details to verify:
  - Ticket number, service category, estimated wait time
  - Date and time printed on the ticket (matches task date?)
  - Institution name on the ticket

#### D. Form Completion Evidence
- If the task requires filling out or submitting forms:
  - Are the required forms visible and identifiable?
  - Are the forms filled out (not blank)?
  - Is the form the correct one for the requested procedure?
  - Can the form title or reference number be read?
  - If the task requires specific information to be entered, is it visible
    in the completed fields?
- Note: personal data on forms may be redacted for privacy -- partial
  redaction is acceptable if the form type and completion status are still
  verifiable.

#### E. Official Stamps, Receipts, and Processing Evidence
- Is there evidence that the institution actually processed the request?
  - Official receipt with transaction number, date, amount paid (if applicable)
  - Stamp or seal on submitted documents indicating receipt/processing
  - File number, case number, or tracking number assigned
  - Appointment confirmation or follow-up date issued
  - "Received" or "Filed" stamps with dates
- A receipt or proof of processing is the strongest evidence that the
  bureaucratic interaction was completed, not just attempted.

#### F. Temporal Consistency
- Do the photos show evidence consistent with a visit during business hours?
  - Is the office open and staffed?
  - Are queue systems active?
  - Does the lighting suggest a time consistent with government office hours?
- Check date stamps on receipts and tickets against the task deadline.
- If the task was created today, evidence showing dates from previous days
  or weeks is a red flag (unless the task explicitly allows pre-existing visits).

#### G. Fraud Indicators Specific to Bureaucratic Tasks
- Stock or generic photos of government buildings without worker presence
- Old receipts or tickets resubmitted for a new task (check dates carefully)
- Fabricated queue tickets (inconsistent fonts, wrong institution name,
  implausible ticket numbers)
- Photos of only the exterior with no evidence of entry or interaction
- Digitally created or modified receipts (uniform background, suspiciously
  clean text, no paper texture)
- Screenshots of online government portals when the task required in-person
  visits (check for browser UI, URL bars, digital interface elements)

**task_checks to populate**:
- `institution_verified` (bool): The correct government office/agency is identifiable in the evidence
- `interaction_documented` (bool): There is evidence of actual interaction with the institution, not just proximity
- `forms_completed` (bool): Required forms are visible, correctly identified, and filled out
- `receipt_obtained` (bool): An official receipt, tracking number, or proof of processing is present
- `official_processing_evident` (bool): Evidence that the institution processed the request (stamps, filed status, assigned numbers)"""
