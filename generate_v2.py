"""
Generate a true hierarchy-tree org chart (Phase 1: structure) from
OrgChart_Data.csv, addressing the executive recommendations:

  1. Reporting lines unmistakable      -> real parent/child tree, not columns
  2. Reporting vs. project/functional  -> solid tree connectors vs. dashed
                                           panel for cross-functional SMEs
  3. Managers visually distinct        -> level badges (size/weight, not color)
  4. Span of control                   -> direct-report count on every card
  5. Compact executive hierarchy       -> Team level collapsed by default
  9. (partial) collapse/expand         -> click a department to open/close
 10. Three levels                      -> Executive / Department / Team

Search, full focus-mode, and org-level filters (location/employment type)
are Phase 2 — this pass is the structural rebuild only.

Reads:  OrgChart_Data.csv
Writes: index.html (the live demo)
"""

import csv
import html
import json
from collections import defaultdict
from datetime import datetime

SOURCE_CSV = "OrgChart_Data.csv"
OUTPUT_HTML = "index.html"  # v2: hierarchy tree, this is the live demo

_NUMERIC_FIELDS = {"ID", "ManagerID", "SortOrder"}
SME_MANAGER_ID = 999
PRIME_LABEL = "PRIME CONTRACTOR"


def load_rows(path):
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for raw in csv.DictReader(f):
            if not raw.get("ID"):
                continue
            cleaned = {}
            for k, v in raw.items():
                if v is not None:
                    v = v.strip()
                if v == "":
                    v = None
                if k in _NUMERIC_FIELDS and v is not None:
                    try:
                        v = int(float(v))
                    except ValueError:
                        pass
                cleaned[k] = v
            rows.append(cleaned)
    return rows


def norm(s):
    return str(s).strip().upper() if s is not None else ""


def is_prime(company):
    return norm(company) == PRIME_LABEL or norm(company) == ""


def yn(v):
    if v is None:
        return False
    return str(v).strip().upper() in ("1", "Y", "YES", "TRUE")


def esc(s):
    return html.escape(str(s)) if s is not None else ""


def is_sme(row):
    try:
        return int(row.get("ManagerID")) == SME_MANAGER_ID
    except (TypeError, ValueError):
        return False


# ---------------------------------------------------------------------------
# Level classification (recommendation #3 + #10).
# Level is derived from BOTH tree depth and title, so a title like
# "Senior Analyst" reads as a senior IC everywhere it appears, while depth
# still separates Executives / Department leads / Team members structurally.
# ---------------------------------------------------------------------------

def classify_level(row, depth, is_task_lead):
    title = norm(row.get("Title"))
    if depth <= 1:
        return "executive"
    if is_task_lead:
        return "manager"
    if depth == 2:
        # Reports directly to the executive but doesn't lead a department
        # (e.g. Financial Analyst, Technical Writer) — program support staff,
        # distinct from both department leads and team members.
        return "support"
    if "SME" in title:
        return "sme"
    if "SENIOR" in title:
        return "senior-ic"
    return "ic"


LEVEL_LABEL = {
    "executive": "Executive",
    "manager": "Department Lead",
    "senior-ic": "Senior",
    "ic": "",
    "sme": "SME",
    "support": "Program Support",
}


def build(rows):
    id_to_row = {r["ID"]: r for r in rows if r.get("ID") is not None}
    org_rows = [r for r in rows if not is_sme(r)]
    sme_rows = [r for r in rows if is_sme(r)]

    children = defaultdict(list)
    roots = []
    for r in org_rows:
        mgr = r.get("ManagerID")
        if mgr is None or mgr not in id_to_row:
            roots.append(r)
        else:
            children[mgr].append(r)
    for k in children:
        children[k].sort(key=lambda r: (r.get("SortOrder") or 0))
    roots.sort(key=lambda r: (r.get("SortOrder") or 0))

    # direct-report counts (real reports only, SMEs excluded — they have no
    # true manager, so they don't count toward anyone's span of control)
    direct_report_count = {rid: len(kids) for rid, kids in children.items()}

    # total headcount under each node (for the department-level count badge)
    def subtree_total(rid):
        total = 0
        for c in children.get(rid, []):
            total += 1 + subtree_total(c["ID"])
        return total

    return id_to_row, children, roots, direct_report_count, subtree_total, sme_rows


