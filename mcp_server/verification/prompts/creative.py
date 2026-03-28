"""
PHOTINT Category Prompt: Creative

Forensic verification checks for tasks requiring creative output -- photography
assignments, art commissions, design work, hand-drawn illustrations, murals,
physical crafts, and other creative deliverables.

The core adversarial concern: workers may submit AI-generated images, stock
photos, previously created work, or work copied from other creators. The vision
model must assess both the creative quality against the brief and the
originality/authenticity of the work.
"""


def get_category_checks(task: dict) -> str:
    """Return category-specific verification instructions for creative tasks.

    Args:
        task: Task dict with title, description, evidence requirements, etc.

    Returns:
        Multi-line string of forensic checks for injection into Layer 5.
    """
    title = task.get("title", "Unknown")
    description = task.get("instructions", task.get("description", ""))

    return f"""### Creative Output Verification

**Task context**: "{title}" -- {description or "No description provided."}

Evaluate the submitted photo evidence against these forensic checks:

#### A. Brief Compliance
- Does the creative output match the task's creative brief and requirements?
- Check every specific element mentioned in the task description:
  - Subject matter (is the correct subject depicted?)
  - Theme, mood, or tone (if specified)
  - Color palette or color restrictions (if specified)
  - Text, slogans, or copy that was requested to be included
  - Specific elements or objects that must appear
- If the brief had multiple requirements, are ALL of them addressed, or only
  some? Partial compliance should be noted.

#### B. Technical Quality Assessment
- Is the technical execution appropriate for the task?
- For photography tasks:
  - Focus: is the subject in sharp focus (unless blur is intentional)?
  - Exposure: properly lit, not blown out or underexposed?
  - Composition: deliberate framing, rule of thirds, leading lines if relevant?
  - White balance: natural color rendition or intentional color grading?
- For art/illustration tasks:
  - Line quality: confident strokes or hesitant/scratchy lines?
  - Proportions: anatomically plausible (if figurative), structurally sound?
  - Color application: even coverage, intentional palette, no accidental mixing?
  - Finishing: does the work appear complete or abandoned mid-process?
- For design tasks:
  - Typography: readable, appropriate font choices, proper hierarchy?
  - Layout: balanced, intentional spacing, visual flow?
  - Resolution: sharp edges, no pixelation at expected viewing size?

#### C. Originality Assessment
- Does the work appear to be original and created for this specific task?
- AI-generation indicators (flag if detected):
  - Unnatural skin textures, plastic-looking surfaces
  - Impossible geometry or physically implausible structures
  - Text rendering errors (garbled letters, nonsensical words in signs or labels)
  - Inconsistent reflections or light sources within the same scene
  - Repeating patterns or tiling artifacts in backgrounds
  - Six or more fingers, fused fingers, impossible hand poses
  - Over-smooth gradients with no natural noise or grain
  - "Too perfect" symmetry in organic subjects
- Stock photo indicators:
  - Watermarks (even partially removed)
  - Unnaturally diverse/posed groups of people (stock photo aesthetic)
  - Generic corporate or lifestyle compositions
  - Suspiciously high production value inconsistent with the task budget
- Copy/plagiarism indicators:
  - Visible watermarks from other artists or platforms
  - Inconsistent style within the same piece (suggesting collage from
    multiple sources)
  - Reverse-image-searchable compositions (note: you cannot search, but
    extremely generic or iconic compositions should raise suspicion)

#### D. Subject Accuracy
- Does the creative work depict what was specifically requested?
- If the task asked for a photo of "sunset over the ocean," is it a sunset
  over the ocean and not a sunrise, not a lake, not a stock image?
- Are identifiable subjects correct? If specific people, places, objects, or
  brands were requested, do they match?
- If the task involved photographing a specific real-world subject, does the
  photo show THAT subject (not a similar one)?

#### E. Format and Specification Compliance
- If the task specified technical requirements, are they met?
  - Orientation: landscape vs portrait vs square as requested
  - Aspect ratio: does it match specifications?
  - Resolution: adequate for the stated purpose (print vs web vs social)?
  - File format: if visible from metadata, does it match requirements?
  - Dimensions: if specific pixel or physical dimensions were requested
- For physical creative work (paintings, crafts, sculptures):
  - Size: does the work appear to match requested dimensions?
  - Medium: correct materials used (watercolor vs acrylic, pen vs pencil)?
  - Surface: correct substrate (canvas, paper, wood, etc.)?

#### F. Style Adherence
- If a specific artistic style was requested, does the output match?
- Style assessment points:
  - Named styles (minimalist, maximalist, photorealistic, abstract, etc.)
  - Reference images: if the task included reference images or mood boards,
    does the output capture the intended aesthetic?
  - Brand guidelines: if the task is for a brand, does it match their
    visual identity?
  - Cultural or period-specific style: if requested, is it accurate?
- Note: creative interpretation within reasonable bounds is acceptable.
  A strict pixel-for-pixel match to a reference is not expected unless
  explicitly requested.

#### G. Creative Authenticity Evidence
- For physical creative work, look for proof of human creation:
  - Work-in-progress photos showing stages of creation
  - Workspace context (art supplies, tools, studio environment)
  - Natural imperfections consistent with hand-made work (slight asymmetry,
    brush texture, pencil pressure variation)
  - The work sitting on or attached to a physical surface in a real environment
- For photography tasks, evidence of being on-location:
  - Context around the subject showing the real environment
  - Natural lighting conditions consistent with the scene
  - Shadows, reflections, and depth of field consistent with real camera optics

#### H. Fraud Indicators Specific to Creative Tasks
- AI-generated images submitted as original photography or hand-made art
- Screenshots of digital art tools (Photoshop, Canva) showing someone else's
  work with minimal modification
- Stock photos with filters applied to disguise their origin
- Previously completed work resubmitted (check temporal metadata)
- Work clearly outside the skill level implied by the worker's portfolio
  (suspiciously professional output from a new worker with no history)
- Physical art that appears to be a print or reproduction rather than an
  original (uniform ink density, halftone dots, perfect color consistency)

**task_checks to populate**:
- `matches_brief` (bool): Creative output addresses the specific requirements in the task brief
- `quality_acceptable` (bool): Technical execution meets a reasonable quality bar for the task
- `appears_original` (bool): Work appears to be original, not AI-generated, stock, or plagiarized
- `subject_correct` (bool): The depicted subject matches what was requested
- `specifications_met` (bool): Format, dimensions, orientation, and other technical specs are satisfied"""
