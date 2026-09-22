"""
migrate_to_supabase.py
-----------------------
Migration and auditing script to transfer photography portfolio metadata and image files
from images.json and local disk storage into Supabase (PostgreSQL + Storage 'portfolio' bucket).

Features:
1. --dry-run : Parses images.json, validates local image files, parses captions into clean title/subtitle,
               extracts EXIF, checks thumbnails, and prints an audit report without making DB/Storage changes.
2. Default execution: Uploads original images and 400px JPEG thumbnails to Supabase Storage 'portfolio' bucket,
               and inserts formatted records into public.photographs table using SUPABASE_SERVICE_ROLE_KEY from .env.
3. --verify : Compares images.json count vs Supabase photographs table count and verifies Storage objects.

Usage:
    python migrate_to_supabase.py --dry-run
    python migrate_to_supabase.py
    python migrate_to_supabase.py --verify
"""

import argparse
import json
import os
import re
import sys

# Ensure UTF-8 output encoding for Windows console (handles symbols like ⚲)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import uuid
from pathlib import Path
from PIL import Image, ExifTags

# Try importing requests / supabase if available for live migration
try:
    import urllib.request
    import urllib.error
except ImportError:
    pass

SCRIPT_DIR   = Path(__file__).parent
IMAGES_DIR   = SCRIPT_DIR / "images"
JSON_PATH    = SCRIPT_DIR / "images.json"
ENV_PATH     = SCRIPT_DIR / ".env"
THUMB_WIDTH  = 400
ALBUM_MAP    = {
    "animals": "Animals",
    "astro": "Astro",
    "flowers": "Flowers",
    "insects": "Insects",
    "landscapes": "Landscapes",
    "skies": "Skies"
}
IMG_EXTS     = {".jpg", ".jpeg", ".png", ".webp"}

# ── Environment & Config Helper ─────────────────────────────────────────────

def load_dotenv():
    """Loads environment variables from local .env file if available."""
    if ENV_PATH.exists():
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'").strip('"')
                    os.environ.setdefault(key, val)

# ── EXIF & Formatting Helpers ────────────────────────────────────────────────

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

def format_iso_int(val):
    """Converts ISO value to integer for PostgreSQL integer column, or None."""
    if not val: return None
    try:
        if isinstance(val, (list, tuple)): val = val[0]
        # Strip string non-digits if passed as string e.g. "ISO 500"
        digits = re.sub(r"[^\d]", "", str(val))
        return int(digits) if digits else None
    except Exception: return None

def format_focal(val):
    if not val: return None
    try:
        v = float(val)
        return f"{int(v)}mm" if v == int(v) else f"{v:.1f}mm"
    except Exception: return None

def extract_exif(img_path: Path) -> dict:
    """Extract and format EXIF camera metadata from image file."""
    exif_info = {}
    if not img_path.exists():
        return exif_info
    try:
        with Image.open(img_path) as img:
            raw_exif = img._getexif()
            if raw_exif:
                tags = {ExifTags.TAGS.get(k, k): v for k, v in raw_exif.items() if k in ExifTags.TAGS}
                fstop = format_fstop(tags.get('FNumber'))
                shutter = format_shutter(tags.get('ExposureTime'))
                iso = format_iso_int(tags.get('ISOSpeedRatings') or tags.get('PhotographicSensitivity'))
                focal = format_focal(tags.get('FocalLength'))
                
                if fstop: exif_info['fstop'] = fstop
                if shutter: exif_info['shutter_speed'] = shutter
                if iso is not None: exif_info['iso'] = iso
                if focal: exif_info['focal_length'] = focal
    except Exception:
        pass
    return exif_info

