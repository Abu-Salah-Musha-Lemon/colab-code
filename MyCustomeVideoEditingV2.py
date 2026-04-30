# ================== SETUP ==================
!pip install pillow opencv-python-headless -q
!apt-get install ffmpeg imagemagick -y -q

import os
import glob
import subprocess
import numpy as np
import cv2
import shutil
from PIL import Image
import time
from google.colab import files as colab_files
IMAGE_EXT = [".jpg", ".jpeg", ".png", ".bmp", ".webp"]

# ================== MOUNT GOOGLE DRIVE ==================
print("=" * 50)
print("📂 Mounting Google Drive...")
from google.colab import drive
drive.mount('/content/drive', force_remount=False)

# ================== PATHS ==================
base          = "/content/drive/MyDrive/MyAutomation"
images_folder = f"{base}/images"
square_folder = f"{base}/square"
background    = f"{base}/assets/background/background.mp4"      # full 1080x1920 bg video
marquee_png   = f"{base}/assets/marquee/marquee.png"            # scrolling top image
overlay1_png  = f"{base}/assets/overlay1/overlay1.png"          # 600x140 centered under marquee
overlay2_png  = f"{base}/assets/overlay2/overlay2.png"          # 1080x140 strip at y=1447
bottom_png    = f"{base}/assets/bottom/bottom.png"              # 600x140 button at bottom
audio_path    = f"{base}/assets/audio/audio125.mp3"             # supports mp3, aac, wav, m4a

# ================== FOLDER & FILE ACCESS CHECK ==================
print("\n" + "=" * 50)
print("🔍 Checking folder & file access...")

errors = []

def check_path(path, label, create=False):
    if os.path.exists(path):
        size = os.path.getsize(path) if os.path.isfile(path) else None
        info = f"({round(size/1024/1024,2)} MB)" if size else ""
        print(f"✅ {label:<30}: {os.path.basename(path)} {info}")
        return True
    else:
        if create:
            try:
                os.makedirs(path, exist_ok=True)
                print(f"📁 {label:<30}: created → {path}")
                return True
            except Exception as e:
                errors.append(f"❌ {label}: cannot create → {e}")
                return False
        else:
            errors.append(f"❌ {label:<30}: NOT FOUND → {path}")
            return False

check_path(base,          "Base folder",      create=False)
check_path(images_folder, "Images folder",    create=True)
check_path(background,    "Background video")
check_path(marquee_png,   "Marquee PNG")
check_path(overlay1_png,  "Overlay1 PNG")
check_path(overlay2_png,  "Overlay2 PNG")
check_path(bottom_png,    "Bottom PNG")

try:
    test_file = f"{base}/.write_test"
    with open(test_file, "w") as f: f.write("ok")
    os.remove(test_file)
    print(f"✅ {'Write permission':<30}: OK")
except Exception as e:
    errors.append(f"❌ Write permission: {e}")

if errors:
    print("\n🚨 Fix these before continuing:")
    for e in errors: print(f"   {e}")
    raise SystemExit("❌ Access check failed.")

print("\n✅ All paths OK — starting pipeline...\n")

# ================== USER SETTINGS ==================
print("=" * 50)
print("⚙️  USER SETTINGS — enter all values")
print("=" * 50)

# ── Video ────────────────────────────────────────────
FPS           = int(float(input("FPS (e.g. 24 / 30 / 60)                          : ")))

# ── Frame ────────────────────────────────────────────
FRAME_W       = int(input("Frame width  px (e.g. 1080)                        : "))
FRAME_H       = int(input("Frame height px (e.g. 1920)                        : "))

# ── Marquee ──────────────────────────────────────────
MARQUEE_H     = int(input("Marquee height px (e.g. 80)                        : "))
MARQUEE_TOP   = int(input("Marquee top margin px (e.g. 50)                    : "))
MARQUEE_SPEED = int(input("Marquee scroll speed px/frame (e.g. 3)             : "))

# ── Overlay1 (under marquee) ─────────────────────────
OV1_W         = int(input("Overlay1 width  px (e.g. 600)                      : "))
OV1_H         = int(input("Overlay1 height px (e.g. 140)                      : "))

# ── Slideshow zone ───────────────────────────────────
SLIDE_W       = int(input("Slideshow width  px (e.g. 1080)                    : "))
SLIDE_H       = int(input("Slideshow height px (e.g. 1200)                    : "))
SLIDE_MARGIN  = int(input("Slideshow inner margin px (e.g. 4)                 : "))

