# ================== SETUP ==================
# Run these in a Colab cell before executing this script:
# !pip install pillow opencv-python-headless -q
# !apt-get install ffmpeg imagemagick -y -q

import os
import glob
import json
import time
import shutil
import subprocess
import numpy as np
import cv2
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from google.colab import drive, files as colab_files

# ================== SETTINGS ==================
base = "/content/drive/MyDrive/MyAutomation"

settings = {
    # ── Paths ──────────────────────────────────────────────────────────
    'base':          f'{base}/',
    'images_folder': f'{base}/images',
    'square_folder': f'{base}/square',
    'preview_folder':f'{base}/previews',
    'logs_folder':   f'{base}/logs',

    # Asset folders
    'background_folder': f'{base}/assets/background',
    'marquee_folder':    f'{base}/assets/marquee',
    'overlay1_folder':   f'{base}/assets/overlay1',
    'overlay2_folder':   f'{base}/assets/overlay2',
    'bottom_folder':     f'{base}/assets/bottom',
    'audio_folder':      f'{base}/assets/audio',

    # Asset file paths — resolved automatically at runtime
    'background':   None,
    'marquee':      None,   # image or video
    'overlay1':     None,   # image or video
    'overlay2':     None,   # image or video
    'bottom':       None,   # image or video
    'audio_path':   None,

    'AUDIO_MODE': '1',   # 1=Loop, 2=Single, 3=None
    'AUDIO_VOL':  1,     # Volume multiplier

    # ── Timing ─────────────────────────────────────────────────────────
    'FPS':             30,
    'DURATION':       2.8,   # Default seconds per slide (can be overridden per-slide)
    'EFFECT_DURATION': 0.8,

    # ── Frame size / aspect ratio preset ───────────────────────────────
    # Presets: 'reels' (1080x1920), 'square' (1080x1080),
    #          'landscape' (1920x1080), 'custom' (use FRAME_W/H below)
    'ASPECT_PRESET': 'reels',
    'FRAME_W': 1080,
    'FRAME_H': 1920,

    # ── Slideshow area ─────────────────────────────────────────────────
    'SLIDE_W':      1080,
    'SLIDE_H':      1200,   # 1080 or 1200
    'SLIDE_MARGIN':    0,

    # ── Transition between slides ──────────────────────────────────────
    # Options: 'cut', 'fade', 'zoom_in', 'slide_left'
    'TRANSITION_TYPE':   'fade',
    'TRANSITION_FRAMES': 15,   # number of frames for the transition

    # ── Marquee ────────────────────────────────────────────────────────
    'MARQUEE_H':     80,
    'MARQUEE_TOP':   80,
    'MARQUEE_SPEED': 120,   # px/sec (image only)

    # ── Overlay 1 ──────────────────────────────────────────────────────
    'OV1_W':      600,
    'OV1_H':      140,
    'OV1_OPACITY': 1.0,   # 0.0–1.0

    # ── Overlay 2 ──────────────────────────────────────────────────────
    # OV2_W auto-derived from FRAME_W if set to 0
    'OV2_W':       0,     # 0 = auto full-width
    'OV2_H':      140,
    'OV2_Y':     1457,    # Fixed — independent of SLIDE_H
    'OV2_OPACITY': 1.0,

    # ── Bottom button ──────────────────────────────────────────────────
    'BTN_W':       960,
    'BTN_H':       540,
    'BTN_OPACITY': 1.0,
    # BTN_Y derived below

    # ── Text overlay ───────────────────────────────────────────────────
    'TEXT_ENABLED': False,
    'TEXT_CONTENT': 'Your text here',
    'TEXT_X':       540,       # center X (pixels)
    'TEXT_Y':      1700,       # Y position (pixels)
    'TEXT_SIZE':     48,       # font size
    'TEXT_COLOR':   (255, 255, 255),   # RGB
    'TEXT_BG_COLOR': None,     # None or (R,G,B,A) for background box

    # ── Output versioning ──────────────────────────────────────────────
    # 'timestamp' → final_video_20260506_143022.mp4
    # 'counter'   → final_video_001.mp4, final_video_002.mp4
    # 'overwrite' → always final_video.mp4 (old behaviour)
    'OUTPUT_NAMING': 'timestamp',

    # ── Preview ────────────────────────────────────────────────────────
    'PREVIEW_ENABLED': True,   # Save preview frames before full render
}

# ── Derived values (always auto-calculated — do not set manually) ──────────
ASPECT_PRESETS = {
    'reels':     (1080, 1920),
    'square':    (1080, 1080),
    'landscape': (1920, 1080),
    'story':     (1080, 1920),
}
if settings['ASPECT_PRESET'] != 'custom':
    w, h = ASPECT_PRESETS.get(settings['ASPECT_PRESET'], (1080, 1920))
    settings['FRAME_W'], settings['FRAME_H'] = w, h

# OV2_W: auto full-width if set to 0
if settings['OV2_W'] == 0:
    settings['OV2_W'] = settings['FRAME_W']

# BTN_Y always derived
#settings['BTN_Y'] = settings['OV2_Y'] + settings['OV2_H'] + 16
settings['BTN_Y'] = 1380

IMAGE_EXT  = [".jpg", ".jpeg", ".png", ".bmp", ".webp"]
VIDEO_EXT  = [".mp4", ".mov", ".avi", ".mkv", ".webm", ".gif"]
AUDIO_EXT  = [".mp3", ".wav", ".aac", ".m4a", ".ogg"]
MEDIA_EXT  = IMAGE_EXT + VIDEO_EXT


# ================== SYSTEM CHECKS ==================

def mount_drive():
    try:
        drive.mount('/content/drive', force_remount=False)
        print("✅ Google Drive mounted.")
    except Exception as e:
        raise RuntimeError(f"❌ Google Drive mount failed: {e}")


