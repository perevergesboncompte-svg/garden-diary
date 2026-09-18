#!/usr/bin/env python3
"""Render the garden skill's markdown into a static site.

Source of truth is the skill's own files, so the site never diverges from the
diary the assistant maintains:

    ~/.claude/skills/garden/plants.md
    ~/.claude/skills/garden/journal.md
    ~/.claude/skills/garden/profile.md

Pages are written to the repository root, which is what GitHub Pages serves.

    python3 build.py

Coordinates are stripped on the way out. profile.md holds the exact latitude and
longitude of the garden, and publishing those would pin a home address, so
REDACT_KEYS below never reach the generated HTML.
"""

import html
import os
import re
import shutil
import sys
import urllib.parse
from datetime import date, datetime
from pathlib import Path

SKILL = Path(os.path.expanduser("~/.claude/skills/garden"))
ROOT = Path(__file__).parent
OUT = ROOT
NOTES = ROOT / "notes"
INBOX = ROOT / "inbox"
PLANTS = []
SPECIES = {}

REDACT_KEYS = {"latitude", "longitude", "elevation", "photos_path", "tasks_path"}

STATUS_ORDER = ["planned", "sown", "germinating", "seedling", "hardening",
                "planted", "establishing", "outdoor", "harvesting",
                "dormant", "done", "failed"]
STATUS_CLASS = {
    "planned": "s-plan", "sown": "s-sown", "germinating": "s-grow",
    "seedling": "s-grow", "hardening": "s-grow", "planted": "s-sown",
    "establishing": "s-grow", "outdoor": "s-grow", "harvesting": "s-crop",
    "dormant": "s-rest", "done": "s-rest", "failed": "s-fail",
}


def slug(text):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "item"


def read(name):
    p = SKILL / name
    if not p.exists():
        sys.exit(f"missing {p}. Run the garden skill first.")
    return p.read_text(encoding="utf-8")


def parse_blocks(text, h_major, h_minor):
    """Split markdown into (major heading, minor heading, field dict, body)."""
    out = []
    major = None
    cur = None
    for line in text.splitlines():
        if line.startswith(h_major + " "):
            major = line[len(h_major) + 1:].strip()
            continue
        if line.startswith(h_minor + " "):
            cur = {"major": major, "title": line[len(h_minor) + 1:].strip(),
                   "fields": {}, "order": [], "body": []}
            out.append(cur)
            continue
        if cur is None:
            continue
        m = re.match(r"^- ([A-Za-z][A-Za-z ]*?):\s*(.*)$", line)
        if m:
            key = m.group(1).strip().lower()
            cur["fields"][key] = m.group(2).strip()
            cur["order"].append(key)
        elif line.strip() and cur["order"]:
            cur["fields"][cur["order"][-1]] += " " + line.strip()
        elif line.strip():
            cur["body"].append(line.strip())
    return out


def parse_plants():
    plants = []
    for b in parse_blocks(read("plants.md"), "##", "###"):
        f = b["fields"]
        status = (f.get("status") or "").lower() or "unknown"
        plants.append({
            "name": b["title"],
            "slug": slug(b["title"]),
            "section": b["major"] or "Other",
            "status": status,
            "fields": f,
            "order": b["order"],
            "key": b["title"].split()[0].lower().strip(",."),
        })
    return plants


def parse_species():
    """Species-level knowledge, one file per crop, each figure carrying a source."""
    d = SKILL / "species"
    out = {}
    if not d.is_dir():
        return out
    for f in sorted(d.glob("*.md")):
        if f.name == "SOURCES.md":
            continue
        sections = []
        cur = None
        title = f.stem.replace("-", " ").title()
        for line in f.read_text().splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
            elif line.startswith("## "):
                cur = (line[3:].strip(), [])
                sections.append(cur)
            else:
                m = re.match(r"^- ([A-Za-z][A-Za-z ]*?):\s*(.*)$", line)
                if m:
                    if cur is None:
                        cur = ("", [])
                        sections.append(cur)
                    cur[1].append((m.group(1).strip(), m.group(2).strip()))
        out[f.stem] = {"slug": f.stem, "name": title, "sections": sections}
    return out


