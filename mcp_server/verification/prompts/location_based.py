"""
PHOTINT Category Prompt: Location-Based

Forensic verification checks for location-specific tasks such as area
surveys, neighborhood checks, route verification, and geographic coverage
assignments.

Unlike physical_presence (which verifies presence at a single point),
location_based tasks may require the worker to cover an area, follow a
route, or document multiple points. The checks emphasize geographic
identifiers, spatial coverage, and sequential consistency.
"""


def get_category_checks(task: dict) -> str:
    title = task.get("title", "Unknown task")
    location = task.get("location", task.get("location_text", "Not specified"))
    instructions = task.get("instructions", task.get("description", ""))

    return f"""### Location-Based Verification (PHOTINT Category: location_based)

**Task context**: "{title}" at/around: {location}
{f"**Task instructions**: {instructions}" if instructions else ""}

Perform the following forensic checks. For each check, note your finding
and rate confidence (CONFIRMED / HIGH / MODERATE / LOW). Absence of
geographic identifiers is a strong negative signal.

#### A. Location Confirmation
1. **Geographic identifiers**: Are street signs, road markers, mile
   markers, building numbers, or named landmarks visible in the photo(s)?
   These are primary indicators. Their absence in an outdoor scene is
   suspicious.
2. **Distinctive features match**: Does the visible environment match the
   expected characteristics of the specified location? Consider
   architecture style, road type, vegetation, terrain, signage language,
   and regional infrastructure (fire hydrant style, traffic light type,
   power line configuration).
3. **GPS metadata vs. visual cues**: If GPS coordinates are available in
   the evidence metadata, do the visual location indicators in the photo
   independently confirm that GPS position? Matching GPS + visual = HIGH
   confidence. GPS present but visual contradicts = RED FLAG.
4. **Regional consistency**: Do all visible elements (language on signs,
   currency on posted prices, vehicle license plates, utility pole style)
   consistently point to the same region/country?

#### B. Area Coverage (for survey/patrol tasks)
5. **Multiple angles or positions**: If the task requires covering an
   area (not just a single point), do the submitted photos show different
   vantage points, angles, or positions within the target area?
6. **Sequential geographic progression**: For route-based tasks, do the
   photos show a logical geographic sequence? Each successive photo
   should be further along the route. Jumping or backtracking without
   explanation is suspicious.
7. **Coverage completeness**: Does the set of photos adequately
   represent the full area or route described in the task? Significant
   gaps in coverage should be noted.
8. **Distinct scenes**: Are the multiple photos genuinely from different
   positions, or are they minor re-framings of the same view? Check
   for parallax differences in foreground/background objects — true
   position changes produce parallax; re-framings do not.

#### C. Environmental Authenticity
9. **Natural environment indicators**: Outdoor scenes should show
   consistent sky conditions, wind direction (flag/banner lean, tree
   sway), and ambient light across all submitted photos.
10. **Time consistency across photos**: If multiple photos are submitted,
    do shadow angles and lighting conditions indicate they were all taken
    within a plausible time window? Drastically different lighting across
    photos claimed to be from the same session is a fraud indicator.
11. **Human and vehicle activity**: Does the level of pedestrian and
    vehicle activity match what you would expect for the location and
    claimed time of day? An empty highway at rush hour or a crowded
    market at 3 AM should raise questions.

#### D. Anti-Fraud Checks
12. **Photo-of-map trick**: Is the worker photographing a map, GPS
    screen, or navigation app instead of the actual location? The
    physical environment must be the primary subject.
13. **Recycled imagery**: Do the photos appear to be taken at different
    times (weather differences, seasonal vegetation changes) despite
    being submitted together? This suggests photos were collected over
    time or obtained from different sources.
14. **Resolution and compression uniformity**: All photos from the same
    device and session should have similar resolution, compression level,
    and color profile. Significant variation suggests mixed sources.

#### E. Required task_checks (include in output JSON)
Your `task_checks` object MUST include these boolean fields:
- `location_confirmed`: Visual evidence confirms the worker was at the specified location
- `geographic_identifiers_visible`: Street signs, landmarks, or other geographic markers are readable
- `area_coverage_adequate`: Photos sufficiently cover the required area or route (or single-point task is documented)
- `gps_consistent`: GPS metadata (if present) is consistent with visible location cues (null if no GPS data)"""
