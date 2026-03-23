# Deployment Checklist - March 23, 2026 Bug Fixes

## Pre-Deployment Verification

**Status:** ✅ All fixes committed to main branch  
**Branch:** main  
**Last Commit:** [Latest commit hash]  
**Ready for Production:** Yes  

## Required Deployments

### 1. Backend (API Server) - HIGH PRIORITY

**Container:** em-production-mcp-server  
**ECS Cluster:** em-production-cluster  
**Region:** us-east-2  

**Required Actions:**
1. **Docker Build & Push:**
   ```bash
   cd ~/clawd/projects/execution-market
   bash scripts/deploy-manual.sh
   ```

2. **ECS Force Redeploy:**
   ```bash
   aws ecs update-service \
     --cluster em-production-cluster \
     --service em-production-mcp-server \
     --force-new-deployment \
     --region us-east-2
   ```

3. **Wait for Stabilization:**
   ```bash
   aws ecs wait services-stable \
     --cluster em-production-cluster \
     --services em-production-mcp-server \
     --region us-east-2
   ```

4. **Health Check:**
   ```bash
   curl -s https://api.execution.market/health
   # Expected: {"status": "ok", "timestamp": "..."}
   ```

**Critical Changes:**
- Multi-wallet support (`_resolve_payer_wallet`)
- Reputation score clamping (0-100)
- WS-2b side effect in post-approval flow
- Cache-aware task status updates

### 2. Environment Variables - CRITICAL

**Service:** em-production-mcp-server  
**Required:** `AGENT_WALLET_PRIVATE_KEY`  

**Action Required:**
```bash
# Add to ECS task definition environment variables:
AGENT_WALLET_PRIVATE_KEY=[Agent wallet private key - NOT platform wallet]
```

**⚠️ CRITICAL:** This must be the agent's dedicated wallet, NOT the platform wallet currently in `WALLET_PRIVATE_KEY`.

**Verification:**
- Check escrow transactions use correct wallet
- BaseScan should show agent wallet as payer, not platform wallet

### 3. Database Migration - REQUIRED

**Database:** Supabase em-production  
**Migration:** 072 - Reputation Score Constraints  

**SQL to Execute:**
```sql
-- Migration 072: Re-add reputation score constraints
ALTER TABLE executors 
ADD CONSTRAINT reputation_score_bounds 
CHECK (reputation_score >= 0 AND reputation_score <= 100);

-- Clamp existing invalid scores
UPDATE executors 
SET reputation_score = 100 
WHERE reputation_score > 100;

UPDATE executors 
SET reputation_score = 0 
WHERE reputation_score < 0;
```

**Verification:**
```sql
SELECT id, wallet_address, reputation_score 
FROM executors 
WHERE reputation_score > 100 OR reputation_score < 0;
-- Should return 0 rows
```

### 4. Frontend (Dashboard) - MEDIUM PRIORITY

**Bucket:** em-production-dashboard  
**CloudFront Distribution:** E2SD27QZ0GK40U  

**Build & Deploy:**
```bash
cd ~/clawd/projects/execution-market/dashboard
npm run build

# Upload main assets
aws s3 sync dist/ s3://em-production-dashboard/ --delete \
  --cache-control 'public, max-age=31536000, immutable' \
  --exclude '*.html' --exclude '*.json' --exclude '*.md'

# Upload index.html with short cache
aws s3 cp dist/index.html s3://em-production-dashboard/index.html \
  --cache-control 'public, max-age=60' --content-type 'text/html'

# Invalidate CloudFront
aws cloudfront create-invalidation \
  --distribution-id E2SD27QZ0GK40U \
  --paths '/index.html' '/assets/*'
```

**Critical Changes:**
- 30-second React Query staleTime
- refetchOnWindowFocus enabled
- Submit Evidence button state management
- Reputation score display clamping

### 5. Skill Files Update - LOW PRIORITY

**Files to Deploy:**
- SKILL.md (v3.9.0 with auto-assignment logic)
- HEARTBEAT.md (updated cron messaging)

**Deploy Command:**
```bash
cd ~/clawd/projects/execution-market/dashboard

# Ensure skill files are in public directory
cp ../path/to/SKILL.md public/skill.md
cp ../path/to/HEARTBEAT.md public/heartbeat.md

# Deploy with frontend (included in step 4)
```

**Verification:**
```bash
curl -sI https://execution.market/skill.md
# Should return: content-type: text/markdown
```

## Feature Flag Verification

**Required Checks:**
```bash
# Check current feature flag status in production
curl -s -H "Authorization: Bearer [API_KEY]" \
  "https://api.execution.market/api/v1/admin/feature-flags" | jq '.'
```

