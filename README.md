# Org Chart Automation Pipeline

Turn a spreadsheet into a live, interactive staffing chart. No manual box-dragging required.

**[Live Demo →](https://belabarbosa.github.io/org-chart-automation-pipeline/)** (v2, current)
**[v1 (original card-column layout) →](https://belabarbosa.github.io/org-chart-automation-pipeline/v1.html)**

## Why this exists

The team's org chart used to be a hand-built diagram developed with Power Point: every new hire, departure, or role change meant manually dragging boxes, recoloring cells, and rechecking a legend by hand. It didn't scale. A team of 20+ people under one lead simply didn't fit the format, and leadership had no fast way to answer basic staffing questions ("how many positions are remote right now?") without counting boxes themselves.

This project replaces that manual process with a pipeline: a structured CSV feeds a Python script that generates a single, self-contained, interactive HTML file.

## Two versions

**v1: Card-column layout.** The first working version: each office/team is a column of stacked people-cards, grouped under Component → Division headers, with click-to-filter by category (Remote, Veteran, Open Position, etc). Solved the original scaling problem, fitting a 3-person team and a 30-person team into the same format.

**v2: Executive hierarchy tree (current).** Rebuilt against a set of executive stakeholder recommendations focused on one question: *can a leader understand the org's structure and accountability in ten seconds?* v2 replaces the column layout with a true reporting tree:

- **Real reporting lines.** The chart is built directly from each person's manager, not a grouping label, so parent → child connector lines show actual accountability.
- **Reporting vs. functional support, visually separated.** Solid lines show formal reporting. Subject-matter experts who support the whole program without reporting into it are pulled into a separate panel connected by a dashed line.
- **Span of control on every lead's card.** "11 direct reports" surfaces org-design questions (too wide? too narrow?) without a separate report.
- **Distinct tiers by badge and weight, not heavy color.** Executive, Department Lead, Program Support, and Subject Matter Expert each get their own badge, so scanning the chart tells you who's who at a glance.
- **Compact by default.** Only the executive layer and the 9 department leads are visible on load. Click a lead to expand their team into a compact grid, one that adds columns as the team grows, instead of stretching into a single wide row or forcing a scrollbar.

## Key results

- **From manual layout to automated generation.** What used to be a 20 to 30 minute manual re-drag-and-recolor task is now a single script run. Adding, removing, or moving someone is a spreadsheet edit, not a diagram edit.
- **Full visibility at every level.** v1 auto-builds a Component → Division → Program → People hierarchy with headcount roll-ups at every level. v2 makes the reporting structure itself the primary view, with span-of-control called out on every lead.
- **Answers in one click, not a search.** v1: click any legend category to instantly highlight everyone in it. v2: click any department to expand its team; formal reporting vs. cross-functional support is visually distinct without needing to ask.

## How it works

1. **Data lives in one CSV.** A flat table where each row is a person, with columns for their manager, team, division, component, company, and a handful of status flags (part-time, remote, veteran, open position, etc.).
2. **A Python script reads it and builds the page.** v1 groups people into office columns and inherits shared fields up the reporting chain. v2 walks the actual manager-ID chain to build a real hierarchy tree, classifies each person's tier from their title and tree depth, and renders solid reporting connectors plus a dashed panel for cross-functional SMEs.
3. **The output is one HTML file per version.** Both open directly in any browser, no server or database required.

## Tech stack

**Python** (data processing, HTML/CSS templating, hierarchy-tree construction), **vanilla JavaScript** (client-side filtering and expand/collapse, zero backend), **CSV** as the single source of truth

## Notable engineering decisions

- **v1 → v2 was a layout rebuild, not a reskin.** The column layout solved "does it scale," but an executive audience needed "can I see who reports to whom in ten seconds," a different question that a card grid can't answer no matter how it's filtered. That called for a real tree, not a variation on the column idea.
- **Data entered once, inherited everywhere (v1).** A team's description, division, and component only need to live on the Task Lead's row; everyone reporting up to them inherits it automatically.
- **Team size scales the grid, not a scrollbar (v2).** A department's expanded team uses more grid columns as headcount grows, instead of a fixed 2-column list with a scrollbar, keeping a 12-person team readable without extra clicks.
- **Title-based tier classification, not tree depth alone (v2).** Two roles can sit at the same depth in the tree (a Department Lead and a Financial Analyst both report to the Deputy PM) but mean very different things organizationally. Classifying by title first, tree position second, keeps those roles visually distinct instead of both reading as "manager."

## Try it

Open `index.html` (v2) or `v1.html` in any browser. No installation needed. To regenerate from your own data, edit `OrgChart_Data.csv` and run:

```bash
python generate_v2.py   # rebuilds index.html (v2, live demo)
python generate_v1.py   # rebuilds v1.html (original layout)
```

## A note on process

I built this using AI as a coding collaborator. I directed the requirements, evaluated every design decision, and drove the pivots described above, including the v1 → v2 rebuild once I had executive stakeholder feedback that called for a different kind of chart entirely. I also caught and verified real bugs along the way (including a filtering bug in v1's group-click feature that I tested and confirmed fixed before shipping it). The AI wrote and iterated on code under my direction. The problem framing, architecture decisions, and quality checks were mine.
