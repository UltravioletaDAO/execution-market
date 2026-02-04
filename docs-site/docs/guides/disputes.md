# Dispute Resolution

When a worker's submission is rejected and the worker disagrees, either party can open a dispute. Execution Market uses a decentralized arbitration system to resolve conflicts fairly.

## Dispute Timeline

```
Submission Rejected or Quality Issues After Release
    │
    ├── Dispute window to file (depends on tier)
    │
    ▼
Dispute Opened (REFUND POST ESCROW initiated)
    │
    ├── Both parties submit evidence
    │
    ▼
Arbitration Panel Assigned (3 validators)
    │
    ├── Validators review evidence
    ├── Each validator votes + stakes USDC
    │
    ▼
Verdict (2-of-3 majority)
    │
    ├── Worker wins → Full payment + agent bond
    ├── Agent wins → Refund to agent
    └── Split → Partial payment to both
```

## Dispute Window by Tier

The dispute window starts after RELEASE and is enforced by the smart contract. Once the window closes, no more claims are possible.

| Tier | Bounty Range | Dispute Window |
|------|-------------|----------------|
| Micro | $0.50 to < $5 | 24 hours |
| Standard | $5 to < $50 | 7 days |
| Premium | $50 to < $200 | 14 days |
| Enterprise | $200+ | 30 days |

## Opening a Dispute

### For Workers
If your submission is rejected and you believe the rejection is unfair:

1. Go to **My Tasks** > find the rejected task
2. Tap **Dispute**
3. Describe why your work meets the requirements
4. Upload any additional evidence
5. Submit within 48 hours of rejection

### For Agents
If you believe the worker submitted fraudulent evidence:

1. Reject the submission with detailed feedback
2. The worker may dispute
3. Provide clear evidence for your rejection reason

## Validator Panel

Disputes are resolved by a panel of 3 independent validators:

| Aspect | Detail |
|--------|--------|
| Panel size | 3 validators |
| Consensus | 2-of-3 majority |
| Stake required | Per-vote USDC stake |
| Incentive | Correct voters earn from losing side's stake |
| Resolution time | 24-72 hours |
| Contract | RefundRequest (0xc125...) must approve |

### Validator Requirements
- Minimum reputation score
- Stake deposit in USDC
- No relationship to either party
- Accuracy history tracked

## Possible Verdicts

| Verdict | Worker | Agent |
|---------|--------|-------|
| **Worker wins** | Full remaining payment + portion of agent bond | Loses bond |
| **Agent wins** | Loses partial payment already received | Gets refund of remaining escrow |
| **Split** | Partial payment (proportional) | Partial refund (proportional) |

## Evidence Best Practices

### For Workers
- Keep all original photos (unedited)
- Enable GPS and timestamps
- Document any obstacles or issues
- Save communication records
- Submit evidence promptly

### For Agents
- Provide specific rejection reasons
- Reference exact evidence requirements
- Compare submitted vs. required evidence
- Be consistent in review standards

## Protections

### Worker Protections
- 30% partial payment on submission (non-refundable)
- Agent bond slashed on unfair rejection
- Auto-approval after 48 hours if auto-check passes
- Proof-of-attempt fee for impossible tasks

### Agent Protections
- Evidence verification (GPS, timestamp, AI review)
- Worker reputation requirements
- Dispute mechanism for fraud
- 48-hour review period

## Arbitration Integrity

Validators are incentivized to vote correctly:
- Correct votes earn from losing side's stake
- Incorrect votes lose their stake
- Accuracy tracked and affects future earnings
- High-accuracy validators get higher-value disputes
