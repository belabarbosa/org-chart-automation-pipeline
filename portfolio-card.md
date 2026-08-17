# Portfolio Card

## Title
Org Chart Automation Pipeline

## One-liner (for a card/tile view)
Replaced a manually-dragged-and-dropped org chart with an automated pipeline, then rebuilt it a second time into a true hierarchy tree once executive stakeholders needed a different question answered: who reports to whom, in ten seconds.

## Short description (2 to 3 sentences, for a card body)
The team's org chart was a hand-edited diagram in a .ppt file. Every staffing change meant manually dragging boxes and recoloring cells. I rebuilt it as a pipeline: a structured spreadsheet feeds a Python script that generates a live, interactive chart automatically. The first version (v1) solved scale with a filterable card-column layout; after gathering executive stakeholder recommendations, I rebuilt it again (v2) into a real reporting-hierarchy tree with span-of-control, tiered role badges, and solid-vs-dashed lines separating formal reporting from cross-functional support.

## Key results (bullets, for expanded view)
- Eliminated manual chart editing. Staffing changes are now a spreadsheet edit, not a redraw
- v1: automatic headcount roll-ups at every level of the org, with zero manual counting; one-click category filtering
- v2: rebuilt around real reporting lines pulled from each person's manager, not a grouping label
- v2: span-of-control ("11 direct reports") surfaced directly on every lead's card
- v2: formal reporting vs. cross-functional support made visually distinct (solid line vs. dashed panel)
- v2: expanded team views scale their grid to team size instead of scrolling
- Both versions scale from a 2-person team to a 20+ person team without the layout breaking down

## Tech stack tags
`Python` `JavaScript` `HTML/CSS` `Data Automation` `CSV/ETL` `Information Architecture`

## Suggested tile category
Data Automation / Internal Tooling

## Note on AI-assisted development
Built using Claude as a coding collaborator, under my direction. I set the requirements, drove the design pivots (including the full v1 → v2 rebuild), and tested and verified the results before shipping.