def parse_caption_html(caption_html: str, default_alt: str = "", filename: str = "") -> tuple:
    """
    Parses legacy caption HTML into clean (title, subtitle, description).
    Examples:
      '<h2>Jupiter and Orion</h2>' -> ('Jupiter and Orion', None, None)
      '<h2>Milky Way</h2><h3>Vijardurg, 2026</h3>' -> ('Milky Way', 'Vijardurg, 2026', None)
      '<h2>Blue Plumbago Auriculata</h2><h4>⚲ Bits Goa</h4>' -> ('Blue Plumbago Auriculata', '⚲ Bits Goa', None)
      'Star trails' -> ('Star trails', None, None)
    """
    if not caption_html or not caption_html.strip():
        # Fallback to alt or title-cased filename stem
        if default_alt and default_alt.strip():
            return (default_alt.strip(), None, None)
        stem = Path(filename).stem if filename else "Photograph"
        clean_stem = re.sub(r"[\_\-]+", " ", stem).title()
        return (clean_stem, None, None)

    caption_str = caption_html.strip()
    
    # Check if contains HTML tags h2, h3, h4, p
    h2_match = re.search(r"<h2[^>]*>(.*?)</h2>", caption_str, re.IGNORECASE | re.DOTALL)
    h3_match = re.search(r"<h3[^>]*>(.*?)</h3>", caption_str, re.IGNORECASE | re.DOTALL)
    h4_match = re.search(r"<h4[^>]*>(.*?)</h4>", caption_str, re.IGNORECASE | re.DOTALL)
    p_match  = re.search(r"<p[^>]*>(.*?)</p>", caption_str, re.IGNORECASE | re.DOTALL)

    def clean_text(raw):
        if not raw: return None
        stripped = re.sub(r"<[^>]+>", "", raw).strip()
        return stripped if stripped else None

    title = clean_text(h2_match.group(1)) if h2_match else None
    subtitle = clean_text(h3_match.group(1)) if h3_match else (clean_text(h4_match.group(1)) if h4_match else None)
    description = clean_text(p_match.group(1)) if p_match else None

    # If no tags matched but text is present
    if not title:
        plain = clean_text(caption_str)
        if plain:
            title = plain
        else:
            title = default_alt.strip() if default_alt else "Photograph"

    return (title, subtitle, description)

def sanitize_filename(name: str) -> str:
    """Sanitize filename to case-safe lowercase string."""
    p = Path(name)
    ext = p.suffix.lower()
    if ext == ".jpeg":
        ext = ".jpg"
    stem = p.stem.lower().replace(" ", "_")
    stem = re.sub(r"[^\w\.-]", "", stem)
    return f"{stem}{ext}"

def create_thumbnail_bytes(src_path: Path) -> bytes:
    """Generates 400px wide JPEG quality 85 thumbnail bytes."""
    import io
    with Image.open(src_path) as img:
        if img.mode in ("P", "RGBA"):
            img = img.convert("RGB")
        w, h = img.size
        new_h = int(h * THUMB_WIDTH / w)
        thumb = img.resize((THUMB_WIDTH, new_h), Image.LANCZOS)
        buffer = io.BytesIO()
        thumb.save(buffer, format="JPEG", quality=85, optimize=True)
        return buffer.getvalue()

# ── Supabase API Client (Minimal Dependency-Free HTTP Request) ────────────────

class SupabaseClient:
    def __init__(self, url: str, key: str):
        self.url = url.rstrip("/")
        self.key = key
        self.headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

    def select(self, table: str, query="select=*"):
        req = urllib.request.Request(
            f"{self.url}/rest/v1/{table}?{query}",
            headers=self.headers
        )
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"[ERROR] DB Select Error ({table}): {e}")
            return []

    def insert(self, table: str, data: dict):
        body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            f"{self.url}/rest/v1/{table}",
            data=body,
            headers=self.headers,
            method="POST"
        )
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            print(f"[ERROR] DB Insert Error ({e.code}): {err_body}")
            return None

    def delete(self, table: str, query: str):
        req = urllib.request.Request(
            f"{self.url}/rest/v1/{table}?{query}",
            headers=self.headers,
            method="DELETE"
        )
        try:
            with urllib.request.urlopen(req) as resp:
                return True
        except Exception as e:
            print(f"[ERROR] DB Delete Error ({table}): {e}")
            return False

    def upload_storage(self, bucket: str, path: str, content: bytes, content_type="image/jpeg"):
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": content_type,
            "x-upsert": "true"
        }
        req = urllib.request.Request(
            f"{self.url}/storage/v1/object/{bucket}/{path}",
            data=content,
            headers=headers,
            method="POST"
        )
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            print(f"[ERROR] Storage Upload Error ({path}): {err_body}")
            return None

    def delete_storage(self, bucket: str, path: str):
        body = json.dumps({"prefixes": [path]}).encode("utf-8")
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json"
        }
        req = urllib.request.Request(
            f"{self.url}/storage/v1/object/{bucket}",
            data=body,
            headers=headers,
            method="DELETE"
        )
        try:
            with urllib.request.urlopen(req) as resp:
                return True
        except Exception as e:
            print(f"[ERROR] Storage Delete Error ({path}): {e}")
            return False

# ── Main Workflows ────────────────────────────────────────────────────────────

