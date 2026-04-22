---
status: done
priority: p1
issue_id: 034
tags: [code-review, seo]
dependencies: []
---

# Sitemap.xml missing /now/ page

## Problem
The /now/ page exists, is linked from primary nav on every page, and has a canonical URL — but sitemap.xml does not include it.

## Proposed Solutions
Add `<url><loc>https://jameschang.co/now/</loc><lastmod>2026-04-15</lastmod><priority>0.7</priority></url>` to sitemap.xml.

## Acceptance Criteria
- [ ] /now/ appears in sitemap.xml with correct URL and recent lastmod.
