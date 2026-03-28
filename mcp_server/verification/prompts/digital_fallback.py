"""
PHOTINT Category Prompt: Digital Fallback

Forensic verification checks for digital-only tasks (data processing, API
integration, content generation, code execution, research). These tasks
primarily produce text, JSON, code, or data output and may not have photo
evidence at all. When photos are present, they are typically screenshots
of completed work. This prompt adapts the PHOTINT framework to handle the
absence of physical-world photography.
"""


def get_category_checks(task: dict) -> str:
    """Return category-specific verification instructions for digital tasks.

    These instructions are injected into Layer 5 (Task Completion Assessment)
    of the PHOTINT base prompt. The vision model uses them to evaluate whether
    the submitted evidence (screenshots or text/data output) proves the worker
    completed the requested digital task.

    Args:
        task: Task dict with title, description/instructions, category,
              location, deadline, evidence_schema, etc.

    Returns:
        Multi-line string with forensic verification checks.
    """
    title = task.get("title", "Unknown task")
    instructions = task.get("instructions", task.get("description", ""))
    category = task.get("category", task.get("task_type", "digital"))

    return f"""### Digital Task Verification (PHOTINT Category: {category} / digital_fallback)

**Task context**: "{title}"
{f"**Task instructions**: {instructions}" if instructions else ""}

**Important note**: Digital tasks (data processing, API integration, content
generation, code execution, research) primarily produce text, JSON, code, or
data output. Photo evidence may not be applicable. If no photos are submitted,
this does NOT automatically indicate fraud -- evaluate the text/data response
instead. If screenshots are submitted, verify their authenticity.

Perform the following forensic checks. For each check, note your finding
and rate confidence (CONFIRMED / HIGH / MODERATE / LOW). Flag absence of
expected evidence as a negative indicator ONLY when photos are expected.

#### A. Screenshot Authenticity (if photos are present)
1. **Native UI elements**: Does the screenshot show native application UI
   elements (window chrome, toolbar, status bar, scroll bars) consistent
   with the application or platform the task involves?
2. **Correct application**: Is the screenshot from the correct application,
   website, or tool specified by the task? Check browser URL bars, window
   titles, application headers, or platform branding.
3. **No obvious editing**: Are there signs of image manipulation in the
   screenshot? Look for inconsistent fonts, misaligned elements, color
   differences between regions, or cut-paste artifacts overlaid on the UI.
4. **Resolution consistency**: Is the screenshot resolution consistent
   throughout? Pasted elements often differ in pixel density or scaling
   from the surrounding native UI.
5. **Timestamp in screenshot**: If the application displays timestamps
   (browser tabs, terminal output, file modification dates), do they
   fall within the task window?

#### B. Output Relevance and Completeness
6. **Output matches request**: Does the submitted output (text, code, data,
   or screenshot content) directly address what the task requested? An
   output on an unrelated topic or for a different task is a clear
   rejection indicator.
7. **All requirements met**: Does the output cover every requirement
   listed in the task instructions? Check for missing sections, partial
   answers, or requirements that were silently skipped.
8. **Completeness**: Is the output complete, or does it appear truncated,
   placeholder-filled, or otherwise unfinished? Look for "TODO", "...",
   placeholder text, or abrupt endings.
9. **Correct format**: If the task specifies an output format (JSON, CSV,
   specific file type, structured report), does the submission conform?

#### C. Quality Assessment
10. **Accuracy**: For factual or data tasks, does the output appear
    accurate based on what can be verified from the screenshot or
    submission? Obvious errors, fabricated data, or nonsensical results
    should be flagged.
11. **Quality level**: Does the output meet the quality standard implied
    or specified by the task? A request for "detailed analysis" answered
    with a single sentence, or "production-ready code" that contains
    syntax errors, falls below expectations.
12. **Originality**: Does the output appear to be original work rather
    than copied from a generic source? For research tasks, look for
    task-specific details rather than boilerplate text.

#### D. No-Photo Evaluation
13. **Photo not applicable**: If no photos were submitted AND the task
    is purely digital (no physical component), mark screenshot checks
    as not applicable rather than negative. The text/data response is
    the primary evidence.
14. **Text response evaluation**: If only a text/data response was
    submitted, evaluate it against the task requirements for relevance,
    completeness, accuracy, and quality. A well-structured, thorough
    text response can be sufficient evidence for digital tasks.

#### E. Fraud Indicators (digital-specific)
15. **Generic or templated output**: Does the output look like a generic
    template that was not customized for the specific task? Pre-made
    responses reused across tasks are a fraud pattern.
16. **Impossible timing**: If the task is complex (e.g., "analyze 50 data
    points") but was completed in implausibly short time (seconds), flag
    as suspicious.
17. **Copy-paste from unrelated source**: Does the output contain
    references, variable names, or context from a clearly different
    project or task?

#### F. Required task_checks (include in output JSON)
Your `task_checks` object MUST include these boolean fields:
- `output_relevant`: The submitted output directly addresses the task requirements
- `screenshot_authentic`: Screenshots show native UI and no manipulation (set to true if no screenshots submitted -- not applicable is not a failure)
- `task_requirements_met`: All specific requirements from the task instructions are addressed
- `output_complete`: The output is complete with no truncation, placeholders, or missing sections
- `quality_acceptable`: The output meets the quality standard expected by the task"""
