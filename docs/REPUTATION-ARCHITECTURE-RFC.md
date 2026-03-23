# RFC: Execution Market Reputation Architecture v2.0

**Status:** Draft  
**Author:** Engineering Team  
**Date:** March 23, 2026  
**Supersedes:** Current Bayesian reputation system  

## Abstract

This RFC proposes a complete redesign of Execution Market's reputation system to achieve on-chain truth, portable reputation, and anti-gaming protection. The new architecture treats blockchain as the canonical source of truth while maintaining performance through intelligent caching.

## 1. Problem Statement

### Current Architecture Issues

The existing reputation system suffers from fundamental architectural flaws:

**1. Source of Truth Confusion**
- `reputation_score` in `executors` table treated as canonical data
- Can desync from on-chain ERC-8004 Reputation Registry
- Database updates bypassing blockchain validation

**2. Data Integrity Failures**  
- Reputation scores can exceed logical bounds (>100)
- Bayesian function produces unbounded outputs
- Missing or dropped CHECK constraints

**3. No Portable Reputation**
- Workers start from zero regardless of external reputation
- ERC-8004 standard allows cross-protocol reputation import
- Lost network effects and reduced worker onboarding

**4. Gaming Vulnerabilities**
- No protection against self-dealing (agent rating own wallets)
- No weighting by task value or agent credibility
- Rapid inflation possible through coordinated ratings

## 2. Proposed Architecture

### 2.1 On-Chain Source of Truth

**Principle:** The ERC-8004 Reputation Registry is the canonical source. Database is cache only.

**Implementation:**
```
┌─────────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│   Execution Market  │    │  ERC-8004 Registry   │    │    Other Protocols  │
│                     │    │                      │    │                     │
│ ┌─────────────────┐ │    │ ┌──────────────────┐ │    │ ┌─────────────────┐ │
│ │ executors.      │ │    │ │ Reputation       │ │    │ │ External Reps   │ │
│ │ reputation_score│─┼────┼→│ Transactions     │ │    │ │ (Cross-chain)   │ │
│ │ (CACHE ONLY)    │ │    │ │ (SOURCE OF TRUTH)│ │    │ │                 │ │
│ └─────────────────┘ │    │ └──────────────────┘ │    │ └─────────────────┘ │
└─────────────────────┘    └──────────────────────┘    └─────────────────────┘
          │                           │                           │
          └───────────── Sync ────────┴─────────── Import ───────┘
```

**Benefits:**
- Eliminates desync issues
- Enables cross-protocol reputation portability  
- Provides cryptographic proof of reputation history
- Supports decentralized auditing

### 2.2 Score Calculation Engine

**Algorithm:** Time-weighted exponential decay with value weighting

```python
def calculate_reputation_score(address: str) -> float:
    """
    Calculate reputation from on-chain transactions
    Returns: Score 0-100 (clamped)
    """
    transactions = get_erc8004_transactions(address)
    
    current_time = time.now()
    weighted_sum = 0
    weight_sum = 0
    
    for tx in transactions:
        # Time decay: newer ratings carry more weight
        time_weight = exp(-DECAY_RATE * (current_time - tx.timestamp))
        
        # Value weighting: higher bounties = more credible
        value_weight = min(sqrt(tx.task_value_usd / 10), 3.0)
        
        # Agent credibility: established agents carry more weight
        agent_weight = get_agent_credibility(tx.agent_address)
        
        total_weight = time_weight * value_weight * agent_weight
        
        weighted_sum += tx.rating * total_weight
        weight_sum += total_weight
    
    if weight_sum == 0:
        return 50  # Default score for new workers
    
    raw_score = weighted_sum / weight_sum
    return clamp(raw_score, 0, 100)
```

**Parameters:**
- `DECAY_RATE = 0.1` (ratings lose 10% weight per year)
- `MIN_TASK_VALUE = $1` (minimum for full weighting)
- `MAX_VALUE_MULTIPLIER = 3x` (cap value weighting)

### 2.3 Portable Reputation Import

**Trust-but-Verify Model:**

When a worker connects a wallet with existing ERC-8004 reputation:

1. **Import with Discount:**
   ```python
   def import_external_reputation(address: str) -> float:
       external_scores = get_external_erc8004_scores(address)
       
       combined_score = 0
       total_weight = 0
       
       for protocol, score in external_scores.items():
           trust_weight = PROTOCOL_TRUST_WEIGHTS.get(protocol, 0.2)
           protocol_weight = get_protocol_reputation(protocol)
           
           combined_score += score * trust_weight * protocol_weight
           total_weight += trust_weight * protocol_weight
       
       return combined_score / total_weight if total_weight > 0 else 50
   ```

2. **Trust Weight by Protocol:**
   ```python
   PROTOCOL_TRUST_WEIGHTS = {
       "gitcoin.co": 0.9,           # Well-known, established
       "upwork-dao.eth": 0.7,       # Emerging but credible  
       "freelancer-protocol": 0.5,  # Unknown/new
       "suspicious.eth": 0.1,       # Low trust
   }
   ```

