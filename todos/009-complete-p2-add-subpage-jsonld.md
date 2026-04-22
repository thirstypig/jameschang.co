---
status: done
priority: p2
issue_id: 009
tags: [code-review, agent-native, seo, schema]
dependencies: []
---

# Add JSON-LD schema to 11 /work/ sub-pages and 3 case studies

## Problem Statement

Only `/index.html` ships structured data. The 11 /work/ replica pages and the 3 case-study articles on the homepage have zero schema. An LLM agent landing directly on `/work/fantastic-leagues/ai-insights/` (e.g., from a search result) has to parse 595 lines of HTML to understand what the page is about. A small JSON-LD block per page would let it answer "what's this page about" in one hop.

## Findings

From agent-native-reviewer agent (P2-A, P2-B, P3-G):
- 11 /work/ pages: no JSON-LD
- 3 case studies (`<article class="case">`): no Article schema
- Homepage has Person + WebSite in @graph — good baseline, but missing project ItemList and role WorkExperience

## Proposed Solutions

### Option A (Recommended): Minimal per-page schema
- Each /work/ page gets a `TechArticle` or `CreativeWork` schema with headline, description, dateModified, author
- Each case study gets an `Article` schema
- Homepage adds `ItemList` of current projects + `hasOccupation` array for roles
- **Effort:** Medium (~1 hour) • **Pros:** high ROI for AI crawl, no UX change

### Option B: Full schema.org compliance
- `SoftwareApplication` for each product, `BreadcrumbList` on every /work/ page, `ContactPoint` for email, `MemberOf` for board role
- **Effort:** Large (~3 hours) • **Pros:** maximum schema coverage • **Cons:** diminishing returns past Option A

### Option C: Status quo
- Site already passes agent-native tests 9/10
- **Effort:** None • **Cons:** leaves easy wins on the table

## Technical Details

Example for `/work/fantastic-leagues/ai-insights/index.html`:
```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "The Fantastic Leagues — AI Insights",
  "about": "League-context AI for fantasy baseball using Gemini 2.5 Flash and Claude Sonnet",
  "author": {"@type": "Person", "name": "James Chang", "url": "https://jameschang.co"},
  "dateModified": "2026-04-14",
  "inLanguage": "en-US",
  "isPartOf": {"@type": "WebSite", "url": "https://jameschang.co"}
}
</script>
```

Homepage additions:
- `ItemList` for 7 current projects (each as a `SoftwareApplication`)
- `hasOccupation: [WorkExperience, WorkExperience, ...]` on Person
- `memberOf: { Organization: "Chinese American Museum" }` on Person

Files:
- All 11 `/work/*/index.html` files
- `/work/index.html` (hub)
- `/index.html` (homepage expansions)

## Acceptance Criteria

- [ ] Every HTML page has at least one JSON-LD block
- [ ] Schemas validate at https://validator.schema.org/
- [ ] Google Rich Results Test passes for homepage and at least one /work/ page
- [ ] Chinese American Museum board role appears in Person schema
- [ ] Case studies are discoverable as Articles in structured data

## Work Log

_(blank)_

## Resources

- Agent-native review (P2-A, P2-B, P3-G)
- schema.org docs for Article, TechArticle, ItemList, SoftwareApplication, WorkExperience
