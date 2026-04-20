Audit the test infrastructure against the checklist below and recommend the single highest-leverage next investment.

This is a **decision-support prompt**, not an install prompt. It produces a status table and a recommendation. The user decides whether to install anything.

## Scan

Detect the presence of each item by running specific checks. Do not speculate — if a check is ambiguous, mark it "unclear" and explain why in one line.

1. **Pre-commit hook**
   - `cat .claude/settings.json 2>/dev/null` — look for a `PreToolUse` hook matching `Bash` + `git commit`.
   - `ls .husky/pre-commit 2>/dev/null` — Husky-style git hook.
   - `ls .git/hooks/pre-commit 2>/dev/null` — native git hook (not just `.sample`).
   - Present if any of the above run pytest or syntax checks.

2. **CI pipeline**
   - `ls .github/workflows/*.yml 2>/dev/null`. Read each one; confirm it actually runs `pytest` or equivalent.
   - Check: does the CI run on push to main? Does it run both unit and E2E tests?

3. **Test documentation**
   - `ls docs/test-plan.md 2>/dev/null`. Read it; check that test counts match reality.
   - Run `python3 -m pytest tests/ --collect-only -q 2>/dev/null | tail -1` to get actual count.

4. **E2E coverage**
   - Count how many HTML pages exist vs. how many are tested by E2E.
   - Check: are feed markers validated? CSP? aria attributes? image references?

5. **OpenSSL parity check**
   - Does a test exist that validates all `openssl enc` calls use the same `-iter` value?

6. **Dark mode parity check**
   - Does a test exist that validates `@media (prefers-color-scheme: dark)` and `[data-theme="dark"]` selector balance?

7. **Visual regression**
   - `ls /tmp/jc-shots/ 2>/dev/null | wc -l` — screenshots from manual checks.
   - Any automated screenshot comparison? (Likely absent.)

8. **Feed sync tests**
   - Do unit tests cover the pure functions in feed sync scripts?
   - Are `fetch_json`/`fetch_text` mocked in any test, or are all feed tests pure-function only?

## Report

Output exactly this shape:

```
Test infrastructure audit:

✓ CI pipeline         — <one-line evidence>
✓ Test documentation  — <one-line evidence>
✗ Pre-commit hook     — <one-line evidence>
...

Recommended next: <item>.
  Why:      <one-sentence impact — ideally cites a real bug or gap this would prevent>.
  Cost:     <estimate — "1 session" / "10 min config" / "1 week incremental">.
  Trade-off: <what it complicates or what you lose>.
  Next step: <single sentence — what the user would say to start it>.
```

## Ranking rules (how to pick "Recommended next")

Prefer items that:

1. **Prevent a bug class we've actually shipped.** A pre-commit hook recommendation that cites the headshot-fallback CI failure beats an abstract "coverage is good" pitch.
2. **Have the highest bug-prevention-per-hour ratio.** Pre-commit hook: 10 min to install, prevents most "forgot to run tests" commits — excellent ratio. Visual regression: hours to wire + ongoing screenshot maintenance — only recommend when CSS drift has bitten you.
3. **Unblock later items.** CI pipeline should come before visual regression, because those are most valuable running on every push, not just locally.

When the user hasn't installed anything, the typical order is:
**pre-commit → CI → feed sync mocking → visual regression → flaky tracking**.

## Guardrails

- **Don't install anything.** This prompt only reads and recommends. If the user says "do it" after seeing the report, run the appropriate install flow as a separate step.
- **Don't over-recommend.** One item at a time. A list of seven is a to-do, not a decision.
- **Cite concrete evidence.** "No pre-commit hook" is weak. "No pre-commit hook; the headshot-fallback images passed locally but failed CI because they were never committed" is strong.
- **If everything is installed:** congratulate briefly and recommend running the existing tooling (coverage report, adding tests for untested functions) rather than inventing new items.
