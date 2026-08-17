"""
Generate a scalable HTML org roster from the OrgData table.
Design: each office/task is a COLUMN with a header + description bar,
followed by a flat stacked list of people. No tree/graph layout, so it
handles 3 people or 30 people in a column equally well — the column just
gets taller.

Reads: OrgChart_Data_Mockup.xlsx (sheet: OrgData)
Writes: v1.html (kept for comparison, no longer the live demo)
"""

import csv
from collections import defaultdict
import html
from datetime import datetime
import json

SOURCE_CSV = "OrgChart_Data.csv"
OUTPUT_HTML = "v1.html"  # v1: card-column layout, kept for comparison

# Columns that must be treated as numbers, not text — CSV gives everything
# back as plain strings, so ID/ManagerID/SortOrder need explicit conversion
# or sorting and the SME (ManagerID=999) check will misbehave.
_NUMERIC_FIELDS = {"ID", "ManagerID", "SortOrder"}


def load_rows(path):
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for raw_row in reader:
            if not raw_row.get("ID"):
                continue  # skip blank trailing rows
            cleaned = {}
            for k, v in raw_row.items():
                if v is not None:
                    v = v.strip()
                if v == "":
                    v = None
                if k in _NUMERIC_FIELDS and v is not None:
                    try:
                        v = int(float(v))
                    except ValueError:
                        pass  # leave as-is; downstream code already guards with try/except
                cleaned[k] = v
            rows.append(cleaned)
    return rows


PRIME_LABEL = "PRIME CONTRACTOR"  # canonical company name; compared case/whitespace-insensitively
LEADERSHIP_LABEL = "LEADERSHIP"
MANAGEMENT_LABEL = "MANAGEMENT"  # sentinel: OfficeProgram value that routes a row to its own titled box, separate from the Leadership row and the Component/Division/Program board


def norm(s):
    """Normalize text for comparison: trim whitespace, uppercase. Prevents
    silent mismatches like 'Prime Contractor' vs 'PRIME CONTRACTOR' or a
    trailing space causing someone to be miscategorized."""
    return str(s).strip().upper() if s is not None else ""


def is_prime(company):
    return norm(company) == PRIME_LABEL or norm(company) == ""


def yn(v):
    """Treat 1, "1", Y, and Yes (any case) as true. Handles Excel storing
    0/1 as either numbers or text depending on how the cell was entered."""
    if v is None:
        return False
    s = str(v).strip().upper()
    return s in ("1", "Y", "YES", "TRUE")


def esc(s):
    return html.escape(str(s)) if s is not None else ""


def person_row_html(row, top_group="", sub_group=""):
    classes = ["person"]
    company = row.get("Company")
    if not is_prime(company):
        classes.append("subcontractor")
    if yn(row.get("IsHiredWaitingBI")):
        classes.append("waiting-bi")
    if yn(row.get("IsOpenPosition")):
        classes.append("open-position")

    tags = []
    if yn(row.get("IsPartTime")):
        tags.append('<span class="tag pt">PT</span>')
    if yn(row.get("IsRetiredPriorAgentOfficer")):
        tags.append('<span class="tag retired">V</span>')
    if yn(row.get("IsRemote")):
        tags.append('<span class="tag remote">R</span>')

    role_line = esc(row.get("Title") or "")
    driver = ""
    if yn(row.get("IsDriverTrainer")):
        driver = '<div class="driver-trainer">Driver/Trainer</div>'

    company_line = ""
    if not is_prime(company):
        company_line = f'<div class="company-name">({esc(company)})</div>'

    return f'''    <div class="{' '.join(classes)}" data-prime="{0 if not is_prime(company) else 1}" data-sub="{0 if is_prime(company) else 1}" data-pt="{1 if yn(row.get("IsPartTime")) else 0}" data-retired="{1 if yn(row.get("IsRetiredPriorAgentOfficer")) else 0}" data-waitingbi="{1 if yn(row.get("IsHiredWaitingBI")) else 0}" data-openposition="{1 if yn(row.get("IsOpenPosition")) else 0}" data-remote="{1 if yn(row.get("IsRemote")) else 0}" data-topgroup="{esc(top_group)}" data-subgroup="{esc(sub_group)}">
      <div class="person-main">
        <span class="person-name">{esc(row.get("Name"))}</span>
        {''.join(tags)}
      </div>
      <div class="person-role">{role_line}</div>
      {company_line}
      {driver}
    </div>'''


