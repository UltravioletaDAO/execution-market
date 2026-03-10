# Contributing to Execution Market

Thank you for your interest in contributing to **Execution Market** — the Universal Execution Layer where AI agents hire humans to get things done. Whether you're fixing a bug, adding a feature, or improving docs, your help is welcome.

---

## Prerequisites

Make sure you have the following installed before getting started:

| Tool       | Version  |
|------------|----------|
| Python     | 3.10+    |
| Node.js    | 18+      |
| Docker     | Latest   |
| git        | Latest   |

---

## Local Development Setup

### Quick Start (Recommended)

The fastest way to spin up the full stack locally:

```bash
docker compose up -d
```

This starts the backend, dashboard, database, and all supporting services.

### Backend Only

```bash
cd mcp_server
pip install -e .
python server.py
```

### Dashboard Only

```bash
cd dashboard
npm install
npm run dev
```

### Environment Variables

Copy the example env file and fill in your local values:

```bash
cp .env.example .env.local
```

Edit `.env.local` with your Supabase credentials, API keys, and any other required configuration.

---

## Running Tests

### Backend (pytest)

```bash
cd mcp_server
pytest
```

The backend has **950+ tests** organized with pytest markers. You can run specific subsets:

```bash
pytest -m core          # Core functionality
pytest -m payments      # Payment flows
pytest -m erc8004       # ERC-8004 standard
pytest -m security      # Security tests
pytest -m infrastructure # Infrastructure tests
```

### Dashboard (Vitest)

```bash
cd dashboard
npm test
```

### End-to-End (Playwright)

```bash
cd e2e
npm run test
```

---

## Code Style

### Python

We use [Ruff](https://docs.astral.sh/ruff/) for formatting and linting:

```bash
cd mcp_server
ruff format .
ruff check .
```

### TypeScript

We use ESLint for the dashboard:

```bash
cd dashboard
npm run lint
```

Please run the appropriate linter before submitting a pull request. CI will catch any issues, but it saves everyone time if you check locally first.

---

## Pull Request Process

1. **Fork** the repository and clone your fork locally.
2. **Create a feature branch** from `main` (see branch naming below).
3. **Make your changes** with clear, focused commits.
4. **Use conventional commits** for your commit messages:
   - `feat:` — A new feature
   - `fix:` — A bug fix
   - `docs:` — Documentation changes
   - `refactor:` — Code restructuring without behavior changes
   - `test:` — Adding or updating tests
5. **Ensure CI passes** — all tests and linting must be green.
6. **Link related issues** in your PR description (e.g., `Closes #42`).
7. **Request a review** and be responsive to feedback.

---

## Branch Naming

Use a prefix that matches the type of work:

| Prefix       | Use for                        |
|--------------|--------------------------------|
| `feat/`      | New features                   |
| `fix/`       | Bug fixes                      |
| `docs/`      | Documentation updates          |
| `refactor/`  | Code refactoring               |
| `test/`      | Test additions or improvements |

Examples: `feat/agent-bidding`, `fix/payment-timeout`, `docs/api-reference`.

---

## Architecture Overview

For a deeper understanding of the system architecture, refer to these documents in the repository root:

- **CLAUDE.md** — AI-facing project context and conventions
- **PLAN.md** — Development roadmap and milestones
- **SPEC.md** — Technical specification and system design

These are the best starting points if you want to understand how the pieces fit together before diving into code.

---

## Good First Issues

New here? Look for issues labeled **"good first issue"** on the GitHub Issues page. These are scoped, well-documented tasks designed to help you get familiar with the codebase without needing deep context.

---

## Community

Execution Market is a **bilingual project**. Both **English** and **Spanish** are welcome in:

- Pull request descriptions and comments
- Issue reports and discussions
- Code review feedback
- Documentation contributions

Use whichever language you're most comfortable with. We value clear communication over any particular language.

---

## Questions?

If something is unclear or you get stuck, open an issue or start a discussion. We'd rather help you contribute than have you struggle in silence.

Happy building.
