---
date: 2026-06-05
tags:
  - type/runbook
  - domain/payments
  - domain/operations
status: active
aliases:
  - "Encender MoonPay onramp"
  - "Activar onramp"
related-files:
  - mcp_server/integrations/moonpay/client.py
  - mcp_server/api/routers/moonpay.py
  - infrastructure/terraform/ecs.tf
  - dashboard/src/components/DepositModal.tsx
  - docs/runbooks/onramp-fraud.md
---

# Runbook — Encender el onramp de MoonPay (H2H deposit)

> **Qué activa esto:** el botón "Depositar" del flujo humano-contrata-humano. Hoy
> está **OFF en prod** (`EM_MOONPAY_ENABLED` no está en `ecs.tf` → default `false`),
> por eso `/api/v1/moonpay/sign-url` da 404 y el modal muestra "no disponible".
>
> **Regla de oro:** NO encender en producción sin **Force-3DS** activo en MoonPay
> (blocker anti-chargeback R3 — ver [[onramp-fraud]]). Por eso este runbook hace
> **sandbox primero** (sin riesgo, sin dinero real) y producción solo cuando 3DS
> esté confirmado.

---

## Estado actual (2026-06-05)

| Pieza | Estado |
|-------|--------|
| Fixes UX (saldo vía Lambda, min $0.01, comisión visible, mensaje claro) | ✅ desplegado (`71560b51`) |
| Velocity caps (migración 110) | ✅ aplicada |
| Worker ≠ publisher (F-04) | ✅ |
| Balance frontend vía Lambda `em_balances` | ✅ |
| Hold period (`EM_ONRAMP_PAYOUT_HOLD_HOURS`) | ⏳ código listo, dormante (=0) |
| **Force 3DS / SCA en MoonPay** | ❌ **no activo** (config de la cuenta MoonPay) |
| Secrets MoonPay en AWS SM + `ecs.tf` | ❌ no creados |
| `EM_MOONPAY_ENABLED` en `ecs.tf` | ❌ no presente (default false) |

**Leyenda de responsable:** 🧑 = lo hace Saul (dashboard MoonPay) · 🤖 = lo hace Claude (AWS/Terraform/deploy) · ✔️ = verificación.

---

## FASE 0 — Sandbox (recomendado: prueba todo el flujo sin riesgo)

> Sandbox usa tarjetas de prueba, no cobra dinero real y no necesita Force-3DS.
> Sirve para validar el flujo completo (sign-url → overlay → balance → publicar)
> antes de exponer producción.

### 🧑 0.1 — Sacar las keys de sandbox de MoonPay
1. Entrar a **https://dashboard.moonpay.com** (cuenta business de Ultravioleta DAO LLC).
2. Cambiar el toggle de entorno a **Sandbox / Test** (suele estar arriba a la derecha).
3. Ir a **Developers → API Keys** (o **Settings → API Keys**).
4. Copiar:
   - **Publishable key** → empieza con `pk_test_...`
   - **Secret key** → empieza con `sk_test_...`
   - ⚠️ La secret key NO se muestra en stream — pásamela por canal seguro o cárgala tú en AWS (paso 0.3).

### 🧑 0.2 — Configurar el webhook de sandbox
1. En el dashboard (modo Sandbox): **Developers → Webhooks → Add endpoint**.
2. URL del endpoint:
   ```
   https://api.execution.market/api/v1/moonpay/webhook
   ```
3. Eventos: seleccionar los de **transaction** (created / updated / completed / failed).
4. Guardar y copiar el **Webhook secret** (lo usa el backend para verificar `Moonpay-Signature-V2`).

### 🤖 0.3 — Crear los secrets sandbox en AWS Secrets Manager
> Valores reales nunca en el repo ni en stream — van directo a AWS SM.
```bash
# Naming alineado con client.py (em/moonpay-secret-key). Region us-east-2.
MSYS_NO_PATHCONV=1 aws secretsmanager create-secret --name em/moonpay-secret-key \
  --secret-string "sk_test_XXXX" --region us-east-2
MSYS_NO_PATHCONV=1 aws secretsmanager create-secret --name em/moonpay-public-key \
  --secret-string "pk_test_XXXX" --region us-east-2
MSYS_NO_PATHCONV=1 aws secretsmanager create-secret --name em/moonpay-webhook-secret \
  --secret-string "whsec_XXXX" --region us-east-2
```
(Si ya existen, usar `put-secret-value` en vez de `create-secret`.)

