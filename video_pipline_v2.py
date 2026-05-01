# ================== SETUP ==================
# Run these in a Colab cell before executing this script:
# !pip install pillow opencv-python-headless -q
# !apt-get install ffmpeg imagemagick -y -q

import os
import glob
import subprocess
import numpy as np
import cv2
from PIL import Image
from google.colab import drive, files as colab_files

# ================== SETTINGS ==================
base = "/content/drive/MyDrive/MyAutomation"

settings = {
    # ── Paths ──────────────────────────────────────────────────────────
    'base':          f'{base}/',
    'images_folder': f'{base}/images',
    'square_folder': f'{base}/square',

    'background':   f'{base}/assets/background/background.mp4',
    'marquee_png':  f'{base}/assets/marquee/marquee.png',
    'overlay1_png': f'{base}/assets/overlay1/overlay1.png',
    'overlay2_png': f'{base}/assets/overlay2/overlay2.png',
    'bottom_png':   f'{base}/assets/bottom/bottom.png',

    'audio_path': f'{base}/assets/audio/audio125.mp3',
    'AUDIO_MODE': '1',   # 1=Loop, 2=Single, 3=None
    'AUDIO_VOL':  1,     # Volume multiplier (1.0 = original)

    # ── Timing ─────────────────────────────────────────────────────────
    'FPS':             30,
    'DURATION':       2.8,   # Seconds each slide is shown
    'EFFECT_DURATION': 0.8,  # Bounce-in effect duration (seconds)

    # ── Frame size ─────────────────────────────────────────────────────
    'FRAME_W': 1080,
    'FRAME_H': 1920,

    # ── Slideshow area ─────────────────────────────────────────────────
    # SLIDE_H can be 1080 or 1200 — overlays are independent of this value.
    # Overlays are composited ON TOP of the slideshow, so changing SLIDE_H
    # does not affect OV2_Y, BTN_Y, MARQUEE_TOP, or OV1 positions.
    'SLIDE_W':      1080,
    'SLIDE_H':      1200,   # Change to 1200 for taller slides — nothing else needs updating
    'SLIDE_MARGIN':    0,   # Extra padding inside slide area (px)

    # ── Marquee (scrolling banner) ─────────────────────────────────────
    # Composited on top of the frame at a fixed Y position.
    'MARQUEE_H':     80,    # Height of the marquee PNG
    'MARQUEE_TOP':   80,    # Y position from top of frame
    'MARQUEE_SPEED': 120,   # Scroll speed in pixels/second (FPS-independent)

    # ── Overlay 1 (brand/logo bar) ─────────────────────────────────────
    # Sits just below the marquee, centered horizontally.
    # Y = MARQUEE_TOP + MARQUEE_H + 57
    'OV1_W': 600,
    'OV1_H': 140,

    # ── Overlay 2 (info/price bar) ─────────────────────────────────────
    # Fixed Y position — always composited on top of the slideshow.
    # Changing SLIDE_H does NOT move this overlay.
    'OV2_W': 1080,
    'OV2_H': 140,
    'OV2_Y': 1457,   # Fixed: overlaid on top of slide regardless of SLIDE_H

    # ── Bottom CTA button ──────────────────────────────────────────────
    # BTN_Y is derived automatically below — do NOT set it manually here.
    'BTN_W': 600,
    'BTN_H': 140,
    # BTN_Y is set after the dict using: OV2_Y + OV2_H + gap
}

# Derive BTN_Y automatically so it always stays below OV2
# Change the gap value (16) to adjust spacing between overlay2 and the button
settings['BTN_Y'] = settings['OV2_Y'] + settings['OV2_H'] + 16   # = 1603

IMAGE_EXT = [".jpg", ".jpeg", ".png", ".bmp", ".webp"]


# ================== HELPERS ==================

def mount_drive():
    """Mount Google Drive with clear error on failure."""
    try:
        drive.mount('/content/drive', force_remount=False)
        print("✅ Google Drive mounted.")
    except Exception as e:
        raise RuntimeError(f"❌ Google Drive mount failed: {e}")


