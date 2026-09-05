"""
generate_thumbs.py
------------------
Scans all album folders, automatically sanitizes & normalizes image filenames on disk
(fixing casing like .JPG -> .jpg, spaces, and special characters to prevent GitHub Pages 404 case errors),
extracts EXIF camera metadata (F-stop, Shutter speed, ISO, Focal length),
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
from PIL import Image, ExifTags

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
        temp_path = file_path.parent / f"_temp_rename_{clean_name}"
        if file_path.exists():
            file_path.rename(temp_path)
            if target_path.exists() and temp_path != target_path:
                target_path.unlink()
            temp_path.rename(target_path)
        print(f"  [renamed] {file_path.name} -> {clean_name}")
        return target_path
    return file_path


def format_shutter(val):
    if not val: return None
    try:
        v = float(val)
        if v <= 0: return None
        if v < 1.0:
            return f"1/{int(round(1.0 / v))}s"
        return f"{v:.1f}s" if v != int(v) else f"{int(v)}s"
    except Exception: return None


def format_fstop(val):
    if not val: return None
    try:
        v = float(val)
        return f"f/{int(v)}" if v == int(v) else f"f/{v:.1f}"
    except Exception: return None


def format_iso(val):
    if not val: return None
    try:
        if isinstance(val, (list, tuple)): val = val[0]
        return str(int(val))
    except Exception: return None


def format_focal(val):
    if not val: return None
    try:
        v = float(val)
        return f"{int(v)}mm" if v == int(v) else f"{v:.1f}mm"
    except Exception: return None


def extract_exif(img_path: Path) -> dict:
    """Extract and format EXIF camera metadata from image."""
    exif_info = {}
    try:
        with Image.open(img_path) as img:
            raw_exif = img._getexif()
            if raw_exif:
                tags = {ExifTags.TAGS.get(k, k): v for k, v in raw_exif.items() if k in ExifTags.TAGS}
                fstop = format_fstop(tags.get('FNumber'))
                shutter = format_shutter(tags.get('ExposureTime'))
                iso = format_iso(tags.get('ISOSpeedRatings') or tags.get('PhotographicSensitivity'))
                focal = format_focal(tags.get('FocalLength'))
                
                if fstop: exif_info['fstop'] = fstop
                if shutter: exif_info['shutter'] = shutter
                if iso: exif_info['iso'] = iso
                if focal: exif_info['focal'] = focal
    except Exception:
        pass
    return exif_info


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
    Sanitizes disk files, extracts EXIF, generates missing thumbnails, and syncs images.json.
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

    # 3. Update existing JSON entries for this album to match exact disk filenames & EXIF
    album_entries = data.get(album, [])
    disk_file_map = {f.name.lower(): f for f in all_images}
    
    updated_json_count = 0
    new_entries = []

    for entry in album_entries:
        old_name = entry.get("file", "")
        sanitized = sanitize_filename(old_name)
        
        if sanitized.lower() in disk_file_map:
            img_file = disk_file_map[sanitized.lower()]
            actual_name = img_file.name
            if entry["file"] != actual_name:
                print(f"  [sync json] {entry['file']} -> {actual_name}")
                entry["file"] = actual_name
                updated_json_count += 1
            
            # Refresh EXIF metadata
            exif = extract_exif(img_file)
            if exif:
                entry["exif"] = exif
            else:
                entry.pop("exif", None)

            new_entries.append(entry)

    tracked_files = {e["file"] for e in new_entries}

    # 4. Generate missing thumbnails and add untracked images
    new_added_count = 0
    for img_path in all_images:
        filename = img_path.name
        thumb_path = thumbs_dir / filename

        if not thumb_path.exists():
            print(f"  generating thumb for {filename} ...")
            make_thumbnail(img_path, thumb_path)

        if filename not in tracked_files:
            exif = extract_exif(img_path)
            new_entry = {"file": filename, "caption": "", "alt": ""}
            if exif:
                new_entry["exif"] = exif
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
        print(f"\n[Done] - {total_updates} update(s)/renames/EXIF synced to images and images.json")
    else:
        print("\n[Done] - All filenames, thumbnails, and EXIF metadata are perfectly normalized.")


if __name__ == "__main__":
    main()