def person_card_html(row, depth, is_task_lead, direct_report_count, subtree_total_fn, dept_id=None):
    level = classify_level(row, depth, is_task_lead)
    rid = row["ID"]
    reports = direct_report_count.get(rid, 0)
    company = row.get("Company")
    contractor = not is_prime(company)

    badges = []
    if LEVEL_LABEL.get(level):
        badges.append(f'<span class="level-badge level-{level}">{esc(LEVEL_LABEL[level])}</span>')
    if contractor:
        badges.append(f'<span class="level-badge level-contractor">{esc(company)}</span>')

    tags = []
    if yn(row.get("IsPartTime")):
        tags.append('<span class="mini-tag">PT</span>')
    if yn(row.get("IsRemote")):
        tags.append('<span class="mini-tag remote">Remote</span>')
    if yn(row.get("IsRetiredPriorAgentOfficer")):
        tags.append('<span class="mini-tag">Veteran</span>')
    if yn(row.get("IsOpenPosition")):
        tags.append('<span class="mini-tag open">Open Position</span>')
    if yn(row.get("IsHiredWaitingBI")):
        tags.append('<span class="mini-tag waiting">Awaiting Clearance</span>')

    reports_html = ""
    if reports > 0:
        total_under = subtree_total_fn(rid)
        extra = f" &middot; {total_under} total" if total_under != reports else ""
        reports_html = f'<div class="reports-line">{reports} direct report{"s" if reports != 1 else ""}{extra}</div>'

    dept_attr = f' data-dept="{esc(dept_id)}"' if dept_id else ""

    return f'''<div class="card card-{level}"{dept_attr} data-id="{rid}" data-manager="{row.get("ManagerID") or ""}">
  <div class="card-badges">{''.join(badges)}</div>
  <div class="card-name">{esc(row.get("Name"))}</div>
  <div class="card-title">{esc(row.get("Title"))}</div>
  {reports_html}
  {f'<div class="card-tags">{"".join(tags)}</div>' if tags else ""}
</div>'''


def render_node(row, depth, children, direct_report_count, subtree_total_fn, dept_id=None, dept_root=False):
    rid = row["ID"]
    is_task_lead = norm(row.get("Title")) == "TASK LEAD"
    if is_task_lead:
        dept_id = f"dept-{rid}"

    card = person_card_html(row, depth, is_task_lead, direct_report_count, subtree_total_fn, dept_id)
    kids = children.get(rid, [])

    if not kids:
        return f"<li>{card}</li>"

    if is_task_lead:
        # Department root: card is always visible; the team is a separate,
        # collapsible GRID (not tree siblings) toggled by clicking the card.
        # Team members are leaves with no reports of their own, so a wrapping
        # grid — like the old column layout — keeps a 12-person team compact
        # instead of spreading 12 table-cells across the page width.
        team_cards = "\n".join(
            person_card_html(c, depth + 1, False, direct_report_count, subtree_total_fn)
            for c in kids
        )
        clickable_card = card.replace(
            f'<div class="card card-manager"',
            f'<div class="card card-manager card-toggle" onclick="toggleDept(\'{dept_id}\')"',
            1,
        )
        # More columns for bigger teams instead of scrolling: 2 up to 6
        # people, then roughly the square root of the team size, capped at
        # 6 columns so cards never go narrower than ~150px.
        n = len(kids)
        cols = 2 if n <= 6 else min(6, max(3, round(n ** 0.5)))
        col_width = 152
        block_width = cols * col_width + (cols - 1) * 8 + 20
        return f'''<li class="dept-root" id="{dept_id}">
{clickable_card}
<div class="team-toggle-hint" onclick="toggleDept('{dept_id}')">{n} team member{"s" if n != 1 else ""} &middot; click to toggle</div>
<div class="team-connector"></div>
<div class="team-block collapsed" style="grid-template-columns: repeat({cols}, minmax(150px, 1fr)); max-width: {block_width}px;">
{team_cards}
</div>
</li>'''

    inner = "\n".join(
        render_node(c, depth + 1, children, direct_report_count, subtree_total_fn, dept_id)
        for c in kids
    )
    return f'''<li>
{card}
<ul>
{inner}
</ul>
</li>'''


