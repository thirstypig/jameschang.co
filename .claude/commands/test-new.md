Write tests for a newly added or modified feature, then execute them and document.

The argument `$ARGUMENTS` is the feature name or area (e.g. `headshot-rotator`, `whoop-sync`, `hitlist-fetch`, `csp-headers`).

## Phase 1 — Understand what changed

1. Run `git diff main...HEAD --stat` and `git log main..HEAD --oneline` to see what this session touched.
2. For the target feature, read the primary source file(s) and list:
   - Pure Python functions (unit tests via pytest)
   - HTML structure / meta tags / attributes (E2E tests via the HTTP server test harness)
   - CSS behavior (E2E tests checking class presence, dark-mode parity)
   - JavaScript behavior (E2E tests checking script output / DOM state — limited to what headless fetching can validate)
   - Feed sync logic (unit tests for data transformation; E2E tests for marker presence)
3. Read `docs/test-plan.md` to see what coverage already exists for this area.

## Phase 2 — Write tests (pyramid order)

For each new piece of behavior, add in this order. Stop after each tier unless the feature truly warrants the next.

1. **Unit tests** — place in `tests/test_shared.py` or `tests/test_feeds.py` (or a new `tests/test_<feature>.py` if the scope justifies it).
   - For Python functions: test with real inputs, no mocking unless the function does I/O (network, file system). Use `monkeypatch` or `tmp_path` for I/O-dependent tests.
   - For feed builder functions: mock `fetch_json`/`fetch_text` to avoid network calls; test the HTML output structure.
   - Name tests after the behavior, not the function: `"returns_muted_when_score_is_none"` not `"test_recovery_color"`.
   - Cover: the happy path, 1–2 edge cases, and the bug that motivated the feature if applicable.

2. **E2E test** — add to `tests/test_site_e2e.py` (or a new `tests/test_<feature>_e2e.py` if the scope justifies it).
   - Uses the shared HTTP server fixture (`setup_module`/`teardown_module`).
   - Test what a browser would see: page loads, correct meta tags, correct attributes, images exist, links resolve.
   - Only add E2E tests when the behavior can't be tested at the unit level (e.g., CSP meta tag presence, aria-pressed attributes, cross-page consistency).

## Phase 3 — Execute

Run in this order, stopping on the first failure:

1. `python3 -c "compile(open('bin/<script>.py').read(), '<script>.py', 'exec')"` for any modified Python files (syntax check).
2. `python3 -m pytest tests/ -v` for the full suite.

If pytest is not installed globally, use the venv: `source /tmp/jc-test-venv/bin/activate && python -m pytest tests/ -v`.

## Phase 4 — Document

1. Update `docs/test-plan.md`:
   - Add the new test file(s) to the relevant table (Unit / E2E).
   - Update the test count in the summary.
   - If you wrote something that closes a gap, note it.
2. If the new tests expose a previously-silent bug, add a one-line entry under the feature's test class so future readers understand the motivation.

## Phase 5 — Report

Respond in this exact shape so the user can skim:

```
Feature: $ARGUMENTS
Unit tests added: N  (file paths)
E2E tests added:  N  (file paths, or "not needed — reason")
Full suite: X passing (was Y before)
test-plan.md: updated (lines changed)
```

## Phase 6 — Decide if commit-worthy

If tests are green and the feature is code-complete, say so and ask whether to commit. If something is half-baked, flag it — don't silently commit partial work.

## Guardrails

- **Don't write tests the feature will pass by definition.** A test like "calling foo() returns what foo() returns" catches nothing. Tests must encode behavior the *caller* depends on.
- **Don't mock what you're testing.** Mock the boundary (network, file system, time), not the unit under test.
- **If you can't name a concrete past or plausible regression the test prevents, consider not writing it.** Every test is code to maintain.
- **Flaky test = broken test.** If an E2E passes on retry but fails the first time, fix the root cause (cleanup, wait-for, isolation) — don't add retries.
