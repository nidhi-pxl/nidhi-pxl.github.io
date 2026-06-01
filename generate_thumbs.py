"""
generate_thumbs.py
------------------
Scans all 6 album folders for images that don't yet have a thumbnail,
generates thumbnails scaled to THUMB_WIDTH px wide (preserving aspect ratio),
and appends new entries to images.json.

Usage:
    python generate_thumbs.py              # process all albums
    python generate_thumbs.py animals      # process one album only

Requirements:
    pip install Pillow
"""

import json
import os
import re
import sys
from pathlib import Path
from PIL import Image

# ── Config ────────────────────────────────────────────────────────────────────

SCRIPT_DIR   = Path(__file__).parent
IMAGES_DIR   = SCRIPT_DIR / "images"
JSON_PATH    = SCRIPT_DIR / "images.json"
THUMB_WIDTH  = 400
ALBUMS       = ["animals", "astro", "flowers", "insects", "landscapes", "skies"]
IMG_EXTS     = {".jpg", ".jpeg", ".png", ".webp"}

# ── Helpers ───────────────────────────────────────────────────────────────────

def natural_sort_key(name: str):
    """Sort filenames so animals9.jpg < animals10.jpg."""
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r"(\d+)", name)]


def make_thumbnail(src: Path, dst: Path):
    """Scale src to THUMB_WIDTH wide, save to dst, preserving aspect ratio."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as img:
        # Convert palette / RGBA images so JPEG save works
        if img.mode in ("P", "RGBA"):
            img = img.convert("RGB")
        w, h = img.size
        new_h = int(h * THUMB_WIDTH / w)
        thumb = img.resize((THUMB_WIDTH, new_h), Image.LANCZOS)
        # Always save as JPEG regardless of source extension
        thumb.save(dst.with_suffix(".jpg"), "JPEG", quality=85, optimize=True)
    print(f"  ✓ thumbnail → {dst.relative_to(SCRIPT_DIR)}")


def process_album(album: str, data: dict) -> int:
    """
    Find images in album folder that have no thumbnail yet,
    generate thumbnails, and append entries to data[album].
    Returns the number of new images added.
    """
    album_dir = IMAGES_DIR / album
    thumbs_dir = album_dir / "thumbs"

    if not album_dir.exists():
        print(f"[skip] {album}/ not found")
        return 0

    thumbs_dir.mkdir(exist_ok=True)

    # Files already tracked in JSON
    existing_files = {entry["file"] for entry in data.get(album, [])}

    # All image files in the album folder (not in thumbs/)
    all_images = sorted(
        [f for f in album_dir.iterdir()
         if f.is_file() and f.suffix.lower() in IMG_EXTS],
        key=lambda f: natural_sort_key(f.name)
    )

    new_count = 0
    for img_path in all_images:
        filename = img_path.stem + ".jpg"   # normalise to .jpg name
        thumb_path = thumbs_dir / filename

        # Generate thumbnail if missing
        if not thumb_path.exists():
            print(f"  generating thumb for {img_path.name} …")
            make_thumbnail(img_path, thumb_path)

        # Append to JSON if not already tracked
        if img_path.name not in existing_files and filename not in existing_files:
            entry = {"file": filename, "caption": "", "alt": ""}
            data.setdefault(album, []).append(entry)
            print(f"  + added to images.json → {album}/{filename}")
            new_count += 1

    return new_count


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # Load existing JSON
    if JSON_PATH.exists():
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    # Decide which albums to process
    target_albums = sys.argv[1:] if len(sys.argv) > 1 else ALBUMS
    invalid = [a for a in target_albums if a not in ALBUMS]
    if invalid:
        print(f"Unknown album(s): {', '.join(invalid)}")
        print(f"Valid albums: {', '.join(ALBUMS)}")
        sys.exit(1)

    total_new = 0
    for album in target_albums:
        print(f"\n── {album} ──")
        total_new += process_album(album, data)

    # Write updated JSON back (preserve formatting)
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    if total_new:
        print(f"\n✅ Done — {total_new} new image(s) added to images.json")
        print("   Open images.json to fill in captions and alt text for new entries.")
    else:
        print("\n✅ Done — no new images found.")


if __name__ == "__main__":
    main()
