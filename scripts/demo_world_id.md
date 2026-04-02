# World ID 4.0 Demo -- Execution Market

## Setup (one-time)

1. Go to https://developer.world.org
2. Create an app, get App ID and RP ID
3. Generate a signing key (secp256k1 private key)
4. Set env vars in .env.local:
   ```
   WORLD_ID_APP_ID=app_...
   WORLD_ID_RP_ID=...
   WORLD_ID_SIGNING_KEY=...  (hex, no 0x)
   ```

## Demo Flow (3 minutes)

### 1. Show the constraint is real
- Open https://execution.market
- Log in as a worker
- Browse tasks -- note task with bounty >= $5.00
- Click "Apply" on the high-value task
- **BLOCKED**: "World ID Orb verification required"

### 2. Verify with World ID
- Go to Profile page
- Click "Verify with World ID"
- Scan QR code with World App (or use Simulator: simulator.worldcoin.org)
- IDKit widget opens, verification completes
- Profile now shows World ID badge (filled circle = Orb verified)

### 3. Apply again
- Return to the high-value task
- Click "Apply" -- **SUCCESS**: application submitted
- Note the World ID badge on your profile preview in the application modal

### 4. Anti-sybil demo
- Log out, create a new worker account with different wallet
- Try to verify with the same World ID
- **BLOCKED**: "This World ID identity is already linked to another account"
- 1 human = 1 worker account, enforced by nullifier uniqueness

### 5. Show the backend verification
- Open https://api.execution.market/docs (Swagger)
- `GET /api/v1/world-id/rp-signature` -- shows RP signing (v4 spec)
- `POST /api/v1/world-id/verify` -- shows Cloud API proof validation
- Check Supabase: `world_id_verifications` table has the proof stored

### 6. ERC-8004 link (bonus)
- Worker's ERC-8004 on-chain identity now has `world_id_verified: orb` metadata
- This is composable -- other protocols can check this attribute on-chain