**Critical Flags:**
- `erc8004_auto_register_worker` - Should be ENABLED for WS-1 fix investigation
- `erc8004_auto_rate_agent` - Should be ENABLED for WS-2b functionality  
- `erc8004_agent_rates_worker` - Should be ENABLED for bidirectional ratings

**If Disabled:**
```bash
# Enable via admin API or Supabase direct update
UPDATE feature_flags SET enabled = true 
WHERE flag_name IN (
  'erc8004_auto_register_worker',
  'erc8004_auto_rate_agent', 
  'erc8004_agent_rates_worker'
);
```

## Post-Deployment Verification

### 1. Health Checks
```bash
# API Health
curl -s https://api.execution.market/health

# ERC-8128 Auth
curl -s https://api.execution.market/api/v1/auth/nonce

# Frontend Load
curl -sI https://execution.market/

# Skill File Access
curl -sI https://execution.market/skill.md
```

### 2. Functional Tests

**Test 1: Multi-Wallet Escrow**
- Create test task with agent wallet
- Verify BaseScan shows agent wallet as escrow payer
- Expected: Agent wallet charged, not platform wallet

**Test 2: Reputation Bounds**
- Check existing profiles with high reputation
- Expected: All scores display 0-100, no 120+ scores

**Test 3: Real-Time UI Updates**
- Submit evidence on task
- Expected: Button disappears immediately, status updates

**Test 4: WS-2b Rating Flow**
- Approve task with agent account
- Check ERC-8004 registry for agent→worker rating
- Expected: Bidirectional ratings recorded

### 3. Monitoring Setup

**Alerts to Configure:**
- Wallet payment monitoring (wrong wallet usage)
- Reputation score constraint violations  
- Cache performance degradation (>30s stale data)
- WS-1/WS-2b flow completion rates

## Rollback Plan

**If Issues Detected:**

1. **Backend Rollback:**
   ```bash
   # Revert to previous ECS task definition
   aws ecs update-service \
     --cluster em-production-cluster \
     --service em-production-mcp-server \
     --task-definition em-production-mcp-server:[PREVIOUS_REVISION]
   ```

2. **Database Rollback:**
   ```sql
   -- Remove constraint if causing issues
   ALTER TABLE executors DROP CONSTRAINT reputation_score_bounds;
   ```

3. **Frontend Rollback:**
   ```bash
   # Redeploy previous frontend version
   aws s3 sync [BACKUP_DIR] s3://em-production-dashboard/
   aws cloudfront create-invalidation --distribution-id E2SD27QZ0GK40U --paths '/*'
   ```

4. **Environment Variable Rollback:**
   - Remove `AGENT_WALLET_PRIVATE_KEY` if causing startup issues
   - System will fall back to `WALLET_PRIVATE_KEY` (platform wallet)

## Timeline Estimation

**Total Deployment Time: ~45 minutes**

1. **Backend Deploy:** 15 minutes (build + ECS update + stabilization)
2. **Database Migration:** 2 minutes  
3. **Environment Variables:** 5 minutes + service restart
4. **Frontend Deploy:** 10 minutes (build + S3 + CloudFront)
5. **Verification & Testing:** 15 minutes

**Recommended Window:** Weekday morning (low traffic)

## Success Criteria

**Deployment Successful When:**
- ✅ All health checks pass
- ✅ Escrow payments use agent wallet (verified via BaseScan)
- ✅ Reputation scores bounded 0-100
- ✅ Dashboard shows real-time updates (30s max delay)
- ✅ Submit Evidence buttons behave correctly  
- ✅ WS-2b ratings appear in ERC-8004 registry
- ✅ No error rate increase in monitoring
- ✅ Feature flags operational

## Dependencies

**External Services:**
- AWS ECS/ECR (backend deployment)
- Supabase (database migration)
- AWS S3/CloudFront (frontend deployment)  
- Base blockchain (wallet verification)
- ERC-8004 registries (reputation verification)

**Team Coordination:**
- DevOps: AWS deployments and monitoring
- Engineering: Verification testing and rollback support
- Operations: User communication if downtime needed

---

**Deployment Lead:** Engineering Team  
**Approval Required:** Tech Lead + DevOps  
**Emergency Contact:** [Team contact information]  

**Status Tracking:**
- [ ] Backend deployed and verified
- [ ] Database migration completed  
- [ ] Environment variables updated
- [ ] Frontend deployed and verified
- [ ] Feature flags verified
- [ ] Post-deployment testing completed
- [ ] Monitoring alerts configured