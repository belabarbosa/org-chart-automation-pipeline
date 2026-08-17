# Org Chart Automation Pipeline

Turn a spreadsheet into a live, interactive staffing chart. No manual box-dragging required.

**[Live Demo →](https://belabarbosa.github.io/org-chart-automation-pipeline/)**

## Why this exists

The team's org chart used to be a hand-built diagram developed with Power Point: every new hire, departure, or role change meant manually dragging boxes, recoloring cells, and rechecking a legend by hand. It didn't scale. A team of 20+ people under one lead simply didn't fit the format, and leadership had no fast way to answer basic staffing questions ("how many positions are remote right now?") without counting boxes themselves.

This project replaces that manual process with a pipeline: a structured CSV feeds a Python script that generates a single, self-contained, interactive HTML file.

## Key results

- **From manual layout to automated generation.** What used to be a 20 to 30 minute manual re-drag-and-recolor task is now a single script run. Adding, removing, or moving someone is a spreadsheet edit, not a diagram edit.
- **Full visibility at every level.** The chart auto-builds a Component to Division to Program to People hierarchy, with a live headcount split (core staff vs. subcontractor) rolled up and totaled at every level, not just per team but per division and per component too, with zero manual counting.
- **Answers in one click, not a search.** Leadership can click any category (Part-Time, Veteran, Remote, Subcontractor, Open Position) and instantly see exactly who's in it, highlighted across the entire org at once. A question that used to mean scanning a diagram by eye now takes one click.

## How it works

1. **Data lives in one CSV.** A flat table where each row is a person, with columns for their manager, team, division, component, company, and a handful of status flags (part-time, remote, veteran, open position, etc.).
2. **A Python script reads it and builds the page.** It groups people into teams, inherits shared fields (like a team's description) up the reporting chain so they only need to be entered once, and generates clean, styled HTML/CSS with no external dependencies.
3. **The output is one HTML file.** It opens directly in any browser, no server or database required. Click any legend item or group header to filter the whole chart to just that category.

## Tech stack

**Python** (data processing, HTML/CSS templating, manager-chain inheritance logic), **vanilla JavaScript** (client-side click-to-filter, zero backend), **CSV** as the single source of truth

## Notable engineering decisions

- **Layout redesign, not just a reskin.** The first version mirrored the original chart's branching tree structure. It broke down past about 10 people in one box, since auto-layout engines sprawl or tangle at that scale. Rebuilt around flat, card-style columns that handle 3 people or 30 equally well, with an automatic two-column view once a team gets too large for one screen.
- **Data entered once, inherited everywhere.** A team's description, division, and component only need to live on the Task Lead's row. Everyone reporting up to them inherits it automatically, instead of requiring the same text copy-pasted onto every row.

## Try it

Open `index.html` in any browser. No installation needed. To regenerate from your own data, edit `OrgChart_Data.csv` and run:

```bash
python generate_html_roster.py
```

## A note on process

I built this using AI as a coding collaborator. I directed the requirements, evaluated every design decision, and drove the pivots described above, including abandoning the first layout approach once it broke down at scale. I also caught and verified real bugs along the way (including a filtering bug in the group-click feature that I tested and confirmed fixed before shipping it). The AI wrote and iterated on code under my direction. The problem framing, architecture decisions, and quality checks were mine.