3. **Decay Over Time:**
   - Imported scores decay as local ratings accumulate
   - Formula: `final = (local_weight * local_avg + import_weight * imported_avg) / total_weight`
   - `local_weight` grows with each EM task: `local_weight = tasks_completed * 1.2`
   - `import_weight` decays over time: `import_weight = initial_trust * exp(-decay * months)`

### 2.4 Anti-Gaming Protections

**1. Self-Dealing Detection:**
```python
def detect_self_dealing(agent_address: str, worker_address: str) -> float:
    """Returns credibility penalty (0-1) for suspicious patterns"""
    
    # Check if addresses are related (same controller, etc.)
    if are_addresses_related(agent_address, worker_address):
        return 0.1  # Heavy penalty
    
    # Check rating patterns  
    agent_ratings = get_ratings_by_agent(agent_address)
    worker_ratings = get_ratings_for_worker(worker_address)
    
    # If agent only rates this worker, suspicious
    if len(agent_ratings) > 0 and all(r.worker == worker_address for r in agent_ratings):
        return 0.3
    
    # If worker only gets ratings from this agent, suspicious
    if len(worker_ratings) > 0 and all(r.agent == agent_address for r in worker_ratings):
        return 0.4
        
    return 1.0  # No penalty
```

**2. Value-Based Weighting:**
- Ratings from $100 tasks carry more weight than $5 tasks
- Prevents cheap task spamming for reputation inflation
- Square root scaling prevents extreme weighting

**3. Agent Credibility Scoring:**
```python
def get_agent_credibility(agent_address: str) -> float:
    """Agent credibility affects rating weight"""
    
    agent_stats = get_agent_statistics(agent_address)
    
    # Base credibility from task history
    task_credibility = min(agent_stats.total_tasks / 20, 1.0)
    
    # Bonus for higher value tasks
    value_credibility = min(agent_stats.avg_task_value / 50, 1.0)
    
    # Penalty for rating pattern irregularities
    pattern_penalty = detect_rating_pattern_issues(agent_address)
    
    return (task_credibility + value_credibility) * pattern_penalty
```

**4. Minimum Task Requirements:**
- "Trusted" tier requires minimum 10 completed tasks on Execution Market
- Imported reputation can't bypass minimum task requirements
- Prevents instant high-tier status from external reputation only

### 2.5 Incremental Updates

**Real-Time Score Adjustment:**
```python
def update_reputation_incremental(address: str, new_rating: float, task_value: float):
    """Update cached score without full recalculation"""
    
    current_score = get_cached_score(address)
    rating_count = get_rating_count(address)
    
    # Learning rate decreases as more ratings accumulate (running average)
    learning_rate = 1.0 / (rating_count + 1)
    
    # Weight by task value
    value_weight = min(sqrt(task_value / 10), 2.0)
    
    # Update formula: exponential moving average
    new_score = current_score + (learning_rate * value_weight * (new_rating - current_score))
    
    # Clamp and store
    final_score = clamp(new_score, 0, 100)
    cache_score(address, final_score, expires_in=3600)
    
    # Schedule full recalculation for high-impact changes
    if abs(new_rating - current_score) > 20:
        schedule_full_recalculation(address, delay=60)
```

**Benefits:**
- Sub-second reputation updates
- Avoids expensive full recalculations on every rating
- Self-correcting via periodic full recalculation
- Handles edge cases with scheduled corrections

### 2.6 Worker Identity at Signup

**Zero-Delay Identity Creation:**

```python
def register_worker_identity(wallet_address: str):
    """Called immediately when worker connects wallet via Dynamic.xyz"""
    
    # Check if ERC-8004 identity already exists
    identity = erc8004_registry.getIdentity(wallet_address)
    
    if not identity.exists:
        # Mint new identity immediately  
        tx = facilitator.mint_identity(
            wallet_address,
            metadata={"source": "execution_market", "version": "1.0"}
        )
        
        # Don't wait for task completion
        log_identity_creation(wallet_address, tx.hash)
    
    # Import any existing external reputation
    external_rep = import_external_reputation(wallet_address)
    if external_rep > 50:  # Above default
        cache_score(wallet_address, external_rep, source="imported")
```

**Timeline:**
- Wallet connection → Identity minted in same transaction
- Reputation imported within 30 seconds
- Worker can receive tasks immediately with appropriate trust level

### 2.7 Assignment Flow Integration

**Smart Auto-Assignment:**