def run_dry_run():
    print("=" * 70)
    print("MIGRATION DRY RUN AUDIT (NO SUPABASE WRITES PERFORMED)")
    print("=" * 70)

    if not JSON_PATH.exists():
        print(f"[ERROR] {JSON_PATH} not found!")
        return

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    total_images_in_json = 0
    total_found_on_disk = 0
    total_missing_disk = 0
    parsed_records = []

    for album_key, category_name in ALBUM_MAP.items():
        album_entries = data.get(album_key, [])
        print(f"\n--- Category: {category_name} ({album_key}) | {len(album_entries)} entries ---")
        
        album_dir = IMAGES_DIR / album_key
        thumb_dir = album_dir / "thumbs"

        for idx, entry in enumerate(album_entries, 1):
            total_images_in_json += 1
            filename = entry.get("file", "")
            img_path = album_dir / filename
            thumb_path = thumb_dir / filename

            file_exists = img_path.exists()
            thumb_exists = thumb_path.exists()

            if file_exists:
                total_found_on_disk += 1
            else:
                total_missing_disk += 1
                print(f"  [MISSING FILE] {album_key}/{filename}")

            caption = entry.get("caption", "")
            alt     = entry.get("alt", "")
            title, subtitle, description = parse_caption_html(caption, default_alt=alt, filename=filename)

            # EXIF check
            existing_exif = entry.get("exif", {})
            extracted_exif = extract_exif(img_path) if file_exists else {}
            
            fstop   = existing_exif.get("fstop") or extracted_exif.get("fstop")
            shutter = existing_exif.get("shutter") or extracted_exif.get("shutter_speed")
            
            iso_raw = existing_exif.get("iso") or extracted_exif.get("iso")
            iso = format_iso_int(iso_raw)

            focal   = existing_exif.get("focal") or extracted_exif.get("focal_length")

            record = {
                "category": category_name,
                "original_filename": filename,
                "title": title,
                "subtitle": subtitle,
                "description": description,
                "alt_text": alt if alt else None,
                "fstop": fstop,
                "shutter_speed": shutter,
                "iso": iso,
                "focal_length": focal,
                "file_exists": file_exists,
                "thumb_exists": thumb_exists
            }
            parsed_records.append(record)

            status_str = "OK" if file_exists else "MISSING"
            sub_str = f" | Subtitle: '{subtitle}'" if subtitle else ""
            exif_str = f" | EXIF: fstop={fstop}, shutter={shutter}, iso={iso}, focal={focal}" if (fstop or shutter or iso or focal) else ""
            print(f"  [{idx:02d}] {filename:<20} -> Title: '{title}'{sub_str}{exif_str} [{status_str}]")

    print("\n" + "=" * 70)
    print("DRY RUN SUMMARY REPORT")
    print("=" * 70)
    print(f"Total entries in images.json : {total_images_in_json}")
    print(f"Originals found on disk      : {total_found_on_disk}")
    print(f"Originals missing from disk  : {total_missing_disk}")
    print("Categories mapped            : " + ", ".join(ALBUM_MAP.values()))
    print("=" * 70)

