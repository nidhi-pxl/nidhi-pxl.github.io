"""
generate_thumbs.py
------------------
Scans all album folders, automatically sanitizes & normalizes image filenames on disk
(fixing casing like .JPG -> .jpg, spaces, and special characters to prevent GitHub Pages 404 case errors),
generates scaled thumbnails, and syncs/audits images.json entries.

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


def sanitize_filename(name: str) -> str:
    """
    Sanitize filename for GitHub Pages cross-platform compatibility:
    1. Lowercase file extension (.JPG -> .jpg, .JPEG -> .jpg).
    2. Lowercase filename stem and replace spaces with underscores.
    3. Remove invalid symbols or parentheses.
    """
    p = Path(name)
    ext = p.suffix.lower()
    if ext == ".jpeg":
        ext = ".jpg"
    stem = p.stem.lower().replace(" ", "_")
    stem = re.sub(r"[^\w\.-]", "", stem)
    return f"{stem}{ext}"


def normalize_disk_file(file_path: Path) -> Path:
    """Rename file on disk to sanitized lower-case filename if needed."""
    clean_name = sanitize_filename(file_path.name)
    if file_path.name != clean_name:
        target_path = file_path.parent / clean_name
        # Use a temporary intermediate filename to force Windows NTFS case-only renames
        temp_path = file_path.parent / f"_temp_rename_{clean_name}"
        if file_path.exists():
            file_path.rename(temp_path)
            if target_path.exists() and temp_path != target_path:
                target_path.unlink()
            temp_path.rename(target_path)
        print(f"  [renamed] {file_path.name} -> {clean_name}")
        return target_path
    return file_path


def make_thumbnail(src: Path, dst: Path):
    """Scale src to THUMB_WIDTH wide, save to dst, preserving aspect ratio."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as img:
        if img.mode in ("P", "RGBA"):
            img = img.convert("RGB")
        w, h = img.size
        new_h = int(h * THUMB_WIDTH / w)
        thumb = img.resize((THUMB_WIDTH, new_h), Image.LANCZOS)
        thumb.save(dst.with_suffix(".jpg"), "JPEG", quality=85, optimize=True)
    print(f"  + thumbnail -> {dst.relative_to(SCRIPT_DIR)}")


def process_album(album: str, data: dict) -> int:
    """
    Sanitizes disk files, generates missing thumbnails, and syncs images.json.
    Returns the number of updates made.
    """
    album_dir = IMAGES_DIR / album
    thumbs_dir = album_dir / "thumbs"

    if not album_dir.exists():
        print(f"[skip] {album}/ not found")
        return 0

    thumbs_dir.mkdir(exist_ok=True)

    # 1. Normalize all image files in the album directory
    raw_images = [f for f in album_dir.iterdir()
                  if f.is_file() and f.suffix.lower() in IMG_EXTS]
    
    all_images = []
    for img_path in raw_images:
        normalized_path = normalize_disk_file(img_path)
        all_images.append(normalized_path)

    all_images = sorted(all_images, key=lambda f: natural_sort_key(f.name))

    # 2. Normalize existing thumbnails in thumbs/
    if thumbs_dir.exists():
        for thumb_path in list(thumbs_dir.iterdir()):
            if thumb_path.is_file() and thumb_path.suffix.lower() in IMG_EXTS:
                normalize_disk_file(thumb_path)

    # 3. Update existing JSON entries for this album to match exact disk filenames
    album_entries = data.get(album, [])
    disk_file_map = {f.name.lower(): f.name for f in all_images}
    
    updated_json_count = 0
    new_entries = []

    for entry in album_entries:
        old_name = entry.get("file", "")
        sanitized = sanitize_filename(old_name)
        
        # If disk file exists with exact or case-matched name, sync it
        if sanitized.lower() in disk_file_map:
            actual_name = disk_file_map[sanitized.lower()]
            if entry["file"] != actual_name:
                print(f"  [sync json] {entry['file']} -> {actual_name}")
                entry["file"] = actual_name
                updated_json_count += 1
            new_entries.append(entry)

    # Track files already present in JSON
    tracked_files = {e["file"] for e in new_entries}

    # 4. Generate missing thumbnails and add untracked images
    new_added_count = 0
    for img_path in all_images:
        filename = img_path.name
        thumb_path = thumbs_dir / filename

        # Generate thumbnail if missing
        if not thumb_path.exists():
            print(f"  generating thumb for {filename} ...")
            make_thumbnail(img_path, thumb_path)

        if filename not in tracked_files:
            new_entry = {"file": filename, "caption": "", "alt": ""}
            new_entries.append(new_entry)
            tracked_files.add(filename)
            print(f"  + added to images.json -> {album}/{filename}")
            new_added_count += 1

    data[album] = new_entries
    return new_added_count + updated_json_count


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if JSON_PATH.exists():
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    target_albums = sys.argv[1:] if len(sys.argv) > 1 else ALBUMS
    invalid = [a for a in target_albums if a not in ALBUMS]
    if invalid:
        print(f"Unknown album(s): {', '.join(invalid)}")
        print(f"Valid albums: {', '.join(ALBUMS)}")
        sys.exit(1)

    total_updates = 0
    for album in target_albums:
        print(f"\n--- {album} ---")
        total_updates += process_album(album, data)

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    if total_updates:
        print(f"\n[Done] - {total_updates} update(s)/renames applied to images and images.json")
    else:
        print("\n[Done] - All filenames and images.json entries are perfectly normalized.")


if __name__ == "__main__":
    main()
