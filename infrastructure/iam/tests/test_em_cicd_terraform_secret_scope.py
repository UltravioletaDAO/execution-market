"""Regression guard for FIX-P2-01 — CI/Terraform deploy credential over-scope.

The `em-cicd-terraform` IAM policy must NOT grant `secretsmanager:*` (which
includes `GetSecretValue`) on the whole `em/*` namespace. It must instead:

  1. grant only management verbs on `em/*`,
  2. grant `GetSecretValue` only on the 6 Terraform-managed secret versions,
  3. carry an explicit Deny backstop on the fund/auth secrets
     (em/x402 platform wallet key, em/supabase, em/admin-key, em/worldid,
     em/ens, em/commission, ...).

These are pure structural assertions on the committed JSON — they need no AWS
access, so they run in CI. A companion IAM policy-simulator check
(test_em_cicd_terraform_secret_scope.sh) proves the same thing against the live
IAM evaluation engine when AWS creds are available.

Run: pytest infrastructure/iam/tests/test_em_cicd_terraform_secret_scope.py
"""
import json
import pathlib

POLICY_PATH = (
    pathlib.Path(__file__).resolve().parents[1] / "em-cicd-terraform-policy.json"
)

# Fund- and auth-controlling secrets the deploy credential must NEVER read.
FUND_AUTH_SECRETS = [
    "em/x402",       # platform/settlement wallet PRIVATE_KEY
    "em/supabase",   # service-role / RLS bypass
    "em/admin-key",  # X-Admin-Key
    "em/worldid",    # World ID RP signing key
    "em/ens",        # ENS owner key
    "em/commission",
]

# The ONLY em/* secrets Terraform reads back (aws_secretsmanager_secret_version).
TF_MANAGED_VERSION_SECRETS = [
    "em/sentry-dsn",
    "em/veryai",
    "em/evidence-jwt-secret",
    "em/payshell/facilitator",
    "em/xmtp",
    "em/meshrelay",
]


def _load_policy():
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def _as_list(value):
    return value if isinstance(value, list) else [value]


def test_policy_is_valid_json_with_statements():
    policy = _load_policy()
    assert policy["Version"] == "2012-10-17"
    assert isinstance(policy["Statement"], list) and policy["Statement"]


def test_no_secretsmanager_wildcard_anywhere():
    """Reproduces the bug: the old policy granted `secretsmanager:*` on em/*.

    On the pre-fix file this assertion FAILS; after the fix it PASSES. This is
    the primary regression guard against a future wildcard re-introduction.
    """
    policy = _load_policy()
    offenders = []
    for stmt in policy["Statement"]:
        actions = _as_list(stmt.get("Action", []))
        if "secretsmanager:*" in actions:
            offenders.append(stmt.get("Sid", "<no-sid>"))
    assert not offenders, (
        "secretsmanager:* (which includes GetSecretValue) must not be granted on "
        f"the em/* namespace. Offending statements: {offenders}"
    )


def test_explicit_deny_covers_fund_and_auth_secrets():
    """An explicit Deny on GetSecretValue must backstop the fund/auth secrets."""
    policy = _load_policy()
    deny_stmts = [
        s
        for s in policy["Statement"]
        if s.get("Effect") == "Deny"
        and "secretsmanager:GetSecretValue" in _as_list(s.get("Action", []))
    ]
    assert deny_stmts, "Missing explicit Deny on secretsmanager:GetSecretValue."

    denied_resources = set()
    for s in deny_stmts:
        denied_resources.update(_as_list(s.get("Resource", [])))

    for secret in FUND_AUTH_SECRETS:
        wanted = (
            f"arn:aws:secretsmanager:us-east-2:518898403364:secret:{secret}-*"
        )
        assert wanted in denied_resources, (
            f"{secret} is not in the Deny backstop (expected resource {wanted})."
        )


def test_get_secret_value_allow_is_scoped_to_managed_versions_only():
    """GetSecretValue Allow must list ONLY the 6 Terraform-managed versions —
    no broad em/* read, and none of the fund/auth secrets."""
    policy = _load_policy()
    allow_get_resources = set()
    for s in policy["Statement"]:
        if s.get("Effect") != "Allow":
            continue
        if "secretsmanager:GetSecretValue" in _as_list(s.get("Action", [])):
            allow_get_resources.update(_as_list(s.get("Resource", [])))

    # No broad namespace read.
    assert (
        "arn:aws:secretsmanager:us-east-2:518898403364:secret:em/*"
        not in allow_get_resources
    ), "GetSecretValue must not be allowed on the whole em/* namespace."

    # Exactly the managed versions are allowed.
    expected = {
        f"arn:aws:secretsmanager:us-east-2:518898403364:secret:{s}-*"
        for s in TF_MANAGED_VERSION_SECRETS
    }
    assert allow_get_resources == expected, (
        "GetSecretValue Allow list must equal the 6 Terraform-managed version "
        f"secrets. Got: {sorted(allow_get_resources)}"
    )

    # No fund/auth secret leaked into the Allow list.
    for secret in FUND_AUTH_SECRETS:
        bad = f"arn:aws:secretsmanager:us-east-2:518898403364:secret:{secret}-*"
        assert bad not in allow_get_resources, (
            f"{secret} must never appear in a GetSecretValue Allow."
        )


def test_management_verbs_still_granted_on_namespace():
    """Terraform must keep create/update/delete/tag on em/* so it can manage
    secret containers and versions."""
    policy = _load_policy()
    mgmt_stmt = next(
        (
            s
            for s in policy["Statement"]
            if s.get("Sid") == "TerraformSecretsManage" and s.get("Effect") == "Allow"
        ),
        None,
    )
    assert mgmt_stmt is not None, "Missing TerraformSecretsManage statement."
    actions = set(_as_list(mgmt_stmt["Action"]))
    for required in (
        "secretsmanager:CreateSecret",
        "secretsmanager:PutSecretValue",
        "secretsmanager:DeleteSecret",
        "secretsmanager:DescribeSecret",
        "secretsmanager:TagResource",
    ):
        assert required in actions, f"Management verb {required} missing."
    # Crucially, GetSecretValue is NOT a management verb here.
    assert "secretsmanager:GetSecretValue" not in actions
    assert "secretsmanager:*" not in actions


def test_scoped_resources_use_arn_suffix_wildcard():
    """Every scoped/denied secret ARN must use the `-*` random-suffix form,
    otherwise it matches nothing in real IAM evaluation."""
    policy = _load_policy()
    for s in policy["Statement"]:
        actions = _as_list(s.get("Action", []))
        if "secretsmanager:GetSecretValue" not in actions:
            continue
        for res in _as_list(s.get("Resource", [])):
            # The namespace-wide read (em/*) is explicitly forbidden elsewhere;
            # any other per-secret ARN must end with the random-suffix wildcard.
            assert res.endswith("-*") or res.endswith("/*"), (
                f"Scoped secret ARN '{res}' must use the '-*' suffix form so it "
                "matches the random 6-char suffix AWS appends to secret ARNs."
            )