### 🤖 0.4 — Cablear secrets + flags en `ecs.tf` (entorno sandbox)
En el container `mcp-server` de `infrastructure/terraform/ecs.tf`, siguiendo el patrón de los demás secrets (ej. `SUPABASE_*`):

```hcl
# environment block
{ name = "EM_MOONPAY_ENABLED",    value = "true" },
{ name = "MOONPAY_API_BASE_URL",  value = "https://api.moonpay.com" },        # sandbox usa el mismo host
{ name = "MOONPAY_WIDGET_BASE_URL", value = "https://buy-sandbox.moonpay.com" }, # ← sandbox widget

# secrets block (valueFrom ARNs de los secrets del paso 0.3)
{ name = "MOONPAY_SECRET_KEY",    valueFrom = "arn:aws:secretsmanager:us-east-2:<YOUR_AWS_ACCOUNT_ID>:secret:em/moonpay-secret-key" },
{ name = "MOONPAY_PUBLIC_KEY",    valueFrom = "arn:aws:secretsmanager:us-east-2:<YOUR_AWS_ACCOUNT_ID>:secret:em/moonpay-public-key" },
{ name = "MOONPAY_WEBHOOK_SECRET", valueFrom = "arn:aws:secretsmanager:us-east-2:<YOUR_AWS_ACCOUNT_ID>:secret:em/moonpay-webhook-secret" },
```
> También dar permiso de lectura de esos 3 secrets al execution role de la task (política IAM del task `mcp-server`), igual que los demás secrets.

### 🤖 0.5 — Deploy + verificación sandbox
```bash
# CI corre terraform apply al pushear infrastructure/terraform/**. Tras el deploy:
curl -s https://api.execution.market/api/v1/moonpay/health | python -m json.tool
# Esperar: enabled=true, secret_key_configured=true, public_key_configured=true,
#          webhook_secret_configured=true
```
✔️ **Smoke E2E (sandbox):** en execution.market → un servicio → "Depositar" → debe abrir el overlay de MoonPay (NO "no disponible"). Pagar con una **tarjeta de prueba de MoonPay sandbox** (los números de test card están en la doc de MoonPay / pregúntale a tu account manager — no los hardcodeo aquí porque no los verifiqué) → confirmar que el saldo de Base sube y se puede publicar.

> Cuando el flujo sandbox pase E2E, apagar sandbox (`EM_MOONPAY_ENABLED=false` o cambiar a keys live) y pasar a la Fase 1.

---

## FASE 1 — Producción (dinero real)

> **No empezar esta fase hasta que 1.1 (Force-3DS) esté confirmado.**

### 🧑 1.1 — Activar Force-3DS / SCA en MoonPay  ⚠️ BLOCKER
**Por qué:** MoonPay es el merchant of record y posee el control de 3DS. Sin
forzarlo, un atacante con tarjeta robada puede comprar USDC → chargeback semanas
después (R3 — tumbó a BitInstant/LocalBitcoins).

**MoonPay no documenta públicamente la pantalla merchant de 3DS** (su Help Center
solo cubre 2FA del usuario final). Pasos a seguir, en orden:
1. En **https://dashboard.moonpay.com** (modo **Production/Live**), revisar
   **Settings → Risk / Compliance / Payments** (el nombre exacto del menú depende
   del tipo de cuenta) buscando una opción de **3DS / Strong Customer
   Authentication / SCA enforcement**.
2. Si no aparece visible, **contactar a tu account manager de MoonPay o a soporte**
   (chat en dashboard o partners@moonpay.com) con esta petición textual:
   > "Please enable **forced 3DS / SCA on all card transactions** for our business
   > account (merchant of record), not just risk-based 3DS."
3. ✔️ **Verificar** que quedó activo: hacer 1 compra real chica con tarjeta propia
   y confirmar que el flujo **pide el challenge 3DS** del banco. Si lo pide → activo.

