# Chamba Tech Stack Recommendation

> NOW-155: Recommended technology stack for Chamba deployment

## Overview

Chamba uses a modern, scalable architecture designed for:
- Real-time task coordination
- Secure payment processing
- Evidence verification
- Multi-region deployment

---

## Core Infrastructure

### Compute
| Layer | Technology | Why |
|-------|------------|-----|
| **Backend** | Python 3.11 + FastAPI | MCP compatibility, async support |
| **Frontend** | React 18 + Vite | Fast builds, PWA support |
| **Database** | Supabase (PostgreSQL) | Real-time, auth, storage |
| **Deployment** | AWS ECS Fargate | Serverless containers |

### Recommended Cloud (AWS)
```
Production:
- ECS Fargate (containers)
- RDS PostgreSQL (if not Supabase)
- S3 (evidence storage)
- CloudFront (CDN)
- Secrets Manager (credentials)
- CloudWatch (monitoring)

Alternative (cost-optimized):
- Railway / Render (backend)
- Vercel (frontend)
- Supabase (DB + Auth + Storage)
```

---

## Backend Stack

### MCP Server
```python
# Core dependencies
fastmcp>=0.1.0      # MCP server framework
pydantic>=2.0       # Validation
httpx>=0.25         # Async HTTP
anthropic>=0.18     # Claude API

# Database
supabase>=2.0       # Supabase client
asyncpg>=0.29       # PostgreSQL driver

# Payments
web3>=6.0           # Ethereum/Base
eth-account>=0.10   # Wallet management

# Verification
pillow>=10.0        # Image processing
imagehash>=4.3      # Perceptual hashing
```

### API Layer (Optional REST)
```python
fastapi>=0.109
uvicorn[standard]>=0.27
python-multipart>=0.0.6  # File uploads
```

---

## Frontend Stack

### Dashboard
```json
{
  "framework": "React 18",
  "build": "Vite 5",
  "styling": "Tailwind CSS 3",
  "state": "Zustand",
  "forms": "React Hook Form",
  "i18n": "react-i18next",
  "routing": "React Router 6",
  "pwa": "vite-plugin-pwa"
}
```

### Mobile-First Requirements
- PWA with offline support
- Service worker for evidence caching
- Native camera API access
- Geolocation API
- Push notifications (Web Push)

---

## Blockchain Stack

### Base Network (Primary)
```
Network: Base Mainnet (Chain ID: 8453)
RPC: https://mainnet.base.org
Explorer: https://basescan.org

Contracts:
- USDC: 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
- x402 MerchantRouter: 0xa48E8AdcA504D2f48e5AF6be49039354e922913F
- x402 DepositRelayFactory: 0x41Cc4D337FEC5E91ddcf4C363700FC6dB5f3A814
```

### Superfluid (Streaming)
```
Host: 0x4C073B3baB6d8826b8C5b229f3cfdC1eC6E47E74
CFA: 0x19ba78B9cDB05A877718841c574325fdB53601bb
USDCx: 0xD04383398dD2426297da660F9CCA3d439AF9ce1b
```

### Why Base?
- Low fees ($0.01-0.10 per tx)
- Fast finality (2 seconds)
- Strong ecosystem (Coinbase backing)
- Native USDC support
- x402 protocol deployed

---

## Database Schema

### Core Tables
```sql
-- Workers
executors (id, wallet, reputation_raw, reputation_bayesian, ...)

-- Tasks
tasks (id, agent_id, title, instructions, bounty_usd, status, ...)

-- Submissions
submissions (id, task_id, executor_id, evidence, status, ...)

-- Escrows
escrows (id, task_id, amount, tx_hash, status, ...)
```

### Real-time
- Supabase Realtime for live updates
- Row-level security for multi-tenancy

---

## Verification Pipeline

