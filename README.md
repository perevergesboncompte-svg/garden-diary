# Garden Diary

A static site for a small raised-bed garden in Costa Mesa, California (USDA zone 10b).
It carries the current state of every plant, a dated diary, and the learnings each crop
produced.

## How it works

The site is generated, not authored. Content lives as markdown in a Claude Code skill
at `~/.claude/skills/garden/`, which is where plants, dated entries, and site conditions
are recorded. `build.py` reads those three files and writes the pages to the repository
root, which is what GitHub Pages serves. Editing the generated HTML accomplishes
nothing, since the next build overwrites it. `assets/site.css` is the stylesheet source
and gets copied to `site.css` on build.

    plants.md    one entry per plant: type, container, sowing date, status, learnings
    journal.md   dated entries, newest first
    profile.md   location, climate normals, measured sun exposure

Rebuild after any change:

    python3 build.py

No dependencies beyond the Python standard library.

The build also copies the source markdown into `notes/`, so this repo carries the
diary's own history rather than only the rendered pages. `git log -p notes/journal.md`
shows how the garden was written up over time.

## Pages

`index.html` lists every plant grouped by where it grows, with its lifecycle status and
the date it was last touched. Each plant gets its own page carrying its fields, its
learnings, and a timeline assembled from every diary entry that mentions it.
`diary.html` is the full log. `conditions.html` holds the climate normals and the
measured sun exposure.

## Location privacy

`profile.md` stores the garden's exact latitude and longitude, because the weather and
evapotranspiration lookups need them. Those never reach the published files. `build.py`
drops the coordinate keys, then reads the actual coordinate values back out of the
source and searches everything it just wrote for them, at both full and three-decimal
precision, exiting non-zero on any hit. Three decimals is included because a truncated
coordinate still resolves to about a city block. The published pages name the city and
the hardiness zone and nothing narrower.

If you add fields to `profile.md`, keep anything street-level out of the ones the site
renders.
