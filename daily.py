#!/usr/bin/env python3
"""Compute today's per-plant actions from the forecast and each plant's state.

Writes notes/today.md, which build.py renders into today.html. Runs from cron, so
it talks to Open-Meteo over plain HTTP rather than through the MCP server, and it
depends on nothing outside the standard library.

    python3 daily.py

Watering is reference evapotranspiration minus rainfall, scaled by a crop
coefficient and the plant's growth stage, times its area. Containers get a
surcharge because they hold no soil reservoir to carry a missed day.
"""

import datetime as dt
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

SKILL = Path.home() / ".claude/skills/garden"
NOTES = Path(__file__).parent / "notes"

STAGE_KC = {
    "sown": 0.4, "germinating": 0.4, "seedling": 0.6, "hardening": 0.9,
    "planted": 0.9, "establishing": 0.9, "outdoor": 0.9, "harvesting": 1.0,
}
SKIP = {"planned", "empty", "dormant", "done", "failed", "unknown"}

DEFAULT_CROP = {"kc": 0.95, "germ": (7, 21), "bolt_f": 85}


def species_table():
    """Read per-crop figures from the species files, the single source of truth.

    Falls back to DEFAULT_CROP for a crop with no species file, and says so, since
    silently using generic numbers is how a briefing becomes confidently wrong.
    """
    out = {}
    d = SKILL / "species"
    if not d.is_dir():
        return out
    for f in d.glob("*.md"):
        if f.name == "SOURCES.md":
            continue
        rec = {}
        for line in f.read_text().splitlines():
            m = re.match(r"^- ([A-Za-z][A-Za-z ]*?):\s*(.*)$", line)
            if not m:
                continue
            k, v = m.group(1).strip(), m.group(2).strip()
            if k == "Crop coefficient":
                rec["kc"] = float(re.search(r"[\d.]+", v).group())
            elif k == "Germination window days":
                n = re.findall(r"\d+", v)
                if len(n) >= 2:
                    rec["germ"] = (int(n[0]), int(n[1]))
            elif k == "Bolts above F":
                rec["bolt_f"] = float(re.search(r"[\d.]+", v).group())
        if "kc" in rec and "germ" in rec:
            rec.setdefault("bolt_f", 999)
            out[f.stem] = rec
    return out


def get(url, **params):
    q = urllib.parse.urlencode(params)
    with urllib.request.urlopen(f"{url}?{q}") as r:
        return json.load(r)


def profile():
    text = (SKILL / "profile.md").read_text()
    out = {}
    for line in text.splitlines():
        m = re.match(r"^- ([A-Za-z][A-Za-z0-9 _-]*?):\s*(.*)$", line)
        if m:
            out[m.group(1).strip().lower()] = m.group(2).strip()
    return out


def plants():
    out = []
    cur = None
    for line in (SKILL / "plants.md").read_text().splitlines():
        if line.startswith("### "):
            cur = {"name": line[4:].strip(), "fields": {}}
            out.append(cur)
        elif cur is not None:
            m = re.match(r"^- ([A-Za-z][A-Za-z ]*?):\s*(.*)$", line)
            if m:
                cur["fields"][m.group(1).strip().lower()] = m.group(2).strip()
    return out


def fmt_vol(ml):
    if ml >= 1000:
        return f"{ml / 1000:.1f} L"
    return f"{int(round(ml / 10.0) * 10)} mL"