def leadership_html(rows):
    leadership = [r for r in rows if norm(r.get("OfficeProgram")) == LEADERSHIP_LABEL]
    leadership.sort(key=lambda r: (r.get("SortOrder") or 0))
    cards = []
    for r in leadership:
        cards.append(f'''  <div class="lead-card">
    <div class="lead-title">{esc(r.get("Title"))}</div>
    <div class="lead-name">{esc(r.get("Name"))}{" PT" if yn(r.get("IsPartTime")) else ""}</div>
  </div>''')
    return "\n".join(cards)


def titled_group_html(rows, sentinel_labels, box_title):
    """Renders a standalone titled box of people (card-per-row, like the
    leadership strip) for any OfficeProgram sentinel value(s) — e.g.
    'Leadership' and 'Management' combined into one box titled
    'Management'. Accepts a single label or a list of labels so rows
    tagged with either value land in the same box."""
    if isinstance(sentinel_labels, str):
        sentinel_labels = [sentinel_labels]
    wanted = {norm(s) for s in sentinel_labels}
    matched = [r for r in rows if norm(r.get("OfficeProgram")) in wanted]
    if not matched:
        return ""
    matched.sort(key=lambda r: (r.get("SortOrder") or 0))
    cards = []
    for r in matched:
        cards.append(f'''    <div class="lead-card">
      <div class="lead-title">{esc(r.get("Title"))}</div>
      <div class="lead-name">{esc(r.get("Name"))}{" PT" if yn(r.get("IsPartTime")) else ""}</div>
    </div>''')
    return f'''<div class="titled-group">
  <div class="titled-group-title">{esc(box_title)}</div>
  <div class="titled-group-row">
{chr(10).join(cards)}
  </div>
</div>'''


def subcontractor_summary_html(rows):
    counts = defaultdict(int)
    for r in rows:
        company = r.get("Company")
        if company and not is_prime(company):
            counts[str(company).strip()] += 1
    total = sum(counts.values())
    if not counts:
        return "", 0
    ordered = sorted(counts.items(), key=lambda kv: -kv[1])
    header_cells = "\n".join(f'      <th>{esc(company)}</th>' for company, _ in ordered)
    data_cells = "\n".join(f'      <td>{count}</td>' for _, count in ordered)
    table = f'''<div class="sub-summary">
  <div class="sub-summary-title">Subcontractors Team ({total})</div>
  <table class="sub-summary-table">
    <thead>
      <tr>
{header_cells}
      </tr>
    </thead>
    <tbody>
      <tr>
{data_cells}
      </tr>
    </tbody>
  </table>
</div>'''
    return table, total


def sme_table_html(sme_rows):
    if not sme_rows:
        return ""
    sme_rows = sorted(sme_rows, key=lambda r: (r.get("SortOrder") or 0))
    rows_html = "\n".join(person_row_html(r) for r in sme_rows)
    return f'''<div class="sme-summary">
  <div class="sme-summary-title">Subject Matter Experts ({len(sme_rows)})</div>
  <div class="sme-list">
{rows_html}
  </div>
</div>'''


TWO_COLUMN_THRESHOLD = 12  # office columns with more people than this switch from a
                           # scrolling single list to a wider two-column layout instead


def office_column_html(office, desc, people, top_group="", sub_group=""):
    people = sorted(people, key=lambda r: (r.get("SortOrder") or 0))
    rows_html = "\n".join(person_row_html(p, top_group, sub_group) for p in people)
    prime_count = sum(1 for p in people if is_prime(p.get("Company")))
    sub_count = len(people) - prime_count
    is_wide = len(people) > TWO_COLUMN_THRESHOLD
    column_class = "office-column office-column-wide" if is_wide else "office-column"
    list_class = "office-list two-col" if is_wide else "office-list"
    return f'''<div class="{column_class}">
  <div class="office-header">
    <div class="office-header-top">
      <span class="office-count-badge"><span class="count-prime">{prime_count}</span> - <span class="count-sub">{sub_count}</span></span>
    </div>
    <div class="office-title">{esc(office)}</div>
    <div class="office-desc">{esc(desc)}</div>
  </div>
  <div class="{list_class}">
{rows_html}
  </div>
</div>'''