### Evidence Processing
```
1. Upload → S3/Supabase Storage
2. Pre-checks (auto):
   - Photo source (camera vs gallery)
   - GPS validation
   - Timestamp check
   - Duplicate detection
   - Tampering detection
   - GenAI detection
3. AI Review (if needed):
   - Claude Vision (claude-sonnet-4-20250514)
   - Task-specific prompts
4. Final decision (auto/agent/human)
```

### Dependencies
```python
# Image analysis
pillow>=10.0
imagehash>=4.3      # Perceptual hashing
piexif>=1.1         # EXIF handling

# AI
anthropic>=0.18     # Claude Vision
openai>=1.0         # GPT-4V (consensus)
```

---

## CI/CD Pipeline

### GitHub Actions
```yaml
Workflow:
1. test-mcp-server:
   - pytest with coverage
   - Type checking (mypy)

2. test-dashboard:
   - npm test
   - Build check

3. build-push:
   - Docker build
   - Push to ECR

4. deploy:
   - ECS deployment
   - Health check

5. e2e-tests:
   - Playwright tests
   - Screenshot on failure
```

---

## Monitoring & Observability

### Recommended Stack
| Purpose | Tool | Why |
|---------|------|-----|
| Metrics | CloudWatch / Grafana | AWS native or self-hosted |
| Logs | CloudWatch Logs | Centralized logging |
| Traces | AWS X-Ray / Jaeger | Distributed tracing |
| Errors | Sentry | Error tracking |
| Uptime | Better Uptime | Status page |

### Key Metrics
- Task completion rate
- Average verification time
- Payment success rate
- Worker retention
- API latency (p50, p95, p99)

---

## Security Considerations

### Must-Have
- [ ] All secrets in AWS Secrets Manager (never in code)
- [ ] HTTPS everywhere (TLS 1.3)
- [ ] Row-level security in Supabase
- [ ] Rate limiting (per IP and user)
- [ ] Input validation (Pydantic)
- [ ] CORS configured properly

### Payment Security
- [ ] Hardware wallet for treasury
- [ ] Multi-sig for large amounts (>$1000)
- [ ] Escrow timeouts
- [ ] Fraud detection active

### Evidence Security
- [ ] No PII in evidence URLs
- [ ] Signed URLs for access
- [ ] Automatic expiration
- [ ] GPS precision limiting

---

## Development Setup

### Local Development
```bash
# Clone
git clone https://github.com/ultravioleta/chamba
cd chamba

# Backend
cd mcp_server
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Frontend
cd ../dashboard
npm install
npm run dev

# Or use Docker
docker-compose up
```

### Environment Variables
```bash
# Required
SUPABASE_URL=
SUPABASE_KEY=
ANTHROPIC_API_KEY=
BASE_RPC_URL=
X402_PRIVATE_KEY=

# Optional
OPENAI_API_KEY=  # For multi-model verification
SENTRY_DSN=
```

---

## Cost Estimates

### Monthly (Starter)
| Service | Cost |
|---------|------|
| Supabase (Free tier) | $0 |
| AWS ECS (2 tasks) | ~$50 |
| CloudWatch | ~$10 |
| Domain + SSL | ~$15 |
| **Total** | ~$75/mo |

### Monthly (Growth)
| Service | Cost |
|---------|------|
| Supabase Pro | $25 |
| AWS ECS (4 tasks) | ~$150 |
| RDS (if needed) | ~$50 |
| CloudFront | ~$20 |
| Monitoring | ~$30 |
| **Total** | ~$275/mo |

---

## Quick Start Commands

```bash
# Deploy to production
./scripts/deploy.sh production

# Run tests
pytest mcp_server/tests/ -v
npm run test --prefix dashboard

# Database migrations
supabase db push

# Local development
docker-compose up -d
```

---

## Recommended Reading

1. **MCP Protocol**: https://modelcontextprotocol.io
2. **x402 Protocol**: https://www.x402.org
3. **Superfluid**: https://docs.superfluid.finance
4. **Base Network**: https://docs.base.org
5. **Supabase**: https://supabase.com/docs
