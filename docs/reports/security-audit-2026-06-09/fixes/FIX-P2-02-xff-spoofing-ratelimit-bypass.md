---
date: 2026-06-09
tags: [type/incident, domain/security]
status: active
severity: P2
finding_id: FIX-P2-02
---
# FIX-P2-02 — X-Forwarded-For leftmost-hop trust defeats per-IP rate limiting + IP auto-ban (and lets an attacker ban arbitrary victim IPs)

## Summary (2-3 sentences)
`utils.net.get_client_ip()` correctly gates `X-Forwarded-For` (XFF) trust on the TCP peer being a trusted proxy, but then takes the **left-most** XFF hop (`xff.split(",")[0]`) as the client IP. Behind the production AWS ALB (default "append" mode), the real client IP is the **right-most** appended entry, so the left-most value is fully attacker-controlled. Every per-IP control (app rate limiter, A2A limiter, progressive IP auto-ban, ERC-8128 nonce limiter, MoonPay velocity cap) keys on this spoofable value — letting an attacker rotate buckets to bypass limits, and poison the in-memory ban list against arbitrary victim IPs. The fix is to derive the client IP from the **right side** of XFF (the right-most entry not in `TRUSTED_PROXY_CIDRS`).

## Severity & Impact (why P2; what funds/data are at risk)
**Severity: P2 (abuse-control / availability hardening gap). No fund loss, no auth/privilege bypass.**

The controls defeated by this bug are all *defense-in-depth* layers sitting on top of two controls that are NOT bypassed:
- **AWS WAF rate rule** (`infrastructure/terraform/waf-cloudfront.tf`), keyed on `aggregate_key_type = "IP"` (the un-spoofable TCP source, no `forwarded_ip_config`) and associated to `aws_lb.main`. This survives and also throttles the ban-poisoning vector at the attacker's real source IP.
- **Cryptographic ERC-8128 wallet auth** — not affected by IP.