def sme_panel_html(sme_rows):
    if not sme_rows:
        return ""
    sme_rows = sorted(sme_rows, key=lambda r: (r.get("SortOrder") or 0))
    cards = []
    for r in sme_rows:
        contractor = not is_prime(r.get("Company"))
        badge = f'<span class="level-badge level-contractor">{esc(r.get("Company"))}</span>' if contractor else ""
        cards.append(f'''<div class="card card-sme">
  <div class="card-badges"><span class="level-badge level-sme">SME</span>{badge}</div>
  <div class="card-name">{esc(r.get("Name"))}</div>
  <div class="card-title">{esc(r.get("Title"))}</div>
</div>''')
    return f'''<div class="sme-connector"></div>
<div class="sme-panel">
  <div class="sme-panel-label">Cross-Functional Support &mdash; dashed line = functional support, not formal reporting</div>
  <div class="sme-panel-cards">
{"".join(cards)}
  </div>
</div>'''


CSS = '''
:root {
  --prime-bg: #EEF1F6;
  --prime-border: #C7CEDB;
  --header-bg: #22314F;
  --header-text: #FFFFFF;
  --ink: #1F2430;
  --muted: #6B7280;
  --page-bg: #F7F8FA;
  --line: #A9AFBC;
  --exec-accent: #22314F;
  --manager-accent: #3B5A8A;
  --support-accent: #7A8B99;
  --senior-accent: #6B7280;
  --ic-accent: #B9BEC7;
  --sme-accent: #8A5A8F;
  --contractor-bg: #FDEEDC;
  --contractor-border: #E8B778;
  --open: #E4572E;
  --waiting: #2563EB;
  --remote: #0D9488;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  padding: 32px;
  background: var(--page-bg);
  font-family: Arial, Helvetica, sans-serif;
  color: var(--ink);
}
h1 { font-size: 20px; margin: 0 0 4px 0; letter-spacing: 0.02em; }
.subtitle { color: var(--muted); font-size: 12px; margin-bottom: 4px; }
.last-updated { color: var(--muted); font-size: 11px; font-style: italic; margin-bottom: 24px; }

.tree-wrap { overflow-x: auto; padding-bottom: 24px; }
.tree, .tree ul { list-style: none; margin: 0; padding: 0; position: relative; display: table; margin: 0 auto; }
.tree ul { width: 100%; }
.tree li {
  display: table-cell;
  text-align: center;
  padding: 28px 10px 0 10px;
  vertical-align: top;
  position: relative;
}
.tree li::before, .tree li::after {
  content: ''; position: absolute; top: 0; right: 50%;
  border-top: 2px solid var(--line); width: 50%; height: 28px;
}
.tree li::after { right: auto; left: 50%; border-left: 2px solid var(--line); }
.tree li:only-child::after, .tree li:only-child::before { display: none; }
.tree li:only-child { padding-top: 0; }
.tree li:first-child::before, .tree li:last-child::after { border: 0 none; }
.tree li:last-child::before { border-right: 2px solid var(--line); border-radius: 0 5px 0 0; }
.tree li:first-child::after { border-radius: 5px 0 0 0; }
.tree > li { padding-top: 0; }
.tree > li::before, .tree > li::after { border: 0 none; }
.tree ul::before {
  content: ''; position: absolute; top: 0; left: 50%;
  border-left: 2px solid var(--line); width: 0; height: 28px;
}

.card {
  display: inline-block;
  text-align: left;
  background: #FFFFFF;
  border: 1px solid #DDD8D2;
  border-left: 4px solid var(--ic-accent);
  border-radius: 6px;
  padding: 8px 12px;
  min-width: 168px;
  max-width: 200px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}
.card-executive { border-left-color: var(--exec-accent); padding: 12px 16px; min-width: 190px; }
.card-executive .card-name { font-size: 15px; }
.card-manager { border-left-color: var(--manager-accent); }
.card-manager.card-toggle { cursor: pointer; }
.card-manager.card-toggle:hover { box-shadow: 0 2px 6px rgba(0,0,0,0.10); }
.card-support { border-left-color: var(--support-accent); }
.card-senior-ic { border-left-color: var(--senior-accent); }
.card-ic { border-left-color: var(--ic-accent); }
.card-sme { border-left-color: var(--sme-accent); min-width: 150px; }

.card-badges { display: flex; gap: 4px; flex-wrap: wrap; margin-bottom: 3px; }
.level-badge {
  font-size: 9px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.03em;
  padding: 1px 5px; border-radius: 3px; background: #F0EDE9; color: var(--muted);
}
.level-executive { background: var(--exec-accent); color: #fff; }
.level-manager { background: var(--manager-accent); color: #fff; }
.level-support { background: var(--support-accent); color: #fff; }
.level-sme { background: var(--sme-accent); color: #fff; }
.level-contractor { background: var(--contractor-bg); border: 1px solid var(--contractor-border); color: var(--ink); }

.card-name { font-size: 13px; font-weight: bold; color: var(--ink); line-height: 1.2; }
.card-title { font-size: 11.5px; color: var(--muted); margin-top: 1px; }
.reports-line { font-size: 10.5px; color: var(--manager-accent); font-weight: bold; margin-top: 4px; }
.card-tags { margin-top: 5px; display: flex; gap: 4px; flex-wrap: wrap; }
.mini-tag {
  font-size: 9px; padding: 1px 5px; border-radius: 3px; background: #F0EDE9; color: var(--ink);
  border: 1px solid rgba(0,0,0,0.08);
}
.mini-tag.remote { background: var(--remote); color: #fff; border-color: var(--remote); }
.mini-tag.open { background: #FDECEA; color: var(--open); border-color: var(--open); }
.mini-tag.waiting { background: #EAF1FD; color: var(--waiting); border-color: var(--waiting); }

.dept-root { vertical-align: top; }
.team-toggle-hint {
  font-size: 10px; color: var(--muted); font-style: italic; margin-top: 6px; cursor: pointer;
}
.team-toggle-hint:hover { color: var(--manager-accent); }
.team-connector { width: 2px; height: 14px; border-left: 2px solid var(--line); margin: 0 auto; }
.team-block.collapsed { display: none; }
.team-block {
  margin: 0 auto;
  display: grid;
  gap: 8px;
  background: #FBFBFA;
  border: 1px solid #E5E1DC;
  border-radius: 6px;
  padding: 10px;
  text-align: left;
}
.team-block .card { min-width: 0; max-width: none; width: 100%; padding: 6px 9px; }
.team-block .card-name { font-size: 12px; }
.team-block .card-title { font-size: 10.5px; }

.sme-connector { width: 2px; height: 24px; background: none; border-left: 2px dashed var(--sme-accent); margin: 0 auto; }
.sme-panel {
  border: 1px dashed var(--sme-accent);
  border-radius: 6px;
  padding: 12px 16px;
  width: fit-content;
  margin: 0 auto 32px auto;
  background: #FBF7FB;
}
.sme-panel-label { font-size: 10.5px; color: var(--sme-accent); font-weight: bold; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.02em; }
.sme-panel-cards { display: flex; gap: 10px; flex-wrap: wrap; }

.legend {
  margin-bottom: 22px; background: #FFFFFF; border: 1px solid #DDD8D2; border-radius: 6px;
  padding: 10px 16px; font-size: 11px; width: fit-content; display: flex; gap: 18px; flex-wrap: wrap;
}
.legend-item { display: flex; align-items: center; gap: 6px; }
'''

