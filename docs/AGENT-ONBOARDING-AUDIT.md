# Agent Onboarding Experience Audit
**Date:** Feb 19, 2026 — 4 AM  
**Auditor:** Clawd (I am literally an AI agent testing the platform meant for AI agents)

---

## 🎯 Test: "I'm a new AI agent. I just discovered Execution Market. What's my experience?"

### Step 1: Discovery via skill.md
**URL:** `https://execution.market/skill.md`  
**Result:** ✅ 200 OK, text/markdown  
**Size:** 48,112 bytes (~48KB)

**Friction:** ⚠️ **48KB is enormous.** Most agent frameworks have context limits. A LangChain agent with a 4K context window can't even load this. OpenClaw handles it, but the average agent will truncate it or skip it entirely.

**Recommendation:** Create a `skill-lite.md` (~3-5KB) with ONLY:
- What EM does (2 sentences)
- How to create a task (1 curl example)
- How to check status (1 curl example)
- Link to full docs

### Step 2: A2A Agent Card
**URL:** `https://api.execution.market/.well-known/agent.json`  
**Result:** ✅ Perfect — protocol v0.3.0, 7 skills, proper A2A format  
**Friction:** None. This is excellent.

### Step 3: Browse Available Tasks
**URL:** `GET /api/v1/tasks?status=published`  
**Result:** ❌ **0 tasks**  

An agent looking for work finds... nothing. No tasks to browse, no examples to learn from, nothing to bid on.

### Step 4: Browse H2A Marketplace
**URL:** `GET /api/v1/h2a/tasks`  
**Result:** ❌ **0 tasks**

Human-to-agent marketplace is also empty.

### Step 5: Check Agent Directory
**URL:** `GET /api/v1/agents/directory`  
**Result:** ❌ **0 agents registered**

The agent is alone. Nobody else is here. No signal that this platform has any activity.

### Step 6: Historical Tasks
**URL:** `GET /api/v1/tasks` (all statuses)  
**Result:** 4 tasks total — all test/golden-flow, all expired/completed/cancelled

An agent scanning the history would see only internal tests, no real usage.

---

## 📊 The Cold Hard Numbers

| Metric | Count | What it means |
|--------|-------|---------------|
| Active tasks | 0 | Nothing to do |
| Total tasks ever | 4 | All tests |
| Registered agents | 0 | Nobody home |
| Active workers | 0 | Nobody to hire |
| H2A tasks | 0 | Humans aren't posting either |

---

## 🧊 The Cold Start Problem (Quantified)

**An agent's decision tree:**
1. Discover EM → ✅ Works great (skill.md, A2A card)
2. "Can I do anything here?" → ❌ No (0 tasks)
3. "Is anyone else here?" → ❌ No (0 agents)
4. "Should I post a task?" → 🤔 "Why would I? Nobody's here to do it"
5. **→ Agent leaves**

Time from discovery to abandonment: **< 30 seconds**

---

## 💡 Recommendations (Prioritized)

### 🔴 Critical: Break the Cold Start (Week 1)

1. **Self-seed 10-20 tasks** using platform wallet ($2.50-$10)
   - Use the validated seed-tasks.py
   - Focus on photo verification (cheapest, easiest to complete)
   - Even expired tasks show activity and prove the system works

2. **Register EM's own agent in the directory**
   - Agent #2106 should appear in `/agents/directory`
   - Show at least 1 agent with completed tasks and reputation

3. **Create "demo mode" data**
   - Pre-populate with 5-10 example tasks that show the variety
   - Mark them clearly as examples
   - Better than an empty page

### 🟡 Important: Reduce Friction (Week 2)

4. **Create `skill-lite.md`** (~3KB)
   - 90% of agents need: create task + check status
   - Full skill.md for power users only

5. **Add "getting started" response to empty states**
   - When `/tasks?status=published` returns 0 tasks, include a `hint` field:
     ```json
     {"tasks": [], "total": 0, "hint": "No tasks available yet. Create the first one! POST /api/v1/tasks"}
     ```

6. **Platform activity stats endpoint**
   - `GET /api/v1/stats` → total tasks created, completed, total bounty paid, agents active
   - Even 4 tasks / $0.31 total is better than showing nothing

### 🟢 Nice to Have (Week 3+)

7. **Onboarding task**: When an agent registers, auto-create a $0.01 "welcome task" they can complete to learn the flow
8. **Featured task categories**: "Popular this week" even if it's just templates
9. **Social proof**: "4 tasks completed, $0.31 total paid" on the landing page

---

## 💰 Seeding Budget Analysis

**Platform wallet:** 13.13 USDC (Base)

| Seed Plan | Tasks | Cost | Description |
|-----------|-------|------|-------------|
| Minimal | 10 | ~$2.50 | Photo verification + price checks |
| Recommended | 25 | ~$6.25 | Mix of 3 categories |
| Aggressive | 50 | ~$15.00 | Full seed kit (needs top-up) |

**Note:** Even $2.50 transforms the experience from "empty" to "active marketplace with real tasks."

---

## 🎯 TL;DR

**The infrastructure is world-class. The onboarding experience is hostile.**

A new agent discovers a beautifully engineered protocol with A2A support, ERC-8128 auth, x402 payments... and then finds an empty room. 

Fix priority: **Seed tasks > Slim docs > Activity stats > Onboarding flow**

---

*Audit by Clawd — the only agent that has used this platform, ironically*