def check_path(path, label, create=False):
    """Check path exists. Raise FileNotFoundError if missing (unless create=True)."""
    if os.path.exists(path):
        return True
    if create:
        os.makedirs(path, exist_ok=True)
        print(f"📁 Created folder: {path}")
        return True
    raise FileNotFoundError(f"❌ Missing required asset [{label}]: {path}")


def get_duration(filepath):
    """Return duration of a media file in seconds via ffprobe."""
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


def fmt(seconds):
    """Format seconds as Xm Ys string e.g. 1m 30s."""
    s = int(seconds)
    return f"{s // 60}m {s % 60}s"


def load_png(path, w, h):
    """Load a PNG with alpha channel and resize to (w, h)."""
    with Image.open(path).convert("RGBA") as im:
        return np.array(im.resize((w, h), Image.LANCZOS))


def alpha_composite(base_bgr, overlay_rgba, x, y):
    """
    Alpha-blend an RGBA overlay onto a BGR canvas at pixel position (x, y).
    Handles partial out-of-bounds overlays safely.
    """
    oh, ow = overlay_rgba.shape[:2]
    bh, bw = base_bgr.shape[:2]
    x1, y1 = max(x, 0), max(y, 0)
    x2, y2 = min(x + ow, bw), min(y + oh, bh)
    if x1 >= x2 or y1 >= y2:
        return base_bgr
    ox1 = x1 - x
    oy1 = y1 - y
    ox2 = ox1 + (x2 - x1)
    oy2 = oy1 + (y2 - y1)
    src     = overlay_rgba[oy1:oy2, ox1:ox2]
    alpha   = src[:, :, 3:4].astype(np.float32) / 255.0
    src_bgr = src[:, :, :3][:, :, ::-1]
    roi     = base_bgr[y1:y2, x1:x2].astype(np.float32)
    base_bgr[y1:y2, x1:x2] = (
        (1 - alpha) * roi + alpha * src_bgr.astype(np.float32)
    ).astype(np.uint8)
    return base_bgr


def open_video_writer(output_path, fps, size):
    """
    Try codecs avc1 → mp4v → XVID in order.
    Returns the first working VideoWriter or raises RuntimeError.
    """
    for codec in ['avc1', 'mp4v', 'XVID']:
        fourcc = cv2.VideoWriter_fourcc(*codec)
        writer = cv2.VideoWriter(output_path, fourcc, fps, size)
        if writer.isOpened():
            print(f"🎬 VideoWriter opened with codec: {codec}")
            return writer
        writer.release()
    raise RuntimeError(f"❌ All codecs failed. Cannot open VideoWriter: {output_path}")


def parse_duration_input(raw):
    """
    Parse user duration string.
    Accepts plain seconds (90 or 90.5) or mm:ss format (1:30).
    Returns float seconds, or None on invalid input.
    """
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


# ================== DURATION LOGIC ==================

