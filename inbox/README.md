# Inbox

Garden updates land here from the site's "Add a note" and "Add photos" buttons.

Notes are markdown holding a plant name, a kind of update, and free text:

    plant: Spinach
    kind: observation

    4 of the 6 are up. Two have yellow leaf edges.

`kind` is one of `observation`, `problem`, `identify`, or `did-something`.
Photos are better uploaded from the plant's own page, because that button files them
into `inbox/<plant>/` and they arrive already attached to that planting. A photo landing
loose in `inbox/` has to be identified before it can be filed.

Once assessed, photos move to `photos/<plant>/` and appear as a dated gallery on that
plant's page.

Anything here is waiting to be read. Once it has been assessed and written into
the diary, the file is removed from this folder, so an empty inbox means
everything is up to date and the results are on the Today and Diary pages.

This folder is the write path because committing a file needs no API token and
cannot be rate limited, unlike posting through the issues API.
