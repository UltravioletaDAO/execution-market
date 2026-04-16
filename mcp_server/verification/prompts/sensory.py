"""
PHOTINT Category Prompt: Sensory

Forensic verification checks for sensory tasks (taste testing, smell
verification, sound assessment, environmental sensing). Since sensory
experiences cannot be directly photographed, checks focus on the source
identification, environmental context, and evidence of genuine interaction.
"""


def get_category_checks(task: dict) -> str:
    title = task.get("title", "Unknown task")
    location = task.get("location", task.get("location_text", "Not specified"))
    instructions = task.get("instructions", task.get("description", ""))

    return f"""### Sensory Task Verification (PHOTINT Category: sensory)

**Task context**: "{title}" at location: {location}
{f"**Task instructions**: {instructions}" if instructions else ""}

**Important note**: Sensory experiences (taste, smell, sound, texture) cannot
be directly captured in a photograph. Verification therefore focuses on
confirming the sensory source, the environment, and evidence that the worker
genuinely interacted with the item or setting. A written or structured
response describing the sensory experience is expected to accompany the photo.

Perform the following forensic checks. For each check, note your finding
and rate confidence (CONFIRMED / HIGH / MODERATE / LOW). Flag absence of
expected evidence as a negative indicator.

#### A. Sensory Source Identification
1. **Source visible and identifiable**: Is the sensory source (food item,
   beverage, product, environment) clearly visible and identifiable in the
   photo? The item under evaluation must be unambiguous.
2. **Product identification**: Can the brand, label, or packaging be read?
   Does the visible product match the specific item the task requires the
   worker to evaluate?
3. **Correct product variant**: If the task specifies a particular flavor,
   scent, variety, or version, does the visible label or packaging confirm
   the correct variant?

#### B. Environmental Context
4. **Correct environment**: Is the worker in the appropriate environment
   for the sensory task? A taste test should be in a food-service setting
   or at home, a noise assessment at the specified location, etc.
5. **Ambient conditions**: Are ambient conditions appropriate for an
   accurate sensory evaluation? Extreme temperatures, strong competing
   odors (visible smoke, chemical containers nearby), or heavy background
   noise sources can compromise sensory accuracy and should be noted.

#### C. Evidence of Interaction
6. **Item opened or handled**: Does the photo show the product has been
   opened, unwrapped, poured, tasted, or otherwise interacted with? A
   sealed, untouched package sitting on a shelf does not prove a sensory
   evaluation occurred.
7. **Consumption evidence**: For taste tasks, is there evidence of
   consumption — partially eaten food, liquid level reduced, utensils
   used, food plated or portioned?
8. **Testing setup**: Is any required testing setup visible? For example,
   multiple samples lined up for comparison, a clean palate (water glass),
   or sensory evaluation forms.

#### D. Written / Structured Response
9. **Textual description present**: Does the submission include a written
   description of the sensory experience? Since photos cannot capture
   taste, smell, or sound, the textual component is essential evidence.
10. **Description specificity**: If a textual response is provided, does
    it contain specific sensory descriptors (e.g., "bitter aftertaste",
    "metallic odor", "high-pitched hum at ~4 kHz") rather than vague
    generalizations?
11. **Response matches product**: Do the sensory observations in the text
    plausibly match the product or environment shown in the photo?

#### E. Authenticity & Staging
12. **Not stock photography**: Does the photo appear to be a genuine
    first-person capture rather than a stock image of the product? Check
    for watermarks, overly polished composition, or generic backgrounds.
13. **Consistent setting**: Is the setting consistent across all submitted
    photos? Different backgrounds or lighting across photos that should
    be from the same session suggest staged or recycled evidence.

#### F. Required task_checks (include in output JSON)
Your `task_checks` object MUST include these boolean fields:
- `source_identified`: The sensory source (product, item, environment) is clearly visible and identifiable
- `environment_appropriate`: The worker is in the correct and suitable environment for the evaluation
- `interaction_evident`: The item was opened, tasted, handled, or otherwise interacted with (not just photographed in packaging)
- `product_matches`: The visible product matches the specific item the task requires
- `testing_conditions_met`: Conditions are appropriate for an accurate sensory evaluation (no competing stimuli, proper setup)"""
