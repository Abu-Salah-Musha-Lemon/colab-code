# ================== SETUP ==================
!pip install pillow opencv-python-headless -q
!apt-get install ffmpeg imagemagick -y -q

import os
import glob
import random
import subprocess
import numpy as np
import cv2
import shutil
from PIL import Image

# ================== MOUNT GOOGLE DRIVE ==================
print("=" * 50)
print("📂 Mounting Google Drive...")
from google.colab import drive
drive.mount('/content/drive', force_remount=False)

# ================== PATHS ==================
base          = "/content/drive/MyDrive/MyAutomation"
images_folder = f"{base}/images"
square_folder = f"{base}/square"

# ── Asset folders (each can contain images/videos/gifs mixed) ────────
asset_folders = {
    "background" : f"{base}/assets/background",   # video/gif/image
    "marquee"    : f"{base}/assets/marquee",       # video/gif/image
    "overlay1"   : f"{base}/assets/overlay1",      # video/gif/image
    "overlay2"   : f"{base}/assets/overlay2",      # video/gif/image
    "bottom"     : f"{base}/assets/bottom",        # video/gif/image
    "audio"      : f"{base}/assets/audio",         # mp3/aac/wav/m4a
}

# ── Supported extensions ─────────────────────────────────────────────
VIDEO_EXT = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
GIF_EXT   = {'.gif'}
IMAGE_EXT = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
AUDIO_EXT = {'.mp3', '.aac', '.wav', '.m4a', '.ogg'}

# ================== FOLDER & FILE ACCESS CHECK ==================
print("\n" + "=" * 50)
print("🔍 Checking folders & file access...")

errors = []

def check_path(path, label, create=False):
    if os.path.exists(path):
        files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))] \
                if os.path.isdir(path) else []
        info  = f"({len(files)} files)" if files else ""
        print(f"✅ {label:<28}: {info}")
        return True
    else:
        if create:
            try:
                os.makedirs(path, exist_ok=True)
                print(f"📁 {label:<28}: created")
                return True
            except Exception as e:
                errors.append(f"❌ {label}: {e}")
                return False
        else:
            errors.append(f"❌ {label:<28}: NOT FOUND → {path}")
            return False

check_path(base,          "Base folder")
check_path(images_folder, "Images folder",  create=True)

for name, folder in asset_folders.items():
    check_path(folder, f"Assets/{name}", create=True)

try:
    test_file = f"{base}/.write_test"
    with open(test_file, "w") as f: f.write("ok")
    os.remove(test_file)
    print(f"✅ {'Write permission':<28}: OK")
except Exception as e:
    errors.append(f"❌ Write permission: {e}")

if errors:
    print("\n🚨 Fix these before continuing:")
    for e in errors: print(f"   {e}")
    raise SystemExit("❌ Access check failed.")

print("\n✅ All paths OK\n")

# ================== ASSET PICKER ==================
def get_files(folder, exts):
    """Get all files in folder matching extensions."""
    files = []
    for f in os.listdir(folder):
        ext = os.path.splitext(f)[1].lower()
        if ext in exts:
            files.append(os.path.join(folder, f))
    return sorted(files)

def pick_asset(folder, exts, label):
    """Randomly pick one file from folder matching extensions."""
    files = get_files(folder, exts)
    if not files:
        print(f"   ⚠️  No files found in {label} folder")
        return None
    picked = random.choice(files)
    ext    = os.path.splitext(picked)[1].lower()
    ftype  = "video" if ext in VIDEO_EXT else "gif" if ext in GIF_EXT else \
             "audio" if ext in AUDIO_EXT else "image"
    print(f"   🎲 {label:<12}: [{ftype}] {os.path.basename(picked)}")
    return picked

def get_file_type(path):
    if path is None: return None
    ext = os.path.splitext(path)[1].lower()
    if ext in VIDEO_EXT: return "video"
    if ext in GIF_EXT:   return "gif"
    if ext in IMAGE_EXT: return "image"
    if ext in AUDIO_EXT: return "audio"
    return None