def parse_journal():
    entries = []
    day = None
    cur = None
    for line in read("journal.md").splitlines():
        m = re.match(r"^## (\d{2})\.(\d{2})\.(\d{4})\s*$", line)
        if m:
            d, mo, y = m.groups()
            day = date(int(y), int(mo), int(d))
            continue
        if line.startswith("### "):
            cur = {"date": day, "title": line[4:].strip(), "fields": {},
                   "order": []}
            entries.append(cur)
            continue
        if cur is None:
            continue
        fm = re.match(r"^- ([A-Za-z][A-Za-z ]*?):\s*(.*)$", line)
        if fm:
            k = fm.group(1).strip().lower()
            cur["fields"][k] = fm.group(2).strip()
            cur["order"].append(k)
        elif line.strip() and cur["order"]:
            cur["fields"][cur["order"][-1]] += " " + line.strip()
    return [e for e in entries if e["date"]]


def parse_profile():
    text = read("profile.md")
    info = {}
    last = None
    for line in text.splitlines():
        m = re.match(r"^- ([A-Za-z][A-Za-z0-9 _]*?):\s*(.*)$", line)
        if m:
            last = m.group(1).strip()
            if last.lower() in REDACT_KEYS:
                last = None
            else:
                info[last] = m.group(2).strip()
        elif last and line.startswith("  ") and line.strip():
            info[last] += " " + line.strip()
        elif not line.strip():
            last = None
    tables = []
    block = []
    for line in text.splitlines():
        if line.strip().startswith("|"):
            block.append(line.strip())
        elif block:
            tables.append(block)
            block = []
    if block:
        tables.append(block)
    return info, tables


def esc(s):
    return html.escape(s or "")


def md_table(rows):
    if len(rows) < 2:
        return ""
    def cells(r):
        return [c.strip() for c in r.strip("|").split("|")]
    head = cells(rows[0])

    body = [cells(r) for r in rows[2:]]
    th = "".join(f"<th>{esc(c)}</th>" for c in head)
    trs = "".join(
        "<tr>" + "".join(f"<td>{esc(c)}</td>" for c in r) + "</tr>"
        for r in body)
    return (f'<div class="scroll" tabindex="0"><table><thead><tr>{th}</tr>'
            f"</thead><tbody>{trs}</tbody></table></div>")


def entries_for(plant, entries):
    hits = []
    for e in entries:
        who = (e["fields"].get("plants") or "").lower()
        if who in ("all", "all plants") or plant["key"] in who:
            hits.append(e)
    return hits