Enlaces MoonPay: [Help Center](https://support.moonpay.com/en/) · [Security FAQ](https://support.moonpay.com/en/articles/388281-security-and-safety-faqs)

### 🧑 1.2 — Keys live + webhook live
- Repetir 0.1 y 0.2 pero en modo **Production/Live**: `pk_live_...`, `sk_live_...`,
  webhook a la misma URL `https://api.execution.market/api/v1/moonpay/webhook`,
  nuevo webhook secret.

### 🤖 1.3 — Rotar los secrets de AWS a los valores live
```bash
MSYS_NO_PATHCONV=1 aws secretsmanager put-secret-value --secret-id em/moonpay-secret-key \
  --secret-string "sk_live_XXXX" --region us-east-2
MSYS_NO_PATHCONV=1 aws secretsmanager put-secret-value --secret-id em/moonpay-public-key \
  --secret-string "pk_live_XXXX" --region us-east-2
MSYS_NO_PATHCONV=1 aws secretsmanager put-secret-value --secret-id em/moonpay-webhook-secret \
  --secret-string "whsec_live_XXXX" --region us-east-2
```

### 🤖 1.4 — `ecs.tf` a producción
- En `ecs.tf`: `MOONPAY_WIDGET_BASE_URL = "https://buy.moonpay.com"` (quitar `buy-sandbox`).
- Mantener `EM_MOONPAY_ENABLED = "true"`.

### 🤖 1.5 — (Recomendado) activar el hold-period anti-self-collusion
```hcl
{ name = "EM_ONRAMP_PAYOUT_HOLD_HOURS", value = "24" },   # bloquea release N horas post-onramp
```
> Cierra el hueco de self-collusion (mismo humano financia con tarjeta robada y se
> auto-aprueba con una segunda cuenta). Empezar con 24h y ajustar.

### 🤖 1.6 — Deploy + verificación producción
```bash
curl -s https://api.execution.market/api/v1/moonpay/health | python -m json.tool   # enabled=true, todo configured=true
```
✔️ Hacer **1 depósito real chico** (ej. el mínimo de MoonPay, ~$5) con tu propia
tarjeta → confirmar challenge 3DS → confirmar USDC en Base → confirmar fila en
`moonpay_transactions` (webhook llegó).

---

## Rollback (apagar el onramp en cualquier momento)
```bash
# En ecs.tf: EM_MOONPAY_ENABLED = "false"  → push → terraform apply
# (o, urgente, editar el env de la task def y force-new-deployment)
```
Efecto: `/api/v1/moonpay/*` vuelve a dar 404, el modal muestra "no disponible".
Balances existentes intactos (EM nunca custodia fondos). Ver [[onramp-fraud]] §Incident response.

---

## Checklist resumido

**Sandbox**
- [ ] 🧑 keys `pk_test_`/`sk_test_` + webhook sandbox (secret)
- [ ] 🤖 3 secrets en AWS SM
- [ ] 🤖 `ecs.tf`: flag ON + `buy-sandbox` widget + secrets cableados + IAM read
- [ ] 🤖 deploy → `/health` todo `true`
- [ ] ✔️ E2E sandbox con tarjeta de prueba

**Producción**
- [ ] 🧑 **Force-3DS activo** (verificado con compra real) ⚠️ BLOCKER
- [ ] 🧑 keys `pk_live_`/`sk_live_` + webhook live (secret)
- [ ] 🤖 rotar secrets AWS a live
- [ ] 🤖 `ecs.tf`: `buy.moonpay.com` + (recomendado) `EM_ONRAMP_PAYOUT_HOLD_HOURS=24`
- [ ] 🤖 deploy → `/health` todo `true`
- [ ] ✔️ depósito real de prueba con challenge 3DS + USDC en Base + webhook

> Cuando estés listo, dime **"sandbox"** o **"producción"** y ejecuto la parte 🤖
> (los pasos 🧑 los necesito de ti: keys + 3DS). Los valores reales (account ID,
> ARNs) están en `CLAUDE.md.local`, no en este archivo.