JS = '''
function toggleDept(id) {
  var el = document.getElementById(id);
  var sub = el.querySelector('.team-block');
  sub.classList.toggle('collapsed');
}
'''


def main():
    rows = load_rows(SOURCE_CSV)
    id_to_row, children, roots, direct_report_count, subtree_total_fn, sme_rows = build(rows)

    tree_lis = "\n".join(
        render_node(r, 0, children, direct_report_count, subtree_total_fn)
        for r in roots
    )

    total_people = len([r for r in rows if not is_sme(r)])
    generated_at = datetime.now().strftime("%B %d, %Y at %I:%M %p")

    html_doc = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Org Chart</title>
<style>{CSS}</style>
</head>
<body>

<h1>Organization Chart</h1>
<div class="subtitle">{total_people} people &middot; solid lines = formal reporting &middot; dashed line = functional support</div>
<div class="last-updated">Last updated: {generated_at}</div>

<div class="legend">
  <div class="legend-item"><span class="level-badge level-executive">Executive</span></div>
  <div class="legend-item"><span class="level-badge level-manager">Department Lead</span></div>
  <div class="legend-item"><span class="level-badge level-support">Program Support</span></div>
  <div class="legend-item"><span class="level-badge level-sme">SME</span> Cross-functional, dashed line</div>
  <div class="legend-item"><span class="level-badge level-contractor">Company</span> shown when not Prime</div>
  <div class="legend-item">Click a Department Lead card to expand/collapse their team</div>
</div>

<div class="tree-wrap">
  <ul class="tree">
{tree_lis}
  </ul>
</div>

{sme_panel_html(sme_rows)}

<script>{JS}</script>

</body>
</html>
'''

    with open(OUTPUT_HTML, "w") as f:
        f.write(html_doc)
    print(f"Wrote {OUTPUT_HTML}")


if __name__ == "__main__":
    main()
