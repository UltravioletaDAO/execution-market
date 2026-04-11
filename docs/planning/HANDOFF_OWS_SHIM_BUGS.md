---
date: 2026-04-07
tags:
  - type/report
  - domain/agents
  - domain/payments
status: active
related-files:
  - dashboard/public/scripts/ows_shim.py
  - dashboard/public/skill.md
---

# Handoff: OWS Shim + Skill Bugs (2026-04-07)

Encontrados durante instalación end-to-end del skill v7.2.0 en Windows + WSL Ubuntu-24.04.

---

## BUG 1 — OWS Shim ignora `wallet_name` (CRITICAL)

**File:** `dashboard/public/scripts/ows_shim.py` (served at `https://execution.market/scripts/ows_shim.py`)

**Problema:** `OWSWallet.address` property ejecuta `ows wallet list` y devuelve la PRIMERA dirección EVM que encuentra, ignorando completamente el `self.name` que el usuario pasó al constructor. Si hay múltiples wallets en el vault, devuelve la dirección equivocada silenciosamente.

**Impacto:** Un agente con 2+ wallets (ej: hackathon-demo + production) firma escrow con la wallet equivocada → fondos se lockan contra el address equivocado → escrow irrecuperable.

**Código buggy:**
```python
@property
def address(self):
    if not self._address:
        r = subprocess.run(["ows", "wallet", "list"], capture_output=True, text=True)
        for line in r.stdout.splitlines():
            if "eip155" in line.lower() and "0x" in line:
                parts = line.split()
                for p in parts:
                    if p.startswith("0x") and len(p) == 42:
                        self._address = p
                        break  # ← returns FIRST match, ignores self.name
    return self._address
```

**Fix (ya aplicado localmente en WSL venv):**
```python
@property
def address(self):
    if not self._address:
        r = subprocess.run(["ows", "wallet", "list"], capture_output=True, text=True)
        current_name = None
        in_target = False
        for line in r.stdout.splitlines():
            stripped = line.strip()
            if stripped.startswith("Name:"):
                current_name = stripped.split(":", 1)[1].strip()
                in_target = (current_name == self.name)
                continue
            if in_target and "eip155" in line.lower() and "0x" in line:
                parts = line.split()
                for p in parts:
                    if p.startswith("0x") and len(p) == 42:
                        self._address = p
                        return self._address
    return self._address
```

**Validación:** El fix resuelve correctamente `claude-test-agent` → `0xe56D...` y `hackathon-demo` → `0x7eb4...` en un vault con 3 wallets.

---

## BUG 2 — SDK extra `escrow` no existe

**Skill v7.2.0 Step 1a dice:**
```bash
pip install -q "uvd-x402-sdk[escrow,wallet]>=0.21.0"
```

**Realidad:** `uvd-x402-sdk 0.22.1` no declara el extra `escrow`. Pip emite warning:
```
WARNING: uvd-x402-sdk 0.22.1 does not provide the extra 'escrow'
```

**Impacto:** No-blocker (se ignora el extra y `advanced_escrow.py` se importa de todas formas), pero confuso. Además, `web3` no se instala automáticamente (ver Bug 3).

**Fix (2 opciones):**
- **SDK:** Agregar `escrow` extra en `pyproject.toml` que incluya `web3>=6`
- **Skill:** Cambiar la instrucción a `pip install "uvd-x402-sdk[wallet]>=0.21.0" web3 eth-account httpx`

---

## BUG 3 — `advanced_escrow` falla por `web3` missing

**Al importar:**
```python
from uvd_x402_sdk.advanced_escrow import AdvancedEscrowClient
# → ModuleNotFoundError: No module named 'web3'
```

**Causa:** `web3` no está en las dependencias base ni en el extra `wallet` del SDK. Solo es necesario para `advanced_escrow.py` (escrow lock/release/refund).

**Fix:** `pip install web3` como paso adicional. Debería ser parte del extra `escrow` (Bug 2).

---

## BUG 4 — Skill warning sobre CLI sign bug está desactualizado

**Skill v7.2.0 dice:**
> WARNING: Do NOT use the OWS CLI (`ows sign message`) for ERC-8128 auth. The CLI v1.2.0 has a known bug that produces 64-byte signatures.

**Realidad:** OWS CLI v1.2.4 produce firmas correctas de 65 bytes. Verificado empíricamente — `eth_account.recover_message()` recupera la dirección correcta.

**Fix:** Actualizar el warning para decir "CLI v1.2.0-1.2.3" y recomendar v1.2.4+, o eliminar el warning si 1.2.4 es la versión mínima disponible en npm.

---

## Prioridad sugerida

| Bug | Severidad | Esfuerzo |
|-----|-----------|----------|
| 1 — Shim wallet_name | **P0** (puede causar pérdida de fondos) | 5 min |
| 2 — SDK extra escrow | P2 (cosmético) | 10 min (SDK repo) |
| 3 — web3 missing dep | P1 (blocker para escrow) | 5 min (SDK repo o skill) |
| 4 — CLI warning outdated | P2 (informacional) | 2 min (skill update) |

## Archivos a tocar

- `dashboard/public/scripts/ows_shim.py` — Bug 1 fix
- `dashboard/public/skill.md` — Bugs 2, 3, 4 (bump version a 7.2.1 PATCH)
- `mcp_server/skills/SKILL.md` — sync copy después de editar skill.md
- SDK repos (`uvd-x402-sdk-python`, `uvd-x402-sdk-typescript`) — Bugs 2, 3