SME_MANAGER_ID = 999  # sentinel: a person with this ManagerID is routed to the SME table instead of any office column


def is_sme(row):
    mgr = row.get("ManagerID")
    try:
        return int(mgr) == SME_MANAGER_ID
    except (TypeError, ValueError):
        return False


def main():
    rows = load_rows(SOURCE_CSV)

    sme_rows = [r for r in rows if is_sme(r)]
    org_rows = [r for r in rows if not is_sme(r)]

    # If a row's own Description is blank, inherit it from their manager
    # (walking up the ManagerID chain if needed). This is what actually ties
    # a person to the correct office column when only the Task Lead's row has
    # the Description filled in — grouping follows the real reporting
    # relationship instead of requiring every row to repeat the same text.
    id_to_row = {r.get("ID"): r for r in rows if r.get("ID") is not None}

    def effective_field(r, field, _seen=None):
        val = r.get(field)
        if val:
            return val
        _seen = _seen or set()
        rid = r.get("ID")
        mgr_id = r.get("ManagerID")
        if rid in _seen or mgr_id is None or mgr_id == SME_MANAGER_ID:
            return ""
        _seen.add(rid)
        mgr_row = id_to_row.get(mgr_id)
        if not mgr_row:
            return ""
        _seen.add(rid)
        return effective_field(mgr_row, field, _seen)

    def effective_description(r):
        return effective_field(r, "Description")

    offices = []           # list of (office_name, description) tuples — the column key
    office_title = {}      # key (Description) -> OfficeProgram text to display as the column header
    office_desc = {}       # key -> description (kept for rendering convenience)
    office_people = defaultdict(list)
    office_top_group = {}  # key -> TopGroup text (e.g. "OFO"), optional
    office_sub_group = {}  # key -> SubGroup text (e.g. "APP"), optional

    def op_list_for(r):
        raw_op = r.get("OfficeProgram")
        if not raw_op:
            return []
        return [p.strip() for p in str(raw_op).replace(";", ",").split(",") if p.strip()]

    # Column key = Description ALONE (not OfficeProgram). This is the simplest
    # rule that guarantees two groups never merge just because they happen to
    # share an OfficeProgram label: every distinct Description gets its own
    # column. Blank Descriptions are inherited from the manager chain first
    # (see effective_description) so team members whose own row has no
    # Description still land in their manager's column.
    for r in org_rows:
        op_list = op_list_for(r)
        if any(norm(op) in (LEADERSHIP_LABEL, MANAGEMENT_LABEL) for op in op_list):
            continue
        desc = effective_description(r)
        if not desc:
            continue  # no description anywhere up the chain — nothing to group by
        if desc not in office_desc:
            offices.append(desc)
            office_desc[desc] = desc
            office_title[desc] = op_list[0] if op_list else ""
            office_top_group[desc] = (effective_field(r, "TopGroup") or "").strip()
            office_sub_group[desc] = (effective_field(r, "SubGroup") or "").strip()
        office_people[desc].append(r)

    # Optional 3-tier hierarchy: TopGroup (e.g. "OFO") > SubGroup (e.g. "APP")
    # > office column (e.g. "ADIS & I-94"). If TopGroup/SubGroup are blank for
    # every row, we fall back to the flat single-row-of-columns layout used
    # before this feature existed — nothing breaks for sheets that don't use it.
    has_hierarchy = any(office_top_group[k] or office_sub_group[k] for k in offices)

    def prime_sub_split(people):
        prime = sum(1 for p in people if is_prime(p.get("Company")))
        return prime, len(people) - prime

    def count_badge_html(people):
        prime, sub = prime_sub_split(people)
        return f'<span class="group-count-badge"><span class="count-prime">{prime}</span> - <span class="count-sub">{sub}</span></span>'

    if has_hierarchy:
        top_order, sub_order_within_top, keys_within_sub = [], defaultdict(list), defaultdict(list)
        for k in offices:
            top = office_top_group[k] or "—"
            sub = office_sub_group[k] or "—"
            if top not in top_order:
                top_order.append(top)
            if sub not in sub_order_within_top[top]:
                sub_order_within_top[top].append(sub)
            keys_within_sub[(top, sub)].append(k)

        top_blocks = []
        for top in top_order:
            sub_blocks = []
            top_people = []
            for sub in sub_order_within_top[top]:
                # Pass the REAL top/sub values (empty string, not the "—"
                # placeholder) down to each person card, so filtering only
                # ever matches genuine group membership.
                real_top = "" if top == "—" else top
                real_sub = "" if sub == "—" else sub
                cols = "\n".join(
                    office_column_html(office_title.get(k, ""), office_desc[k], office_people[k], real_top, real_sub)
                    for k in keys_within_sub[(top, sub)]
                )
                sub_people = [p for k in keys_within_sub[(top, sub)] for p in office_people[k]]
                top_people.extend(sub_people)
                if sub != "—":
                    sub_header = (
                        f'<div class="sub-group-header group-filterable" '
                        f'onclick="applyGroupFilter(\'subgroup\', {esc(json.dumps(sub))}, this)">'
                        f'<span class="group-title">{esc(sub)}</span>{count_badge_html(sub_people)}</div>'
                    )
                else:
                    sub_header = ""
                sub_blocks.append(f'''<div class="sub-group">
  {sub_header}
  <div class="sub-group-columns">
{cols}
  </div>
</div>''')
            if top != "—":
                top_header = (
                    f'<div class="top-group-header group-filterable" '
                    f'onclick="applyGroupFilter(\'topgroup\', {esc(json.dumps(top))}, this)">'
                    f'<span class="group-title">{esc(top)}</span>{count_badge_html(top_people)}</div>'
                )
            else:
                top_header = f'<div class="top-group-header">{esc(top)}</div>'
            top_blocks.append(f'''<div class="top-group">
  {top_header}
  <div class="top-group-body">
{"".join(sub_blocks)}
  </div>
</div>''')
        columns_html = "\n".join(top_blocks)
    else:
        columns_html = "\n".join(
            office_column_html(office_title.get(key, ""), office_desc[key], office_people[key]) for key in offices
        )

    contract_support_html = titled_group_html(org_rows, [LEADERSHIP_LABEL, MANAGEMENT_LABEL], "Management")
    sub_summary_html, sub_total = subcontractor_summary_html(rows)
    sme_section_html = sme_table_html(sme_rows)

    total_people = len([r for r in rows if norm(r.get("OfficeProgram")) not in (LEADERSHIP_LABEL, MANAGEMENT_LABEL) and not is_sme(r)])
    generated_at = datetime.now().strftime("%B %d, %Y at %I:%M %p")

    # Legend counts — computed across every person in the roster, so the
    # legend doubles as a quick roll-up rather than just a color key.
    # Only count people who are actually rendered as filterable/taggable
    # .person cards. Leadership/Management box entries use a simpler card
    # style with no tags, so including them here would make the legend
    # numbers disagree with what clicking a filter actually highlights.
    filterable_rows = [r for r in rows if norm(r.get("OfficeProgram")) not in (LEADERSHIP_LABEL, MANAGEMENT_LABEL)]
    prime_total = sum(1 for r in filterable_rows if is_prime(r.get("Company")))
    sub_total_all = sum(1 for r in filterable_rows if not is_prime(r.get("Company")))
    pt_total = sum(1 for r in filterable_rows if yn(r.get("IsPartTime")))
    retired_total = sum(1 for r in filterable_rows if yn(r.get("IsRetiredPriorAgentOfficer")))
    waiting_bi_total = sum(1 for r in filterable_rows if yn(r.get("IsHiredWaitingBI")))
    open_position_total = sum(1 for r in filterable_rows if yn(r.get("IsOpenPosition")))
    remote_total = sum(1 for r in filterable_rows if yn(r.get("IsRemote")))

    html_doc = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Org Roster</title>
