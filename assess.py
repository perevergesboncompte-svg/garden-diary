"""Measure garden photos in inbox/ and file them into photos/ with a record."""

import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent
INBOX = ROOT / "inbox"
PHOTOS = ROOT / "photos"

A_STAR_MAX = -8.0
MIN_BLOB_PX = 40
LONG_EDGE = 1400
MERGE_PX = 9
HUE_SHIFT_FLOOR_DEG = 4.0


def load(path):
    """Read an image and downscale its long edge to LONG_EDGE."""
    bgr = cv2.imread(str(path))
    if bgr is None:
        raise ValueError(f"unreadable image: {path}")
    h, w = bgr.shape[:2]
    if max(h, w) > LONG_EDGE:
        s = LONG_EDGE / max(h, w)
        bgr = cv2.resize(bgr, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    return bgr


def correct_colour(path_img):
    """Colour-correct from an in-frame ColorChecker, or pass through uncorrected.

    Returns:
        The image and the method name, which gates cross-session comparison.
    """
    det = cv2.mcc.CCheckerDetector_create()
    if det.process(path_img, cv2.mcc.MCC24):
        chk = det.getBestColorChecker()
        if chk is not None:
            src = chk.getChartsRGB()[:, 1].reshape(-1, 3) / 255.0
            model = cv2.ccm.ColorCorrectionModel(
                src.reshape(-1, 1, 3).astype(np.float64), cv2.ccm.COLORCHECKER_Macbeth)
            model.run()
            rgb = cv2.cvtColor(path_img, cv2.COLOR_BGR2RGB).astype(np.float64) / 255.0
            out = np.clip(model.infer(rgb) * 255.0, 0, 255).astype(np.uint8)
            return cv2.cvtColor(out, cv2.COLOR_RGB2BGR), "colorchecker"
    return path_img, "uncorrected"


def vegetation_mask(bgr):
    """Mask green foliage by thresholding the LAB green-red opponent channel."""
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    return ((lab[:, :, 1] - 128.0) < A_STAR_MAX)


def blobs(mask):
    """Return foliage areas per plant, largest first, merging split fragments.

    Arguments:
        mask: Boolean foliage mask, whose own pixel counts set the size floor so
            that merging cannot promote a fragment past it.
    """
    m = mask.astype(np.uint8)
    grouped = cv2.dilate(m, np.ones((MERGE_PX, MERGE_PX), np.uint8))
    n, labelled, _, _ = cv2.connectedComponentsWithStats(grouped, 8)
    if n < 2:
        return []
    true_area = np.bincount(labelled[mask].ravel(), minlength=n)
    areas = [int(true_area[i]) for i in range(1, n) if true_area[i] >= MIN_BLOB_PX]
    return sorted(areas, reverse=True)


def circular_hue(hue_deg):
    """Return the circular mean and standard deviation of hue angles in degrees.

    Arguments:
        hue_deg: Hue angles on the 0-360 scale, which wrap and so cannot be
            averaged arithmetically.
    """
    rad = np.deg2rad(hue_deg.astype(np.float64))
    c, s = np.cos(rad).mean(), np.sin(rad).mean()
    mean = np.rad2deg(np.arctan2(s, c)) % 360.0
    r = min(1.0, (c * c + s * s) ** 0.5)
    sd = np.rad2deg((-2.0 * np.log(r)) ** 0.5) if r > 0 else 180.0
    return float(mean), float(sd)


def colour_metrics(bgr, mask):
    """Measure foliage colour, separating the light-robust hue from the rest.

    Returns:
        Mapping with hue at the top level and light-dependent indices nested
        under light_dependent, empty when the mask holds no pixels.
    """
    if not mask.any():
        return {}
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    hue = hsv[:, :, 0][mask].astype(np.float32) * 2.0
    sat = hsv[:, :, 1][mask].astype(np.float32) / 255.0
    val = hsv[:, :, 2][mask].astype(np.float32) / 255.0
    hue_mean, hue_sd = circular_hue(hue)
    dgci = (((hue - 60.0) / 60.0) + (1.0 - sat) + (1.0 - val)) / 3.0
    b, g, r = [bgr[:, :, i][mask].astype(np.float32) for i in range(3)]
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    return {
        "hue_circular_mean": round(hue_mean, 2),
        "hue_circular_sd": round(hue_sd, 2),
        "light_dependent": {
            "dgci": round(float(dgci.mean()), 4),
            "saturation": round(float(sat.mean()), 4),
            "value": round(float(val.mean()), 4),
            "g_minus_b": round(float((g - b).mean()), 2),
            "lab_a": round(float((lab[:, :, 1][mask] - 128.0).mean()), 2),
            "lab_b": round(float((lab[:, :, 2][mask] - 128.0).mean()), 2),
        },
    }


def assess(path):
    """Measure one photo and return its record."""
    bgr, method = correct_colour(load(path))
    mask = vegetation_mask(bgr)
    areas = blobs(mask)
    rec = {
        "colour_method": method,
        "pixels": int(mask.size),
        "cover_pct": round(100.0 * float(mask.sum()) / mask.size, 3),
        "blob_count": len(areas),
        "blob_area_median": int(np.median(areas)) if areas else 0,
        "blob_area_largest": areas[0] if areas else 0,
    }
    rec.update(colour_metrics(bgr, mask))
    return rec


def prior(slug):
    """Return the most recent earlier record for a plant, or None."""
    d = PHOTOS / slug
    if not d.is_dir():
        return None
    for f in sorted(d.glob("*.json"), reverse=True):
        try:
            return json.loads(f.read_text())
        except ValueError:
            continue
    return None


def deltas(rec, was):
    """Compare a record with its predecessor, gating hue on the illumination floor."""
    if not was:
        return {}
    out = {}
    for k in ("cover_pct", "blob_count", "blob_area_median"):
        if k in rec and k in was:
            out[f"d_{k}"] = round(rec[k] - was[k], 3)
    if "hue_circular_mean" in rec and "hue_circular_mean" in was:
        d = (rec["hue_circular_mean"] - was["hue_circular_mean"] + 180.0) % 360.0 - 180.0
        out["d_hue_deg"] = round(d, 2)
        out["hue_changed"] = abs(d) >= HUE_SHIFT_FLOOR_DEG
    return out


def file_photo(src, slug, stamp):
    """Move a photo into photos/<slug>/ under a dated name and return the path."""
    d = PHOTOS / slug
    d.mkdir(parents=True, exist_ok=True)
    dst = d / f"{stamp}{src.suffix.lower()}"
    n = 2
    while dst.exists():
        dst = d / f"{stamp}-{n}{src.suffix.lower()}"
        n += 1
    shutil.move(str(src), str(dst))
    return dst


def main():
    stamp = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", stamp):
        sys.exit(f"date must be YYYY-MM-DD, got {stamp!r}")
    if not INBOX.is_dir():
        sys.exit("no inbox/")
    found = 0
    for sub in sorted(p for p in INBOX.iterdir() if p.is_dir()):
        for img in sorted(f for f in sub.iterdir()
                          if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")):
            rec = assess(img)
            rec["date"] = stamp
            rec.update(deltas(rec, prior(sub.name)))
            dst = file_photo(img, sub.name, stamp)
            dst.with_suffix(".json").write_text(json.dumps(rec, indent=2) + "\n")
            found += 1
            print(f"{sub.name}/{dst.name}  cover {rec['cover_pct']}%  "
                  f"plants {rec['blob_count']}  "
                  f"hue {rec.get('hue_circular_mean', '-')}  "
                  f"[{rec['colour_method']}]")
    print(f"{found} photo(s) assessed" if found else "inbox empty")


if __name__ == "__main__":
    main()