Concrete impact:
1. **IP auto-ban subsystem fully defeated** (`security/ip_ban.py`, added after the 2026-04 Tor-exit flood, `ip_ban.py:1-9`). Each request can carry a fresh spoofed hop-0, so 429/401 strikes never accumulate in one bucket and a banned bucket is never re-hit.
2. **App per-IP rate limit + A2A limiter (15/300s) + ERC-8128 nonce limiter (5/60s) bypassed** by rotating hop-0; capped only by WAF's coarse per-real-IP cap.
3. **Ban-poisoning of arbitrary third-party IPs** (the only genuinely novel harm): spoof `XFF: <victim>`, trip the 20×401 (`UNAUTH_THRESHOLD`) or 10×429 (`BAN_THRESHOLD`) threshold, and `<victim>` is added to the in-memory ban list. When the real victim later connects with no XFF, the ALB sets `XFF=<victim>`, `is_banned()` returns 403, and progressive escalation (`2h → 24h → 7d`, `ip_ban.py:38-46`) can push repeated poisoning to a 7-day ban. Mitigating factors that keep this at P2: bans are **in-memory per ECS task** (`ip_ban.py:31-35` module-level dicts), reset on restart/deploy, and the attacker's poisoning requests are themselves WAF-rate-limited on their real source IP.
4. **MoonPay per-IP onramp velocity cap bypassed** — `moonpay._resolve_device_ip` (`moonpay.py:173-185`) is strictly worse: it honors `xff.split(",")[0]` with **no trusted-proxy gate at all**. (It feeds MoonPay's risk engine, not an EM control, but is still spoofable.)

No customer funds or escrow are at risk through this finding directly. It is an availability/abuse-control hardening gap — hence P2, not P1.

## Affected code (exact file:line references, with short redacted quotes)

- **`mcp_server/utils/net.py:134-147`** — the root defect. Once the peer is trusted, it returns the **left-most** hop:
  ```python
  # XFF is a comma-separated chain "client, proxy1, proxy2". The left-most
  # entry is the original client.
  hop0 = xff.split(",")[0].strip()
  ...
  return hop0
  ```
  This comment/assumption is wrong for an *appending* proxy (AWS ALB): the ALB appends the real source to the **right**, so a client-supplied `XFF: 9.9.9.9` arrives at the backend as `9.9.9.9, <real_client>` and `split(",")[0]` returns the attacker-chosen `9.9.9.9`.

- **`mcp_server/api/middleware.py:158`** — `client_ip = _get_client_ip(request)` feeds the ban check (`:166 is_banned`), the A2A early-reject 401 strike (`:198 record_unauthorized`), the A2A limiter (`:216 _check_a2a_limit`), and the app limiter (`:254 check_all_limits`).

- **`mcp_server/api/middleware.py:720-732`** — `_get_client_ip()` is a thin wrapper that delegates to `utils.net.get_client_ip` (`_trusted_get_client_ip`). Fixing `net.py` fixes this callsite automatically.

- **`mcp_server/api/auth.py:751-768`** — `_get_nonce_client_ip()` also delegates to `utils.net.get_client_ip`. Fixed automatically by the `net.py` change.

- **`mcp_server/api/routers/moonpay.py:182-185`** — `_resolve_device_ip()` has its **own** spoofable XFF parse with no trusted-proxy gate:
  ```python
  xff = request.headers.get("x-forwarded-for")
  if xff:
      return xff.split(",")[0].strip()
  ```
  Must be changed to delegate to the hardened `get_client_ip`.

- **`mcp_server/api/routers/moonpay.py:385`** — `request_ip = get_client_ip(request)` (the velocity-cap path) is *already* on the central helper; fixed automatically by the `net.py` change.

- **`mcp_server/security/ip_ban.py:49-124`** — `is_banned` / `record_429` / `record_unauthorized` all key on the spoofable IP string. No change to this file is needed (its keys become trustworthy once `net.py` is fixed), but see the *defense-in-depth* note in The Fix.

- **`mcp_server/tests/test_client_ip.py:88-94`** — `test_xff_hop0_used_when_multiple_entries` **codifies the vulnerable behavior** (asserts the left-most `198.51.100.1`). This test MUST be updated, or it will re-assert the bug.

- **`infrastructure/terraform/alb.tf:159-184`** — `aws_lb.main` has **no `xff_header_processing` override** anywhere in `*.tf` (grep is empty), so the ALB runs in default **append** mode. `variables.tf:22-25` sets `vpc_cidr = "10.0.0.0/16"`, which is inside the default trusted CIDR `10.0.0.0/8` (`net.py:51`) — so the ALB's VPC-private peer IP is always trusted and XFF is always honored.

## Root cause (the real underlying defect)
The trusted-proxy boundary check is correct, but the **hop selection is backwards for an appending proxy**. AWS ALB (and the equivalent CloudFront-in-front-of-origin topology) *appends* the real TCP source to the right of any client-supplied `X-Forwarded-For`. The code assumes the proxy *prepends* / that the left-most hop is the original client. Therefore the value the code trusts is the one segment of the chain that the client fully controls. There is no AWS ALB attribute that strips a client-PREPENDED XFF (`xff_header_processing` only supports `append` / `preserve` / `remove`), so this can only be fixed in code.

## Exploit scenario (concrete attacker steps)
Topology: `attacker → AWS ALB (append mode) → ECS (FastAPI)`. The ALB peer (VPC-private 10.0.x.x) is always trusted.

**A. Rate-limit / ban bypass (rotate buckets):**
1. Attacker sends each request with a fresh spoofed header, e.g. `X-Forwarded-For: 7.7.7.<n>` (incrementing `n`).
2. At the backend the header becomes `7.7.7.<n>, <attacker_real_ip>`. `get_client_ip()` returns `7.7.7.<n>`.
3. Every per-IP limiter and the ban tracker key on the rotating `7.7.7.<n>`, so strikes never accumulate and limits never trip. The attacker enjoys effectively unlimited app-layer requests, throttled only by the coarse WAF per-real-IP cap.

**B. Ban-poisoning of a victim IP (`203.0.113.50`):**
1. Attacker repeatedly hits `/a2a/v1` with no auth headers and `X-Forwarded-For: 203.0.113.50`.
2. Each request is an unauthenticated A2A call → `record_unauthorized("203.0.113.50")` (`middleware.py:198`).
3. After 20 such requests within 5 min (`UNAUTH_THRESHOLD`), `203.0.113.50` is added to `_bans` (`ip_ban.py:113-114`). Repeating across deploys/tasks and across the 429 path escalates to 24h then 7d.
4. The real victim at `203.0.113.50` connects (no XFF). The ALB appends → backend sees `XFF: 203.0.113.50` → `is_banned("203.0.113.50")` is True → **403 for the legitimate victim** on that ECS task.

## The Fix (PRECISE, code-level)

### 1. `mcp_server/utils/net.py` — select the right-most non-trusted hop (PRIMARY FIX)

Replace the left-most hop selection (lines 134-147) with a right-to-left walk that returns the first XFF entry **not** in `TRUSTED_PROXY_CIDRS` (i.e. the address the ALB appended = the real TCP source as the ALB saw it). This generalizes cleanly to a future CloudFront-in-front topology: add CloudFront's published ranges to `TRUSTED_PROXY_CIDRS` and the walk will skip them.

Replace this block:

```python
    # XFF is a comma-separated chain "client, proxy1, proxy2". The left-most
    # entry is the original client.
    hop0 = xff.split(",")[0].strip()
    if not hop0:
        return client_host

    # Guard against malformed entries (non-IP strings) — return the peer
    # rather than echoing junk back into rate limiter keys.
    try:
        ipaddress.ip_address(hop0)
    except ValueError:
        return client_host

    return hop0
```

with:

```python
    # XFF is a comma-separated chain. With an APPENDING proxy (AWS ALB in
    # default mode, and CloudFront-to-origin), the proxy appends the real TCP
    # source to the RIGHT of any client-supplied value. The left-most entries
    # are therefore attacker-controlled. Walk right-to-left and return the
    # first entry that is NOT itself a trusted proxy — that is the real client
    # as seen by the edge proxy. Everything to its left is client-supplied and
    # must be ignored. (FIX-P2-02)
    hops = [h.strip() for h in xff.split(",") if h.strip()]
    for hop in reversed(hops):
        try:
            ipaddress.ip_address(hop)
        except ValueError:
            # Malformed entry — skip it, keep walking left.
            continue
        if not _is_trusted_proxy(hop):
            return hop
    # All hops were trusted proxies or malformed — fall back to the peer.
    return client_host
```

Also update the rule docstring (lines 108-110) so it does not re-document the wrong behavior:

```python
    3. If the TCP peer IS a trusted proxy, return the right-most
       ``X-Forwarded-For`` entry that is not itself a trusted proxy (the real
       client as seen by the edge proxy, which appends to the right). Malformed
       or all-trusted XFF falls back to the TCP peer.
```

**Behavior preserved:** the untrusted-peer path (lines 121-126) is unchanged; malformed/empty XFF still falls back to the peer; missing client still returns `"unknown"`.

### 2. `mcp_server/api/routers/moonpay.py` — delegate to the hardened helper

`get_client_ip` is already imported at line 34. Replace `_resolve_device_ip` (lines 173-185):

```python
def _resolve_device_ip(request: Request, override: Optional[str]) -> str:
    """Pick the client IP MoonPay's risk engine should see.

    Delegates to the hardened :func:`utils.net.get_client_ip` so the
    trusted-proxy boundary and right-most-hop selection (FIX-P2-02) apply.
    An explicit ``override`` (validated upstream) still wins.
    """
    if override:
        return override
    return get_client_ip(request)
```

This removes the only callsite with no trusted-proxy gate. `sign_url_endpoint` (line 385) already uses `get_client_ip` and inherits the fix.

### 3. `mcp_server/tests/test_client_ip.py` — fix the test that codifies the bug

Replace `test_xff_hop0_used_when_multiple_entries` (lines 88-94) and add explicit ban-poisoning regression coverage. See the Test plan below for the exact assertions.

### 4. Defense-in-depth: tighten `TRUSTED_PROXY_CIDRS` in ECS (env var, flag-gated, safe)

**Env var:** `TRUSTED_PROXY_CIDRS`
**Safe value for production:** `"10.0.0.0/16"` (the actual VPC CIDR — `variables.tf:25`), instead of relying on the broad RFC1918 default `10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,127.0.0.0/8` (`net.py:51`). This ensures only the real VPC range is trusted, so a different RFC1918 peer (e.g. an internal pivot/SSRF) is not auto-trusted.

This is **secondary** — the right-most-hop fix in (1) is the primary remedy and works regardless. Roll this var out only after the code fix is deployed, because narrowing the trust set is only safe once selection is correct.

**Terraform diff — `infrastructure/terraform/ecs.tf`** (insert in the `environment` list of `aws_ecs_task_definition.mcp_server`, e.g. right after line 328 `FACILITATOR_TIMEOUT_SECONDS`):

```hcl
        { name = "FACILITATOR_TIMEOUT_SECONDS", value = "30" },
+       # FIX-P2-02: trust only the real VPC CIDR as a forwarding proxy, not
+       # the broad RFC1918 default. The ALB lives in this range; XFF is only
+       # honored when the TCP peer is inside it.
+       { name = "TRUSTED_PROXY_CIDRS", value = var.vpc_cidr },
      ], local.mcp_otel_env)
```

**Manual aws CLI note (if applying without a full Terraform run):** register a new task-definition revision with the added env var and force a new deployment:
```bash
# 1. Describe current task def -> edit JSON -> add the env entry -> register-task-definition
# 2. aws ecs update-service --cluster <YOUR_ECS_CLUSTER> --service <YOUR_ECR_MCP_REPO> \
#      --task-definition <new-revision-arn> --region us-east-2
```
Prefer the `deploy-mcp` / `deploy-check` skills for the actual rollout.

### Backward-compatibility risk & safe rollout

- **Could this lock out legitimate agents?** Low risk. For the current single-ALB topology the right-most non-trusted hop *is* the real client IP (the ALB appends exactly one hop). Legitimate clients are unaffected; they were never the spoofers. The only behavior change is which value lands in rate-limit/ban keys — and that value becomes *more* correct.
- **Edge case — a legitimate client whose real IP happens to be inside a trusted CIDR** (e.g. an internal service calling through the ALB from `10.0.0.0/16`): the walk would skip it and fall back to the peer. This is the desired conservative behavior (such "client" IPs are non-routable and ambiguous anyway) and matches the pre-fix fallback semantics.
- **Rollout order (staged):**
  1. Ship the code fix in (1)–(3). It is self-contained and requires no infra change to be correct.
  2. After the code fix is live and verified, set `TRUSTED_PROXY_CIDRS=10.0.0.0/16` via (4). If anything regresses, simply unset the env var to restore the broad default — the code fix still holds.
- No DB migration is required for this finding. (Persisting/sharing ban state across ECS tasks would further harden ban-poisoning but is out of scope here; the right-most-hop fix removes the spoofing root cause, which is the primary remedy.)

## Test plan (how the execution team proves it's fixed)

### Unit/integration tests to add — `mcp_server/tests/test_client_ip.py`

1. **Replace** `test_xff_hop0_used_when_multiple_entries` (it currently codifies the bug) with the ALB-append reality:
   ```python
   def test_rightmost_untrusted_hop_is_client_for_appending_proxy(self):
       # ALB appends the real source to the RIGHT. Header arriving at the
       # backend: "<spoofed client>, <real client appended by ALB>".
       req = _FakeRequest(
           peer_host="10.0.0.5",  # ALB, trusted
           headers={"X-Forwarded-For": "1.2.3.4, 203.0.113.7"},
       )
       # Must resolve to the appended (right-most non-trusted) IP, NOT 1.2.3.4.
       assert get_client_ip(req) == "203.0.113.7"
   ```

2. **Reproduces the spoofing bug then passes after the fix** — a spoofed left prefix must not change the result:
   ```python
   def test_spoofed_left_prefix_is_ignored(self):
       base = _FakeRequest(
           peer_host="10.0.0.5",
           headers={"X-Forwarded-For": "203.0.113.7"},
       )
       spoofed = _FakeRequest(
           peer_host="10.0.0.5",
           headers={"X-Forwarded-For": "9.9.9.9, 203.0.113.7"},
       )
       # Attacker prepending 9.9.9.9 must NOT alter the derived client IP.
       assert get_client_ip(spoofed) == get_client_ip(base) == "203.0.113.7"
   ```

3. **Trailing trusted hops are skipped** (multi-proxy chain robustness):
   ```python
   def test_walks_past_trailing_trusted_hops(self):
       req = _FakeRequest(
           peer_host="10.0.0.5",
           headers={"X-Forwarded-For": "203.0.113.7, 10.0.0.1, 10.0.0.2"},
       )
       assert get_client_ip(req) == "203.0.113.7"
   ```

4. **All-trusted / malformed-only XFF falls back to peer** (no regression of existing fallback tests):
   ```python
   def test_all_trusted_xff_falls_back_to_peer(self):
       req = _FakeRequest(
           peer_host="10.0.0.5",
           headers={"X-Forwarded-For": "10.0.0.1, 10.0.0.2"},
       )
       assert get_client_ip(req) == "10.0.0.5"
   ```
   Keep the existing `TestUntrustedPeerPath`, `TestMalformedXff`, `TestEdgeCases`, and `TestTrustedCidrsEnvVar` classes — they remain valid (untrusted peer still ignores XFF entirely; empty/whitespace/non-IP XFF still falls back to peer).

5. **Ban-poisoning regression** (new test, e.g. `mcp_server/tests/test_ip_ban_spoofing.py`) — proves a spoofed left hop can no longer poison a victim bucket:
   ```python
   def test_spoofed_xff_cannot_poison_victim_ban():
       from utils.net import get_client_ip
       # Simulate 25 unauth A2A hits with spoofed victim prefix behind the ALB.
       req = _FakeRequest(
           peer_host="10.0.0.5",
           headers={"X-Forwarded-For": "203.0.113.50, 198.51.100.99"},
       )
       resolved = get_client_ip(req)
       # The derived IP is the ALB-appended attacker IP, NOT the victim.
       assert resolved == "198.51.100.99"
       assert resolved != "203.0.113.50"
   ```
   (`_FakeRequest`/`_FakeClient`/`_FakeHeaders` can be imported/shared from `test_client_ip.py` or duplicated locally.)

6. **MoonPay delegation** — add to the MoonPay router tests: `_resolve_device_ip(request_with_spoofed_xff, override=None)` returns the right-most non-trusted hop (not the left-most), and `override` still wins when provided.

Run profile: `cd mcp_server && pytest tests/test_client_ip.py tests/test_ip_ban_spoofing.py -v` plus the MoonPay router test module. Confirm no regression in `pytest -m security`.

### Manual / E2E verification steps

1. Deploy the code fix to a staging ECS task behind the ALB.
2. From an external host, send `curl https://api.execution.market/api/v1/auth/nonce -H 'X-Forwarded-For: 1.1.1.1'` repeatedly (>5 times in 60s). With the fix, the limiter keys on your *real* IP and you receive a `429` after the 5th request (`X-RateLimit-Type: nonce`). Pre-fix, rotating the spoofed value evaded the cap.
3. Attempt ban-poisoning: send `>20` unauthenticated `/a2a/v1` requests within 5 min carrying `X-Forwarded-For: <a-victim-IP-you-control-but-do-not-use-for-this-test>`. Then connect from that victim IP normally — confirm it is **not** 403-banned. Pre-fix it would be banned.
4. Check CloudWatch `IP_BANNED` log lines: confirm the `ip=` field now shows real source IPs, not header-supplied values.

## Rollback plan
- **Code:** the change is contained to `utils/net.py`, `routers/moonpay.py`, and tests. Revert the commit to restore prior behavior. No data migration to undo.
- **Env var (step 4):** if narrowing `TRUSTED_PROXY_CIDRS` causes any unexpected lockout, **unset** `TRUSTED_PROXY_CIDRS` in the ECS task definition (or remove the Terraform line) and force a new deployment — this restores the broad RFC1918 default while keeping the correct right-most-hop code fix in place.
- Because ban state is in-memory per ECS task, any erroneous bans created during testing clear on the next deploy/restart.

## Verification checklist (boxes the executor ticks before marking done)
- [ ] `utils/net.py` now walks XFF right-to-left and returns the right-most non-trusted hop; left-most/all-trusted/malformed falls back to the peer.
- [ ] `utils/net.py` rule-3 docstring updated to describe right-most selection (no stale left-most wording).
- [ ] `routers/moonpay.py::_resolve_device_ip` delegates to `get_client_ip` (override still honored); no raw `xff.split(",")[0]` remains in the file.
- [ ] `grep -rn 'split(","\)\[0\]' mcp_server` returns no XFF-parsing callsite (only the central helper handles XFF).
- [ ] `test_client_ip.py` no longer asserts left-most-hop; new right-most/spoofed-prefix/trailing-trusted/all-trusted tests added and passing.
- [ ] New ban-poisoning regression test added and passing (spoofed prefix cannot select the victim IP).
- [ ] MoonPay router test asserts `_resolve_device_ip` uses right-most hop + honors `override`.
- [ ] `cd mcp_server && pytest tests/test_client_ip.py -v` and `pytest -m security` are green; full suite unchanged otherwise.
- [ ] (Defense-in-depth, staged after code fix) ECS task def sets `TRUSTED_PROXY_CIDRS = var.vpc_cidr` (`10.0.0.0/16`); Terraform applied or task-def revision registered + service updated.
- [ ] Manual E2E: nonce limiter trips on real IP with rotating spoofed XFF; ban-poisoning of a victim IP no longer reproduces.
- [ ] CloudWatch `IP_BANNED`/rate-limit logs show real source IPs, not header values.