def ask_video_duration(auto_duration, bg_duration):
    """
    Show upload summary then ask the user how long the final video should be.

    Behaviour based on comparison:
      Input > bg_duration  → background loops to fill
      Input == bg_duration → background fits exactly
      Input < auto_duration → slideshow trimmed
      Input > auto_duration → slideshow loops
      Enter (blank)         → use auto_duration

    Returns chosen duration as float seconds.
    """
    print()
    print("─" * 55)
    print("⏱️  How long should the final video be?")
    print(f"   [Enter]       → Auto: {fmt(auto_duration)} ({auto_duration:.1f}s)")
    print(f"   A number      → Seconds,   e.g.  90")
    print(f"   mm:ss format  → e.g.  1:30  or  2:00")
    print(f"   Minimum: 10s  |  No maximum cap")
    print("─" * 55)

    while True:
        raw = input("👉 Your choice: ").strip()

        if raw == "":
            chosen = auto_duration
            print(f"✅ Using auto duration: {fmt(chosen)} ({chosen:.1f}s)")
        else:
            chosen = parse_duration_input(raw)
            if chosen is None:
                print("❌ Invalid input. Try  90  or  1:30  then press Enter.")
                continue
            if chosen < 10:
                print("❌ Minimum is 10 seconds. Please enter a larger value.")
                continue
            print(f"✅ Final video set to: {fmt(chosen)} ({chosen:.1f}s)")

        print()

        # Background comparison
        if chosen > bg_duration + 0.1:
            loops = chosen / bg_duration
            extra = chosen - bg_duration
            print(f"   🔁 Background ({fmt(bg_duration)}) is SHORTER than your video.")
            print(f"      → Loops ~{loops:.2f}x  (repeats every {fmt(bg_duration)}, extra: {extra:.1f}s).")
        elif abs(chosen - bg_duration) <= 0.1:
            print(f"   ✅ Background fits exactly — no looping needed.")
        else:
            trim = bg_duration - chosen
            print(f"   ✂️  Background ({fmt(bg_duration)}) is LONGER than your video.")
            print(f"      → Trimmed by {trim:.1f}s.")

        # Slideshow comparison
        if chosen < auto_duration - 0.1:
            trimmed    = auto_duration - chosen
            cut_slides = int(trimmed / settings['DURATION'])
            print(f"   ✂️  Slideshow ({fmt(auto_duration)}) TRIMMED by"
                  f" {trimmed:.1f}s (~{cut_slides} slide(s) cut).")
        elif chosen > auto_duration + 0.1:
            loops = chosen / auto_duration
            print(f"   🔁 Slideshow ({fmt(auto_duration)}) LOOPS ~{loops:.2f}x"
                  f" to fill {fmt(chosen)}.")
        else:
            print(f"   ✅ Slideshow fits exactly — no looping or trimming needed.")

        print()
        return float(chosen)


# ================== IMAGE HANDLING ==================

def check_and_upload_images(images_folder, settings):
    """
    Full image upload flow:
      1. Delete existing images from folder.
      2. Upload new images — save each, show its full path.
      3. Handle duplicate filenames automatically.
      4. Auto-calculate slideshow duration from image count.
      5. Fetch background duration and warn if slideshow exceeds it.
      6. Ask user to confirm or change final video duration.
      7. Return (saved_paths, final_duration).
    """
    os.makedirs(images_folder, exist_ok=True)

    # Step 1: Delete old images
    existing = [
        f for f in glob.glob(f"{images_folder}/*")
        if os.path.isfile(f) and os.path.splitext(f)[1].lower() in IMAGE_EXT
    ]
    if existing:
        for f in existing:
            os.remove(f)
        print(f"🗑️  Deleted {len(existing)} old image(s) from images folder.")

    # Step 2 & 3: Upload and save
    print("📂 Please upload your image files (JPG, PNG, WEBP, BMP, etc.)")
    while True:
        uploaded = colab_files.upload()

        if not uploaded:
            print("⚠️  Nothing uploaded. Please try again.")
            continue

        saved   = []
        skipped = []

        for filename, data in uploaded.items():
            ext = os.path.splitext(filename)[1].lower()
            if ext not in IMAGE_EXT:
                skipped.append(filename)
                print(f"⚠️  Skipped (unsupported format): {filename}")
                continue

            # Resolve duplicate filenames
            base_name, file_ext = os.path.splitext(filename)
            dest    = os.path.join(images_folder, filename)
            counter = 1
            while os.path.exists(dest):
                dest = os.path.join(images_folder, f"{base_name}_{counter}{file_ext}")
                counter += 1

            with open(dest, "wb") as f:
                f.write(data)

            saved.append(dest)
            print(f"💾 Saved: {dest}")

        if skipped:
            print(f"\n⚠️  Skipped {len(skipped)} non-image file(s): {skipped}")

        if not saved:
            print("❌ No valid images saved. Please upload .jpg / .png / .webp etc.")
            continue

        print(f"\n✅ {len(saved)} image(s) uploaded.")
        print(f"📁 Folder: {images_folder}")

        # Step 4: Auto-calculate slideshow duration
        image_count   = len(saved)
        auto_duration = image_count * settings['DURATION']

        # Step 5: Background duration for comparison
        bg_duration = get_duration(settings['background'])

        print()
        print("─" * 55)
        print(f"📊 Upload summary:")
        print(f"   Images uploaded  : {image_count}")
        print(f"   Seconds per slide: {settings['DURATION']}s")
        print(f"   Slideshow length : {fmt(auto_duration)} ({auto_duration:.1f}s)")
        print(f"   Background video : {fmt(bg_duration)} ({bg_duration:.1f}s)")
        print(f"   Slide height     : {settings['SLIDE_H']}px")
        print(f"   OV2_Y (fixed)    : {settings['OV2_Y']}px  (overlaid on top of slide)")
        print(f"   BTN_Y (derived)  : {settings['BTN_Y']}px")

        if auto_duration > bg_duration:
            over = auto_duration - bg_duration
            print()
            print(f"   ⚠️  Slideshow ({fmt(auto_duration)}) is LONGER than background"
                  f" ({fmt(bg_duration)}) by {over:.1f}s.")
            print(f"       Background will loop automatically.")
        elif auto_duration < bg_duration:
            under = bg_duration - auto_duration
            print()
            print(f"   ℹ️  Slideshow ({fmt(auto_duration)}) is SHORTER than background"
                  f" ({fmt(bg_duration)}) by {under:.1f}s.")
            print(f"       You can extend the video — slideshow will loop to fill.")
        else:
            print()
            print(f"   ✅ Slideshow and background are the same length.")

        # Step 6: Ask user for final duration
        final_duration = ask_video_duration(auto_duration, bg_duration)

        return saved, final_duration