def page(title, body, nav_here=""):
    def link(href, label, key):
        c = ' class="here"' if key == nav_here else ""
        return f'<a href="{href}"{c}>{label}</a>'
    depth = "../" if nav_here == "plant" else ""
    nav = " ".join([
        link(f"{depth}today.html", "Today", "today"),
        link(f"{depth}index.html", "Plants", "index"),
        link(f"{depth}diary.html", "Diary", "diary"),
        link(f"{depth}conditions.html", "Conditions", "conditions"),
        link(f"{depth}knowledge.html", "Knowledge", "species"),
    ])
    slug = repo_slug()
    add = ""
    if slug:
        add = (f'<span class="actions">'
               f'<a class="add" href="{depth}note.html">Add a note</a>'
               f'<a class="add alt" href="{photo_url(slug)}">Add photos</a>'
               f'</span>')
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex">
<title>{esc(title)}</title>
<link rel="stylesheet" href="{depth}site.css">
</head><body>
<a class="skip" href="#main">Skip to content</a>
<header><a class="brand" href="{depth}index.html">Garden Diary</a><nav>{nav}</nav>{add}</header>
<main id="main">{body}</main>
<footer>Built {date.today().isoformat()} from the garden skill's notes.</footer>
</body></html>
"""


def badge(status):
    cls = STATUS_CLASS.get(status, "s-plan")
    return f'<span class="badge {cls}">{esc(status)}</span>'


def field_list(fields, order, skip=()):
    rows = []
    for k in order:
        if k in skip or not fields.get(k):
            continue
        rows.append(f"<dt>{esc(k.title())}</dt><dd>{esc(fields[k])}</dd>")
    return f"<dl>{''.join(rows)}</dl>" if rows else ""


def build_index(plants, entries, info):
    last = {}
    for p in plants:
        es = entries_for(p, entries)
        last[p["slug"]] = max((e["date"] for e in es), default=None)

    where = info.get("City", "")
    zone = info.get("USDA hardiness zone", "")
    head = f"<h1>Garden Diary</h1><p class='lede'>{esc(where)}"
    if zone:
        head += f" &middot; zone {esc(zone.split('(')[0].strip())}"
    head += "</p>"

    growing = [p for p in plants if p["status"] not in ("unknown", "empty")]
    by_section = {}
    for p in growing:
        by_section.setdefault(p["section"], []).append(p)

    parts = [head]
    for section, ps in by_section.items():
        parts.append(f"<h2>{esc(section)}</h2><div class='grid'>")
        ps.sort(key=lambda p: (STATUS_ORDER.index(p["status"])
                               if p["status"] in STATUS_ORDER else 99,
                               p["name"]))
        for p in ps:
            when = last[p["slug"]]
            meta = []
            if p["fields"].get("sown"):
                meta.append("sown " + p["fields"]["sown"])
            if when:
                meta.append("updated " + when.strftime("%d %b %Y"))
            parts.append(
                f"<a class='card' href='plants/{p['slug']}.html'>"
                f"<h3>{esc(p['name'])}</h3>{badge(p['status'])}"
                f"<p class='meta'>{esc(' &middot; '.join(meta))}</p></a>"
                .replace("&amp;middot;", "&middot;"))
        parts.append("</div>")

    empty = [p for p in plants if p["status"] == "empty"]
    if empty:
        parts.append("<h2>Free space</h2><p>" +
                     esc(", ".join(p["name"] for p in empty)) + "</p>")
    return page("Garden Diary", "".join(parts), "index")


def build_plant(p, entries):
    parts = [f"<h1>{esc(p['name'])} {badge(p['status'])}</h1>",
             f"<p class='meta'>{esc(p['section'])}</p>"]
    parts.append(field_list(p["fields"], p["order"], skip=("status", "notes",
                                                           "learnings")))
    if p["fields"].get("learnings"):
        parts.append("<h2>Learnings</h2><p>" +
                     esc(p["fields"]["learnings"]) + "</p>")
    if p["fields"].get("notes"):
        parts.append("<h2>Notes</h2><p>" + esc(p["fields"]["notes"]) + "</p>")

    sp = SPECIES.get(p["fields"].get("species", ""))
    if sp:
        parts.append(f"<h2>General {esc(sp['name'].lower())}</h2>")
        parts.append("<p class='meta'>What this crop needs in general, as opposed "
                     f"to how this planting is doing. "
                     f"<a href='../species/{sp['slug']}.html'>Full record</a>.</p>")
        rows = []
        want = {"Root depth", "Raised bed", "Sowing depth mm", "Plant spacing cm",
                "Days to germination", "Days to harvest", "Bolts above F",
                "Repeat harvest", "Sun"}
        for head, items in sp["sections"]:
            for k, v in items:
                if k in want:
                    val, src = cite(v)
                    rows.append(f"<dt>{esc(k)}</dt><dd>{val} {src}</dd>")
        parts.append(f"<dl>{''.join(rows)}</dl>")

    es = sorted(entries_for(p, entries), key=lambda e: e["date"], reverse=True)
    parts.append("<h2>This planting</h2>")
    if not es:
        parts.append("<p class='meta'>No diary entries mention this yet.</p>")
    for e in es:
        parts.append(
            f"<article class='entry'><h3>{esc(e['title'])}"
            f"<time>{e['date'].strftime('%d %b %Y')}</time></h3>"
            + field_list(e["fields"], e["order"], skip=("plants",))
            + "</article>")
    return page(p["name"], "".join(parts), "plant")


def build_note(plants, slug):
    """A compose form that writes the note here and hands GitHub one click.

    The filename carries a click-time timestamp, so several notes on the same day
    no longer collide on a single inbox/update.md.
    """
    opts = "".join(f"<option>{esc(p['name'])}</option>" for p in plants
                   if p["status"] not in ("empty", "unknown"))
    kinds = ["observation", "problem", "identify", "did-something"]
    kopts = "".join(f"<option>{k}</option>" for k in kinds)
    body = f"""<h1>Add a note</h1>