# ── Animation ────────────────────────────────────────
DURATION        = float(input("Per image duration  (e.g. 0.5 / 1.0 / 1.5 / 2.0) : "))
EFFECT_DURATION = float(input("Bounce effect dur   (must be <= duration)          : "))

if EFFECT_DURATION > DURATION:
    EFFECT_DURATION = DURATION
    print(f"⚠️  Effect capped to {DURATION}s")

# ── Overlay2 (at y=1447) ─────────────────────────────
OV2_W         = int(input("Overlay2 width  px (e.g. 1080)                     : "))
OV2_H         = int(input("Overlay2 height px (e.g. 140)                      : "))
OV2_Y         = int(input("Overlay2 Y pos  px (e.g. 1447)                     : "))

# ── Bottom button ────────────────────────────────────
BTN_W         = int(input("Bottom button width  px (e.g. 600)                 : "))
BTN_H         = int(input("Bottom button height px (e.g. 140)                 : "))
BTN_MARGIN    = int(input("Bottom button margin from bottom px (e.g. 50)      : "))

# ================== AUDIO SETTINGS ==================
# Add to USER SETTINGS section

# audio_path = f"{base}/assets/audio/audio125.mp3"   # supports mp3, aac, wav, m4a

print("\nAudio Settings:")
print("  1 = Loop audio to match video length")
print("  2 = Trim audio to match video length")
print("  3 = No audio")
AUDIO_MODE = input("Audio mode (1 / 2 / 3)                            : ").strip()
AUDIO_VOL  = float(input("Audio volume (e.g. 0.5 / 1.0 / 1.5)              : "))

# ── Auto-calculate all positions (everything centered) ──
MARQUEE_W     = FRAME_W                              # full width
MARQUEE_X     = 0
MARQUEE_Y     = MARQUEE_TOP

OV1_X         = (FRAME_W - OV1_W) // 2
# OV1_Y         = MARQUEE_Y + MARQUEE_H               # directly under marquee
OV1_Y         = MARQUEE_Y + MARQUEE_H+57               # directly under marquee

SLIDE_X       = (FRAME_W - SLIDE_W) // 2
SLIDE_Y       = OV1_Y + OV1_H                       # directly under overlay1
effective_w   = SLIDE_W - SLIDE_MARGIN * 2
effective_h   = SLIDE_H - SLIDE_MARGIN * 2
SLIDE_CX      = SLIDE_X + SLIDE_MARGIN              # content X (with margin)
SLIDE_CY      = SLIDE_Y + SLIDE_MARGIN              # content Y (with margin)
SIZE          = (effective_w, effective_h)

OV2_X         = (FRAME_W - OV2_W) // 2

BTN_X         = (FRAME_W - BTN_W) // 2
# BTN_Y         = FRAME_H - BTN_MARGIN - BTN_H
BTN_Y         = 1600

print(f"""
┌─────────────────────────────────────────────────────┐
  FPS                   : {FPS}
  Frame                 : {FRAME_W}x{FRAME_H}
  ───────────────────────────────────────────────────
  Layer 1  background   : {FRAME_W}x{FRAME_H}
                          x=0  y=0  (full frame)
  ───────────────────────────────────────────────────
  Layer 2  marquee      : {MARQUEE_W}x{MARQUEE_H}
                          x={MARQUEE_X}  y={MARQUEE_Y}  (top margin={MARQUEE_TOP}px)
                          scroll={MARQUEE_SPEED}px/frame
  ───────────────────────────────────────────────────
  Layer 3  overlay1     : {OV1_W}x{OV1_H}
                          x={OV1_X} (centered)  y={OV1_Y}
  ───────────────────────────────────────────────────
  Layer 4  slideshow    : {SLIDE_W}x{SLIDE_H}
                          x={SLIDE_X} (centered)  y={SLIDE_Y}
                          margin={SLIDE_MARGIN}px → {effective_w}x{effective_h}
                          content at x={SLIDE_CX}  y={SLIDE_CY}
  ───────────────────────────────────────────────────
  Layer 5  overlay2     : {OV2_W}x{OV2_H}
                          x={OV2_X} (centered)  y={OV2_Y}
  ───────────────────────────────────────────────────
  Layer 6  bottom btn   : {BTN_W}x{BTN_H}
                          x={BTN_X} (centered)  y={BTN_Y}
                          margin={BTN_MARGIN}px from bottom
└─────────────────────────────────────────────────────┘
""")

confirm = input("✅ Confirm layout and start? (y/n) : ").strip().lower()
if confirm != 'y':
    raise SystemExit("Pipeline cancelled.")