# ================== IMAGE CONVERSION ==================

def convert_images_to_square(input_images, square_folder, size):
    """
    Letterbox each image into the target size (no stretching).
    - Scales down preserving aspect ratio
    - Pads with black to fill remaining space
    - Saves as JPEG for consistent format
    - Skips corrupt or unreadable files with a warning
    """
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
            print(f"⚠️  Skipping unreadable image [{filename}]: {e}")

    if not converted:
        raise RuntimeError("❌ No valid images could be converted.")

    return converted


# ================== SLIDESHOW BUILDER ==================

def build_slideshow(image_paths, size, fps, final_duration, effect_duration, settings):
    """
    Build a slideshow video exactly `final_duration` seconds long.

    Each image is shown for settings['DURATION'] seconds with a bounce-in effect.
    The image sequence loops automatically if final_duration > natural slideshow length.
    The sequence is trimmed automatically if final_duration < natural slideshow length.

    Returns the path to the built slideshow file.
    """
    output_path    = os.path.join(settings['base'], "slideshow_raw.mp4")
    total_frames   = int(final_duration * fps)
    frames_per_img = int(settings['DURATION'] * fps)
    effect_frames  = int(effect_duration * fps)
    decay          = max(effect_frames / 4.0, 1.0)

    # Pre-load all slides to avoid repeated disk reads
    slides = []
    for img_path in image_paths:
        img = cv2.imread(img_path)
        if img is None:
            print(f"⚠️  Could not read: {img_path}")
            continue
        slides.append(cv2.resize(img, size))

    if not slides:
        raise RuntimeError("❌ No valid slides could be loaded.")

    writer = open_video_writer(output_path, fps, size)

    try:
        for frame_idx in range(total_frames):
            slide_idx = (frame_idx // frames_per_img) % len(slides)
            n         = frame_idx % frames_per_img

            img = slides[slide_idx]
            h   = img.shape[0]

            if n < effect_frames:
                offset_y = int(h * np.exp(-n / decay) * np.cos(n / 8.0) ** 2)
            else:
                offset_y = 0

            M     = np.float32([[1, 0, 0], [0, 1, offset_y]])
            frame = cv2.warpAffine(
                img, M, size,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=(0, 0, 0)
            )
            writer.write(frame)
    finally:
        writer.release()

    print(f"✅ Slideshow built: {output_path}")
    return output_path


# ================== COMPOSITING ==================

def composite_layers(background_path, slideshow_path, overlays, output_path,
                     frame_size, fps, total_frames, settings):
    """
    Composite all layers frame-by-frame into a single raw video.

    Layer order (bottom to top):
      1. Background video  — full frame, loops automatically
      2. Slideshow frames  — composited into slide area, loops automatically
      3. Marquee           — scrolling banner, speed in px/second (FPS-independent)
      4. Overlay 1         — brand/logo bar, fixed position
      5. Overlay 2         — info/price bar, fixed position ON TOP of slideshow
      6. Bottom button     — CTA button, fixed position below overlay 2

    Both background and slideshow loop by seeking back to frame 0 when exhausted.
    Prints progress every 30 frames.
    """
    FRAME_W, FRAME_H = frame_size

    bg_cap = cv2.VideoCapture(background_path)
    sl_cap = cv2.VideoCapture(slideshow_path)

    if not bg_cap.isOpened():
        raise RuntimeError(f"❌ Cannot open background: {background_path}")
    if not sl_cap.isOpened():
        raise RuntimeError(f"❌ Cannot open slideshow: {slideshow_path}")

    writer = open_video_writer(output_path, fps, frame_size)

    # Slideshow area — centered horizontally, starts at calculated Y
    slide_area_w = settings['SLIDE_W'] - 2 * settings['SLIDE_MARGIN']
    slide_area_h = settings['SLIDE_H'] - 2 * settings['SLIDE_MARGIN']
    slide_x      = (FRAME_W - slide_area_w) // 2
    slide_y      = (
        settings['MARQUEE_TOP']
        + settings['MARQUEE_H']
        + 57
        + settings['OV1_H']
        + 20
    )

    try:
        for frame_idx in range(total_frames):
            if frame_idx % 30 == 0:
                pct = int(frame_idx / total_frames * 100)
                print(f"  ⏳ Compositing {frame_idx}/{total_frames} ({pct}%)", end='\r')

            # ── Layer 1: Background (loop on exhaustion) ──────────────
            ret_bg, bg_frame = bg_cap.read()
            if not ret_bg:
                bg_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret_bg, bg_frame = bg_cap.read()
            canvas = cv2.resize(bg_frame, frame_size)

            # ── Layer 2: Slideshow (loop on exhaustion) ───────────────
            ret_sl, sl_frame = sl_cap.read()
            if not ret_sl:
                sl_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret_sl, sl_frame = sl_cap.read()
            if ret_sl:
                sl_resized = cv2.resize(sl_frame, (slide_area_w, slide_area_h))
                canvas[
                    slide_y:slide_y + slide_area_h,
                    slide_x:slide_x + slide_area_w
                ] = sl_resized

            # ── Layer 3: Marquee (scrolling, FPS-independent speed) ───
            mq       = overlays['marquee']['img']
            scroll_x = int((frame_idx / fps) * settings['MARQUEE_SPEED']) % FRAME_W
            mq_tile  = np.concatenate([mq, mq], axis=1)
            mq_crop  = mq_tile[:, scroll_x:scroll_x + FRAME_W]
            canvas   = alpha_composite(
                canvas, mq_crop,
                overlays['marquee']['x'],
                overlays['marquee']['y']
            )

            # ── Layers 4–6: Static overlays (on top of everything) ────
            for key in ['overlay1', 'overlay2', 'button']:
                ov = overlays[key]
                canvas = alpha_composite(canvas, ov['img'], ov['x'], ov['y'])

            writer.write(canvas)

    finally:
        bg_cap.release()
        sl_cap.release()
        writer.release()

    print(f"\n✅ Composite built: {output_path}")


# ================== ENCODING ==================

def encode_final(comp_raw, audio_path, audio_mode, output_path, duration, volume):
    """
    Encode the composite video with audio using ffmpeg.

    Audio modes:
      '1' → loop audio to fill the entire video duration
      '2' → single play (warns if audio is shorter than video)
      '3' → no audio

    Raises RuntimeError if ffmpeg fails or output file is missing/empty.
    """
    base_cmd = ['ffmpeg', '-y', '-i', comp_raw]

    if audio_mode == "3" or not os.path.exists(audio_path):
        cmd = base_cmd + [
            '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
            output_path
        ]

    elif audio_mode == "1":
        cmd = (base_cmd
               + ['-stream_loop', '-1', '-i', audio_path]
               + ['-filter_complex', f'[1:a]volume={volume}[a]']
               + ['-map', '0:v', '-map', '[a]']
               + ['-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                  '-c:a', 'aac', '-b:a', '192k',
                  '-t', str(duration), output_path])

    elif audio_mode == "2":
        audio_dur = get_duration(audio_path)
        if audio_dur < duration:
            print(f"⚠️  Audio ({audio_dur:.1f}s) shorter than video ({duration:.1f}s)."
                  " Tail will be silent. Consider AUDIO_MODE '1' to loop.")
        cmd = (base_cmd
               + ['-i', audio_path]
               + ['-filter_complex', f'[1:a]volume={volume}[a]']
               + ['-map', '0:v', '-map', '[a]']
               + ['-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                  '-c:a', 'aac', '-b:a', '192k',
                  '-t', str(duration), output_path])
    else:
        raise ValueError(f"❌ Unknown AUDIO_MODE '{audio_mode}'. Use '1', '2', or '3'.")

    print("🎞️  Encoding final video with ffmpeg...")
    result = subprocess.run(cmd, stderr=subprocess.PIPE)

    if result.returncode != 0:
        raise RuntimeError(f"❌ FFmpeg failed:\n{result.stderr.decode()}")

    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError(f"❌ Output file missing or empty: {output_path}")

    print(f"✅ Encoded: {output_path}")


# ================== CLEANUP ==================

def cleanup(slideshow_raw, comp_raw, images_folder, final_video):
    """
    Delete temporary files and clear the images folder.
    Skips entirely if the final video is not confirmed to exist and have content —
    this preserves files for debugging if the pipeline failed mid-run.
    """
    if not os.path.exists(final_video) or os.path.getsize(final_video) == 0:
        print("⚠️  Final video not confirmed — skipping cleanup to preserve files.")
        return

    for path in [slideshow_raw, comp_raw]:
        if os.path.exists(path):
            os.remove(path)

    for f in glob.glob(os.path.join(images_folder, "*")):
        if os.path.isfile(f):
            os.remove(f)

    print("🧹 Temp files and images folder cleaned.")


# ================== PIPELINE ==================

def run_video_pipeline(settings):
    """
    Main pipeline entry point. Runs all stages in order:

      Stage 1  Mount Google Drive
      Stage 2  Validate all required asset paths
      Stage 3  Upload images → show paths → auto-calc duration → ask user
      Stage 4  Convert images to square (letterbox, no stretching)
      Stage 5  Build slideshow (loops or trims to match chosen duration)
      Stage 6  Load overlays and composite all layers
               - Background loops if shorter than final_duration
               - Slideshow placed first, overlays composited ON TOP
               - OV2_Y and BTN_Y are fixed regardless of SLIDE_H
      Stage 7  Encode final video with audio (ffmpeg)
      Stage 8  Cleanup temp files (only if final video confirmed)
    """
    print("=" * 55)
    print("🚀 Starting video pipeline...")
    print(f"   SLIDE_H : {settings['SLIDE_H']}px")
    print(f"   OV2_Y   : {settings['OV2_Y']}px  (fixed, overlaid on slide)")
    print(f"   BTN_Y   : {settings['BTN_Y']}px  (derived: OV2_Y + OV2_H + 16)")
    print("=" * 55)

    # ── Stage 1: Mount Drive ──────────────────────────────────────────
    mount_drive()

    # ── Stage 2: Validate paths ───────────────────────────────────────
    check_path(settings['base'], "Base folder")
    check_path(settings['images_folder'], "Images folder", create=True)
    check_path(settings['square_folder'], "Square folder",  create=True)

    for label, path in [
        ('Background video', settings['background']),
        ('Marquee PNG',      settings['marquee_png']),
        ('Overlay1 PNG',     settings['overlay1_png']),
        ('Overlay2 PNG',     settings['overlay2_png']),
        ('Bottom PNG',       settings['bottom_png']),
    ]:
        check_path(path, label)

    # ── Stage 3: Upload images + choose duration ──────────────────────
    input_images, final_duration = check_and_upload_images(
        settings['images_folder'], settings
    )

    # ── Stage 4: Convert to square (letterbox) ────────────────────────
    effective_size = (
        settings['SLIDE_W'] - 2 * settings['SLIDE_MARGIN'],
        settings['SLIDE_H'] - 2 * settings['SLIDE_MARGIN'],
    )
    square_images = convert_images_to_square(
        input_images, settings['square_folder'], effective_size
    )

    # ── Stage 5: Build slideshow (exact final_duration length) ────────
    slideshow_raw = build_slideshow(
        square_images, effective_size,
        settings['FPS'], final_duration,
        settings['EFFECT_DURATION'], settings
    )

    # ── Stage 6: Load overlays and composite ──────────────────────────
    bg_duration    = get_duration(settings['background'])
    slide_duration = get_duration(slideshow_raw)
    total_frames   = int(final_duration * settings['FPS'])

    print()
    print(f"📐 Background  : {fmt(bg_duration)} ({bg_duration:.2f}s)")
    print(f"📐 Slideshow   : {fmt(slide_duration)} ({slide_duration:.2f}s)")
    print(f"📐 Final video : {fmt(final_duration)} ({final_duration:.2f}s)"
          f"  →  {total_frames} frames")
    print()

    # Build overlays dict — named keys instead of a list to make order explicit
    FRAME_W = settings['FRAME_W']

    overlays = {
        'marquee': {
            'img': load_png(settings['marquee_png'], FRAME_W, settings['MARQUEE_H']),
            'x': 0,
            'y': settings['MARQUEE_TOP'],
        },
        'overlay1': {
            'img': load_png(settings['overlay1_png'], settings['OV1_W'], settings['OV1_H']),
            'x': (FRAME_W - settings['OV1_W']) // 2,
            'y': settings['MARQUEE_TOP'] + settings['MARQUEE_H'] + 57,
        },
        'overlay2': {
            'img': load_png(settings['overlay2_png'], settings['OV2_W'], settings['OV2_H']),
            'x': (FRAME_W - settings['OV2_W']) // 2,
            'y': settings['OV2_Y'],   # Fixed — independent of SLIDE_H
        },
        'button': {
            'img': load_png(settings['bottom_png'], settings['BTN_W'], settings['BTN_H']),
            'x': (FRAME_W - settings['BTN_W']) // 2,
            'y': settings['BTN_Y'],   # Derived — OV2_Y + OV2_H + 16
        },
    }

    comp_raw = os.path.join(settings['base'], "composite_raw.mp4")
    composite_layers(
        settings['background'], slideshow_raw, overlays, comp_raw,
        (settings['FRAME_W'], settings['FRAME_H']),
        settings['FPS'], total_frames, settings
    )

    # ── Stage 7: Encode final video ───────────────────────────────────
    final_video = os.path.join(settings['base'], "final_video.mp4")
    encode_final(
        comp_raw, settings['audio_path'], settings['AUDIO_MODE'],
        final_video, final_duration, settings['AUDIO_VOL']
    )

    # ── Stage 8: Cleanup ──────────────────────────────────────────────
    cleanup(slideshow_raw, comp_raw, settings['images_folder'], final_video)

    print()
    print("=" * 55)
    print("🎉 Pipeline complete!")
    print(f"📹 Final video : {final_video}")
    print(f"⏱️  Duration   : {fmt(final_duration)} ({final_duration:.1f}s)")
    print("=" * 55)


# ================== RUN ==================
run_video_pipeline(settings)
