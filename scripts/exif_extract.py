"""Extract GPS coordinates and capture timestamp from smartphone photo EXIF metadata.

Usable both as a library (import and call `extract_gps_and_timestamp`) and as a
CLI that scans a folder of raw images and writes a manifest CSV, so the rest of
the pipeline (annotation, training, reporting) has a location/time index before
any dataset tooling touches the images.
"""
import argparse
import csv
from datetime import datetime
from pathlib import Path

from PIL import ExifTags, Image

_TAGS = {v: k for k, v in ExifTags.TAGS.items()}
_GPS_TAGS = {v: k for k, v in ExifTags.GPSTAGS.items()}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic"}


def _dms_to_decimal(dms, ref):
    degrees, minutes, seconds = (float(v) for v in dms)
    decimal = degrees + minutes / 60 + seconds / 3600
    if ref in ("S", "W"):
        decimal = -decimal
    return decimal


def _parse_gps(gps_info):
    if not gps_info or "GPSLatitude" not in gps_info or "GPSLongitude" not in gps_info:
        return None, None
    lat = _dms_to_decimal(gps_info["GPSLatitude"], gps_info.get("GPSLatitudeRef", "N"))
    lon = _dms_to_decimal(gps_info["GPSLongitude"], gps_info.get("GPSLongitudeRef", "E"))
    return lat, lon


def extract_gps_and_timestamp(image_path: str) -> dict:
    """Return {"latitude", "longitude", "timestamp"} for a single image.

    Any field that isn't present in the EXIF data (e.g. GPS was disabled, or
    the photo was stripped of metadata) is returned as None rather than
    raising, since partial metadata is common and callers decide how strict
    to be.
    """
    result = {"latitude": None, "longitude": None, "timestamp": None}

    with Image.open(image_path) as img:
        exif_raw = img.getexif()
        if not exif_raw:
            return result

        exif = {ExifTags.TAGS.get(tag_id, tag_id): value for tag_id, value in exif_raw.items()}

        gps_ifd = exif_raw.get_ifd(_TAGS.get("GPSInfo", 0x8825)) if "GPSInfo" in exif else None
        if gps_ifd:
            gps_info = {ExifTags.GPSTAGS.get(tag_id, tag_id): value for tag_id, value in gps_ifd.items()}
            result["latitude"], result["longitude"] = _parse_gps(gps_info)

        timestamp_str = exif.get("DateTimeOriginal") or exif.get("DateTime")
        if timestamp_str:
            try:
                result["timestamp"] = datetime.strptime(timestamp_str, "%Y:%m:%d %H:%M:%S").isoformat()
            except ValueError:
                result["timestamp"] = timestamp_str

    return result


def scan_directory(images_dir: str, manifest_path: str) -> int:
    """Walk `images_dir`, extract EXIF for every image, write a manifest CSV.

    Returns the number of images written to the manifest.
    """
    images_dir = Path(images_dir)
    rows = []
    for path in sorted(images_dir.rglob("*")):
        if path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        metadata = extract_gps_and_timestamp(str(path))
        rows.append({"filename": str(path.relative_to(images_dir)), **metadata})

    manifest_path = Path(manifest_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["filename", "latitude", "longitude", "timestamp"])
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images-dir", default="raw_images", help="Folder of raw smartphone photos")
    parser.add_argument("--manifest", default="raw_images/manifest.csv", help="Output CSV path")
    args = parser.parse_args()

    count = scan_directory(args.images_dir, args.manifest)
    print(f"Wrote {count} entries to {args.manifest}")


if __name__ == "__main__":
    main()
