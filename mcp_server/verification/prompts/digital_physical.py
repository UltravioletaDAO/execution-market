"""
PHOTINT Category Prompt: Digital-Physical

Forensic verification checks for hybrid tasks that bridge the digital and
physical worlds -- print and deliver a document, configure an IoT device,
set up equipment, install software on a physical machine, etc.

The worker must demonstrate that both the digital component (screen
display, printout, configuration) and the physical component (device in
place, printout delivered, equipment installed) are present and connected.
"""


def get_category_checks(task: dict) -> str:
    """Return category-specific verification instructions for digital-physical tasks.

    These instructions are injected into Layer 5 (Task Completion Assessment)
    of the PHOTINT base prompt. The vision model uses them to evaluate whether
    the submitted photo evidence proves the worker completed both the digital
    and physical aspects of the task.

    Args:
        task: Task dict with title, description/instructions, category,
              location, deadline, evidence_schema, etc.

    Returns:
        Multi-line string with forensic verification checks.
    """
    title = task.get("title", "Unknown task")
    location = task.get("location", task.get("location_text", "Not specified"))
    instructions = task.get("instructions", task.get("description", ""))

    return f"""### Digital-Physical Verification (PHOTINT Category: digital_physical)

**Task context**: "{title}" at location: {location}
{f"**Task instructions**: {instructions}" if instructions else ""}

Perform the following forensic checks. For each check, note your finding
and rate confidence (CONFIRMED / HIGH / MODERATE / LOW). Flag absence of
expected evidence as a negative indicator.

#### A. Digital Component Verification
1. **Digital output visible**: Is the digital component of the task
   visible in the evidence? This could be a screen display, printout,
   configuration interface, terminal output, or software UI.
2. **Screenshot authenticity**: If a screenshot is submitted as evidence,
   does it show a native device UI? Look for the correct operating
   system chrome, status bar, app frames, and screen resolution. Edited
   or mocked-up UIs are a fraud indicator.
3. **Configuration verification**: If the task required configuring
   settings (WiFi credentials, device parameters, software options),
   are the configured values visible and matching the requirements?
4. **Correct device or application**: Is the digital evidence from the
   correct device type, software version, or platform specified in the
   task instructions?
5. **No editing artifacts on digital evidence**: Check for inconsistent
   fonts, misaligned UI elements, Photoshop-style layer edges, or
   color mismatches that suggest the digital screenshot was fabricated.

#### B. Physical Component Verification
6. **Physical object in place**: Is the physical component verified?
   This could be a device installed at a location, a printout delivered,
   equipment set up and operational, or hardware physically connected.
7. **Installation completeness**: Is the physical setup fully complete,
   not partially assembled? Look for loose cables, missing parts,
   protective film still attached, or setup screens still showing on
   devices that should be past initial configuration.
8. **Physical environment**: Does the environment where the physical
   component is placed match the task requirements (correct room, wall
   mount, desk position, outdoor location)?
9. **Condition and quality**: Is the physical deliverable in good
   condition? For printouts: legible text, correct orientation, no
   smudges. For devices: powered on, operational indicators visible.

#### C. Digital-Physical Connection
10. **Bridge between components**: Is there a clear, verifiable
    connection between the digital and physical evidence? For example:
    - Printed document content matches the digital file
    - Device screen shows the same WiFi SSID as the router label
    - Configuration UI shows the same parameters as the physical setup
    - Software output references the hardware it is running on
11. **Same environment**: Do the digital and physical components appear
    to be in the same location and time? Mismatched backgrounds,
    lighting, or timestamps between digital and physical photos suggest
    evidence assembled from different sessions.
12. **Functional verification**: Is there evidence that the integrated
    system works, not just that components are present? An IoT device
    showing a dashboard with live data is stronger than a powered-off
    device next to a laptop.

#### D. Before/After Comparison
13. **Before state documented**: If the task involves transformation
    (installation, setup, repair), is there evidence of the initial
    state for comparison?
14. **After state demonstrates completion**: Does the after-state photo
    clearly show the task is finished, not merely in progress? Partial
    progress (50% installed, configuration wizard still running) is
    not completion.
15. **Progress is authentic**: If before/after photos are provided, are
    they from the same location? Check consistent background elements,
    furniture, wall markings, or lighting to confirm both photos depict
    the same scene.

#### E. Staging & Fraud Detection
16. **Simulated configuration**: Could the worker have opened a settings
    page, taken a screenshot, then not actually applied the changes?
    Look for "Apply" or "Save" buttons that are still active vs.
    confirmation messages that changes were applied.
17. **Stock device photos**: Generic product photos from manufacturer
    websites are not evidence of physical setup. Look for
    environmental context (desk, cables, other objects) that proves
    the photo was taken in a real setting.
18. **Mismatched serial numbers**: If device serial numbers or model
    numbers are visible in both digital and physical evidence, they
    must match.

#### F. Required task_checks (include in output JSON)
Your `task_checks` object MUST include these boolean fields:
- `digital_component_verified`: Digital output (screen, printout, config) is visible and authentic
- `physical_component_verified`: Physical element (device, printout, equipment) is in place
- `connection_clear`: Digital and physical components are demonstrably linked
- `setup_complete`: Installation or setup is fully finished, not partially done
- `configuration_correct`: Settings and parameters match the task requirements"""