def main():
    p = profile()
    crops = species_table()
    lat = float(p["latitude"])
    lon = float(p["longitude"])
    today = dt.date.today()

    w = get("https://api.open-meteo.com/v1/forecast",
            latitude=lat, longitude=lon,
            daily=("et0_fao_evapotranspiration,precipitation_sum,"
                   "temperature_2m_max,temperature_2m_min,"
                   "wind_speed_10m_max,precipitation_probability_max"),
            hourly="sunshine_duration,soil_temperature_6cm",
            timezone="America/Los_Angeles", temperature_unit="fahrenheit",
            forecast_days=6)
    d, h = w["daily"], w["hourly"]

    et0_mm = d["et0_fao_evapotranspiration"][0] or 0.0
    rain_mm = d["precipitation_sum"][0] or 0.0
    tmax, tmin = d["temperature_2m_max"][0], d["temperature_2m_min"][0]
    wind = d["wind_speed_10m_max"][0]

    soil = [v for t, v in zip(h["time"], h["soil_temperature_6cm"])
            if t[:10] == today.isoformat() and v is not None]
    soil_f = sum(soil) / len(soil) if soil else None

    win = p.get("sun window hours", "0-24")
    h0, h1 = (int(x) for x in win.split("-"))
    sun_h = sum(s / 3600.0 for t, s in
                zip(h["time"], h["sunshine_duration"])
                if t[:10] == today.isoformat() and s is not None
                and h0 <= int(t[11:13]) < h1)

    deficit = max(0.0, et0_mm - rain_mm)
    highs = list(zip(d["time"], d["temperature_2m_max"]))
    wet = [(d["time"][i], d["precipitation_sum"][i])
           for i in range(len(d["time"])) if (d["precipitation_sum"][i] or 0) >= 3]

    shared = {}
    for pl in plants():
        f = pl["fields"]
        if f.get("status", "").lower() in SKIP:
            continue
        c = f.get("container", "").split(",")[0].strip().lower()
        if "pot" in c or "container" in c:
            shared.setdefault(c, []).append(pl["name"])

    L = [f"# Today — {today.isoformat()}", ""]
    L.append("## Conditions")
    L.append(f"- High and low: {tmax:.0f} F / {tmin:.0f} F")
    if soil_f is not None:
        L.append(f"- Soil temperature: {soil_f:.0f} F at 6 cm")
    L.append(f"- Direct sun: {sun_h:.1f} h inside the "
             f"{h0:02d}:00 to {h1:02d}:00 unshaded window")
    L.append(f"- Evapotranspiration: {et0_mm:.1f} mm")
    L.append(f"- Rain today: {rain_mm:.1f} mm")
    L.append(f"- Watering demand after rain: {deficit:.1f} mm")
    L.append(f"- Wind peak: {wind:.0f} km/h")
    if wet:
        L.append("- Rain ahead: " + ", ".join(f"{t} ({v:.0f} mm)"
                                              for t, v in wet))
    L.append("")

    for pl in plants():
        f = pl["fields"]
        status = f.get("status", "unknown").lower()
        if status in SKIP:
            continue
        key = (f.get("species") or pl["name"].split()[0]).lower().strip(",.")
        crop = crops.get(key)
        generic = crop is None
        if generic:
            crop = DEFAULT_CROP
        try:
            area = float(f.get("area", "0").split()[0])
        except ValueError:
            area = 0.0
        stage = STAGE_KC.get(status, 0.9)
        container = any(w in f.get("container", "").lower()
                        for w in ("pot", "container"))
        ml = deficit * crop["kc"] * stage * area * 1000 * (1.4 if container
                                                           else 1.0)

        L.append(f"## {pl['name']}")
        if generic:
            L.append("- Figures: generic defaults, this crop has no species file "
                     "yet, so treat the numbers below as rough")

        cname = f.get("container", "").split(",")[0].strip().lower()
        group = shared.get(cname, [])
        if deficit <= 0:
            L.append("- Water: skip, rain covers today's demand")
        elif len(group) > 1:
            L.append(f"- Water: {fmt_vol(ml)} for the whole {cname}, which it "
                     f"shares with {len(group) - 1} other "
                     f"{'plant' if len(group) == 2 else 'plants'}. One watering "
                     "serves them all, so do not repeat it per plant")
        elif status in ("sown", "germinating"):
            L.append(f"- Water: {fmt_vol(ml)}, split into two light passes to "
                     "keep the top 2 cm damp without washing seed")
        else:
            L.append(f"- Water: {fmt_vol(ml)}")

        if f.get("sown"):
            m = re.match(r"(\d{2})\.(\d{2})\.(\d{4})", f["sown"])
            if m and status in ("sown", "germinating"):
                dd, mm, yy = (int(x) for x in m.groups())
                sown = dt.date(yy, mm, dd)
                lo, hi = crop["germ"]
                age = (today - sown).days
                if age < lo:
                    L.append(f"- Germination: day {age}, expect first sprouts "
                             f"{(sown + dt.timedelta(days=lo)).isoformat()} to "
                             f"{(sown + dt.timedelta(days=hi)).isoformat()}")
                elif age <= hi:
                    L.append(f"- Germination: day {age}, inside the {lo} to "
                             f"{hi} day window, sprouts due now")
                else:
                    L.append(f"- Germination: day {age}, past the {hi} day "
                             "window. Nothing up means resow")

        over = [(t, v) for t, v in highs
                if v is not None and v > crop["bolt_f"]]
        if len(over) >= 2:
            peak_t, peak_v = max(over, key=lambda x: x[1])
            L.append(f"- Heat watch: {len(over)} of the next {len(highs)} days "
                     f"clear this crop's {crop['bolt_f']:.0f} F bolting "
                     f"threshold, peaking {peak_v:.0f} F on {peak_t}. Sustained "
                     "heat is what triggers bolting, not one warm afternoon")
        if wind and wind >= 30:
            L.append(f"- Wind: {wind:.0f} km/h dries containers and shreds "
                     "tender leaves. Check moisture twice today")
        L.append("")

    NOTES.mkdir(exist_ok=True)
    (NOTES / "today.md").write_text("\n".join(L))
    print(f"wrote {NOTES / 'today.md'} "
          f"(deficit {deficit:.1f} mm, sun {sun_h:.1f} h)")


if __name__ == "__main__":
    main()