# ================== CONVERTERS ==================
def get_duration(filepath):
    result = subprocess.run(
        ["ffprobe", "-v", "error",
         "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", filepath],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try: return float(result.stdout.strip())
    except: return 0.0

def asset_to_frames(path, target_w, target_h, total_frames, fps):
    """
    Convert any asset (image/gif/video) into a list of numpy frames (BGR).
    Loops/trims to exactly total_frames.
    """
    ftype  = get_file_type(path)
    frames = []

    if ftype == "image":
        # single image → repeat for all frames
        with Image.open(path).convert("RGBA") as im:
            arr = np.array(im.resize((target_w, target_h), Image.LANCZOS))
        frames = [arr] * total_frames

    elif ftype == "gif":
        # extract all gif frames
        with Image.open(path) as gif:
            while True:
                try:
                    frame = gif.copy().convert("RGBA").resize(
                        (target_w, target_h), Image.LANCZOS)
                    frames.append(np.array(frame))
                    gif.seek(gif.tell() + 1)
                except EOFError:
                    break
        if not frames:
            frames = [np.zeros((target_h, target_w, 4), dtype=np.uint8)]
        # loop gif frames to total_frames
        frames = [frames[i % len(frames)] for i in range(total_frames)]

    elif ftype == "video":
        cap = cv2.VideoCapture(path)
        raw = []
        while True:
            ret, frm = cap.read()
            if not ret: break
            frm_resized = cv2.resize(frm, (target_w, target_h))
            # convert BGR→RGBA
            rgba = cv2.cvtColor(frm_resized, cv2.COLOR_BGR2BGRA)
            rgba[:, :, 3] = 255
            raw.append(rgba)
        cap.release()
        if not raw:
            raw = [np.zeros((target_h, target_w, 4), dtype=np.uint8)]
        # loop video frames to total_frames
        frames = [raw[i % len(raw)] for i in range(total_frames)]

    return frames

def alpha_composite(base_bgr, overlay_rgba, x, y):
    oh, ow = overlay_rgba.shape[:2]
    bh, bw = base_bgr.shape[:2]
    x1, y1 = max(x, 0), max(y, 0)
    x2, y2 = min(x + ow, bw), min(y + oh, bh)
    if x1 >= x2 or y1 >= y2: return base_bgr
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

# ================== USER SETTINGS ==================
print("=" * 50)
print("⚙️  USER SETTINGS")
print("=" * 50)

FPS           = int(float(input("FPS (e.g. 24 / 30 / 60)                          : ")))
FRAME_W       = int(input("Frame width  px (e.g. 1080)                        : "))
FRAME_H       = int(input("Frame height px (e.g. 1920)                        : "))

MARQUEE_H     = int(input("Marquee height px (e.g. 80)                        : "))
MARQUEE_TOP   = int(input("Marquee top margin px (e.g. 50)                    : "))
MARQUEE_SPEED = int(input("Marquee scroll speed px/frame (e.g. 3)             : "))

OV1_W         = int(input("Overlay1 width  px (e.g. 600)                      : "))
OV1_H         = int(input("Overlay1 height px (e.g. 140)                      : "))

SLIDE_W       = int(input("Slideshow width  px (e.g. 1080)                    : "))
SLIDE_H       = int(input("Slideshow height px (e.g. 1200)                    : "))
SLIDE_MARGIN  = int(input("Slideshow inner margin px (e.g. 4)                 : "))

DURATION        = float(input("Per image duration  (e.g. 0.5 / 1.0 / 1.5)       : "))
EFFECT_DURATION = float(input("Bounce effect dur   (must be <= duration)          : "))

if EFFECT_DURATION > DURATION:
    EFFECT_DURATION = DURATION
    print(f"⚠️  Effect capped to {DURATION}s")

OV2_W         = int(input("Overlay2 width  px (e.g. 1080)                     : "))
OV2_H         = int(input("Overlay2 height px (e.g. 140)                      : "))
OV2_Y         = int(input("Overlay2 Y pos  px (e.g. 1447)                     : "))

BTN_W         = int(input("Bottom button width  px (e.g. 600)                 : "))
BTN_H         = int(input("Bottom button height px (e.g. 140)                 : "))
print("Bottom button Y reference:")
print("  1 = from bottom of frame")
print("  2 = from bottom of slideshow")
BTN_REF       = input("Choose (1 / 2)                                     : ").strip()
BTN_MARGIN    = int(input("Bottom button margin px (e.g. 50 / 0)             : "))

AUDIO_VOL     = float(input("Audio volume (e.g. 0.5 / 1.0 / 1.5)              : "))
print("Audio mode:")
print("  1 = loop to video length")
print("  2 = trim to video length")
print("  3 = no audio")
AUDIO_MODE    = input("Audio mode (1 / 2 / 3)                            : ").strip()

# ── Auto-calculate positions ──────────────────────────
MARQUEE_X     = 0
MARQUEE_Y     = MARQUEE_TOP
OV1_X         = (FRAME_W - OV1_W) // 2
OV1_Y         = MARQUEE_Y + MARQUEE_H
SLIDE_X       = (FRAME_W - SLIDE_W) // 2
SLIDE_Y       = OV1_Y + OV1_H
effective_w   = SLIDE_W - SLIDE_MARGIN * 2
effective_h   = SLIDE_H - SLIDE_MARGIN * 2
SLIDE_CX      = SLIDE_X + SLIDE_MARGIN
SLIDE_CY      = SLIDE_Y + SLIDE_MARGIN
SIZE          = (effective_w, effective_h)
OV2_X         = (FRAME_W - OV2_W) // 2
BTN_X         = (FRAME_W - BTN_W) // 2
SLIDE_BOTTOM  = SLIDE_Y + SLIDE_H

if BTN_REF == "2":
    BTN_Y = SLIDE_BOTTOM + BTN_MARGIN
else:
    BTN_Y = FRAME_H - BTN_MARGIN - BTN_H

# ================== RANDOMLY PICK ASSETS ==================
print("\n" + "=" * 50)
print("🎲 Randomly picking assets...")

ALL_MEDIA = VIDEO_EXT | GIF_EXT | IMAGE_EXT

picked_bg      = pick_asset(asset_folders["background"], ALL_MEDIA,   "background")
picked_marquee = pick_asset(asset_folders["marquee"],    ALL_MEDIA,   "marquee")
picked_ov1     = pick_asset(asset_folders["overlay1"],   ALL_MEDIA,   "overlay1")
picked_ov2     = pick_asset(asset_folders["overlay2"],   ALL_MEDIA,   "overlay2")
picked_btn     = pick_asset(asset_folders["bottom"],     ALL_MEDIA,   "bottom")
picked_audio   = pick_asset(asset_folders["audio"],      AUDIO_EXT,   "audio") \
                 if AUDIO_MODE != "3" else None

for name, path in [("background", picked_bg), ("marquee", picked_marquee),
                   ("overlay1",   picked_ov1), ("overlay2", picked_ov2),
                   ("bottom",     picked_btn)]:
    if path is None:
        raise SystemExit(f"❌ No asset found for '{name}'. Add files to assets/{name}/")

# ── Background must be video for duration reference ───────────────────
bg_type = get_file_type(picked_bg)
if bg_type == "video":
    bg_duration = get_duration(picked_bg)
elif bg_type == "gif":
    bg_duration = 10.0    # default gif background = 10s
    print(f"   ℹ️  GIF background → using 10s default duration")
else:
    bg_duration = 10.0
    print(f"   ℹ️  Image background → using 10s default duration")

# ================== STEP 1: Check images ==================
print("\n" + "=" * 50)
print("Step 1: Check images folder")

input_images = [f for f in glob.glob(f"{images_folder}/*") if os.path.isfile(f)]
if len(input_images) == 0:
    raise SystemExit(f"❌ No images in: {images_folder}")

print(f"✅ Found {len(input_images)} image(s):")
for f in input_images:
    print(f"   {os.path.basename(f)}")

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

output_path    = f"{base}/slideshow_raw.mp4"
writer         = cv2.VideoWriter(output_path,
                                 cv2.VideoWriter_fourcc(*'mp4v'),
                                 FPS, SIZE)
success_images = []

for idx, img_path in enumerate(square_images):
    print(f"  [{idx+1}/{len(square_images)}] {os.path.basename(img_path)}")
    img = cv2.imread(img_path)
    if img is None: continue
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
    print(f"✅ Slideshow ready  |  🗑️ {deleted} images cleared")
else:
    raise SystemExit("❌ Slideshow failed.")

# ================== STEP 5: Duration match ==================
print("\n" + "=" * 50)
print("Step 5: Calculate final duration")

slideshow_duration  = get_duration(slideshow_path)
final_duration      = min(bg_duration, slideshow_duration)
total_output_frames = int(final_duration * FPS)

print(f"Background  : {bg_duration}s")
print(f"Slideshow   : {slideshow_duration}s")
print(f"Final       : {final_duration}s  ({total_output_frames} frames)")

# ================== STEP 6: Pre-render all asset frames ==================
print("\n" + "=" * 50)
print("Step 6: Pre-render asset frames")

print(f"   background → video stream")
print(f"   marquee    → {total_output_frames} frames")
mq_frames  = asset_to_frames(picked_marquee, FRAME_W,  MARQUEE_H,
                              total_output_frames, FPS)
print(f"   overlay1   → {total_output_frames} frames")
ov1_frames = asset_to_frames(picked_ov1,     OV1_W,    OV1_H,
                              total_output_frames, FPS)
print(f"   overlay2   → {total_output_frames} frames")
ov2_frames = asset_to_frames(picked_ov2,     OV2_W,    OV2_H,
                              total_output_frames, FPS)
print(f"   bottom     → {total_output_frames} frames")
btn_frames = asset_to_frames(picked_btn,     BTN_W,    BTN_H,
                              total_output_frames, FPS)
print("✅ All asset frames ready")

# ── Marquee tile for scrolling (only needed if image/gif/video) ───────
# We tile frame-by-frame during compositing

# ================== STEP 7: Composite ==================
print("\n" + "=" * 50)
print("Step 7: Composite all layers")

# background video reader (or image/gif handled per frame)
if bg_type == "video":
    bg_cap = cv2.VideoCapture(picked_bg)
elif bg_type == "gif":
    bg_gif_frames = asset_to_frames(picked_bg, FRAME_W, FRAME_H,
                                    total_output_frames, FPS)
    bg_cap = None
else:
    # static image
    bg_static = cv2.resize(cv2.imread(picked_bg), (FRAME_W, FRAME_H))
    bg_cap    = None

sl_cap     = cv2.VideoCapture(slideshow_path)
comp_raw   = f"{base}/composite_raw.mp4"
out_writer = cv2.VideoWriter(comp_raw,
                             cv2.VideoWriter_fourcc(*'mp4v'),
                             FPS, (FRAME_W, FRAME_H))

for frame_idx in range(total_output_frames):

    # ── Layer 1: Background ───────────────────────────────────────────
    if bg_type == "video":
        ret_bg, bg_frame = bg_cap.read()
        if not ret_bg:
            bg_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            _, bg_frame = bg_cap.read()
        canvas = cv2.resize(bg_frame, (FRAME_W, FRAME_H))
    elif bg_type == "gif":
        rgba   = bg_gif_frames[frame_idx]
        canvas = rgba[:, :, :3][:, :, ::-1].copy()
    else:
        canvas = bg_static.copy()

    # ── Layer 2: Marquee scrolling ────────────────────────────────────
    mq_rgba = mq_frames[frame_idx]                     # RGBA frame
    # tile for seamless scroll
    mq_tile  = np.concatenate([mq_rgba, mq_rgba], axis=1)
    scroll_x = (frame_idx * MARQUEE_SPEED) % FRAME_W
    mq_crop  = mq_tile[:, scroll_x:scroll_x + FRAME_W]
    canvas   = alpha_composite(canvas, mq_crop, MARQUEE_X, MARQUEE_Y)

    # ── Layer 3: Overlay1 — 600x140 centered ─────────────────────────
    canvas = alpha_composite(canvas, ov1_frames[frame_idx], OV1_X, OV1_Y)

    # ── Layer 4: Slideshow ────────────────────────────────────────────
    ret_sl, sl_frame = sl_cap.read()
    if not ret_sl:
        sl_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        _, sl_frame = sl_cap.read()
    if ret_sl:
        sl_resized = cv2.resize(sl_frame, SIZE)
        canvas[SLIDE_CY:SLIDE_CY + effective_h,
               SLIDE_CX:SLIDE_CX + effective_w] = sl_resized

    # ── Layer 5: Overlay2 — centered at OV2_Y ────────────────────────
    canvas = alpha_composite(canvas, ov2_frames[frame_idx], OV2_X, OV2_Y)

    # ── Layer 6: Bottom button ────────────────────────────────────────
    canvas = alpha_composite(canvas, btn_frames[frame_idx], BTN_X, BTN_Y)

    out_writer.write(canvas)

    if frame_idx % (FPS * 5) == 0:
        pct = round(frame_idx / total_output_frames * 100, 1)
        print(f"   {frame_idx}/{total_output_frames}  "
              f"({round(frame_idx/FPS,1)}s)  {pct}%")

if bg_cap: bg_cap.release()
sl_cap.release()
out_writer.release()
print("✅ Composite done")

# ================== STEP 8: Encode final with audio ==================
print("\n" + "=" * 50)
print("Step 8: Encode final video")

final = f"{base}/final_video.mp4"

if AUDIO_MODE == "3" or picked_audio is None:
    ret = os.system(
        f'ffmpeg -y -i "{comp_raw}" '
        f'-c:v libx264 -preset fast -pix_fmt yuv420p "{final}"')

elif AUDIO_MODE == "1":
    print(f"🎵 Looping: {os.path.basename(picked_audio)}  vol={AUDIO_VOL}")
    ret = os.system(
        f'ffmpeg -y '
        f'-i "{comp_raw}" '
        f'-stream_loop -1 -i "{picked_audio}" '
        f'-filter_complex "[1:a]volume={AUDIO_VOL}[a]" '
        f'-map 0:v -map "[a]" '
        f'-c:v libx264 -preset fast -pix_fmt yuv420p '
        f'-c:a aac -b:a 192k -t {final_duration} "{final}"')

elif AUDIO_MODE == "2":
    print(f"🎵 Trim: {os.path.basename(picked_audio)}  vol={AUDIO_VOL}")
    ret = os.system(
        f'ffmpeg -y '
        f'-i "{comp_raw}" '
        f'-i "{picked_audio}" '
        f'-filter_complex "[1:a]volume={AUDIO_VOL}[a]" '
        f'-map 0:v -map "[a]" '
        f'-c:v libx264 -preset fast -pix_fmt yuv420p '
        f'-c:a aac -b:a 192k -t {final_duration} "{final}"')

if ret == 0 and os.path.exists(final):
    os.remove(comp_raw)
    os.remove(slideshow_path)
    final_size = round(os.path.getsize(final) / 1024 / 1024, 2)
    print(f"\n{'=' * 50}")
    print(f"✅ DONE — final_video.mp4")
    print(f"⏱️  Duration  : {final_duration}s")
    print(f"📦  Size      : {final_size} MB")
    print(f"📁  Saved to  : {final}")
    print(f"\n🎲 Assets used this run:")
    print(f"   background : {os.path.basename(picked_bg)}")
    print(f"   marquee    : {os.path.basename(picked_marquee)}")
    print(f"   overlay1   : {os.path.basename(picked_ov1)}")
    print(f"   overlay2   : {os.path.basename(picked_ov2)}")
    print(f"   bottom     : {os.path.basename(picked_btn)}")
    if picked_audio:
        print(f"   audio      : {os.path.basename(picked_audio)}")
else:
    print(f"❌ Encoding failed — composite_raw.mp4 kept for debug")
