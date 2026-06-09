#!/usr/bin/env bash
# FIX-P2-01 — IAM policy-simulator verification of the em-cicd-terraform policy.
#
# Proves, against the real AWS IAM evaluation engine, that the committed policy
# JSON denies GetSecretValue on the fund/auth secrets while keeping the
# Terraform-managed version secrets readable and the management verbs intact.
#
# This is the live counterpart to the offline structural test
# (test_em_cicd_terraform_secret_scope.py). It requires AWS creds with
# iam:SimulateCustomPolicy. It NEVER reads or prints any secret value — it only
# asks IAM "would this action be allowed?".
#
#   Pre-fix policy  -> em/x402 GetSecretValue == allowed  (bug)
#   Post-fix policy -> em/x402 GetSecretValue == explicitDeny (fixed)
set -euo pipefail

POLICY="$(cd "$(dirname "$0")/.." && pwd)/em-cicd-terraform-policy.json"
ACCT=518898403364

arn() { echo "arn:aws:secretsmanager:us-east-2:${ACCT}:secret:${1}-AbCd12"; }

sim() { # $1=action $2=resource-arn -> EvalDecision
  aws iam simulate-custom-policy \
    --policy-input-list "$(jq -c . "$POLICY")" \
    --action-names "$1" --resource-arns "$2" \
    --query 'EvaluationResults[0].EvalDecision' --output text
}

fail=0

# MUST be denied (the fund/auth secrets).
for s in em/x402 em/supabase em/admin-key em/worldid em/ens em/commission; do
  d=$(sim secretsmanager:GetSecretValue "$(arn "$s")")
  if [ "$d" = "explicitDeny" ] || [ "$d" = "implicitDeny" ]; then
    echo "PASS  deny   $s ($d)"
  else
    echo "FAIL  $s readable ($d)"; fail=1
  fi
done

# MUST remain allowed (Terraform-managed versions).
for s in em/sentry-dsn em/veryai em/evidence-jwt-secret em/xmtp em/meshrelay; do
  d=$(sim secretsmanager:GetSecretValue "$(arn "$s")")
  if [ "$d" = "allowed" ]; then
    echo "PASS  read   $s ($d)"
  else
    echo "FAIL  $s not readable by TF ($d)"; fail=1
  fi
done

# Management verbs MUST stay allowed on the namespace.
for a in CreateSecret PutSecretValue DeleteSecret TagResource DescribeSecret; do
  d=$(sim "secretsmanager:$a" "$(arn em/x402)")
  if [ "$d" = "allowed" ]; then
    echo "PASS  mgmt   $a ($d)"
  else
    echo "FAIL  mgmt $a => $d"; fail=1
  fi
done

if [ "$fail" -ne 0 ]; then echo "RESULT: FAIL"; exit 1; fi
echo "RESULT: PASS"