# ================== HELPERS ==================
def get_duration(filepath):
    result = subprocess.run(
        ["ffprobe", "-v", "error",
         "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", filepath],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return float(result.stdout.strip())

def load_png(path, w, h):
    with Image.open(path).convert("RGBA") as im:
        return np.array(im.resize((w, h), Image.LANCZOS))

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

# ================== STEP 1: Check images ==================
print("\n" + "=" * 50)
print("Step 1: Check images folder")

# import time
# from google.colab import files as colab_files


def check_and_upload_images():
    """Check images folder. If empty, open upload dialog and save to folder."""
    while True:
        input_images = [f for f in glob.glob(f"{images_folder}/*")
                        if os.path.isfile(f)]

        if len(input_images) > 0:
            print(f"✅ Found {len(input_images)} image(s):")
            for f in input_images:
                size = round(os.path.getsize(f) / 1024, 1)
                print(f"   {os.path.basename(f)}  ({size} KB)")
            return input_images

        # ── Folder is empty ──────────────────────────
        print(f"⚠️  Images folder is empty: {images_folder}")
        print(f"\nOptions:")
        print(f"  1 = Upload images now (opens file picker)")
        print(f"  2 = I already copied images to Drive — re-check")
        print(f"  3 = Cancel pipeline")

        choice = input("\nChoose (1 / 2 / 3) : ").strip()

        if choice == "1":
            # ── Upload via Colab file picker ─────────
            print(f"\n📂 Opening file picker — select your images...")
            print(f"   (supports jpg, jpeg, png, bmp, webp)")
            try:
                uploaded = colab_files.upload()   # opens browser dialog

                if not uploaded:
                    print("⚠️  No files uploaded. Try again.")
                    continue

                saved   = []
                skipped = []

                for filename, data in uploaded.items():
                    ext = os.path.splitext(filename)[1].lower()
                    if ext not in IMAGE_EXT:
                        skipped.append(filename)
                        print(f"   ⚠️  Skipped (not an image): {filename}")
                        continue

                    dest = os.path.join(images_folder, filename)
                    with open(dest, "wb") as f:
                        f.write(data)
                    saved.append(filename)
                    size = round(len(data) / 1024, 1)
                    print(f"   ✅ Saved: {filename}  ({size} KB)")

                if skipped:
                    print(f"\n   ⚠️  {len(skipped)} non-image file(s) skipped: "
                          f"{', '.join(skipped)}")

                if not saved:
                    print("❌ No valid images saved. Try again.")
                    continue

                print(f"\n✅ {len(saved)} image(s) saved to: {images_folder}")
                # loop back to re-check

            except Exception as e:
                print(f"❌ Upload failed: {e}")
                print("   Try option 2 — copy files manually to Drive first.")
                continue

        elif choice == "2":
            # ── Re-check Drive folder ────────────────
            print(f"\n🔄 Re-checking: {images_folder}")
            time.sleep(1)
            continue

        elif choice == "3":
            raise SystemExit("Pipeline cancelled — no images provided.")

        else:
            print("❓ Invalid choice. Enter 1, 2, or 3.")

# ── Run check ────────────────────────────────────────
input_images = check_and_upload_images()

# ================== STEP 2: Convert images ==================
print("\n" + "=" * 50)
print(f"Step 2: Convert images → {effective_w}x{effective_h}")

os.makedirs(square_folder, exist_ok=True)
converted = [];  convert_failed = []

for img_path in input_images:
    filename = os.path.basename(img_path)
    output   = f"{square_folder}/{filename}"
    try:
        with Image.open(img_path) as im:
            w, h = im.size
            print(f"   {filename} → {w}x{h}", end=" ")
    except Exception as e:
        print(f"\n   ⚠️ Cannot read: {e}")
        convert_failed.append(img_path); continue

    if w == effective_w and h == effective_h:
        shutil.copy2(img_path, output)
        print(f"→ already correct ✅")
        converted.append(img_path); continue

    cmd = (f'convert "{img_path}" -resize {effective_w}x{effective_h}^ '
           f'-gravity center -extent {effective_w}x{effective_h} "{output}"')
    if os.system(cmd) == 0 and os.path.exists(output):
        print(f"→ converted ✅"); converted.append(img_path)
    else:
        print(f"→ ❌ FAILED"); convert_failed.append(img_path)

print(f"\n✅ Converted: {len(converted)}  ❌ Failed: {len(convert_failed)}")
if len(converted) == 0:
    raise SystemExit("No images converted.")

for img_path in converted:
    try: os.remove(img_path)
    except: pass

# ================== STEP 3: Verify ==================
print("\n" + "=" * 50)
print("Step 3: Verify converted images")

square_images = sorted([f for f in glob.glob(f"{square_folder}/*") if os.path.isfile(f)])
if len(square_images) == 0:
    raise SystemExit("❌ Square folder empty.")
print(f"✅ {len(square_images)} image(s) ready")

# ================== STEP 4: Build slideshow ==================
print("\n" + "=" * 50)
print("Step 4: Build slideshow — Swing D bounce")

total_frames  = int(round(DURATION * FPS))
effect_frames = int(round(EFFECT_DURATION * FPS))
decay         = effect_frames / 4.0
print(f"   {total_frames} frames/image  |  {effect_frames} effect frames")

output_path    = f"{base}/slideshow_raw.mp4"
writer         = cv2.VideoWriter(output_path,
                                 cv2.VideoWriter_fourcc(*'mp4v'),
                                 FPS, SIZE)
success_images = []

for idx, img_path in enumerate(square_images):
    print(f"  [{idx+1}/{len(square_images)}] {os.path.basename(img_path)}")
    img = cv2.imread(img_path)
    if img is None:
        print(f"  ⚠️ Skipping"); continue
    img  = cv2.resize(img, SIZE)
    h, w = img.shape[:2]
    for n in range(total_frames):
        offset_y = (int(h * np.exp(-n / decay) * np.cos(n / 8.0) ** 2)
                    if n < effect_frames else 0)
        M     = np.float32([[1, 0, 0], [0, 1, offset_y]])
        frame = cv2.warpAffine(img, M, SIZE,
                               borderMode=cv2.BORDER_CONSTANT,
                               borderValue=(0, 0, 0))
        writer.write(frame)
    success_images.append(img_path)

writer.release()

slideshow_path = f"{base}/slideshow.mp4"
ret = os.system(
    f'ffmpeg -y -i "{output_path}" -c:v libx264 -pix_fmt yuv420p -r {FPS} "{slideshow_path}"')

if ret == 0 and os.path.exists(slideshow_path):
    os.remove(output_path)
    deleted = 0
    for p in success_images:
        try: os.remove(p); deleted += 1
        except: pass
    try:
        if not os.listdir(square_folder): os.rmdir(square_folder)
    except: pass
    print(f"✅ Slideshow ready  |  🗑️ {deleted} square images cleared")
else:
    raise SystemExit("❌ Slideshow creation failed.")

# ================== STEP 5: Duration match ==================
print("\n" + "=" * 50)
print("Step 5: Match durations")

bg_duration         = get_duration(background)
slideshow_duration  = get_duration(slideshow_path)
final_duration      = min(bg_duration, slideshow_duration)
total_output_frames = int(final_duration * FPS)

print(f"Background  : {bg_duration}s")
print(f"Slideshow   : {slideshow_duration}s")
print(f"Final       : {final_duration}s  ({total_output_frames} frames)")

# ================== STEP 6: Pre-load static PNGs ==================
print("\n" + "=" * 50)
print("Step 6: Pre-load PNG overlays")

# Marquee — full width, tiled x2 for seamless scroll
mq_img  = load_png(marquee_png, FRAME_W, MARQUEE_H)
mq_tile = np.concatenate([mq_img, mq_img], axis=1)
print(f"   Marquee  : {FRAME_W}x{MARQUEE_H}  tiled x2")

# Overlay1 — centered under marquee
ov1_img = load_png(overlay1_png, OV1_W, OV1_H)
print(f"   Overlay1 : {OV1_W}x{OV1_H}  x={OV1_X}  y={OV1_Y}")

# Overlay2 — centered at OV2_Y
ov2_img = load_png(overlay2_png, OV2_W, OV2_H)
print(f"   Overlay2 : {OV2_W}x{OV2_H}  x={OV2_X}  y={OV2_Y}")

# Bottom button — centered
btn_img = load_png(bottom_png, BTN_W, BTN_H)
print(f"   Bottom   : {BTN_W}x{BTN_H}  x={BTN_X}  y={BTN_Y}")

# ================== STEP 7: Composite ==================
print("\n" + "=" * 50)
print("Step 7: Composite all layers")

bg_cap     = cv2.VideoCapture(background)
sl_cap     = cv2.VideoCapture(slideshow_path)
comp_raw   = f"{base}/composite_raw.mp4"
out_writer = cv2.VideoWriter(comp_raw,
                             cv2.VideoWriter_fourcc(*'mp4v'),
                             FPS, (FRAME_W, FRAME_H))

for frame_idx in range(total_output_frames):

    # ── Layer 1: Background video ─────────────────────────────────────
    ret_bg, bg_frame = bg_cap.read()
    if not ret_bg:
        bg_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        _, bg_frame = bg_cap.read()
    canvas = cv2.resize(bg_frame, (FRAME_W, FRAME_H))

    # ── Layer 2: Marquee — scrolls left→right, 50px top margin ───────
    scroll_x = (frame_idx * MARQUEE_SPEED) % FRAME_W
    mq_crop  = mq_tile[:, scroll_x:scroll_x + FRAME_W]
    canvas   = alpha_composite(canvas, mq_crop, MARQUEE_X, MARQUEE_Y)

    # ── Layer 3: Overlay1 — 600x140 centered under marquee ───────────
    canvas = alpha_composite(canvas, ov1_img, OV1_X, OV1_Y)

    # ── Layer 4: Slideshow — centered, under overlay1 ─────────────────
    ret_sl, sl_frame = sl_cap.read()
    if not ret_sl:
        sl_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        _, sl_frame = sl_cap.read()
    if ret_sl:
        sl_resized = cv2.resize(sl_frame, SIZE)
        canvas[SLIDE_CY:SLIDE_CY + effective_h,
               SLIDE_CX:SLIDE_CX + effective_w] = sl_resized

    # ── Layer 5: Overlay2 — 1080x140 centered at y=OV2_Y ─────────────
    canvas = alpha_composite(canvas, ov2_img, OV2_X, OV2_Y)

    # ── Layer 6: Bottom button — 600x140 centered, 50px from bottom ──
    canvas = alpha_composite(canvas, btn_img, BTN_X, BTN_Y)

    out_writer.write(canvas)

    if frame_idx % (FPS * 5) == 0:
        pct = round(frame_idx / total_output_frames * 100, 1)
        print(f"   {frame_idx}/{total_output_frames}  "
              f"({round(frame_idx/FPS,1)}s)  {pct}%")

bg_cap.release()
sl_cap.release()
out_writer.release()
print("✅ Composite raw done")

# ================== STEP 8: Encode final with audio ==================
print("\n" + "=" * 50)
print("Step 8: Encode final video with audio")

final = f"{base}/final_video.mp4"

if AUDIO_MODE == "3" or not os.path.exists(audio_path):
    # ── No audio ─────────────────────────────────────────────────────
    if AUDIO_MODE != "3":
        print(f"⚠️  audio.mp3 not found — encoding without audio")
    ret = os.system(
        f'ffmpeg -y -i "{comp_raw}" '
        f'-c:v libx264 -preset fast -pix_fmt yuv420p '
        f'"{final}"')

elif AUDIO_MODE == "1":
    # ── Loop audio to fill video length ──────────────────────────────
    print(f"🎵 Audio: looping to {final_duration}s  volume={AUDIO_VOL}")
    ret = os.system(
        f'ffmpeg -y '
        f'-i "{comp_raw}" '
        f'-stream_loop -1 -i "{audio_path}" '
        f'-filter_complex "[1:a]volume={AUDIO_VOL}[a]" '
        f'-map 0:v -map "[a]" '
        f'-c:v libx264 -preset fast -pix_fmt yuv420p '
        f'-c:a aac -b:a 192k '
        f'-t {final_duration} '
        f'"{final}"')

elif AUDIO_MODE == "2":
    # ── Trim audio to video length ────────────────────────────────────
    audio_duration = get_duration(audio_path)
    print(f"🎵 Audio: {audio_duration}s trimmed to {final_duration}s  volume={AUDIO_VOL}")
    if audio_duration < final_duration:
        print(f"⚠️  Audio ({audio_duration}s) shorter than video ({final_duration}s)")
        print(f"   → Audio will end early. Use mode 1 to loop instead.")
    ret = os.system(
        f'ffmpeg -y '
        f'-i "{comp_raw}" '
        f'-i "{audio_path}" '
        f'-filter_complex "[1:a]volume={AUDIO_VOL}[a]" '
        f'-map 0:v -map "[a]" '
        f'-c:v libx264 -preset fast -pix_fmt yuv420p '
        f'-c:a aac -b:a 192k '
        f'-t {final_duration} '
        f'"{final}"')

if ret == 0 and os.path.exists(final):
    os.remove(comp_raw)
    os.remove(slideshow_path)
    final_size = round(os.path.getsize(final) / 1024 / 1024, 2)
    print(f"\n{'=' * 50}")
    print(f"✅ DONE — final_video.mp4")
    print(f"⏱️  Duration : {final_duration}s")
    print(f"📦  Size     : {final_size} MB")
    print(f"📁  Saved to : {final}")
else:
    print(f"❌ Encoding failed — composite_raw.mp4 kept for debug")
