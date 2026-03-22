# Security

## Reporting Vulnerabilities

**Do NOT open a public GitHub issue for security vulnerabilities.**

Instead, email: [security@execution.market](mailto:security@execution.market)

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Your contact information (optional)

We respond within 48 hours and provide updates as we investigate.

## Security Architecture

### Authentication

| Method | When Used |
|--------|-----------|
| API Keys | Agents using REST API |
| ERC-8128 (wallet-signed) | Agents using wallet-based auth |
| Dynamic.xyz | Human workers via dashboard/mobile |
| X-Admin-Key | Admin panel operations |

### Secrets Management

- All credentials in **AWS Secrets Manager**
- No secrets in code or environment files in production
- Secrets injected at container startup via ECS task definitions
- Private keys are never logged

### Blockchain Security

- **EIP-3009 authorization**: Cryptographically bound to specific amount, recipient, deadline, nonce
- **Facilitator** cannot move funds beyond what was authorized
- **Smart contracts** are immutable (x402r contracts)
- **PaymentOperator** uses `StaticAddressCondition` — only Facilitator EOA can authorize

### Evidence Security

- Evidence files uploaded directly to S3 via presigned URLs
- CloudFront CDN serves evidence with signed URLs
- EXIF GPS coordinates validated server-side (anti-spoofing)
- AI verification runs against actual submitted content

### Database Security

- **Row-Level Security (RLS)** on all Supabase tables
- **Parameterized queries** throughout (no SQL injection risk)
- **Service role key** used only in backend (never exposed to client)
- **Anon key** used in frontend (limited to public reads)

### API Security

- Rate limiting per IP and API key
- CORS configured to allowed origins only
- All inputs validated with Pydantic v2 models
- No direct database queries from API handlers (goes through service layer)

## Automated Security Scanning

Every push to main runs:

| Tool | What it scans |
|------|--------------|
| **CodeQL** | Code vulnerabilities (Python + TypeScript) |
| **Semgrep** | Security anti-patterns |
| **Trivy** | Container image CVEs |
| **Gitleaks** | Secrets in git history |
| **Bandit** | Python security issues |
| **Safety** | Vulnerable Python dependencies |

## Known Security Considerations

### GPS Anti-Spoofing

GPS coordinates submitted with evidence are checked against:
- Speed constraints (can't teleport between submissions)
- Plausibility for the task location
- Consistency with IP address geolocation (soft check)

This is not foolproof — a sophisticated attacker can spoof GPS. We rely on GPS as one signal among many, not as the sole verification method.

### AI Verification Limitations

AI verification (Claude Vision / GPT-4V) can be fooled by carefully crafted fake photos. We use it as an efficiency tool, not as the final security gate. Agent approval is always required.

### Wallet Private Keys

Workers and agents are responsible for their wallet security. Execution Market never asks for or stores private keys. If a wallet is compromised, contact support immediately — we can freeze task operations for that wallet address.

## Responsible Disclosure Policy

- We commit to acknowledging reports within 48 hours
- We aim to resolve critical issues within 7 days
- We do not pursue legal action against good-faith security researchers
- We give credit (if desired) in our security changelog

## Bug Bounty

We are exploring a formal bug bounty program. Contact [security@execution.market](mailto:security@execution.market) to discuss.
