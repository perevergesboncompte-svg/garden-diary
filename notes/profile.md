# Garden Profile

## Location

- City: Costa Mesa, California, United States
- Timezone: America/Los_Angeles
- Language: English

## Climate

- USDA hardiness zone: 10b (derived, mean annual absolute minimum 39.1 F over 2015-2024)
- Sunset climate zone: 24 (coastal Southern California, marine influence)
- Climate type: frost_free
- last_frost_date: none

Because the climate type is `frost_free`, all seasonal timing comes from
`references/socal-frost-free.md`. Do NOT use the last-frost formulas in SKILL.md.
- first_frost_date: none
- Coldest temperature in the 10-year record: 36.6 F (2015-12-29)
- Days at or below 32 F, 2015-2024: 0
- Days at or below 36 F, 2015-2024: 0
- Chance of a night at or below 36 F: 6% in January, 2% in February, 5% in
  December, 0% every other month (NOAA 1991-2020 normals, Santa Ana KSNA)
- Chance of a night at or below 32 F: 0% in every month (same source)
- Hottest month: September, not July. Santa Ana averages 3.6 days above 90 F in
  September against 0.8 in July, because that is Santa Ana wind season. Coastal
  Costa Mesa is milder still, Newport Beach averaging 0.1 such days in September.

The 2015-2024 window this profile's monthly table was built from ran warm, so it
recorded no night at or below 36 F. The long-run normals above say a cold January
night is uncommon rather than impossible. Frost is the part that is genuinely
absent: zero probability in every month, in a 30-year record.

### Monthly normals (Open-Meteo ERA5, 2015-2024)

| Month | Sun hours/day | Daylight h | Sun % | Mean low F | Mean high F | Rain mm | ET0 mm | Irrigation deficit mm |
|-------|---------------|-----------|-------|-----------|------------|---------|--------|----------------------|
| Jan | 8.4 | 10.2 | 82% | 48.8 | 62.9 | 78.9 | 59.3 | -19.5 |
| Feb | 9.1 | 11.0 | 83% | 48.9 | 63.7 | 67.1 | 71.8 | 4.7 |
| Mar | 10.4 | 12.0 | 86% | 50.9 | 63.8 | 67.0 | 92.0 | 25.0 |
| Apr | 11.2 | 13.1 | 86% | 54.2 | 66.7 | 17.3 | 112.9 | 95.6 |
| May | 11.6 | 13.9 | 84% | 56.9 | 66.9 | 12.4 | 119.3 | 106.8 |
| Jun | 12.2 | 14.4 | 85% | 60.7 | 71.7 | 3.1 | 133.3 | 130.3 |
| Jul | 12.8 | 14.1 | 91% | 64.1 | 75.5 | 1.9 | 143.8 | 141.9 |
| Aug | 12.0 | 13.4 | 90% | 65.0 | 77.0 | 9.3 | 137.0 | 127.7 |
| Sep | 11.0 | 12.4 | 89% | 64.1 | 76.7 | 13.4 | 113.8 | 100.4 |
| Oct | 10.0 | 11.3 | 88% | 60.0 | 74.4 | 12.5 | 95.3 | 82.8 |
| Nov | 9.3 | 10.4 | 90% | 53.4 | 69.2 | 23.3 | 75.4 | 52.0 |
| Dec | 8.1 | 10.0 | 81% | 49.3 | 63.5 | 65.8 | 57.4 | -8.5 |

Deficit is ET0 minus rainfall, so it is the monthly irrigation budget per square metre
(1 mm = 1 litre/m2). December and January are the only months where rain covers demand.

The May and June sun percentages dip below the July figure because of the coastal marine
layer. Monthly averages understate it. On an individual day the fog can hold off sunrise
by three or four hours, which matters for any bed that only gets morning light. Use
`scripts/sun_hours.py` to measure a specific bed instead of reading these averages.

## Growing setup

- Growing format: 3 raised beds plus 1 container
- Bed size: 21 x 23 in each (0.31 m2 each, 0.94 m2 total)
- Bed depth: 8 to 10 inches
- Bed base: lined with landscape fabric or mesh, so water drains but roots stay in the
  bed. The 8 to 10 inches is the entire root zone, which keeps carrots restricted to
  short and round varieties and dill marginal. Drainage is not a concern here, so the
  winter-wet warning in references/socal-frost-free.md applies to the pot, not the beds.
- Container: 8 in diameter (0.032 m2)
- Sun window hours: 14-18
- Sun needed by cool-season crops: 3 to 6 hours (Maryland Extension), so this site's
  measured 4 to 5 hours is inside the range for leafy greens and marginal for roots,
  which Colorado State puts at 8 hours
- Indoor seedling space: unknown
- Native soil type: unknown
- Compost system: unknown
- Existing trees, shrubs, perennials: unknown
- Substrate: unknown
- Experience level: unknown
- Preferred seed suppliers: unknown

### Measured sun exposure

Reported window: shaded all morning, direct sun from about 13:30 until roughly one
hour before sunset. Everything shares this one exposure.

| Period | Direct sun | Open sky | Shading cost | Class |
|--------|-----------|----------|-------------|-------|
| Mid-September (measured 09-18 Sep) | 4.0 to 4.9 h | 9.0 h | 45 to 56% | part sun |
| December (measured over Dec 2025, window 13:00 to 16:00) | 2.5 h | 7.5 h | 67% | part shade |

Two things follow, and both matter more than the raw hour count.

**The sun arrives on the wrong half of the day.** Cool-season greens want morning sun
and afternoon shade. This site is the exact inverse: it misses the mild morning and
takes the full afternoon heat load. Treat heat stress and bolting as the standing risk
here, not insufficient light.

**Winter is worse than the December figure suggests.** The 2.5 h number holds the
13:30 start fixed, but a lower winter sun throws longer shadows, so whatever blocks
the morning will hold the shade later than 13:30 in December, not earlier. Re-measure
in December with `scripts/sun_hours.py` after observing the actual arrival time. Since
winter is the productive season in this climate, this is the site's main limitation.

Nothing fruiting (tomato, pepper, squash, cucumber, basil) will produce well at this
exposure. Leafy crops, roots, and most herbs will.

Maryland Extension puts cool-season crops at 3 to 6 hours of direct sun and
warm-season crops at 6 to 8, which places this site inside the range for everything
currently planted and outside it for anything fruiting. Colorado State disagrees
upward on individual crops, asking 8 hours for radish, beet, kale and onion against 6
for lettuce, spinach and chard. Both are extension services and neither is wrong, so
read 4 to 5 measured hours as comfortable for leafy greens and marginal for roots.

## Integrations

- tasks_backend: none
