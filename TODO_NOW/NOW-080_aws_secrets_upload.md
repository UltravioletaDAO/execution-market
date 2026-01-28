# NOW-080: Upload Secrets to AWS Secrets Manager

## Status: PENDING
## Priority: P0 - Required for production

## Secreto a Crear

Nombre: `chamba/production`
Región: `us-east-2`

## Valores Requeridos (desde .env.local)

```json
{
  "SUPABASE_URL": "https://xxx.supabase.co",
  "SUPABASE_ANON_KEY": "eyJ...",
  "SUPABASE_SERVICE_ROLE_KEY": "eyJ...",
  "X402_FACILITATOR_URL": "https://facilitator.ultravioletadao.xyz",
  "X402_MERCHANT_ID": "chamba-production",
  "ANTHROPIC_API_KEY": "sk-ant-...",
  "BASE_RPC_URL": "https://mainnet.base.org",
  "WALLET_PRIVATE_KEY": "0x..."
}
```

## Comando para Crear

```bash
# Crear secreto con valores
aws secretsmanager create-secret \
  --name chamba/production \
  --region us-east-2 \
  --secret-string '{
    "SUPABASE_URL": "VALUE",
    "SUPABASE_ANON_KEY": "VALUE",
    "SUPABASE_SERVICE_ROLE_KEY": "VALUE",
    "X402_FACILITATOR_URL": "https://facilitator.ultravioletadao.xyz",
    "X402_MERCHANT_ID": "chamba-production",
    "ANTHROPIC_API_KEY": "VALUE",
    "BASE_RPC_URL": "https://mainnet.base.org",
    "WALLET_PRIVATE_KEY": "VALUE"
  }'
```

## Actualizar Secreto Existente

```bash
aws secretsmanager put-secret-value \
  --secret-id chamba/production \
  --region us-east-2 \
  --secret-string '{ ... }'
```

## Verificar

```bash
# Verificar que existe
aws secretsmanager describe-secret \
  --secret-id chamba/production \
  --region us-east-2

# Ver keys (NO valores)
aws secretsmanager get-secret-value \
  --secret-id chamba/production \
  --region us-east-2 \
  --query 'SecretString' | jq 'keys'
```

## Uso en ECS Task Definition

```json
{
  "secrets": [
    {
      "name": "SUPABASE_URL",
      "valueFrom": "arn:aws:secretsmanager:us-east-2:YOUR_AWS_ACCOUNT_ID:secret:chamba/production:SUPABASE_URL::"
    },
    {
      "name": "SUPABASE_SERVICE_ROLE_KEY",
      "valueFrom": "arn:aws:secretsmanager:us-east-2:YOUR_AWS_ACCOUNT_ID:secret:chamba/production:SUPABASE_SERVICE_ROLE_KEY::"
    }
  ]
}
```

## IMPORTANTE

- **NUNCA** commitear valores de secrets
- Usar placeholders en documentación
- Rotar keys si se exponen accidentalmente
- El secreto debe existir ANTES de crear ECS tasks