<style>
  :root {{
    --prime-bg: #EEF1F6;
    --prime-border: #C7CEDB;
    --sub-bg: #FDEEDC;
    --sub-border: #E8B778;
    --header-bg: #22314F;
    --header-text: #FFFFFF;
    --ink: #1F2430;
    --muted: #6B7280;
    --page-bg: #F7F8FA;
    --waiting-bi: #2563EB;
    --open-position: #E4572E;
    --remote: #0D9488;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    padding: 32px;
    background: var(--page-bg);
    font-family: Arial, Helvetica, sans-serif;
    color: var(--ink);
  }}
  h1 {{
    font-size: 20px;
    margin: 0 0 4px 0;
    letter-spacing: 0.02em;
  }}
  .subtitle {{
    color: var(--muted);
    font-size: 12px;
    margin-bottom: 4px;
  }}
  .last-updated {{
    color: var(--muted);
    font-size: 11px;
    font-style: italic;
    margin-bottom: 20px;
  }}
  .leadership-row {{
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 24px;
  }}
  .lead-card {{
    background: var(--prime-bg);
    border: 1px solid var(--prime-border);
    border-radius: 4px;
    padding: 8px 14px;
    min-width: 150px;
  }}
  .lead-title {{
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--muted);
    font-weight: bold;
  }}
  .lead-name {{
    font-size: 13px;
    font-weight: bold;
    margin-top: 2px;
  }}
  .titled-group {{
    margin-bottom: 24px;
    background: #FFFFFF;
    border: 1px solid #DDD8D2;
    border-radius: 6px;
    overflow: hidden;
    width: fit-content;
  }}
  .titled-group-title {{
    background: var(--header-bg);
    color: var(--header-text);
    font-size: 12.5px;
    font-weight: bold;
    letter-spacing: 0.03em;
    padding: 8px 14px;
  }}
  .titled-group-row {{
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    padding: 12px;
  }}
  .board {{
    display: flex;
    align-items: flex-start;
    gap: 14px;
    overflow-x: auto;
    padding-bottom: 20px;
  }}
  .office-column {{
    background: #FFFFFF;
    border: 1px solid #DDD8D2;
    border-radius: 6px;
    width: 200px;
    flex: 0 0 200px;
    overflow: hidden;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
  }}
  .office-column-wide {{
    width: 380px;
    flex: 0 0 380px;
  }}
  .office-header {{
    background: var(--header-bg);
    color: var(--header-text);
    padding: 10px 12px;
  }}
  .office-header-top {{
    display: flex;
    justify-content: flex-end;
    margin-bottom: 4px;
  }}
  .office-count-badge {{
    background: #FFFFFF;
    font-size: 9.5px;
    font-weight: bold;
    padding: 1px 5px;
    border-radius: 3px;
    line-height: 1.4;
  }}
  .count-prime {{
    color: var(--muted);
  }}
  .count-sub {{
    color: var(--sub-border);
  }}
  .office-title {{
    font-size: 12.5px;
    font-weight: bold;
    line-height: 1.25;
  }}
  .office-desc {{
    font-size: 10px;
    opacity: 0.85;
    margin-top: 3px;
    line-height: 1.3;
  }}
  .top-group {{
    background: #FFFFFF;
    border: 1px solid #C9C4BE;
    border-radius: 6px;
    overflow: hidden;
    flex: 0 0 auto;
  }}
  .top-group-header {{
    background: #8C8C8C;
    color: #FFFFFF;
    font-size: 12.5px;
    font-weight: bold;
    padding: 8px 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    position: relative;
  }}
  .top-group-header .group-title {{
    text-align: center;
  }}
  .top-group-header .group-count-badge {{
    position: absolute;
    right: 12px;
  }}
  .top-group-body {{
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 10px;
  }}
  .sub-group {{
    display: flex;
    flex-direction: column;
    gap: 6px;
  }}
  .sub-group-header {{
    background: #ADADAD;
    color: #FFFFFF;
    font-size: 11px;
    font-weight: bold;
    padding: 6px 10px;
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    position: relative;
  }}
  .sub-group-header .group-title {{
    text-align: center;
  }}
  .sub-group-header .group-count-badge {{
    position: absolute;
    right: 8px;
  }}
  .group-count-badge {{
    background: #FFFFFF;
    font-size: 9.5px;
    font-weight: bold;
    padding: 1px 5px;
    border-radius: 3px;
    line-height: 1.4;
  }}
  .group-filterable {{
    cursor: pointer;
    transition: filter 0.15s, outline 0.15s;
  }}
  .group-filterable:hover {{
    filter: brightness(1.12);
  }}
  .group-filterable.active {{
    outline: 2px solid var(--remote);
    outline-offset: -2px;
  }}
  .sub-group-columns {{
    display: flex;
    align-items: flex-start;
    gap: 8px;
  }}
  .office-count {{
    font-size: 10px;
    color: var(--muted);
    padding: 6px 12px 0 12px;
  }}
  .office-list {{
    padding: 6px 8px 10px 8px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    max-height: 640px;
    overflow-y: auto;
  }}
  .office-list.two-col {{
    display: block;
    column-count: 2;
    column-gap: 10px;
    max-height: none;
    overflow: visible;
  }}
  .office-list.two-col .person {{
    break-inside: avoid;
    -webkit-column-break-inside: avoid;
    margin-bottom: 6px;
  }}
  .person {{
    background: var(--prime-bg);
    border: 1px solid var(--prime-border);
    border-radius: 4px;
    padding: 6px 8px;
  }}
  .person.subcontractor {{
    background: var(--sub-bg);
    border-color: var(--sub-border);
  }}
  .person-main {{
    display: flex;
    align-items: baseline;
    gap: 5px;
  }}
  .person-name {{
    font-size: 12px;
    font-weight: bold;
  }}
  .person.waiting-bi .person-name {{
    color: var(--waiting-bi);
  }}
  .person.open-position .person-name {{
    color: var(--open-position);
  }}
  .person-role {{
    font-size: 10px;
    color: var(--muted);
  }}
  .company-name {{
    font-size: 9.5px;
    color: var(--muted);
    font-style: italic;
  }}
  .driver-trainer {{
    font-size: 9.5px;
    color: var(--muted);
    font-weight: bold;
    margin-top: 2px;
  }}
  .tag {{
    font-size: 11px;
    font-weight: bold;
    padding: 1px 5px;
    border-radius: 3px;
    background: #FFFFFF;
    border: 1px solid rgba(0,0,0,0.15);
    color: var(--ink);
  }}
  .tag.remote {{
    background: var(--remote);
    border-color: var(--remote);
    color: #FFFFFF;
  }}
  .legend {{
    margin-top: 0;
    margin-bottom: 20px;
    display: block;
    background: #FFFFFF;
    border: 1px solid #DDD8D2;
    border-radius: 6px;
    padding: 10px 16px;
    font-size: 11px;
    width: fit-content;
  }}
  .legend-item {{
    display: inline-block;
    margin-right: 24px;
    white-space: nowrap;
  }}
  .legend-item .swatch {{
    display: inline-block;
    vertical-align: middle;
    margin-right: 6px;
  }}
  .legend-count {{
    color: var(--muted);
    font-weight: normal;
  }}
  .legend-item.filterable {{
    cursor: pointer;
    padding: 3px 6px;
    border-radius: 4px;
    transition: background 0.15s;
  }}
  .legend-item.filterable:hover {{
    background: #F0EDE9;
  }}
  .legend-item.filterable.active {{
    background: #FDECEA;
    outline: 1px solid var(--open-position);
  }}
  .legend-clear {{
    color: var(--muted);
    font-style: italic;
  }}
  .person {{
    transition: opacity 0.15s;
  }}
  .person.dimmed {{
    opacity: 0.15;
  }}
  .swatch {{
    width: 14px;
    height: 14px;
    border-radius: 3px;
    border: 1px solid rgba(0,0,0,0.15);
  }}
  /* Scrollbar tidy-up */
  .office-list::-webkit-scrollbar {{ width: 6px; }}
  .office-list::-webkit-scrollbar-thumb {{ background: #C9C4BE; border-radius: 3px; }}

  .sub-summary {{
    margin-top: 0;
    margin-bottom: 20px;
    background: #FFFFFF;
    border: 1px solid #DDD8D2;
    border-radius: 6px;
    padding: 14px 16px;
    width: fit-content;
    min-width: 220px;
  }}
  .sub-summary-title {{
    font-size: 12.5px;
    font-weight: bold;
    margin-bottom: 10px;
    color: var(--ink);
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }}
  .sub-summary-table {{
    border-collapse: separate;
    border-spacing: 8px 0;
    margin-left: -8px;
  }}
  .sub-summary-table th {{
    background: var(--sub-bg);
    border: 1px solid var(--sub-border);
    border-radius: 4px 4px 0 0;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: bold;
    color: var(--ink);
    white-space: nowrap;
    border-bottom: none;
  }}
  .sub-summary-table td {{
    background: var(--sub-bg);
    border: 1px solid var(--sub-border);
    border-top: none;
    border-radius: 0 0 4px 4px;
    padding: 4px 12px 6px 12px;
    font-size: 13px;
    font-weight: bold;
    color: var(--ink);
    text-align: center;
  }}
  .sme-summary {{
    margin-top: 18px;
    background: #FFFFFF;
    border: 1px solid #DDD8D2;
    border-radius: 6px;
    padding: 14px 16px;
    width: fit-content;
    max-width: 100%;
  }}
  .sme-summary-title {{
    font-size: 12.5px;
    font-weight: bold;
    margin-bottom: 10px;
    color: var(--ink);
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }}
  .sme-list {{
    display: flex;
    flex-direction: column;
    gap: 6px;
    width: 240px;
  }}
  .sme-list .person {{
    width: auto;
  }}
</style>
</head>
<body>

<h1>Company Roster</h1>
<div class="subtitle">{len(offices)} offices &middot; {total_people} people &middot; generated from OrgData</div>
<div class="last-updated">Last updated: {generated_at}</div>

{sub_summary_html}

{contract_support_html}

<div class="legend">
  <div class="legend-item filterable" data-filter-key="prime" onclick="applyFilter('prime', this)"><span class="swatch" style="background:var(--prime-bg);border-color:var(--prime-border);"></span> Prime Contractor <span class="legend-count">({prime_total})</span></div>
  <div class="legend-item filterable" data-filter-key="sub" onclick="applyFilter('sub', this)"><span class="swatch" style="background:var(--sub-bg);border-color:var(--sub-border);"></span> Subcontractor <span class="legend-count">({sub_total_all})</span></div>
  <div class="legend-item filterable" data-filter-key="pt" onclick="applyFilter('pt', this)"><span class="tag">PT</span> Part Time <span class="legend-count">({pt_total})</span></div>
  <div class="legend-item filterable" data-filter-key="retired" onclick="applyFilter('retired', this)"><span class="tag">V</span> Veteran <span class="legend-count">({retired_total})</span></div>
  <div class="legend-item filterable" data-filter-key="waitingbi" onclick="applyFilter('waitingbi', this)"><span style="color:var(--waiting-bi); font-weight:bold;">Name</span> Waiting for Equipment <span class="legend-count">({waiting_bi_total})</span></div>
  <div class="legend-item filterable" data-filter-key="openposition" onclick="applyFilter('openposition', this)"><span style="color:var(--open-position); font-weight:bold;">Name</span> Open Position &ndash; Waiting to be Hired <span class="legend-count">({open_position_total})</span></div>
  <div class="legend-item filterable" data-filter-key="remote" onclick="applyFilter('remote', this)"><span class="tag remote">R</span> Remote <span class="legend-count">({remote_total})</span></div>
  <div class="legend-item filterable legend-clear" onclick="clearFilter()">&times; Clear filter</div>
</div>

<div class="board">
{columns_html}
</div>

{sme_section_html}

<script>
  var activeFilter = null;

  function clearFilter() {{
    document.querySelectorAll('.person').forEach(function(el) {{
      el.classList.remove('dimmed');
    }});
    document.querySelectorAll('.legend-item.filterable, .group-filterable').forEach(function(el) {{
      el.classList.remove('active');
    }});
    activeFilter = null;
  }}

  function applyFilter(key, el) {{
    var filterId = 'flag:' + key;
    if (activeFilter === filterId) {{
      clearFilter();
      return;
    }}
    document.querySelectorAll('.legend-item.filterable, .group-filterable').forEach(function(e) {{
      e.classList.remove('active');
    }});
    el.classList.add('active');
    activeFilter = filterId;
    document.querySelectorAll('.person').forEach(function(p) {{
      var match = p.getAttribute('data-' + key) === '1';
      p.classList.toggle('dimmed', !match);
    }});
  }}

  function applyGroupFilter(attr, value, el) {{
    var filterId = 'group:' + attr + ':' + value;
    if (activeFilter === filterId) {{
      clearFilter();
      return;
    }}
    document.querySelectorAll('.legend-item.filterable, .group-filterable').forEach(function(e) {{
      e.classList.remove('active');
    }});
    el.classList.add('active');
    activeFilter = filterId;
    document.querySelectorAll('.person').forEach(function(p) {{
      var match = p.getAttribute('data-' + attr) === value;
      p.classList.toggle('dimmed', !match);
    }});
  }}
</script>

</body>
</html>
'''

    with open(OUTPUT_HTML, "w") as f:
        f.write(html_doc)
    print(f"Wrote {OUTPUT_HTML}")
    print(f"{len(offices)} offices, {total_people} people (excluding leadership)")


if __name__ == "__main__":
    main()
