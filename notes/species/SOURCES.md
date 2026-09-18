# Where the species figures come from

Every figure in the files beside this one ends with its source in square brackets,
so any number can be traced and corrected. These are the sources, and the licence
terms this project has to honour.

## EcoCrop [EcoCrop]

FAO EcoCrop, redistributed by OpenCLIM/UKCEH at
https://github.com/OpenCLIM/ecocrop (DOI 10.5281/zenodo.10843625).
Licensed under the Open Government Licence v3, which permits redistribution and
adaptation with attribution.

Supplies soil pH, temperature bands, killing temperature, field cycle length and
soil-depth class.

Two cautions carried into the data. Its cycle length is a whole-field figure and
runs longer than days to first pick, so it is labelled as such rather than passed
off as a harvest date. Its soil-depth field describes the soil profile a field
needs, not how deep the roots go, which is why radish reads deeper than lettuce:
it is labelled and must not be read as a pot size.

The carrot row is `Daucus carota`, the wild species, so its pH span of 4.2 to 8.7
is wider than a garden cultivar's real tolerance.

## OpenFarm [OpenFarm]

Recovered from the shuttered OpenFarm.cc by
https://github.com/thefullnacho/openfarm-crops-rescue, dedicated to the public
domain under CC0 1.0. Each record carries a Wayback URL for the page it came from.

Supplies row spacing, plant spacing and sun category.

The rescuer's own warning applies: OpenFarm was community-edited and degraded over
time. Roughly one in six records that carry both spacing fields has them
conflated, so the 15 crops here were checked by hand rather than bulk-imported.

## PlantVarietyDB [PlantVarietyDB]

https://github.com/bripatch/plant-variety-database, CC BY 4.0, by Wind River
Greens.

Supplies days to germination, days to harvest and container suitability, each as a
median across that crop's varieties with the sample size stated, because some
crops have only one or two entries.

Only its numeric columns are used. Its prose is derived substantially from Johnny's
Selected Seeds and NC State Extension, neither of which licensed it for
redistribution, so none of that text appears here. Its planting calendar is not
used at all: 5.7% of its rows end the harvest before it starts.

## powerplant [powerplant]

https://github.com/Ecohackerfarm/powerplant, MIT, `db/matrix.js`. 274 hand-written
companion pairs with polarity, so antagonists are distinguishable from friends.

Pairings are filtered to crops in this library. The raw matrix associates
vegetables with orchard trees, which is true enough in a permaculture guild and
useless in a 21 by 23 inch bed.

## INRAE [INRAE]

INRAE "Pepiniere-Mesclun" v1.1, DOI 10.57745/IQVM2I, by Kevin Morel, at
entrepot.recherche.data.gouv.fr. Licence Ouverte / Etalab 2.0, which permits reuse,
adaptation and commercial use with attribution.

Supplies rooting depth, nutrient demand, minimum rotation gap and the soils and
preceding crop families to avoid. Every value in the source carries its own inline
citation, and the workbook's reference sheet resolves them.

This is the only source found with real rooting depth. Its three-level scale is the
native one rather than a relabelling of something else, and the values spread
sensibly across the 75 crops it covers. Rooting depth is what actually decides
whether a crop suits a raised bed, so it matters more here than any other imported
field.

It is a French market-garden dataset, calibrated to the oceanic climate of
north-west France, so read its rotation advice as sound and its timing as foreign.
It omits the perennial culinary herbs, which is why dill has no entry.

## hand-entered [hand-entered]

Sowing depth, bolting threshold, raised-bed verdict, succession interval and
repeat-harvest behaviour.

These are hand-entered because no open dataset contains them, which was checked
across fourteen candidate sources rather than assumed. Beware one trap in this area:
a dataset that appears to carry rooting depth holds EcoCrop's three soil-depth
buckets converted to inches, giving three distinct values across 227 crops dressed
up as one-decimal measurements.

Treat these as the least certain figures here, and correct them from your own
results. A measured value from your own bed beats any of these sources, because it
carries your soil, your aspect and your marine layer.

## Deliberately excluded

Growable Ground Plant Database, for being CC BY-NC: the NonCommercial term would
travel into everything built on it. Its unique fields were worth having, but three
of its columns do not survive inspection, and its pH and soil depth are copied from
EcoCrop, so agreement between the two proves nothing.

Extension-service tables and Knott's Handbook, which hold the best figures and none
of the rights. US land-grant extension output is university copyright, not federal
public domain. Read them, cite them, do not copy their tables.
