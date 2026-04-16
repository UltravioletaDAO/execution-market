"""
PHOTINT Category Prompt: Knowledge Access

Forensic verification checks for tasks requiring access to local knowledge
sources -- scanning book pages, photographing documents, capturing information
from physical reference materials, archives, or records.

The core adversarial concern: workers may submit screenshots of digital copies,
photos of photocopies, or images that do not actually contain the requested
information. The vision model must distinguish genuine physical document
photography from digital reproductions and verify that the captured content
satisfies the task requirements.
"""


def get_category_checks(task: dict) -> str:
    title = task.get("title", "Unknown")
    description = task.get("instructions", task.get("description", ""))

    return f"""### Knowledge Access Verification

**Task context**: "{title}" -- {description or "No description provided."}

Evaluate the submitted photo evidence against these forensic checks:

#### A. Information Readability
- Is the requested information clearly visible and legible in the photo?
- Can the text be read without ambiguity? Check for motion blur, camera shake,
  or shallow depth of field that renders key passages unreadable.
- If numbers, dates, or proper nouns are part of the request, are they sharp
  enough to transcribe with certainty?
- Zoom mentally into the critical regions: would OCR succeed on the text shown?

#### B. Physical Document Authenticity
- Does the image show a PHYSICAL document photographed in a real environment?
- Look for paper texture, fiber patterns, page curvature near the spine,
  natural shadows cast by page edges, and perspective distortion from the
  camera angle -- these are hallmarks of genuine document photography.
- Check for ambient reflections on glossy pages or laminated surfaces.
- Is the document resting on a surface (desk, table, lap) with visible context,
  or is it floating on a pure white/black background (suspicious)?

#### C. Screenshot and Digital Copy Detection
- REJECT if the image is a screenshot of a PDF, e-book reader, web page, or
  digital scan. Indicators:
  - Perfectly flat text with zero perspective distortion
  - Visible scroll bars, browser chrome, app UI, status bars, navigation
  - Uniform white background with no paper texture
  - Pixel-perfect edges on text (no optical softening from camera lens)
  - Screen moire patterns (cross-hatch interference from photographing a screen)
  - Device bezels, rounded corners, or notification bars visible
- A photo OF a screen showing the document is also a red flag -- look for
  screen glare, pixel grid, refresh line artifacts, and color banding.

#### D. Content Completeness
- Is the FULL requested content visible in the frame?
- Are there page numbers, headers, or section markers that confirm the correct
  page or section was photographed?
- If the task requested multiple pages or sections, are all of them present
  across the submitted photos?
- Has relevant content been cropped out at the edges? Check whether text runs
  off-frame, especially at margins.
- If an ISBN, publication date, edition, or author is relevant, is it captured?

#### E. Source Identification
- Can the source material be identified? Look for:
  - Book covers, title pages, copyright pages
  - Journal headers, volume/issue numbers
  - Archive catalog numbers, library stamps, call numbers
  - Newspaper mastheads, publication dates
- Does the identified source match what the task expected?

#### F. Content Relevance
- Does the photographed content actually answer the task's question or provide
  the specific information requested?
- A clear photo of the WRONG page, WRONG document, or WRONG section should be
  flagged even if technically well-captured.
- Is there evidence the worker understood the request and found the correct
  material, or does it appear to be a random page submission?

#### G. Fraud Indicators Specific to Knowledge Access
- Stock photos of generic open books (no specific content readable)
- Previously captured photos resubmitted (check EXIF date vs task creation)
- Photocopies photographed to simulate original access (flat lighting, toner
  artifacts, visible photocopy edge borders)
- AI-generated text in document images (inconsistent font rendering, nonsense
  words, misaligned baselines)

**task_checks to populate**:
- `information_readable` (bool): Requested information is clearly legible
- `document_authentic` (bool): Appears to be a genuine physical document, not a digital reproduction
- `content_complete` (bool): All requested content is visible without critical cropping
- `relevant_to_task` (bool): Content actually answers the task's specific question
- `not_digital_screenshot` (bool): Photo is of a physical document, not a screenshot or screen photo"""