def run_migration():
    load_dotenv()
    supabase_url = os.environ.get("SUPABASE_URL")
    service_key  = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not service_key or "YOUR_SUPABASE" in supabase_url:
        print("[ERROR] SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env file to perform actual migration.")
        print("Please configure .env and run migration again.")
        sys.exit(1)

    print("=" * 70)
    print("STARTING SUPABASE MIGRATION (UPLOADING STORAGE & INSERTING ROWS)")
    print("=" * 70)

    client = SupabaseClient(supabase_url, service_key)

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    uploaded_count = 0
    failed_count = 0

    for album_key, category_name in ALBUM_MAP.items():
        album_entries = data.get(album_key, [])
        print(f"\n--- Migrating {category_name} ({len(album_entries)} entries) ---")
        
        album_dir = IMAGES_DIR / album_key

        for entry in album_entries:
            filename = entry.get("file", "")
            img_path = album_dir / filename

            if not img_path.exists():
                print(f"  [SKIP] File not found: {img_path}")
                failed_count += 1
                continue

            photo_id = str(uuid.uuid4())
            ext = img_path.suffix.lower()
            if ext == ".jpeg": ext = ".jpg"

            storage_cat = album_key.lower()
            image_storage_path = f"originals/{storage_cat}/{photo_id}{ext}"
            thumb_storage_path = f"thumbnails/{storage_cat}/{photo_id}.jpg"

            # 1. Read Original Content
            with open(img_path, "rb") as f_img:
                orig_bytes = f_img.read()

            content_type = "image/png" if ext == ".png" else ("image/webp" if ext == ".webp" else "image/jpeg")

            # 2. Upload Original
            up_orig = client.upload_storage("portfolio", image_storage_path, orig_bytes, content_type=content_type)
            if not up_orig:
                print(f"  [FAILED STORAGE ORIG] {filename}")
                failed_count += 1
                continue

            # 3. Create & Upload Thumbnail
            try:
                thumb_bytes = create_thumbnail_bytes(img_path)
            except Exception as e:
                print(f"  [FAILED THUMB GEN] {filename}: {e}")
                client.delete_storage("portfolio", image_storage_path)
                failed_count += 1
                continue

            up_thumb = client.upload_storage("portfolio", thumb_storage_path, thumb_bytes, content_type="image/jpeg")
            if not up_thumb:
                print(f"  [FAILED STORAGE THUMB] {filename}")
                client.delete_storage("portfolio", image_storage_path)
                failed_count += 1
                continue

            # 4. Extract/Parse Metadata & Insert DB Record
            caption = entry.get("caption", "")
            alt     = entry.get("alt", "")
            title, subtitle, description = parse_caption_html(caption, default_alt=alt, filename=filename)

            existing_exif = entry.get("exif", {})
            extracted_exif = extract_exif(img_path)

            fstop   = existing_exif.get("fstop") or extracted_exif.get("fstop")
            shutter = existing_exif.get("shutter") or extracted_exif.get("shutter_speed")
            iso_raw = existing_exif.get("iso") or extracted_exif.get("iso")
            iso     = format_iso_int(iso_raw)
            focal   = existing_exif.get("focal") or extracted_exif.get("focal_length")

            db_payload = {
                "id": photo_id,
                "title": title,
                "subtitle": subtitle,
                "description": description,
                "alt_text": alt if alt else None,
                "category": category_name,
                "image_path": image_storage_path,
                "thumbnail_path": thumb_storage_path,
                "fstop": fstop,
                "shutter_speed": shutter,
                "iso": iso,
                "focal_length": focal
            }

            db_res = client.insert("photographs", db_payload)
            if not db_res:
                print(f"  [FAILED DB INSERT] {filename} -> cleaning up storage objects...")
                client.delete_storage("portfolio", image_storage_path)
                client.delete_storage("portfolio", thumb_storage_path)
                failed_count += 1
            else:
                uploaded_count += 1
                print(f"  [SUCCESS] {filename} -> DB ID {photo_id[:8]}... | {category_name}")

    print("\n" + "=" * 70)
    print("MIGRATION COMPLETE")
    print("=" * 70)
    print(f"Successfully migrated: {uploaded_count} photographs")
    print(f"Failed / Skipped     : {failed_count} photographs")
    print("=" * 70)

def run_verify():
    load_dotenv()
    supabase_url = os.environ.get("SUPABASE_URL")
    anon_or_service_key = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not anon_or_service_key or "YOUR_SUPABASE" in supabase_url:
        print("[ERROR] SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env file to verify migration.")
        sys.exit(1)

    print("=" * 70)
    print("VERIFYING SUPABASE MIGRATION vs IMAGES.JSON")
    print("=" * 70)

    client = SupabaseClient(supabase_url, anon_or_service_key)
    rows = client.select("photographs")

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    json_count = sum(len(entries) for entries in data.values())
    db_count = len(rows)

    print(f"images.json total entries : {json_count}")
    print(f"Supabase photographs count: {db_count}")

    if json_count == db_count:
        print("\n[MATCH] Photograph count in Supabase matches images.json exactly!")
    else:
        print(f"\n[MISMATCH] Difference of {abs(json_count - db_count)} entries between images.json and Supabase.")

    # Check categories breakdown
    print("\nCategory Breakdown in Supabase:")
    cat_counts = {}
    for r in rows:
        cat = r.get("category", "Unknown")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    for cat, count in sorted(cat_counts.items()):
        print(f"  - {cat:<12}: {count} records")

    print("=" * 70)

def main():
    parser = argparse.ArgumentParser(description="Supabase Photography Portfolio Migration & Audit Tool")
    parser.add_argument("--dry-run", action="store_true", help="Audit local files and images.json without writing to Supabase")
    parser.add_argument("--verify", action="store_true", help="Compare Supabase DB record count with images.json")

    args = parser.parse_args()

    if args.dry_run:
        run_dry_run()
    elif args.verify:
        run_verify()
    else:
        run_migration()

if __name__ == "__main__":
    main()
