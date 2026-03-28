"""
PHOTINT Category Prompt: Data Collection

Forensic verification checks for data gathering tasks (surveys, measurements,
counting, data recording). The worker must demonstrate that they collected
accurate, complete, and correctly sourced data at the right location or setting.
"""


def get_category_checks(task: dict) -> str:
    """Return category-specific verification instructions for data collection tasks.

    These instructions are injected into Layer 5 (Task Completion Assessment)
    of the PHOTINT base prompt. The vision model uses them to evaluate whether
    the submitted photo evidence proves the worker gathered the requested data
    accurately and completely.

    Args:
        task: Task dict with title, description/instructions, category,
              location, deadline, evidence_schema, etc.

    Returns:
        Multi-line string with forensic verification checks.
    """
    title = task.get("title", "Unknown task")
    location = task.get("location", task.get("location_text", "Not specified"))
    instructions = task.get("instructions", task.get("description", ""))

    return f"""### Data Collection Verification (PHOTINT Category: data_collection)

**Task context**: "{title}" at location: {location}
{f"**Task instructions**: {instructions}" if instructions else ""}

Perform the following forensic checks. For each check, note your finding
and rate confidence (CONFIRMED / HIGH / MODERATE / LOW). Flag absence of
expected evidence as a negative indicator.

#### A. Data Readability
1. **Data visibility**: Is the data being collected clearly visible and
   readable in the photo? Text, numbers, labels, and other data points
   must be legible without guesswork.
2. **Focus and resolution**: Is the photo sharp enough to read all relevant
   data values? Blurred text, unreadable gauges, or pixelated numbers are
   negative indicators.
3. **Contrast and lighting**: Is the data well-lit with sufficient contrast?
   Glare, shadows, or reflections obscuring data points should be flagged.

#### B. Measurement Accuracy
4. **Measuring tools visible**: If the task involves measurement, is the
   measuring instrument clearly visible in the photo (ruler, tape measure,
   scale, thermometer, gauge)?
5. **Scale readability**: Can the measurement scale be read accurately?
   Are the scale markings, units, and the measurement reading all visible
   in a single frame?
6. **Units clear**: Are the units of measurement identifiable? Ambiguous
   units (e.g., cm vs. inches) should be flagged if the task specifies
   particular units.
7. **Calibration and reference**: Are known-size reference objects present
   in the photo for scale verification? For spatial measurements, a
   familiar-size object (coin, pen, hand) provides independent scale
   confirmation.

#### C. Survey and Data Completeness
8. **All data points captured**: Does the evidence cover every data point
   the task requested? Count the number of entries, fields, or items
   against the task requirements. Missing fields are a negative indicator.
9. **Systematic approach**: Was the data collected in an organized manner?
   Look for logical ordering, sequential numbering, or structured layout
   that indicates methodical collection rather than haphazard sampling.
10. **No obvious gaps**: Are there visible gaps in the data set? Skipped
    rows, empty fields, or discontinuities in sequential data suggest
    incomplete collection.

#### D. Counting and Enumeration
11. **Items countable**: For counting tasks, are all items clearly visible
    and individually distinguishable? Overlapping, obscured, or out-of-frame
    items prevent accurate verification.
12. **Nothing obscured**: Is the full area of interest visible? Objects
    hidden behind other objects, cut off by the frame edge, or lost in
    shadow cannot be counted and should be flagged.
13. **Count consistency**: If the worker reported a count, does the visible
    evidence support that number? A clear discrepancy between the reported
    count and the visible items is a strong negative indicator.

#### E. Environmental Context
14. **Correct location/setting**: Was the data collected at the location or
    in the setting specified by the task? Look for environmental cues
    (signage, infrastructure, indoor/outdoor) that confirm the collection
    site.
15. **Appropriate conditions**: Were the environmental conditions suitable
    for accurate data collection? For example, outdoor measurements during
    a storm, or readings taken in incorrect lighting, may compromise
    data quality.

#### F. Required task_checks (include in output JSON)
Your `task_checks` object MUST include these boolean fields:
- `data_readable`: All collected data is clearly visible and legible
- `measurements_clear`: Measuring tools and readings are identifiable (true if no measurements required)
- `collection_complete`: All requested data points are present with no obvious gaps
- `correct_location`: Data was collected at the specified location or setting
- `systematic_approach`: Data was gathered in an organized, methodical manner"""
