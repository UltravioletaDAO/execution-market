"""Regression guard for FIX-P2-03: untrusted github.event.* must not be
interpolated directly into run: shell blocks in deploy workflows.

GitHub Actions substitutes ${{ <expr> }} into the run: text BEFORE bash parses
it, so any $(...)/backtick in an attacker-influenceable value (release.tag_name,
release.body, head_commit, pull_request, issue, comment) executes as a command
on the runner. The fix binds such values to the step `env:` map (passed as env
VALUES, never re-tokenized) and references them as quoted shell vars.

On the pre-fix deploy-prod.yml this test FAILS (lines with
`VERSION=${{ github.event.release.tag_name }}` etc. live in run: blocks);
after the fix it PASSES because those values are bound via env:.

Run: pytest tests/ci/test_no_run_block_injection.py
"""
import re
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

WORKFLOWS = [
    ".github/workflows/deploy-prod.yml",
    ".github/workflows/deploy.yml",
]

# Untrusted, attacker-influenceable expression sources.
UNTRUSTED = re.compile(
    r"\$\{\{\s*github\.event\.(release|head_commit|pull_request|issue|comment)\b",
)


def _run_block_lines(text: str):
    """Yield lines that are inside a `run:` block (heuristic: track the
    indentation of the run: key and collect deeper-indented lines).

    `env:` blocks are NOT run: blocks, so env-bound interpolations are
    correctly ignored — that is exactly the safe pattern the fix uses.
    """
    lines = text.splitlines()
    inside = False
    run_indent = 0
    for ln in lines:
        stripped = ln.strip()
        indent = len(ln) - len(ln.lstrip())
        if re.match(r"run:\s*\|", stripped) or stripped == "run: |":
            inside = True
            run_indent = indent
            continue
        if inside:
            if stripped and indent <= run_indent:
                inside = False
            else:
                yield ln


def test_no_untrusted_interpolation_in_run_blocks():
    offenders = []
    for wf in WORKFLOWS:
        p = REPO_ROOT / wf
        text = p.read_text(encoding="utf-8")
        for ln in _run_block_lines(text):
            if UNTRUSTED.search(ln):
                offenders.append(f"{wf}: {ln.strip()}")
    assert not offenders, (
        "Untrusted github.event.* interpolated into run: block — "
        "bind via env: and quote instead:\n" + "\n".join(offenders)
    )


def test_deploy_prod_has_top_level_permissions_block():
    """FIX-P2-03 Change 1: an explicit least-privilege top-level permissions:
    block must shrink the GITHUB_TOKEN blast radius."""
    text = (REPO_ROOT / ".github/workflows/deploy-prod.yml").read_text(
        encoding="utf-8"
    )
    assert re.search(r"(?m)^permissions:\s*$", text), (
        "deploy-prod.yml is missing a top-level `permissions:` block."
    )
    # The block must grant only read on contents (no broad write default).
    block = re.search(r"(?m)^permissions:\n(?:[ \t]+.+\n?)+", text)
    assert block and "contents: read" in block.group(0), (
        "Top-level permissions: must include `contents: read`."
    )


def test_extract_version_revalidates_tag_in_aws_creds_job():
    """FIX-P2-03 Change 3: the AWS-creds Extract version step must re-validate
    the env-bound TAG against strict semver before using it."""
    text = (REPO_ROOT / ".github/workflows/deploy-prod.yml").read_text(
        encoding="utf-8"
    )
    # The Extract version step must bind TAG via env: ...
    assert re.search(r"name:\s*Extract version[\s\S]*?TAG:\s*\$\{\{\s*github\.event\.release\.tag_name", text), (
        "Extract version step must bind the tag via env:"
    )
    # ... and re-validate it against the strict semver regex.
    assert re.search(r'\[\[\s*!\s*"\$TAG"\s*=~\s*\^v\[0-9\]', text), (
        "Extract version step must re-validate $TAG against ^v[0-9]+... semver."
    )