<p class='lede'>Write it here. The button hands it to GitHub already filled in,
so all that is left is Commit.</p>
<form id="f" class="note-form">
  <label>Plant
    <select id="plant">{opts}<option>Something else</option>
      <option>The whole garden</option></select></label>
  <label>Kind
    <select id="kind">{kopts}</select></label>
  <label>What happened
    <textarea id="detail" rows="7" placeholder="4 of the 6 spinach are up. Two have yellow leaf edges."></textarea></label>
  <button type="submit" class="add">Save to the diary</button>
  <p class="meta" id="hint"></p>
</form>
<p class="meta">Photos go through
<a href="{photo_url(slug)}">Add photos</a>, which uploads straight into the
inbox. A note is not required with them, though saying which plant helps.</p>
<script>
document.getElementById('f').addEventListener('submit', function (e) {{
  e.preventDefault();
  var d = document.getElementById('detail').value.trim();
  if (!d) {{ document.getElementById('hint').textContent =
      'Write something first.'; return; }}
  var n = new Date();
  var p = function (x) {{ return String(x).padStart(2, '0'); }};
  var stamp = n.getFullYear() + '-' + p(n.getMonth() + 1) + '-' + p(n.getDate())
            + '-' + p(n.getHours()) + p(n.getMinutes()) + p(n.getSeconds());
  var content = 'plant: ' + document.getElementById('plant').value + '\\n'
              + 'kind: ' + document.getElementById('kind').value + '\\n'
              + 'logged: ' + n.toISOString() + '\\n\\n' + d + '\\n';
  var url = 'https://github.com/{slug}/new/main'
          + '?filename=' + encodeURIComponent('inbox/' + stamp + '.md')
          + '&value=' + encodeURIComponent(content);
  window.open(url, '_blank');
}});
</script>"""
    return page("Add a note", body, "note")


def cite(value):
    """Split a trailing [source] marker off a value so it can be styled."""
    m = re.match(r"^(.*?)\s*\[([^\]]+)\]\s*$", value)
    if not m:
        return esc(value), ""
    return esc(m.group(1)), f'<span class="src">{esc(m.group(2))}</span>'


def species_rows(sp, limit=None):
    out = []
    for head, items in sp["sections"]:
        if head:
            out.append(f"<h2>{esc(head)}</h2>")
        rows = []
        for k, v in items:
            val, src = cite(v)
            rows.append(f"<dt>{esc(k)}</dt><dd>{val} {src}</dd>")
        out.append(f"<dl>{''.join(rows)}</dl>")
        if limit and len(out) >= limit:
            break
    return "".join(out)


def build_species_index(species):
    parts = ["<h1>Plant knowledge</h1>",
             "<p class='lede'>What each crop needs, separate from what is "
             "currently growing. Every figure names its source.</p>",
             "<div class='grid'>"]
    for sp in species.values():
        depth = next((v for h, its in sp["sections"] for k, v in its
                      if k == "Root depth"), "")
        bed = next((v for h, its in sp["sections"] for k, v in its
                    if k == "Raised bed"), "")
        meta = " &middot; ".join(x.split("[")[0].strip()
                                for x in (depth, bed) if x)
        parts.append(f"<a class='card' href='species/{sp['slug']}.html'>"
                     f"<h3>{esc(sp['name'])}</h3>"
                     f"<p class='meta'>{esc(meta)}</p></a>"
                     .replace("&amp;middot;", "&middot;"))
    parts.append("</div>")
    parts.append("<p class='meta'>Figures come from EcoCrop, INRAE, OpenFarm, "
                 "PlantVarietyDB and powerplant, plus hand-entered values where no "
                 "open dataset carries the field. See "
                 "<a href='sources.html'>sources</a>.</p>")
    return page("Plant knowledge", "".join(parts), "species")


def build_species(sp, plants):
    mine = [p for p in plants if p["fields"].get("species") == sp["slug"]]
    parts = [f"<h1>{esc(sp['name'])}</h1>"]
    if mine:
        links = ", ".join(f"<a href='../plants/{p['slug']}.html'>{esc(p['name'])}"
                          f"</a>" for p in mine)
        parts.append(f"<p class='lede'>Growing now: {links}</p>")
    else:
        parts.append("<p class='lede'>Not currently in the garden.</p>")
    parts.append(species_rows(sp))
    return page(sp["name"], "".join(parts), "plant")


def build_today(plants):
    """Render notes/today.md, which daily.py regenerates from the forecast."""
    src = NOTES / "today.md"
    if not src.exists():
        return page("Today", "<h1>Today</h1><p class='meta'>No briefing yet. "
                    "Run <code>daily.py</code>.</p>", "today")

    text = src.read_text()
    m = re.search(r"^# Today\s*[—-]\s*(\S+)", text, re.M)
    stamp = m.group(1) if m else "?"
    fresh = stamp == date.today().isoformat()

    slugs = {p["name"]: p["slug"] for p in plants}
    parts = [f"<h1>Today</h1><p class='lede'>{esc(stamp)}"]
    if not fresh:
        parts.append(" &middot; <strong>stale</strong>, the forecast has moved on")
    parts.append("</p>")

    sec = None
    items = []

    def flush():
        if sec is None:
            return
        head = esc(sec)
        if sec in slugs:
            head = f"<a href='plants/{slugs[sec]}.html'>{head}</a>"
        rows = "".join(
            f"<dt>{esc(k)}</dt><dd>{esc(v)}</dd>" for k, v in items)
        parts.append(f"<article class='entry'><h3>{head}</h3>"
                     f"<dl>{rows}</dl></article>")

    dropped = []
    for line in text.splitlines():
        if line.startswith("## "):
            flush()
            sec, items = line[3:].strip(), []
        else:
            fm = re.match(r"^- ([A-Za-z][A-Za-z ]*?):\s*(.*)$", line)
            if fm:
                items.append((fm.group(1).strip(), fm.group(2).strip()))
            elif line.startswith("- "):
                dropped.append(line)
    flush()
    if dropped:
        sys.exit("today.md has bullet lines the renderer cannot parse, so they "
                 "would vanish from the page. Field keys must be letters and "
                 "spaces only:\n  " + "\n  ".join(dropped))
    return page("Today", "".join(parts), "today")


def build_diary(entries):
    parts = ["<h1>Diary</h1>"]
    cur = None
    for e in sorted(entries, key=lambda e: e["date"], reverse=True):
        if e["date"] != cur:
            cur = e["date"]
            parts.append(f"<h2>{cur.strftime('%d %B %Y')}</h2>")
        parts.append(
            f"<article class='entry'><h3>{esc(e['title'])}</h3>"
            + field_list(e["fields"], e["order"]) + "</article>")
    return page("Diary", "".join(parts), "diary")


def build_conditions(info, tables):
    parts = ["<h1>Conditions</h1>"]
    keep = ["City", "Timezone", "Language", "USDA hardiness zone",
            "Sunset climate zone", "Climate type", "last_frost_date",
            "Coldest temperature in the 10-year record",
            "Days at or below 32 F, 2015-2024",
            "Days at or below 36 F, 2015-2024",
            "Chance of a night at or below 36 F",
            "Chance of a night at or below 32 F",
            "Hottest month",
            "Sun needed by cool-season crops",
            "Growing format", "Bed size", "Container"]
    rows = "".join(f"<dt>{esc(k)}</dt><dd>{esc(info[k])}</dd>"
                   for k in keep if info.get(k))
    parts.append(f"<dl>{rows}</dl>")
    titles = ["Monthly normals", "Measured sun exposure"]
    for i, t in enumerate(tables[:2]):
        parts.append(f"<h2>{titles[i] if i < len(titles) else 'Data'}</h2>")
        parts.append(md_table(t))
    return page("Conditions", "".join(parts), "conditions")


def repo_slug():
    cfg = ROOT / ".git" / "config"
    m = re.search(r"github\.com[:/]([\w.-]+/[\w.-]+?)(?:\.git)?\s", cfg.read_text())
    return m.group(1) if m else None


def photo_url(slug):
    return f"https://github.com/{slug}/upload/main/inbox"


def secrets():
    """The literal coordinate strings that must never appear in published files.

    Derived from profile.md rather than hardcoded, so the check keeps working if
    the garden moves. Each value is also checked at 3-decimal precision, since a
    truncated coordinate still resolves to roughly a city block.
    """
    out = set()
    for line in read("profile.md").splitlines():
        m = re.match(r"^- (Latitude|Longitude):\s*(-?\d+\.\d+)\s*$", line,
                     re.I)
        if m:
            v = m.group(2)
            out.add(v)
            whole, frac = v.split(".")
            if len(frac) >= 3:
                out.add(f"{whole}.{frac[:3]}")
    return out


def export_notes():
    """Copy the source markdown into the repo so git carries the diary's history.

    plants.md and journal.md go across verbatim. profile.md is filtered, since it
    is the one file holding the garden's coordinates.
    """
    NOTES.mkdir(exist_ok=True)
    for name in ("plants.md", "journal.md"):
        shutil.copy(SKILL / name, NOTES / name)

    sd = SKILL / "species"
    if sd.is_dir():
        (NOTES / "species").mkdir(exist_ok=True)
        for f in sd.glob("*.md"):
            shutil.copy(f, NOTES / "species" / f.name)

    kept = []
    for line in read("profile.md").splitlines():
        m = re.match(r"^- ([A-Za-z][A-Za-z0-9 _]*?):", line)
        if m and m.group(1).strip().lower() in REDACT_KEYS:
            continue
        kept.append(line)
    (NOTES / "profile.md").write_text("\n".join(kept) + "\n")


def main():
    global PLANTS, SPECIES
    plants = parse_plants()
    PLANTS = plants
    SPECIES = parse_species()
    entries = parse_journal()
    info, tables = parse_profile()

    OUT.mkdir(exist_ok=True)
    (OUT / "plants").mkdir(exist_ok=True)
    src_css = ROOT / "assets" / "site.css"
    shutil.copy(src_css, OUT / "site.css")
    (OUT / ".nojekyll").write_text("")

    (OUT / "index.html").write_text(build_index(plants, entries, info))
    (OUT / "today.html").write_text(build_today(plants))
    if repo_slug():
        (OUT / "note.html").write_text(build_note(plants, repo_slug()))
    (OUT / "diary.html").write_text(build_diary(entries))
    (OUT / "conditions.html").write_text(build_conditions(info, tables))
    if SPECIES:
        (OUT / "species").mkdir(exist_ok=True)
        (OUT / "knowledge.html").write_text(build_species_index(SPECIES))
        for sp in SPECIES.values():
            (OUT / "species" / f"{sp['slug']}.html").write_text(
                build_species(sp, plants))
        src = SKILL / "species" / "SOURCES.md"
        if src.exists():
            body = ["<h1>Sources</h1>"]
            for line in src.read_text().splitlines():
                if line.startswith("# "):
                    continue
                if line.startswith("## "):
                    body.append(f"<h2>{esc(line[3:])}</h2>")
                elif line.strip():
                    body.append(f"<p>{esc(line)}</p>")
            merged = re.sub(r"</p><p>", " ", "".join(body))
            (OUT / "sources.html").write_text(page("Sources", merged, "species"))
    for p in plants:
        if p["status"] == "empty":
            continue
        (OUT / "plants" / f"{p['slug']}.html").write_text(
            build_plant(p, entries))

    export_notes()

    published = list(OUT.rglob("*.html")) + list(NOTES.rglob("*.md"))
    leaked = [k for k in REDACT_KEYS for f in published
              if k in f.read_text().lower()]
    coords = [f"{f}:{s}" for s in secrets() for f in published
              if s in f.read_text()]
    if leaked or coords:
        sys.exit(f"REDACTION FAILED: keys={set(leaked)} coords={set(coords)}")

    n = len([p for p in plants if p["status"] != "empty"])
    print(f"built {n} plant pages, {len(entries)} diary entries -> {OUT}")
    print("no coordinates present in output")


if __name__ == "__main__":
    main()
