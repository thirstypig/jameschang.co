---
status: done
priority: p3
issue_id: 060
tags: [code-review, quality]
dependencies: []
---

# Bare `except Exception` in Spotify state load and podcast aging

## Problem
`bin/update-spotify.py:82` has `except Exception:` around state-file load, which swallows OSError + JSONDecodeError but also bugs like AttributeError or TypeError from refactoring. Line 240 has another `except Exception:` around podcast-age arithmetic. Too broad.

## Proposed Solutions
Narrow to `except (OSError, json.JSONDecodeError):` for state load, and `except (KeyError, ValueError, TypeError):` for podcast aging.

## Acceptance Criteria
- [ ] No bare `except Exception` in update-spotify.py.
