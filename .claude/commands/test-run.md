Run the full test suite (syntax check → unit → E2E) and report cleanly.

## Steps

Run these in sequence. Stop at the first failure — don't mask errors by continuing.

1. **Syntax check (all Python scripts):**
   - `python3 -c "compile(open(f).read(), f, 'exec')"` for each file in `bin/*.py`.
   - Report: pass/fail per file.

2. **Unit + E2E (full pytest suite):**
   - `python3 -m pytest tests/ -v`
   - If pytest is not installed globally, use: `source /tmp/jc-test-venv/bin/activate && python -m pytest tests/ -v`
   - Report: `<unit-passed> unit + <e2e-passed> E2E, <total> total`

## Report format

Keep it terse. Aim for this shape:

```
✓ syntax    3 scripts  (0.1s)
✓ 55 unit + 16 E2E     (1.2s)
Total: 71 tests green
```

On failure:
```
✗ <where> — <file:line>: <assertion>
<next steps — one sentence>
```

## Arguments

- `/test-run` — full suite. Use before commits.
- `/test-run <feature>` — run only tests matching the feature name: `python3 -m pytest tests/ -v -k <feature>`. Use during iteration on one feature.
- `/test-run e2e` — run only E2E tests: `python3 -m pytest tests/test_site_e2e.py -v`. Use to validate HTML/meta/CSP changes.

## Guardrails

- **Don't skip on "known flakes."** Flakes are bugs — report them honestly.
- **Don't retry automatically.** If the first run fails, show the failure. Let the user decide whether to retry.
- **Never suppress output to make things look clean.** Tail + summarize is fine; silently swallowing errors is not.
