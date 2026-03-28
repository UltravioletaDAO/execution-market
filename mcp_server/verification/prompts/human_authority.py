"""
PHOTINT Category Prompt: Human Authority

Forensic verification checks for tasks requiring the exercise of human
authority -- notarized documents, certified translations, official stamps,
signatures, apostilles, sworn declarations, and other acts that require a
credentialed human to perform.

The core adversarial concern: forged or fabricated official documents,
counterfeit stamps/seals, expired or invalid credentials of the authorizing
person, or documents that appear official but lack legally required elements.
These tasks involve legal instruments where fraud can have serious consequences.
"""


def get_category_checks(task: dict) -> str:
    """Return category-specific verification instructions for human authority tasks.

    Args:
        task: Task dict with title, description, evidence requirements, etc.

    Returns:
        Multi-line string of forensic checks for injection into Layer 5.
    """
    title = task.get("title", "Unknown")
    description = task.get("instructions", task.get("description", ""))
    location = task.get("location", task.get("location_text", ""))

    return f"""### Human Authority Verification

**Task context**: "{title}" -- {description or "No description provided."}
**Jurisdiction context**: {location or "Not specified"}

Evaluate the submitted photo evidence against these forensic checks:

#### A. Signature Verification
- Is a handwritten signature clearly visible on the document?
- Does the signature appear to be applied with a pen on paper (ink texture,
  pressure variation, natural stroke dynamics) vs digitally inserted (uniform
  line weight, perfectly smooth curves, no pen lift artifacts)?
- If multiple signatures are required (e.g., notary + party), are all present?
- Is the signature placed in the expected field/location on the document?

#### B. Seal and Stamp Authentication
- Is an official seal, stamp, or embossing visible?
- Stamp quality assessment:
  - Crisp, well-defined edges with ink saturation = likely original impression
  - Blurry, faded, or fragmented edges = possible photocopy or digital overlay
  - Uniform color without ink bleeding = suspicious (real stamps often have
    slight ink spread on paper)
- If an embossed seal is expected, look for raised/depressed surface texture
  visible through light reflection or shadow. Embossing cannot be photocopied.
- Does the seal contain expected elements: coat of arms, registration number,
  institution name, official text?

#### C. Required Fields Completeness
- Are ALL required fields filled in? Check for:
  - Full legal names of all parties
  - Dates (execution date, expiration date if applicable)
  - Case numbers, file numbers, or registration numbers
  - Document reference numbers or serial numbers
  - Jurisdiction identification
  - Purpose or subject matter of the document
- Are fields filled by hand, typed, or left blank? Blank required fields
  indicate an incomplete document.

#### D. Authority Identification
- Can the authorizing person be identified? Look for:
  - Printed name and title (Notary Public, Certified Translator, etc.)
  - Professional license or commission number
  - Commission expiration date (is it still valid?)
  - Jurisdiction of authority (state, country, territory)
  - Bar number, registration number, or certification ID
- If a notary, is the notary block/jurat complete with all statutory elements?

#### E. Document Format and Standards
- Does the document format match known standards for this type of document
  in the relevant jurisdiction?
- Check for expected elements:
  - Letterhead with institution name, address, contact information
  - Proper legal language and formatting conventions
  - Correct paper size and orientation for the jurisdiction
  - Page numbering if multi-page (and initialing of each page if required)
- Does the formatting appear professional and consistent, or does it look
  like a hastily assembled template?

#### F. Security Features
- If the document type typically includes security features, are they present?
  - Watermarks (visible when backlit or at angles)
  - Holographic elements (rainbow reflections, color-shifting areas)
  - Security paper (patterns, colored fibers, reactive elements)
  - Microprinting (extremely small text that appears as a line to the naked eye)
  - Sequential numbering from official stock
- Absence of expected security features is a significant red flag for
  high-value official documents.

#### G. Tampering Detection
- Look for evidence of alteration to critical fields:
  - Different ink colors or pen types within the same handwritten section
  - White-out, correction tape, or overwritten text
  - Cut-and-paste artifacts (misaligned text, inconsistent backgrounds)
  - Digital modification (font changes within typed sections, resolution
    differences between text regions)
  - Dates or names that appear to have been changed after initial completion
- Compare the apparent age of the document with claimed dates -- fresh-looking
  paper with a date from months/years ago may indicate backdating.

#### H. Fraud Indicators Specific to Human Authority
- Template documents downloaded from the internet with fields filled in
  (check for common template watermarks or generic formatting)
- Self-notarization (same handwriting for notary and party signatures)
- Stamps or seals that appear digitally superimposed (perfectly aligned,
  no paper interaction, uniform opacity)
- Documents that reference non-existent registration numbers or institutions
- AI-generated official-looking documents (check for realistic-seeming but
  nonsensical legal language, institution names that do not exist)

**task_checks to populate**:
- `signature_visible` (bool): Required signature(s) are clearly visible and appear genuine
- `seal_authentic` (bool): Official seal/stamp/embossing appears to be an authentic impression
- `fields_complete` (bool): All required fields are filled in with appropriate information
- `authority_identified` (bool): Authorizing person's name, title, and credentials are visible
- `document_format_valid` (bool): Document format matches expected standards for this document type
- `no_tampering` (bool): No evidence of alteration, overwriting, or post-completion modification"""
