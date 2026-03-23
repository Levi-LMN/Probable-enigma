"""
optimise_images.py
──────────────────
One-off script to compress and resize all existing project/experience images
in static/uploads/ and update the database paths to point to the new WebP files.

Usage (run from your project root):
    python optimise_images.py              # dry run — shows what would change
    python optimise_images.py --apply      # actually converts files + updates DB
    python optimise_images.py --apply --delete-originals   # also removes old files

Requirements:
    pip install Pillow
    (Flask + SQLAlchemy must already be installed)
"""

import os
import sys
import argparse
import secrets
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
UPLOAD_ROOT   = Path("static/uploads")   # relative to project root
MAX_WIDTH     = 1400                     # px — wider images are scaled down
WEBP_QUALITY  = 82                       # 0-100; 80-85 is the sweet spot
JPEG_QUALITY  = 82                       # fallback if WebP fails
SUPPORTED_IN  = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif", ".bmp", ".tiff"}
# ─────────────────────────────────────────────────────────────────────────────


def sizeof_fmt(num_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"


def optimise_image(src_path: Path, max_width: int, quality: int) -> tuple[bytes, str]:
    """
    Open *src_path*, resize if needed, encode to WebP (or JPEG as fallback).
    Returns (encoded_bytes, extension_with_dot).
    """
    from PIL import Image, ImageOps

    img = Image.open(src_path)
    img = ImageOps.exif_transpose(img)          # fix phone rotation

    # Normalise colour mode
    if img.mode in ("RGBA", "LA"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # Downscale only
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)

    import io

    # Try WebP
    buf = io.BytesIO()
    try:
        img.save(buf, "WEBP", quality=quality, method=4)
        return buf.getvalue(), ".webp"
    except Exception:
        pass

    # JPEG fallback
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
    return buf.getvalue(), ".jpg"


def collect_images(upload_root: Path) -> list[Path]:
    paths = []
    for p in upload_root.rglob("*"):
        if p.is_file() and p.suffix.lower() in SUPPORTED_IN:
            paths.append(p)
    return sorted(paths)


def main():
    parser = argparse.ArgumentParser(description="Batch-optimise portfolio images.")
    parser.add_argument("--apply",            action="store_true", help="Write converted files (default: dry run)")
    parser.add_argument("--delete-originals", action="store_true", help="Remove original files after converting")
    parser.add_argument("--no-db",            action="store_true", help="Skip database path updates")
    parser.add_argument("--upload-root",      default=str(UPLOAD_ROOT), help=f"Upload folder (default: {UPLOAD_ROOT})")
    parser.add_argument("--max-width",        type=int, default=MAX_WIDTH)
    parser.add_argument("--quality",          type=int, default=WEBP_QUALITY)
    args = parser.parse_args()

    upload_root = Path(args.upload_root)

    if not upload_root.exists():
        print(f"[ERROR] Upload root not found: {upload_root}")
        sys.exit(1)

    dry_run = not args.apply
    if dry_run:
        print("=" * 60)
        print("  DRY RUN — no files will be written.")
        print("  Add --apply to perform the conversion.")
        print("=" * 60)

    images = collect_images(upload_root)
    if not images:
        print("No images found. Nothing to do.")
        return

    print(f"\nFound {len(images)} image(s) under {upload_root}\n")

    # ── DB setup (optional) ───────────────────────────────────────────────────
    db_session = None
    ProjectImage = None
    WorkExperience = None

    if not args.no_db and args.apply:
        try:
            from app import create_app, db as _db
            from models import ProjectImage as _PI, WorkExperience as _WE
            _app = create_app()
            _ctx = _app.app_context()
            _ctx.push()
            db_session   = _db.session
            ProjectImage  = _PI
            WorkExperience = _WE
            print("[DB] Connected — will update image paths in the database.\n")
        except Exception as e:
            print(f"[DB] Could not connect ({e}). DB paths won't be updated.\n")

    # ── Process each file ─────────────────────────────────────────────────────
    total_saved = 0
    converted   = 0
    skipped     = 0
    errors      = 0

    # Map old relative path → new relative path (for DB updates)
    # e.g.  "uploads/projects/abc.jpg"  →  "uploads/projects/abc.webp"
    path_map: dict[str, str] = {}

    for src in images:
        original_size = src.stat().st_size
        rel = src.relative_to(Path("static"))  # e.g. uploads/projects/abc.jpg
        subfolder = src.parent.name             # e.g. projects / experience

        print(f"  {rel}  ({sizeof_fmt(original_size)})", end="")

        # Skip if already an optimised WebP that's within size budget
        if src.suffix.lower() == ".webp" and original_size < 200 * 1024:
            print("  → already small WebP, skipped")
            skipped += 1
            continue

        try:
            data, ext = optimise_image(src, args.max_width, args.quality)
        except Exception as e:
            print(f"  → ERROR: {e}")
            errors += 1
            continue

        new_size  = len(data)
        saving    = original_size - new_size
        saving_pc = (saving / original_size * 100) if original_size else 0

        # Build new filename (keep same stem unless extension changes)
        new_stem     = src.stem if src.suffix.lower() == ext else src.stem
        new_filename = new_stem + ext
        new_path     = src.parent / new_filename

        # If the extension changes we need a unique name to avoid collisions
        if src.suffix.lower() != ext:
            new_filename = secrets.token_hex(12) + ext
            new_path     = src.parent / new_filename

        old_rel_db = str(rel).replace("\\", "/")           # uploads/projects/old.jpg
        new_rel_db = str(new_path.relative_to(Path("static"))).replace("\\", "/")

        print(f"  → {sizeof_fmt(new_size)}  (saved {sizeof_fmt(saving)}, {saving_pc:.0f}%)", end="")

        if not dry_run:
            # Write the new file
            new_path.write_bytes(data)

            # Remove the original only when the name actually changed
            # (if extension stayed the same, new_path == src, already overwritten)
            if args.delete_originals and new_path != src and src.exists():
                src.unlink()
                print("  [old deleted]", end="")

            path_map[old_rel_db] = new_rel_db

        print()
        total_saved += saving
        converted   += 1

    # ── Update DB ─────────────────────────────────────────────────────────────
    if db_session and path_map and not dry_run:
        print(f"\n[DB] Updating {len(path_map)} path(s)…")
        updated = 0

        for old_path, new_path_db in path_map.items():
            if old_path == new_path_db:
                continue

            # ProjectImage rows
            rows = ProjectImage.query.filter_by(filename=old_path).all()
            for row in rows:
                row.filename = new_path_db
                updated += 1

            # WorkExperience logo
            logo_rows = WorkExperience.query.filter_by(company_logo=old_path).all()
            for row in logo_rows:
                row.company_logo = new_path_db
                updated += 1

        try:
            db_session.commit()
            print(f"[DB] Updated {updated} database row(s). ✓")
        except Exception as e:
            db_session.rollback()
            print(f"[DB] Commit failed: {e}")

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    if dry_run:
        print(f"  DRY RUN complete.")
        print(f"  Would convert : {converted} image(s)")
        print(f"  Would skip    : {skipped} image(s)")
        print(f"  Estimated saving: ~{sizeof_fmt(total_saved)}")
        print(f"\n  Run with --apply to perform the conversion.")
    else:
        print(f"  Done!")
        print(f"  Converted : {converted} image(s)")
        print(f"  Skipped   : {skipped} image(s)")
        print(f"  Errors    : {errors}")
        print(f"  Space saved: {sizeof_fmt(total_saved)}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()