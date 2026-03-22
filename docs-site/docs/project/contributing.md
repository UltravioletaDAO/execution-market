# Contributing

Execution Market is open source (MIT) and welcomes contributions from the community.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/execution-market.git`
3. Set up local development: see [Local Development](/guides/local-dev)
4. Create a branch: `git checkout -b feature/your-feature-name`
5. Make your changes
6. Run tests: `pytest` (backend) + `npm run test` (dashboard)
7. Submit a pull request

## What to Contribute

### Good First Issues

Look for issues labeled `good-first-issue` on GitHub. These are:
- Documentation improvements
- Bug fixes with clear reproduction steps
- New task categories or evidence types
- SDK method additions
- Dashboard UI improvements

### High-Impact Areas

- **New payment networks**: Use the `add-network` skill checklist
- **New language support**: i18n translations (currently EN/ES)
- **Mobile app features**: Expo React Native
- **Testing**: More E2E tests with Playwright
- **Documentation**: New guides and examples

## Development Workflow

### Branch Naming

```
feature/short-description     # New features
fix/bug-description            # Bug fixes
docs/what-you-documented       # Documentation
test/what-you-tested           # Test additions
refactor/what-you-refactored   # Refactoring
```

### Commit Messages

Follow [Conventional Commits](https://conventionalcommits.org/):

```
feat(payments): add Scroll network support
fix(dashboard): resolve task card overflow on mobile
docs(api): add webhooks authentication example
test(erc8004): add reputation volatility test cases
```

### Pull Request Requirements

- [ ] Tests pass (`pytest` + `npm run test`)
- [ ] No ruff/ESLint warnings
- [ ] Documentation updated if needed
- [ ] PR description explains the change and why

## Code Style

### Python

```bash
# Auto-format
ruff format .

# Lint
ruff check .

# Type check
mypy mcp_server/
```

### TypeScript

```bash
# Lint
cd dashboard && npm run lint

# Type check
npx tsc --noEmit
```

## Testing Requirements

All new features must have tests:

- **Backend**: pytest test in appropriate `tests/` file with the right marker
- **Dashboard**: Vitest unit test in `src/test/`
- **E2E**: Playwright test in `e2e/` for new user flows

Minimum coverage expectation: new code should be covered by tests.

## Security Contributions

For security vulnerabilities, **do NOT open a public issue**. See [SECURITY.md](/project/security) for the responsible disclosure process.

## Code of Conduct

Execution Market follows a [Code of Conduct](https://github.com/UltravioletaDAO/execution-market/blob/main/CODE_OF_CONDUCT.md). We are committed to a welcoming and inclusive community.

Key points:
- Be respectful and inclusive
- Focus on constructive feedback
- No harassment, discrimination, or personal attacks

## License

Contributions are accepted under the **MIT License**. By submitting a PR, you agree to license your contribution under MIT.

## Questions?

- Open a GitHub Discussion for general questions
- Open a GitHub Issue for bug reports and feature requests
- For security issues, see [SECURITY.md](/project/security)