```python
def evaluate_worker_application(task_id: str, worker_address: str) -> AssignmentDecision:
    """Determine if worker should be auto-assigned or needs operator review"""
    
    # Get current reputation (cached or calculate)
    reputation = get_reputation_score(worker_address)
    task = get_task(task_id)
    
    # Auto-assign thresholds
    if reputation >= 80:
        return AssignmentDecision.AUTO_ASSIGN
    
    # Special handling for imported reputation
    if has_imported_reputation(worker_address):
        discounted_score = reputation * get_import_trust_factor(worker_address)
        if discounted_score >= 70:
            return AssignmentDecision.AUTO_ASSIGN_WITH_MONITORING
    
    # High-value tasks need higher thresholds
    if task.bounty_usd > 100 and reputation < 90:
        return AssignmentDecision.OPERATOR_REVIEW
    
    # New workers or low reputation
    if reputation < 60 or get_task_count(worker_address) < 3:
        return AssignmentDecision.OPERATOR_REVIEW
    
    return AssignmentDecision.AUTO_ASSIGN
```

## 3. Implementation Plan

### Phase 1: Foundation (Week 1-2)
1. **Migration 073:** Add reputation cache metadata
   - `reputation_source` enum: ('calculated', 'imported', 'default')
   - `last_calculated` timestamp  
   - `calculation_version` for algorithm versioning

2. **ERC-8004 Integration Service:**
   - Transaction reader for on-chain reputation data
   - Cross-chain import logic
   - Protocol trust weight configuration

### Phase 2: Score Engine (Week 3-4)  
1. **New Calculation Engine:**
   - Implement time-weighted algorithm
   - Anti-gaming detection functions
   - Incremental update system

2. **Background Sync Service:**
   - Periodic full recalculation (hourly)
   - Cross-protocol reputation import
   - Cache invalidation and warming

### Phase 3: Smart Assignment (Week 5-6)
1. **Assignment Logic Update:**
   - Reputation-based auto-assignment
   - Risk-adjusted thresholds for task value
   - Operator notification system

2. **Worker Onboarding:**
   - Identity minting at signup
   - External reputation detection and import
   - Progressive trust building

### Phase 4: Monitoring & Optimization (Week 7-8)
1. **Analytics Dashboard:**
   - Reputation distribution metrics
   - Gaming detection alerts
   - Assignment automation rates

2. **Performance Tuning:**
   - Cache optimization
   - Algorithm parameter adjustment
   - Load testing and scaling

## 4. Migration Strategy

### Data Migration
1. **Backup current reputation scores**
2. **Recalculate all scores** using new algorithm from historical ratings
3. **Identify discrepancies** and analyze impact
4. **Gradual rollout** with A/B testing (10% → 50% → 100% traffic)

### Rollback Plan
- Maintain parallel legacy system for 30 days
- Feature flag for instant rollback  
- Automated discrepancy monitoring with alerts

## 5. Success Metrics

### Primary KPIs
- **Reputation Accuracy:** < 5% deviation from on-chain truth
- **Gaming Resistance:** < 1% of ratings flagged as suspicious  
- **Assignment Automation:** > 70% of applications auto-assigned
- **Worker Onboarding:** 90% retention after first imported reputation task

### Performance Targets
- **Score Calculation:** < 100ms for incremental updates
- **Full Recalculation:** < 5 minutes for complete worker history
- **Cache Hit Rate:** > 95% for active workers

## 6. Security Considerations

### Attack Vectors
1. **Sybil Attacks:** Multiple fake identities → Mitigated by task value weighting
2. **Time Gaming:** Artificially accelerated rating cycles → Mitigated by time decay  
3. **Cross-Protocol Gaming:** Fake reputation import → Mitigated by trust weights
4. **Economic Attacks:** High-value fake tasks → Mitigated by agent credibility

### Monitoring
- Real-time anomaly detection for unusual reputation changes
- Pattern analysis for coordinated gaming attempts
- Cross-reference with blockchain analytics for related addresses

## 7. Future Extensions

### Possible Enhancements
1. **Machine Learning:** Predictive reputation scoring based on behavior patterns
2. **Specialized Scores:** Skill-specific reputation (design vs. development vs. research)
3. **Reputation Lending:** Established workers vouching for newcomers  
4. **Governance Integration:** Reputation-weighted voting on platform decisions

### ERC-8004 Evolution
- Support for reputation delegation
- Multi-dimensional reputation vectors
- Privacy-preserving reputation (zero-knowledge proofs)

## 8. Conclusion

This architecture positions Execution Market as a leader in decentralized reputation systems while providing immediate practical benefits:

- **Workers:** Portable reputation reduces onboarding friction  
- **Agents:** Better worker quality prediction and automatic assignment
- **Platform:** Gaming-resistant system that scales across protocols
- **Ecosystem:** Standard-setting implementation of ERC-8004

The proposed system maintains backward compatibility while fixing fundamental issues in the current architecture. Implementation risk is low due to the phased approach and comprehensive rollback strategy.

---

**References:**
- [ERC-8004: Decentralized Identity Registry](https://eips.ethereum.org/EIPS/eip-8004)
- [Current EM Reputation System Documentation](./REPUTATION-CURRENT.md)  
- [Execution Market Technical Specification](../SPEC.md)

**Implementation Tracking:**
- GitHub Issue: #TBD
- Technical Lead: Engineering Team  
- Estimated Delivery: 8 weeks from approval