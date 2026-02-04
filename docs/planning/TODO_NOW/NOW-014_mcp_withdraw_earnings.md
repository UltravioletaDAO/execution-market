# NOW-014: Implementar em_withdraw_earnings

## Metadata
- **Prioridad**: P1
- **Fase**: 1 - MCP Server
- **Dependencias**: NOW-019, NOW-024 (x402 integration)
- **Archivos a modificar**: `mcp_server/server.py`
- **Tiempo estimado**: 2-3 horas

## Descripción
Implementar el tool MCP que permite a un worker retirar sus ganancias acumuladas a su wallet.

## Contexto Técnico
- **Payment rail**: x402-rs (USDC on Base)
- **Min withdrawal**: $5.00 (para cubrir gas)
- **Instant**: No batching, pago directo

## Input Schema
```json
{
  "executor_id": "uuid",
  "wallet_address": "0x...",
  "amount_usdc": 25.50,
  "withdraw_all": false
}
```

## Output Schema
```json
{
  "success": true,
  "withdrawal_id": "uuid",
  "amount_usdc": 25.50,
  "tx_hash": "0x...",
  "network": "base",
  "estimated_arrival": "instant"
}
```

## Código de Referencia

```python
Tool(
    name="em_withdraw_earnings",
    description="Withdraw accumulated earnings to wallet",
    inputSchema={
        "type": "object",
        "properties": {
            "executor_id": {
                "type": "string",
                "description": "UUID of the executor"
            },
            "wallet_address": {
                "type": "string",
                "description": "Destination wallet address"
            },
            "amount_usdc": {
                "type": "number",
                "description": "Amount to withdraw in USDC"
            },
            "withdraw_all": {
                "type": "boolean",
                "default": False,
                "description": "Withdraw entire balance"
            }
        },
        "required": ["executor_id", "wallet_address"]
    }
)

async def withdraw_earnings(args: dict) -> list[TextContent]:
    executor_id = args["executor_id"]
    wallet_address = args["wallet_address"]
    amount_usdc = args.get("amount_usdc")
    withdraw_all = args.get("withdraw_all", False)

    supabase = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_KEY"]
    )

    # 1. Get executor and verify wallet
    executor = supabase.table("executors").select("*").eq("id", executor_id).single().execute()
    if not executor.data:
        return [TextContent(type="text", text='{"error": "Executor not found"}')]

    # Verify wallet matches (security)
    if executor.data.get("wallet_address") and executor.data["wallet_address"] != wallet_address:
        return [TextContent(type="text", text='{"error": "Wallet address does not match registered wallet"}')]

    # 2. Calculate available balance
    available = await calculate_available_balance(supabase, executor_id)

    if available <= 0:
        return [TextContent(type="text", text='{"error": "No available balance to withdraw"}')]

    # 3. Determine withdrawal amount
    if withdraw_all:
        withdrawal_amount = available
    else:
        if amount_usdc is None:
            return [TextContent(type="text", text='{"error": "amount_usdc required when withdraw_all is false"}')]
        if amount_usdc > available:
            return [TextContent(type="text", text=json.dumps({"error": f"Insufficient balance. Available: ${available:.2f}"})}')]
        withdrawal_amount = amount_usdc

    # 4. Check minimum withdrawal
    MIN_WITHDRAWAL = 5.00
    if withdrawal_amount < MIN_WITHDRAWAL:
        return [TextContent(type="text", text=json.dumps({"error": f"Minimum withdrawal is ${MIN_WITHDRAWAL}"})}')]

    # 5. Create withdrawal record
    withdrawal = supabase.table("withdrawals").insert({
        "executor_id": executor_id,
        "wallet_address": wallet_address,
        "amount_usdc": withdrawal_amount,
        "status": "pending"
    }).execute()

    withdrawal_id = withdrawal.data[0]["id"]

    # 6. Execute x402 payment
    try:
        from integrations.x402.client import X402Client
        x402 = X402Client()

        tx_result = await x402.send_payment(
            to_address=wallet_address,
            amount_usdc=withdrawal_amount,
            memo=f"Execution Market withdrawal {withdrawal_id}"
        )

        # 7. Update withdrawal with tx hash
        supabase.table("withdrawals").update({
            "tx_hash": tx_result["tx_hash"],
            "status": "completed",
            "completed_at": "now()"
        }).eq("id", withdrawal_id).execute()

        result = {
            "success": True,
            "withdrawal_id": withdrawal_id,
            "amount_usdc": withdrawal_amount,
            "tx_hash": tx_result["tx_hash"],
            "network": "base",
            "estimated_arrival": "instant"
        }

    except Exception as e:
        # Mark withdrawal as failed
        supabase.table("withdrawals").update({
            "status": "failed",
            "error_message": str(e)
        }).eq("id", withdrawal_id).execute()

        return [TextContent(type="text", text=json.dumps({"error": f"Payment failed: {str(e)}"}))]

    return [TextContent(type="text", text=json.dumps(result))]


async def calculate_available_balance(supabase, executor_id: str) -> float:
    """Calculate available balance (earned - withdrawn)"""
    # Total earned from completed payments
    earned = supabase.table("payments").select(
        "amount_usdc"
    ).eq("executor_id", executor_id).eq("status", "completed").execute()

    total_earned = sum(float(p["amount_usdc"]) for p in earned.data) if earned.data else 0

    # Total already withdrawn
    withdrawn = supabase.table("withdrawals").select(
        "amount_usdc"
    ).eq("executor_id", executor_id).in_("status", ["completed", "pending"]).execute()

    total_withdrawn = sum(float(w["amount_usdc"]) for w in withdrawn.data) if withdrawn.data else 0

    return total_earned - total_withdrawn
```

## Migration Requerida
```sql
CREATE TABLE IF NOT EXISTS withdrawals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  executor_id UUID REFERENCES executors(id) NOT NULL,
  wallet_address TEXT NOT NULL,
  amount_usdc DECIMAL(18, 6) NOT NULL,
  tx_hash TEXT,
  status TEXT DEFAULT 'pending',
  error_message TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

CREATE INDEX idx_withdrawals_executor ON withdrawals(executor_id);
CREATE INDEX idx_withdrawals_status ON withdrawals(status);
```

## Criterios de Éxito
- [ ] Tool registrado en MCP server
- [ ] Balance calculation correcta
- [ ] Minimum withdrawal enforced ($5)
- [ ] x402 payment ejecutado
- [ ] Withdrawal record creado
- [ ] tx_hash guardado
- [ ] Error handling para payment failures

## Test Cases
```python
# Test 1: Successful withdrawal
result = await withdraw_earnings({
    "executor_id": "executor-with-balance",
    "wallet_address": "0x123...",
    "amount_usdc": 25.00
})
assert result["success"] == True
assert result["tx_hash"] is not None

# Test 2: Insufficient balance
result = await withdraw_earnings({
    "executor_id": "executor-with-10",
    "wallet_address": "0x123...",
    "amount_usdc": 100.00
})
assert "Insufficient balance" in result["error"]

# Test 3: Below minimum
result = await withdraw_earnings({
    "executor_id": "executor-uuid",
    "wallet_address": "0x123...",
    "amount_usdc": 2.00
})
assert "Minimum withdrawal" in result["error"]

# Test 4: Withdraw all
result = await withdraw_earnings({
    "executor_id": "executor-with-50",
    "wallet_address": "0x123...",
    "withdraw_all": True
})
assert result["amount_usdc"] == 50.00
```