def check_disk_space(settings, final_duration):
    """
    Estimate required disk space and warn if insufficient.
    Estimate: raw frames + slideshow + composite + final ≈ 3× raw frame size.
    """
    FRAME_W     = settings['FRAME_W']
    FRAME_H     = settings['FRAME_H']
    fps         = settings['FPS']
    total_frames = int(final_duration * fps)

    raw_bytes      = total_frames * FRAME_W * FRAME_H * 3         # uncompressed BGR
    estimate_bytes = raw_bytes * 3                                  # safety 3× multiplier
    estimate_gb    = estimate_bytes / (1024 ** 3)

    free_bytes = shutil.disk_usage("/content").free
    free_gb    = free_bytes / (1024 ** 3)

    print(f"💾 Disk check:")
    print(f"   Estimated required : ~{estimate_gb:.1f} GB")
    print(f"   Available on /content: {free_gb:.1f} GB")

    if free_gb < estimate_gb:
        raise RuntimeError(
            f"❌ Not enough disk space. Need ~{estimate_gb:.1f} GB but only "
            f"{free_gb:.1f} GB available. Shorten the video or free up space."
        )
    print(f"   ✅ Sufficient disk space.")


def validate_overlay_bounds(settings):
    """
    Warn if any overlay position exceeds the frame boundaries.
    Does not stop the pipeline — just prints a warning.
    """
    FRAME_W = settings['FRAME_W']
    FRAME_H = settings['FRAME_H']
    checks = [
        ("Overlay 2 bottom edge", settings['OV2_Y'] + settings['OV2_H'], FRAME_H),
        ("Bottom button bottom",  settings['BTN_Y'] + settings['BTN_H'], FRAME_H),
        ("Overlay 2 right edge",  settings['OV2_W'],                     FRAME_W),
        ("Overlay 1 right edge",  (FRAME_W - settings['OV1_W']) // 2 + settings['OV1_W'], FRAME_W),
        ("Bottom button right",   (FRAME_W - settings['BTN_W']) // 2 + settings['BTN_W'], FRAME_W),
    ]
    all_ok = True
    for label, value, limit in checks:
        if value > limit:
            print(f"   ⚠️  {label} ({value}px) exceeds frame ({limit}px) — will be clipped.")
            all_ok = False
    if all_ok:
        print(f"   ✅ All overlay positions are within the frame.")


# ================== HELPERS ==================

def get_duration(filepath):
    result = subprocess.run(
        ["ffprobe", "-v", "error",
         "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", filepath],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def get_video_fps(filepath):
    """Return the FPS of a video file."""
    result = subprocess.run(
        ["ffprobe", "-v", "error",
         "-select_streams", "v:0",
         "-show_entries", "stream=r_frame_rate",
         "-of", "default=noprint_wrappers=1:nokey=1", filepath],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    try:
        num, den = result.stdout.strip().split(b"/")
        return float(num) / float(den)
    except Exception:
        return 0.0


def fmt(seconds):
    s = int(seconds)
    return f"{s // 60}m {s % 60}s"


def is_video(path):
    return os.path.splitext(path)[1].lower() in VIDEO_EXT


def is_image(path):
    return os.path.splitext(path)[1].lower() in IMAGE_EXT


def load_image_as_rgba(path, w, h):
    with Image.open(path).convert("RGBA") as im:
        return np.array(im.resize((w, h), Image.LANCZOS))


def apply_opacity(rgba, opacity):
    """Scale the alpha channel of an RGBA array by opacity (0.0–1.0)."""
    if opacity >= 1.0:
        return rgba
    result        = rgba.copy().astype(np.float32)
    result[:,:,3] = result[:,:,3] * opacity
    return result.astype(np.uint8)


def alpha_composite(base_bgr, overlay_rgba, x, y):
    oh, ow = overlay_rgba.shape[:2]
    bh, bw = base_bgr.shape[:2]
    x1, y1 = max(x, 0), max(y, 0)
    x2, y2 = min(x + ow, bw), min(y + oh, bh)
    if x1 >= x2 or y1 >= y2:
        return base_bgr
    ox1, oy1 = x1 - x, y1 - y
    ox2, oy2 = ox1 + (x2 - x1), oy1 + (y2 - y1)
    src     = overlay_rgba[oy1:oy2, ox1:ox2]
    alpha   = src[:, :, 3:4].astype(np.float32) / 255.0
    src_bgr = src[:, :, :3][:, :, ::-1]
    roi     = base_bgr[y1:y2, x1:x2].astype(np.float32)
    base_bgr[y1:y2, x1:x2] = (
        (1 - alpha) * roi + alpha * src_bgr.astype(np.float32)
    ).astype(np.uint8)
    return base_bgr


def open_video_writer(output_path, fps, size):
    for codec in ['avc1', 'mp4v', 'XVID']:
        fourcc = cv2.VideoWriter_fourcc(*codec)
        writer = cv2.VideoWriter(output_path, fourcc, fps, size)
        if writer.isOpened():
            print(f"🎬 VideoWriter opened [{codec}]")
            return writer
        writer.release()
    raise RuntimeError(f"❌ All codecs failed: {output_path}")


def parse_duration_input(raw):
    raw = raw.strip()
    if ":" in raw:
        parts = raw.split(":")
        try:
            return float(int(parts[0]) * 60 + int(parts[1]))
        except (ValueError, IndexError):
            return None
    try:
        return float(raw)
    except ValueError:
        return None


def generate_output_path(base_dir, naming_mode):
    """
    Generate output video path based on naming mode.
    'timestamp' → final_video_20260506_143022.mp4
    'counter'   → final_video_001.mp4 (increments automatically)
    'overwrite' → final_video.mp4
    """
    if naming_mode == 'timestamp':
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(base_dir, f"final_video_{ts}.mp4")

    elif naming_mode == 'counter':
        counter = 1
        while True:
            path = os.path.join(base_dir, f"final_video_{counter:03d}.mp4")
            if not os.path.exists(path):
                return path
            counter += 1

    else:  # overwrite
        return os.path.join(base_dir, "final_video.mp4")


def save_settings_log(settings, final_video, final_duration, logs_folder):
    """Save a JSON snapshot of settings next to the final video for reproducibility."""
    os.makedirs(logs_folder, exist_ok=True)
    log_name = os.path.splitext(os.path.basename(final_video))[0] + "_settings.json"
    log_path = os.path.join(logs_folder, log_name)

    log_data = {
        "rendered_at":    datetime.now().isoformat(),
        "final_video":    final_video,
        "final_duration": final_duration,
        "settings": {
            k: v for k, v in settings.items()
            if not k.endswith('_folder') and v is not None
        }
    }
    with open(log_path, "w") as f:
        json.dump(log_data, f, indent=2)
    print(f"📋 Settings log saved: {log_path}")


def list_files_in_folder(folder, allowed_exts):
    os.makedirs(folder, exist_ok=True)
    return sorted([
        f for f in glob.glob(f"{folder}/*")
        if os.path.isfile(f) and os.path.splitext(f)[1].lower() in allowed_exts
    ])


# ================== ASSET MANAGEMENT ==================

def resolve_single_asset(label, folder, allowed_exts, ext_display):
    """
    Resolve exactly ONE asset file.
      Empty    → upload prompt
      1 file   → use automatically
      Multiple → user picks one, extras ARE KEPT safely.
    """
    os.makedirs(folder, exist_ok=True)
    files = list_files_in_folder(folder, allowed_exts)

    if len(files) == 0:
        print()
        print(f"  📂 {label} folder is empty.")
        print(f"     Folder: {folder}")
        print(f"     Please upload the {label} file ({ext_display}).")
        return _upload_single_asset(label, folder, allowed_exts, ext_display)

    if len(files) == 1:
        ftype = "VIDEO" if is_video(files[0]) else "IMAGE"
        print(f"  ✅ {label:22s} [{ftype}] → {files[0]}")
        # Warn on FPS mismatch for video overlays
        if is_video(files[0]):
            src_fps = get_video_fps(files[0])
            if src_fps > 0 and abs(src_fps - settings['FPS']) > 1:
                print(f"     ⚠️  FPS mismatch: asset={src_fps:.1f} vs pipeline={settings['FPS']}."
                      f" Overlay may play at wrong speed. Match FPS or re-export asset.")
        return files[0]

    # Multiple files
    print()
    print(f"  ⚠️  {label} folder has {len(files)} files — only 1 is allowed.")
    print(f"     Folder: {folder}")
    for i, f in enumerate(files, 1):
        size_kb = os.path.getsize(f) / 1024
        ftype   = "VIDEO" if is_video(f) else "IMAGE"
        print(f"     [{i}] [{ftype}] {os.path.basename(f)}  ({size_kb:.0f} KB)")
    print(f"\n     [D] Delete all and upload a new file")
    print()

    while True:
        raw = input(f"     👉 Choose [1-{len(files)}] or D: ").strip().upper()
        if raw == "D":
            for f in files:
                os.remove(f)
                print(f"     🗑️  Deleted: {os.path.basename(f)}")
            return _upload_single_asset(label, folder, allowed_exts, ext_display)
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(files):
                chosen = files[idx]
                # Deletion loop removed. Files are kept safely in the folder.
                print(f"  ✅ {label:22s} → {chosen} (Other files kept)")
                return chosen
            print(f"     ❌ Enter 1–{len(files)} or D.")
        except ValueError:
            print(f"     ❌ Invalid input.")


def _upload_single_asset(label, folder, allowed_exts, ext_display):
    while True:
        uploaded = colab_files.upload()
        if not uploaded:
            print(f"     ⚠️  Nothing uploaded. Please try again.")
            continue
        saved = None
        for filename, data in uploaded.items():
            ext = os.path.splitext(filename)[1].lower()
            if ext not in allowed_exts:
                print(f"     ⚠️  '{filename}' not supported ({ext_display}). Skipped.")
                continue
            dest = os.path.join(folder, filename)
            with open(dest, "wb") as f:
                f.write(data)
            saved = dest
            print(f"     💾 Saved: {dest}")
            break
        if saved:
            return saved
        print(f"     ❌ No valid file saved. Please upload a {ext_display} file.")


def check_all_assets(settings):
    print()
    print("─" * 55)
    print("🔍 Checking asset folders...")
    print("─" * 55)

    asset_checks = [
        ('background', 'Background video',  'background_folder', VIDEO_EXT,  'MP4, MOV, AVI'),
        ('marquee',    'Marquee',           'marquee_folder',    MEDIA_EXT,  'PNG/JPG/MP4/MOV/GIF'),
        ('overlay1',   'Overlay 1',         'overlay1_folder',   MEDIA_EXT,  'PNG/JPG/MP4/MOV/GIF'),
        ('overlay2',   'Overlay 2',         'overlay2_folder',   MEDIA_EXT,  'PNG/JPG/MP4/MOV/GIF'),
        ('bottom',     'Bottom button',     'bottom_folder',     MEDIA_EXT,  'PNG/JPG/MP4/MOV/GIF'),
        ('audio_path', 'Audio file',        'audio_folder',      AUDIO_EXT,  'MP3, WAV, AAC'),
    ]

    for settings_key, label, folder_key, allowed_exts, ext_display in asset_checks:
        settings[settings_key] = resolve_single_asset(
            label, settings[folder_key], allowed_exts, ext_display
        )

    print()
    print("✅ All assets confirmed.")
    print("─" * 55)
    return settings


# ================== IMAGE UPLOAD ==================

def check_and_upload_images(images_folder, settings):
    """
    Smart image folder handling:
      Folder has files → list them, ask: Delete & upload new OR Keep existing
      Folder is empty  → upload prompt directly
    Returns (saved_paths, final_duration).
    """
    os.makedirs(images_folder, exist_ok=True)

    # Always clear square/ folder to avoid stale converted images
    square_folder = settings['square_folder']
    if os.path.exists(square_folder):
        stale = [f for f in glob.glob(f"{square_folder}/*") if os.path.isfile(f)]
        if stale:
            for f in stale:
                os.remove(f)
            print(f"🗑️  Cleared {len(stale)} stale file(s) from square/ folder.")

    existing = [
        f for f in glob.glob(f"{images_folder}/*")
        if os.path.isfile(f) and os.path.splitext(f)[1].lower() in IMAGE_EXT
    ]

    print()
    print("─" * 55)
    print("🖼️  Slide images")
    print("─" * 55)

    if existing:
        print(f"  ⚠️  The images folder has {len(existing)} existing file(s):")
        for f in existing:
            print(f"      • {os.path.basename(f)}")
        print()
        print(f"  [D] Delete all old files and upload new ones")
        print(f"  [K] Keep existing files and use them")
        print()

        while True:
            choice = input("  👉 D to delete & upload, K to keep: ").strip().upper()
            if choice == "D":
                for f in existing:
                    os.remove(f)
                print(f"  🗑️  Deleted {len(existing)} old file(s).")
                saved = _upload_images(images_folder)
                break
            elif choice == "K":
                print(f"  ✅ Keeping {len(existing)} existing image(s).")
                saved = existing
                break
            else:
                print("  ❌ Enter D or K.")
    else:
        print(f"  📂 Images folder is empty.")
        saved = _upload_images(images_folder)

    # Slide order control
    saved = ask_slide_order(saved)

    # Per-slide duration
    slide_durations = ask_per_slide_duration(saved, settings['DURATION'])

    # Auto-calc total slideshow duration
    auto_duration = sum(slide_durations)
    bg_duration   = get_duration(settings['background'])

    print()
    print("─" * 55)
    print(f"📊 Summary:")
    print(f"   Images          : {len(saved)}")
    print(f"   Slideshow length: {fmt(auto_duration)} ({auto_duration:.1f}s)")
    print(f"   Background video: {fmt(bg_duration)} ({bg_duration:.1f}s)")

    if auto_duration > bg_duration:
        print(f"\n   ⚠️  Slideshow longer than background by"
              f" {auto_duration - bg_duration:.1f}s. Background will loop.")
    elif auto_duration < bg_duration:
        print(f"\n   ℹ️  Slideshow shorter than background by"
              f" {bg_duration - auto_duration:.1f}s. Slideshow will loop if extended.")
    else:
        print(f"\n   ✅ Slideshow and background are the same length.")

    final_duration = ask_video_duration(auto_duration, bg_duration)

    return saved, slide_durations, final_duration


def _upload_images(images_folder):
    print(f"  📂 Upload slide images (JPG, PNG, WEBP, BMP, etc.)")
    while True:
        uploaded = colab_files.upload()
        if not uploaded:
            print("  ⚠️  Nothing uploaded. Please try again.")
            continue

        saved, skipped = [], []
        for filename, data in uploaded.items():
            ext = os.path.splitext(filename)[1].lower()
            if ext not in IMAGE_EXT:
                skipped.append(filename)
                continue
            base_name, file_ext = os.path.splitext(filename)
            dest    = os.path.join(images_folder, filename)
            counter = 1
            while os.path.exists(dest):
                dest = os.path.join(images_folder, f"{base_name}_{counter}{file_ext}")
                counter += 1
            with open(dest, "wb") as f:
                f.write(data)
            saved.append(dest)
            print(f"     💾 Saved: {dest}")

        if skipped:
            print(f"  ⚠️  Skipped {len(skipped)} unsupported file(s): {skipped}")
        if not saved:
            print("  ❌ No valid images. Upload .jpg / .png / .webp etc.")
            continue

        print(f"\n  ✅ {len(saved)} image(s) uploaded.")
        return saved


def ask_slide_order(saved):
    """
    Show current slide order and ask if the user wants to reorder.
    User can enter a comma-separated new order e.g. 3,1,4,2
    """
    print()
    print("─" * 55)
    print("🔢 Slide order:")
    for i, f in enumerate(saved, 1):
        print(f"   [{i}] {os.path.basename(f)}")
    print()
    print("   Press [Enter] to keep this order.")
    print("   Or enter new order e.g.  3,1,4,2")

    while True:
        raw = input("   👉 Order: ").strip()
        if raw == "":
            print("   ✅ Using default order.")
            return saved

        try:
            indices = [int(x.strip()) - 1 for x in raw.split(",")]
            if sorted(indices) != list(range(len(saved))):
                print(f"   ❌ Must use each number 1–{len(saved)} exactly once.")
                continue
            reordered = [saved[i] for i in indices]
            print("   ✅ New order:")
            for i, f in enumerate(reordered, 1):
                print(f"      [{i}] {os.path.basename(f)}")
            return reordered
        except (ValueError, IndexError):
            print(f"   ❌ Invalid. Use comma-separated numbers e.g.  3,1,2")


def ask_per_slide_duration(saved, default_duration):
    """
    Ask if the user wants to set per-slide durations.
    Default: all slides use settings['DURATION'].
    Custom: user can set each slide individually.
    """
    print()
    print("─" * 55)
    print(f"⏱️  Slide durations (default: {default_duration}s each)")
    print(f"   [Enter] → all slides use {default_duration}s")
    print(f"   [C]     → set custom duration per slide")

    while True:
        raw = input("   👉 Choice: ").strip().upper()
        if raw == "":
            durations = [default_duration] * len(saved)
            print(f"   ✅ All slides: {default_duration}s each.")
            return durations

        if raw == "C":
            durations = []
            print()
            for i, f in enumerate(saved, 1):
                fname = os.path.basename(f)
                while True:
                    val = input(f"      Slide {i} [{fname}] duration"
                                f" (Enter={default_duration}s): ").strip()
                    if val == "":
                        durations.append(default_duration)
                        break
                    try:
                        d = float(val)
                        if d < 0.5:
                            print("      ❌ Minimum 0.5s.")
                            continue
                        durations.append(d)
                        break
                    except ValueError:
                        print("      ❌ Enter a number e.g. 3.5")
            print(f"   ✅ Custom durations set.")
            return durations

        print("   ❌ Press Enter or C.")


# ================== DURATION LOGIC ==================

def ask_video_duration(auto_duration, bg_duration):
    print()
    print("─" * 55)
    print("⏱️  Final video length?")
    print(f"   [Enter]  → Auto {fmt(auto_duration)} ({auto_duration:.1f}s)")
    print(f"   Seconds  → e.g. 90")
    print(f"   mm:ss    → e.g. 1:30")
    print(f"   Min: 10s | No max cap")
    print("─" * 55)

    while True:
        raw = input("👉 Your choice: ").strip()
        if raw == "":
            chosen = auto_duration
            print(f"✅ Auto: {fmt(chosen)}")
        else:
            chosen = parse_duration_input(raw)
            if chosen is None:
                print("❌ Invalid. Try 90 or 1:30")
                continue
            if chosen < 10:
                print("❌ Minimum 10 seconds.")
                continue
            print(f"✅ Final video: {fmt(chosen)} ({chosen:.1f}s)")

        print()
        if chosen > bg_duration + 0.1:
            print(f"   🔁 Background loops ~{chosen / bg_duration:.2f}x.")
        elif abs(chosen - bg_duration) <= 0.1:
            print(f"   ✅ Background fits exactly.")
        else:
            print(f"   ✂️  Background trimmed to {fmt(chosen)}.")

        if chosen < auto_duration - 0.1:
            print(f"   ✂️  Slideshow trimmed by {auto_duration - chosen:.1f}s.")
        elif chosen > auto_duration + 0.1:
            print(f"   🔁 Slideshow loops ~{chosen / auto_duration:.2f}x.")
        else:
            print(f"   ✅ Slideshow fits exactly.")

        print()
        return float(chosen)


# ================== IMAGE CONVERSION ==================

def convert_images_to_square(input_images, square_folder, size):
    """Letterbox images to target size. No stretching. Saves as JPEG."""
    os.makedirs(square_folder, exist_ok=True)
    converted = []
    for img_path in input_images:
        filename = os.path.basename(img_path)
        output   = os.path.join(square_folder, os.path.splitext(filename)[0] + ".jpg")
        try:
            with Image.open(img_path).convert("RGB") as im:
                im.thumbnail(size, Image.LANCZOS)
                canvas = Image.new("RGB", size, (0, 0, 0))
                offset = ((size[0] - im.width) // 2, (size[1] - im.height) // 2)
                canvas.paste(im, offset)
                canvas.save(output, "JPEG", quality=95)
                converted.append(output)
        except Exception as e:
            print(f"⚠️  Skipping unreadable [{filename}]: {e}")
    if not converted:
        raise RuntimeError("❌ No valid images could be converted.")
    return converted


# ================== TEXT OVERLAY ==================

def apply_text_overlay(frame_bgr, settings):
    """
    Draw text on a BGR frame using PIL.
    Supports optional background box behind the text.
    """
    if not settings.get('TEXT_ENABLED'):
        return frame_bgr

    img = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img, "RGBA")

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                                  settings['TEXT_SIZE'])
    except Exception:
        font = ImageFont.load_default()

    text   = settings['TEXT_CONTENT']
    x, y   = settings['TEXT_X'], settings['TEXT_Y']
    color  = settings['TEXT_COLOR']
    bg_col = settings.get('TEXT_BG_COLOR')

    bbox = draw.textbbox((x, y), text, font=font, anchor="mm")

    if bg_col:
        pad = 10
        draw.rectangle(
            [bbox[0]-pad, bbox[1]-pad, bbox[2]+pad, bbox[3]+pad],
            fill=bg_col
        )

    draw.text((x, y), text, font=font, fill=color + (255,), anchor="mm")
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


# ================== TRANSITION EFFECTS ==================

def apply_transition(prev_frame, next_frame, t, transition_type):
    """
    Blend two BGR frames at position t (0.0=prev, 1.0=next).
    Supported: 'fade', 'zoom_in', 'slide_left', 'cut'
    """
    if transition_type == 'cut' or t <= 0:
        return next_frame if t >= 1.0 else prev_frame

    h, w = prev_frame.shape[:2]

    if transition_type == 'fade':
        return cv2.addWeighted(prev_frame, 1.0 - t, next_frame, t, 0)

    elif transition_type == 'zoom_in':
        scale  = 1.0 + 0.08 * t
        center = (w // 2, h // 2)
        M      = cv2.getRotationMatrix2D(center, 0, scale)
        zoomed = cv2.warpAffine(next_frame, M, (w, h),
                                borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
        return cv2.addWeighted(prev_frame, 1.0 - t, zoomed, t, 0)

    elif transition_type == 'slide_left':
        offset = int(w * t)
        canvas = np.zeros_like(prev_frame)
        # prev slides out to the left
        if offset < w:
            canvas[:, :w-offset] = prev_frame[:, offset:]
        # next slides in from the right
        canvas[:, w-offset:] = next_frame[:, :offset]
        return canvas

    return cv2.addWeighted(prev_frame, 1.0 - t, next_frame, t, 0)


# ================== SLIDESHOW BUILDER ==================

def build_slideshow(image_paths, slide_durations, size, fps,
                    final_duration, effect_duration, settings):
    """
    Build slideshow video exactly final_duration seconds long.
    Supports per-slide durations, transition effects, and loops/trims automatically.
    """
    output_path   = os.path.join(settings['base'], "slideshow_raw.mp4")
    total_frames  = int(final_duration * fps)
    effect_frames = int(effect_duration * fps)
    decay         = max(effect_frames / 4.0, 1.0)
    trans_frames  = settings.get('TRANSITION_FRAMES', 15)
    trans_type    = settings.get('TRANSITION_TYPE', 'fade')

    # Pre-load slides
    slides = []
    for img_path in image_paths:
        img = cv2.imread(img_path)
        if img is None:
            print(f"⚠️  Could not read: {img_path}")
            continue
        slides.append(cv2.resize(img, size))
    if not slides:
        raise RuntimeError("❌ No valid slides loaded.")

    # Build per-slide frame counts (cycling if total_frames > natural length)
    def get_slide_at_frame(frame_idx):
        """Return (slide_img, n_within_slide, is_last_frame_of_slide, next_slide_img)."""
        # Compute natural total frames for one full pass
        natural_frames = [int(d * fps) for d in slide_durations]
        natural_total  = sum(natural_frames)
        # Handle loop/trim
        effective_idx  = frame_idx % natural_total
        cumulative     = 0
        for i, nf in enumerate(natural_frames):
            if effective_idx < cumulative + nf:
                n     = effective_idx - cumulative
                next_i = (i + 1) % len(slides)
                return slides[i], n, nf, slides[next_i]
            cumulative += nf
        return slides[-1], 0, natural_frames[-1], slides[0]

    writer = open_video_writer(output_path, fps, size)
    t_start = time.time()

    try:
        for frame_idx in range(total_frames):
            # ETA display
            if frame_idx % 30 == 0 and frame_idx > 0:
                elapsed   = time.time() - t_start
                fps_actual = frame_idx / elapsed
                remaining = (total_frames - frame_idx) / fps_actual if fps_actual > 0 else 0
                pct       = int(frame_idx / total_frames * 100)
                print(f"  🎞️  Slideshow {frame_idx}/{total_frames} ({pct}%)"
                      f"  ETA: {fmt(remaining)}", end='\r')

            img, n, total_n, next_img = get_slide_at_frame(frame_idx)
            h = img.shape[0]

            # Bounce-in effect
            if n < effect_frames:
                offset_y = int(h * np.exp(-n / decay) * np.cos(n / 8.0) ** 2)
                M        = np.float32([[1, 0, 0], [0, 1, offset_y]])
                frame    = cv2.warpAffine(img, M, size,
                                          borderMode=cv2.BORDER_CONSTANT,
                                          borderValue=(0, 0, 0))
            else:
                frame = img.copy()

            # Transition at end of slide
            frames_until_end = total_n - n
            if frames_until_end <= trans_frames and trans_type != 'cut':
                t = 1.0 - (frames_until_end / trans_frames)
                frame = apply_transition(frame, next_img, t, trans_type)

            writer.write(frame)
    finally:
        writer.release()

    print(f"\n✅ Slideshow built: {output_path}")
    return output_path


# ================== PREVIEW GENERATOR ==================

def generate_previews(background_path, slideshow_path, overlay_readers,
                      settings, preview_folder):
    """
    Save 3 preview frames (first, middle, last) as JPEGs before the full render.
    Lets the user verify the layout without waiting for the full composite.
    """
    if not settings.get('PREVIEW_ENABLED', True):
        return

    os.makedirs(preview_folder, exist_ok=True)
    FRAME_W, FRAME_H = settings['FRAME_W'], settings['FRAME_H']

    bg_cap = cv2.VideoCapture(background_path)
    sl_cap = cv2.VideoCapture(slideshow_path)
    sl_total = int(sl_cap.get(cv2.CAP_PROP_FRAME_COUNT))

    slide_area_w = settings['SLIDE_W'] - 2 * settings['SLIDE_MARGIN']
    slide_area_h = settings['SLIDE_H'] - 2 * settings['SLIDE_MARGIN']
    slide_x      = (FRAME_W - slide_area_w) // 2
    slide_y      = (settings['MARQUEE_TOP'] + settings['MARQUEE_H']
                    + 57 + settings['OV1_H'] + 20)

    preview_frames = {
        'first':  0,
        'middle': max(0, sl_total // 2),
        'last':   max(0, sl_total - 1),
    }

    fps = settings['FPS']
    saved_previews = []

    for name, frame_idx in preview_frames.items():
        bg_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        _, bg_frame = bg_cap.read()
        canvas = cv2.resize(bg_frame, (FRAME_W, FRAME_H))

        sl_cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret_sl, sl_frame = sl_cap.read()
        if ret_sl:
            sl_resized = cv2.resize(sl_frame, (slide_area_w, slide_area_h))
            canvas[slide_y:slide_y + slide_area_h,
                   slide_x:slide_x + slide_area_w] = sl_resized

        # Marquee
        mq_rgba = overlay_readers['marquee'].read()
        if overlay_readers['marquee'].mode == "image":
            scroll_x = int((frame_idx / fps) * settings['MARQUEE_SPEED']) % FRAME_W
            mq_tile  = np.concatenate([mq_rgba, mq_rgba], axis=1)
            mq_rgba  = mq_tile[:, scroll_x:scroll_x + FRAME_W]
        canvas = alpha_composite(canvas, mq_rgba, 0, settings['MARQUEE_TOP'])

        # Static overlays
        ov1 = apply_opacity(overlay_readers['overlay1'].read(), settings['OV1_OPACITY'])
        canvas = alpha_composite(canvas, ov1,
                                 (FRAME_W - settings['OV1_W']) // 2,
                                 settings['MARQUEE_TOP'] + settings['MARQUEE_H'] + 57)

        ov2 = apply_opacity(overlay_readers['overlay2'].read(), settings['OV2_OPACITY'])
        canvas = alpha_composite(canvas, ov2,
                                 (FRAME_W - settings['OV2_W']) // 2,
                                 settings['OV2_Y'])

        btn = apply_opacity(overlay_readers['button'].read(), settings['BTN_OPACITY'])
        canvas = alpha_composite(canvas, btn,
                                 (FRAME_W - settings['BTN_W']) // 2,
                                 settings['BTN_Y'])

        if settings.get('TEXT_ENABLED'):
            canvas = apply_text_overlay(canvas, settings)

        preview_path = os.path.join(preview_folder, f"preview_{name}.jpg")
        cv2.imwrite(preview_path, canvas)
        saved_previews.append(preview_path)
        print(f"   🖼️  Preview saved: {preview_path}")

    bg_cap.release()
    sl_cap.release()

    print()
    print("   ✅ 3 preview frames saved. Check them before continuing.")
    print(f"   📁 Preview folder: {preview_folder}")
    cont = input("   👉 Continue with full render? [Enter=Yes / N=Stop]: ").strip().upper()
    if cont == "N":
        raise SystemExit("🛑 Render stopped by user after preview. Check previews and re-run.")


# ================== OVERLAY READER ==================

class OverlayReader:
    """Unified reader for image or video overlays. Videos loop automatically. Includes Green Screen removal."""

    def __init__(self, path, w, h):
        self.path, self.w, self.h = path, w, h
        self._cap = self._frame = None

        if is_video(path):
            self._cap = cv2.VideoCapture(path)
            if not self._cap.isOpened():
                raise RuntimeError(f"❌ Cannot open overlay video: {path}")
            self.mode = "video"
        else:
            self._frame = load_image_as_rgba(path, w, h)
            self.mode   = "image"

    def read(self):
        if self.mode == "image":
            return self._frame
        
        ret, frame = self._cap.read()
        if not ret:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self._cap.read()
            
        frame_resized = cv2.resize(frame, (self.w, self.h))
        rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
        
        # --- GREEN SCREEN (CHROMA KEY) REMOVAL ---
        # Convert frame to HSV to isolate the green color
        hsv = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2HSV)
        
        # Define the range of "green" (adjust these values if your green screen is too dark/light)
        lower_green = np.array([35, 50, 50])
        upper_green = np.array([85, 255, 255])
        
        # Create a mask where green pixels are white (255) and everything else is black (0)
        mask = cv2.inRange(hsv, lower_green, upper_green)
        
        # Invert the mask: Green becomes transparent (0), subjects become solid (255)
        alpha = cv2.bitwise_not(mask)
        
        # Reshape alpha to add it as the 4th channel
        alpha = alpha[..., np.newaxis] 
        
        return np.concatenate([rgb, alpha], axis=2)

    def release(self):
        if self._cap:
            self._cap.release()


# ================== COMPOSITING ==================

def composite_layers(background_path, slideshow_path, overlay_readers,
                     output_path, frame_size, fps, total_frames, settings):
    """
    Composite all layers frame-by-frame with ETA tracking.
    Layer order: Background → Slideshow → Marquee → OV1 → OV2 → Button → Text
    """
    FRAME_W, FRAME_H = frame_size

    bg_cap = cv2.VideoCapture(background_path)
    sl_cap = cv2.VideoCapture(slideshow_path)
    if not bg_cap.isOpened(): raise RuntimeError(f"❌ Cannot open background: {background_path}")
    if not sl_cap.isOpened(): raise RuntimeError(f"❌ Cannot open slideshow: {slideshow_path}")

    writer = open_video_writer(output_path, fps, frame_size)

    slide_area_w = settings['SLIDE_W'] - 2 * settings['SLIDE_MARGIN']
    slide_area_h = settings['SLIDE_H'] - 2 * settings['SLIDE_MARGIN']
    slide_x      = (FRAME_W - slide_area_w) // 2
    slide_y      = (settings['MARQUEE_TOP'] + settings['MARQUEE_H']
                    + 57 + settings['OV1_H'] + 20)

    t_start = time.time()

    try:
        for frame_idx in range(total_frames):
            if frame_idx % 30 == 0 and frame_idx > 0:
                elapsed    = time.time() - t_start
                fps_actual = frame_idx / elapsed
                remaining  = (total_frames - frame_idx) / fps_actual if fps_actual > 0 else 0
                pct        = int(frame_idx / total_frames * 100)
                print(f"  ⏳ Compositing {frame_idx}/{total_frames} ({pct}%)"
                      f"  ETA: {fmt(remaining)}", end='\r')

            # Background
            ret_bg, bg_frame = bg_cap.read()
            if not ret_bg:
                bg_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                _, bg_frame = bg_cap.read()
            canvas = cv2.resize(bg_frame, frame_size)

            # Slideshow
            ret_sl, sl_frame = sl_cap.read()
            if not ret_sl:
                sl_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                _, sl_frame = sl_cap.read()
            sl_resized = cv2.resize(sl_frame, (slide_area_w, slide_area_h))
            canvas[slide_y:slide_y + slide_area_h,
                   slide_x:slide_x + slide_area_w] = sl_resized

            # Marquee
            mq_rgba = overlay_readers['marquee'].read()
            if overlay_readers['marquee'].mode == "image":
                scroll_x = int((frame_idx / fps) * settings['MARQUEE_SPEED']) % FRAME_W
                mq_tile  = np.concatenate([mq_rgba, mq_rgba], axis=1)
                mq_rgba  = mq_tile[:, scroll_x:scroll_x + FRAME_W]
            canvas = alpha_composite(canvas, mq_rgba, 0, settings['MARQUEE_TOP'])

            # Overlay 1
            ov1 = apply_opacity(overlay_readers['overlay1'].read(), settings['OV1_OPACITY'])
            canvas = alpha_composite(canvas, ov1,
                                     (FRAME_W - settings['OV1_W']) // 2,
                                     settings['MARQUEE_TOP'] + settings['MARQUEE_H'] + 57)

            # Overlay 2
            ov2 = apply_opacity(overlay_readers['overlay2'].read(), settings['OV2_OPACITY'])
            canvas = alpha_composite(canvas, ov2,
                                     (FRAME_W - settings['OV2_W']) // 2,
                                     settings['OV2_Y'])

            # Bottom button
            btn = apply_opacity(overlay_readers['button'].read(), settings['BTN_OPACITY'])
            canvas = alpha_composite(canvas, btn,
                                     (FRAME_W - settings['BTN_W']) // 2,
                                     settings['BTN_Y'])

            # Text overlay
            if settings.get('TEXT_ENABLED'):
                canvas = apply_text_overlay(canvas, settings)

            writer.write(canvas)

    finally:
        bg_cap.release()
        sl_cap.release()
        writer.release()
        for r in overlay_readers.values():
            r.release()

    elapsed = time.time() - t_start
    print(f"\n✅ Composite built in {fmt(elapsed)}: {output_path}")


# ================== ENCODING ==================

def encode_final(comp_raw, audio_path, audio_mode, output_path, duration, volume):
    base_cmd = ['ffmpeg', '-y', '-i', comp_raw]

    if audio_mode == "3" or not os.path.exists(audio_path):
        cmd = base_cmd + ['-c:v', 'libx264', '-pix_fmt', 'yuv420p', output_path]
    elif audio_mode == "1":
        cmd = (base_cmd
               + ['-stream_loop', '-1', '-i', audio_path]
               + ['-filter_complex', f'[1:a]volume={volume}[a]']
               + ['-map', '0:v', '-map', '[a]']
               + ['-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                  '-c:a', 'aac', '-b:a', '192k', '-t', str(duration), output_path])
    elif audio_mode == "2":
        audio_dur = get_duration(audio_path)
        if audio_dur < duration:
            print(f"⚠️  Audio ({audio_dur:.1f}s) shorter than video ({duration:.1f}s). "
                  "Tail will be silent.")
        cmd = (base_cmd
               + ['-i', audio_path]
               + ['-filter_complex', f'[1:a]volume={volume}[a]']
               + ['-map', '0:v', '-map', '[a]']
               + ['-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                  '-c:a', 'aac', '-b:a', '192k', '-t', str(duration), output_path])
    else:
        raise ValueError(f"❌ Unknown AUDIO_MODE '{audio_mode}'.")

    print("🎞️  Encoding final video...")
    result = subprocess.run(cmd, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(f"❌ FFmpeg failed:\n{result.stderr.decode()}")
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError(f"❌ Output missing or empty: {output_path}")
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"✅ Encoded: {output_path}  ({size_mb:.1f} MB)")


# ================== CLEANUP ==================

def cleanup(slideshow_raw, comp_raw, images_folder, square_folder, final_video):
    """Delete all temp files. Skips if final video not confirmed."""
    if not os.path.exists(final_video) or os.path.getsize(final_video) == 0:
        print("⚠️  Final video not confirmed — skipping cleanup.")
        return

    for path in [slideshow_raw, comp_raw]:
        if path and os.path.exists(path):
            os.remove(path)
            print(f"🗑️  Deleted temp: {os.path.basename(path)}")

    removed = 0
    for folder in [images_folder, square_folder]:
        for f in glob.glob(os.path.join(folder, "*")):
            if os.path.isfile(f):
                os.remove(f)
                removed += 1
    if removed:
        print(f"🗑️  Cleared {removed} file(s) from images/ and square/ folders.")

    print("🧹 Cleanup complete.")


# ================== PIPELINE ==================

def run_video_pipeline(settings):
    """
    Full pipeline with all issues resolved and new features:

      Stage 1  Mount Drive
      Stage 2  Apply aspect ratio preset + validate overlay bounds
      Stage 3  Check all asset folders (empty→upload | 1→auto | multiple→pick)
      Stage 4  Upload images (folder state aware) → reorder slides → per-slide duration
      Stage 5  Disk space pre-check
      Stage 6  Convert to square (square/ cleared first to avoid stale files)
      Stage 7  Build slideshow (per-slide duration + transitions + ETA)
      Stage 8  Preview frames (first/middle/last) — user confirms before full render
      Stage 9  Composite all layers (opacity control + text overlay + ETA)
      Stage 10 Encode with audio
      Stage 11 Save settings log to Drive
      Stage 12 Cleanup temp files — final video always kept on Drive
    """
    run_start = time.time()

    print("=" * 55)
    print("🚀 Video pipeline starting...")
    print(f"   Preset  : {settings['ASPECT_PRESET']} ({settings['FRAME_W']}×{settings['FRAME_H']})")
    print(f"   SLIDE_H : {settings['SLIDE_H']}px")
    print(f"   OV2_Y   : {settings['OV2_Y']}px  (fixed)")
    print(f"   BTN_Y   : {settings['BTN_Y']}px  (derived)")
    print(f"   OV2_W   : {settings['OV2_W']}px  (auto full-width)")
    print(f"   Transition: {settings['TRANSITION_TYPE']}")
    print(f"   Naming  : {settings['OUTPUT_NAMING']}")
    print("=" * 55)

    # Stage 1
    mount_drive()

    # Stage 2: Validate overlay bounds
    print()
    print("─" * 55)
    print("📐 Validating overlay positions...")
    validate_overlay_bounds(settings)

    # Stage 3
    settings = check_all_assets(settings)

    # Stage 4
    os.makedirs(settings['images_folder'], exist_ok=True)
    os.makedirs(settings['square_folder'],  exist_ok=True)
    os.makedirs(settings['preview_folder'], exist_ok=True)
    os.makedirs(settings['logs_folder'],    exist_ok=True)

    input_images, slide_durations, final_duration = check_and_upload_images(
        settings['images_folder'], settings
    )

    # Stage 5: Disk space check
    print()
    print("─" * 55)
    check_disk_space(settings, final_duration)

    # Stage 6
    effective_size = (
        settings['SLIDE_W'] - 2 * settings['SLIDE_MARGIN'],
        settings['SLIDE_H'] - 2 * settings['SLIDE_MARGIN'],
    )
    square_images = convert_images_to_square(
        input_images, settings['square_folder'], effective_size
    )

    # Stage 7
    slideshow_raw = build_slideshow(
        square_images, slide_durations, effective_size,
        settings['FPS'], final_duration, settings['EFFECT_DURATION'], settings
    )

    bg_duration    = get_duration(settings['background'])
    slide_duration = get_duration(slideshow_raw)
    total_frames   = int(final_duration * settings['FPS'])

    print()
    print(f"📐 Background  : {fmt(bg_duration)}")
    print(f"📐 Slideshow   : {fmt(slide_duration)}")
    print(f"📐 Final video : {fmt(final_duration)}  →  {total_frames} frames")
    print()

    FRAME_W = settings['FRAME_W']

    # Log overlay types
    for label, key, w, h in [
        ("Marquee",  "marquee",  FRAME_W,            settings['MARQUEE_H']),
        ("Overlay1", "overlay1", settings['OV1_W'],  settings['OV1_H']),
        ("Overlay2", "overlay2", settings['OV2_W'],  settings['OV2_H']),
        ("Button",   "bottom",   settings['BTN_W'],  settings['BTN_H']),
    ]:
        path = settings[key]
        kind = "VIDEO" if is_video(path) else "IMAGE"
        print(f"   {label:10s}: [{kind}] {os.path.basename(path)}")
    print()

    # Build overlay readers
    overlay_readers = {
        'marquee':  OverlayReader(settings['marquee'],  FRAME_W,             settings['MARQUEE_H']),
        'overlay1': OverlayReader(settings['overlay1'], settings['OV1_W'],   settings['OV1_H']),
        'overlay2': OverlayReader(settings['overlay2'], settings['OV2_W'],   settings['OV2_H']),
        'button':   OverlayReader(settings['bottom'],   settings['BTN_W'],   settings['BTN_H']),
    }

    # Stage 8: Preview
    print("─" * 55)
    print("🖼️  Generating preview frames...")
    generate_previews(
        settings['background'], slideshow_raw, overlay_readers,
        settings, settings['preview_folder']
    )

    # Stage 9: Composite
    comp_raw = os.path.join(settings['base'], "composite_raw.mp4")
    composite_layers(
        settings['background'], slideshow_raw, overlay_readers, comp_raw,
        (settings['FRAME_W'], settings['FRAME_H']),
        settings['FPS'], total_frames, settings
    )

    # Stage 10: Encode
    final_video = generate_output_path(settings['base'], settings['OUTPUT_NAMING'])
    encode_final(
        comp_raw, settings['audio_path'], settings['AUDIO_MODE'],
        final_video, final_duration, settings['AUDIO_VOL']
    )

    # Stage 11: Save settings log
    save_settings_log(settings, final_video, final_duration, settings['logs_folder'])

    # Stage 12: Cleanup
    cleanup(slideshow_raw, comp_raw,
            settings['images_folder'], settings['square_folder'], final_video)

    total_time = time.time() - run_start
    print()
    print("=" * 55)
    print("🎉 Pipeline complete!")
    print(f"⏱️  Duration     : {fmt(final_duration)} ({final_duration:.1f}s)")
    print(f"🕐 Render time  : {fmt(total_time)}")
    print(f"💾 Final video  : {final_video}")
    print("=" * 55)


# ================== RUN ==================
run_video_pipeline(settings)
