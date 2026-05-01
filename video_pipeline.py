# ================== SETUP ==================
# !pip install pillow opencv-python-headless -q
# !apt-get install ffmpeg imagemagick -y -q

import os
import glob
import subprocess
import shutil
import numpy as np
import cv2
from PIL import Image
from google.colab import drive, files as colab_files

# ================== SETTINGS ==================
base = "/content/drive/MyDrive/MyAutomation"

settings = {
    'base': f'{base}/',
    'images_folder': f'{base}/images',
    'square_folder': f'{base}/square',

    'background': f'{base}/assets/background/background.mp4',
    'marquee_png': f'{base}/assets/marquee/marquee.png',
    'overlay1_png': f'{base}/assets/overlay1/overlay1.png',
    'overlay2_png': f'{base}/assets/overlay2/overlay2.png',
    'bottom_png': f'{base}/assets/bottom/bottom.png',

    'audio_path': f'{base}/assets/audio/audio125.mp3',
    'AUDIO_MODE': '1',      # 1=Loop, 2=Single, 3=None
    'AUDIO_VOL': 1,         # Volume scaling

    'FPS': 30,
    'DURATION': 2.8,        # Seconds per slide
    'EFFECT_DURATION': 0.8, # Bounce effect duration in seconds

    'FRAME_W': 1080,
    'FRAME_H': 1920,
    'SLIDE_W': 1080,
    'SLIDE_H': 1080,
    'SLIDE_MARGIN': 0,

    'MARQUEE_H': 80,
    'MARQUEE_TOP': 80,
    'MARQUEE_SPEED': 120,   # Pixels per second (not per frame)

    'OV1_W': 600,
    'OV1_H': 140,
    'OV2_W': 1080,
    'OV2_H': 140,
    'OV2_Y': 1447,

    'BTN_W': 600,
    'BTN_H': 140,
    'BTN_Y': 1550,
}

IMAGE_EXT = [".jpg", ".jpeg", ".png", ".bmp", ".webp"]

# ================== HELPERS ==================

def mount_drive():
    """Mount Google Drive with error handling."""
    try:
        drive.mount('/content/drive', force_remount=False)
        print("✅ Google Drive mounted.")
    except Exception as e:
        raise RuntimeError(f"❌ Google Drive mount failed: {e}")


def check_path(path, label, create=False):
    """Check if a path exists. Raise an error if it doesn't (unless create=True)."""
    if os.path.exists(path):
        return True
    if create:
        os.makedirs(path, exist_ok=True)
        print(f"📁 Created folder: {path}")
        return True
    raise FileNotFoundError(f"❌ Missing required asset [{label}]: {path}")


def get_duration(filepath):
    """Get duration of a media file in seconds using ffprobe."""
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


def load_png(path, w, h):
    """Load a PNG with alpha channel and resize it."""
    with Image.open(path).convert("RGBA") as im:
        return np.array(im.resize((w, h), Image.LANCZOS))


def alpha_composite(base_bgr, overlay_rgba, x, y):
    """Composite an RGBA overlay onto a BGR base frame at position (x, y)."""
    oh, ow = overlay_rgba.shape[:2]
    bh, bw = base_bgr.shape[:2]
    x1, y1 = max(x, 0), max(y, 0)
    x2, y2 = min(x + ow, bw), min(y + oh, bh)
    if x1 >= x2 or y1 >= y2:
        return base_bgr
    ox1, oy1 = x1 - x, y1 - y
    ox2, oy2 = ox1 + (x2 - x1), oy1 + (y2 - y1)
    src = overlay_rgba[oy1:oy2, ox1:ox2]
    alpha = src[:, :, 3:4].astype(np.float32) / 255.0
    src_bgr = src[:, :, :3][:, :, ::-1]
    roi = base_bgr[y1:y2, x1:x2].astype(np.float32)
    base_bgr[y1:y2, x1:x2] = (
        (1 - alpha) * roi + alpha * src_bgr.astype(np.float32)
    ).astype(np.uint8)
    return base_bgr


def open_video_writer(output_path, fps, size):
    """Try multiple codecs and return a working VideoWriter, or raise."""
    for codec in ['avc1', 'mp4v', 'XVID']:
        fourcc = cv2.VideoWriter_fourcc(*codec)
        writer = cv2.VideoWriter(output_path, fourcc, fps, size)
        if writer.isOpened():
            print(f"🎬 VideoWriter opened with codec: {codec}")
            return writer
        writer.release()
    raise RuntimeError(f"❌ Could not open VideoWriter for: {output_path}")


# ================== IMAGE HANDLING ==================

def check_and_upload_images(images_folder):
    """
    1. Delete any existing images in the folder.
    2. Prompt user to upload new images.
    3. Save uploaded images to the folder and show file locations.
    4. Return list of saved file paths.
    """
    os.makedirs(images_folder, exist_ok=True)

    # Condition 1: Delete old images if they exist
    existing = [
        f for f in glob.glob(f"{images_folder}/*")
        if os.path.isfile(f) and os.path.splitext(f)[1].lower() in IMAGE_EXT
    ]
    if existing:
        for f in existing:
            os.remove(f)
        print(f"🗑️  Deleted {len(existing)} old image(s) from images folder.")

    # Condition 2 & 4: Upload and save new images
    print("📂 Please upload your image files (JPG, PNG, WEBP, BMP, etc.)")
    while True:
        uploaded = colab_files.upload()

        if not uploaded:
            print("⚠️  Nothing uploaded. Please try again.")
            continue

        saved = []
        skipped = []

        for filename, data in uploaded.items():
            ext = os.path.splitext(filename)[1].lower()
            if ext not in IMAGE_EXT:
                skipped.append(filename)
                print(f"⚠️  Skipped (not a supported image): {filename}")
                continue

            # Handle duplicate filenames
            base_name, file_ext = os.path.splitext(filename)
            dest = os.path.join(images_folder, filename)
            counter = 1
            while os.path.exists(dest):
                dest = os.path.join(images_folder, f"{base_name}_{counter}{file_ext}")
                counter += 1

            with open(dest, "wb") as f:
                f.write(data)

            saved.append(dest)
            print(f"💾 Saved: {dest}")  # Condition 4: show file location

        if skipped:
            print(f"\n⚠️  Skipped {len(skipped)} non-image file(s): {skipped}")

        if saved:
            print(f"\n✅ {len(saved)} image(s) uploaded successfully.")
            print(f"📁 Location: {images_folder}")
            return saved
        else:
            print("❌ No valid image files were saved. Please upload .jpg/.png/.webp etc.")


def convert_images_to_square(input_images, square_folder, size):
    """
    Resize images to the target size using crop-and-pad (letterbox).
    Preserves aspect ratio — no stretching.
    Saves output as JPEG for consistency.
    """
    os.makedirs(square_folder, exist_ok=True)
    converted = []

    for img_path in input_images:
        filename = os.path.basename(img_path)
        output = os.path.join(square_folder, os.path.splitext(filename)[0] + ".jpg")

        try:
            with Image.open(img_path).convert("RGB") as im:
                im.thumbnail(size, Image.LANCZOS)           # Scale down, preserve ratio
                canvas = Image.new("RGB", size, (0, 0, 0))  # Black padding canvas
                offset = ((size[0] - im.width) // 2, (size[1] - im.height) // 2)
                canvas.paste(im, offset)
                canvas.save(output, "JPEG", quality=95)
                converted.append(output)
        except Exception as e:
            print(f"⚠️  Skipping corrupt/unreadable image [{filename}]: {e}")

    if not converted:
        raise RuntimeError("❌ No valid images could be converted to square format.")

    return converted


# ================== VIDEO BUILDING ==================

def build_slideshow(image_paths, size, fps, duration, effect_duration, output_path):
    """
    Build a raw slideshow video from images with a bounce/settle effect.
    Each image is shown for `duration` seconds with a settle animation.
    """
    total_frames = int(duration * fps)
    effect_frames = int(effect_duration * fps)
    decay = effect_frames / 4.0

    writer = open_video_writer(output_path, fps, size)

    try:
        for img_path in image_paths:
            img = cv2.imread(img_path)
            if img is None:
                print(f"⚠️  Could not read image for slideshow: {img_path}")
                continue
            img = cv2.resize(img, size)
            h = img.shape[0]

            for n in range(total_frames):
                if n < effect_frames:
                    offset_y = int(h * np.exp(-n / decay) * np.cos(n / 8.0) ** 2)
                else:
                    offset_y = 0
                M = np.float32([[1, 0, 0], [0, 1, offset_y]])
                frame = cv2.warpAffine(
                    img, M, size,
                    borderMode=cv2.BORDER_CONSTANT,
                    borderValue=(0, 0, 0)
                )
                writer.write(frame)
    finally:
        writer.release()

    print(f"✅ Slideshow built: {output_path}")


def composite_layers(background_path, slideshow_path, overlays, output_path,
                     frame_size, fps, total_frames, settings):
    """
    Composite background video + slideshow + PNG overlays into a single raw video.
    Shows a progress update every 30 frames.
    """
    FRAME_W, FRAME_H = frame_size

    bg_cap = cv2.VideoCapture(background_path)
    sl_cap = cv2.VideoCapture(slideshow_path)

    if not bg_cap.isOpened():
        raise RuntimeError(f"❌ Could not open background video: {background_path}")
    if not sl_cap.isOpened():
        raise RuntimeError(f"❌ Could not open slideshow video: {slideshow_path}")

    writer = open_video_writer(output_path, fps, frame_size)

    slide_area_w = settings['SLIDE_W'] - 2 * settings['SLIDE_MARGIN']
    slide_area_h = settings['SLIDE_H'] - 2 * settings['SLIDE_MARGIN']
    slide_x = (FRAME_W - slide_area_w) // 2
    slide_y = (settings['MARQUEE_TOP'] + settings['MARQUEE_H'] + 57
               + settings['OV1_H'] + 20)

    try:
        for frame_idx in range(total_frames):
            # Progress indicator every 30 frames
            if frame_idx % 30 == 0:
                pct = int(frame_idx / total_frames * 100)
                print(f"  ⏳ Compositing frame {frame_idx}/{total_frames} ({pct}%)", end='\r')

            # Background frame (loop if needed)
            ret_bg, bg_frame = bg_cap.read()
            if not ret_bg:
                bg_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret_bg, bg_frame = bg_cap.read()
            canvas = cv2.resize(bg_frame, frame_size)

            # Marquee (scrolling) — speed in pixels/second, not pixels/frame
            mq = overlays[0]['img']
            scroll_x = int((frame_idx / fps) * settings['MARQUEE_SPEED']) % FRAME_W
            mq_crop = np.concatenate([mq, mq], axis=1)[:, scroll_x:scroll_x + FRAME_W]
            canvas = alpha_composite(canvas, mq_crop, overlays[0]['x'], overlays[0]['y'])

            # All other static overlays
            for ov in overlays[1:]:
                canvas = alpha_composite(canvas, ov['img'], ov['x'], ov['y'])

            # Slideshow frame (loop if needed)
            ret_sl, sl_frame = sl_cap.read()
            if not ret_sl:
                sl_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret_sl, sl_frame = sl_cap.read()
            if ret_sl:
                sl_resized = cv2.resize(sl_frame, (slide_area_w, slide_area_h))
                canvas[slide_y:slide_y + slide_area_h, slide_x:slide_x + slide_area_w] = sl_resized

            writer.write(canvas)
    finally:
        bg_cap.release()
        sl_cap.release()
        writer.release()

    print(f"\n✅ Composite video built: {output_path}")


# ================== ENCODING ==================

def encode_final(comp_raw, audio_path, audio_mode, output_path, duration, volume):
    """
    Encode the composite raw video with audio using ffmpeg.
    Raises RuntimeError if ffmpeg fails.
    """
    base_cmd = ['ffmpeg', '-y', '-i', comp_raw]

    if audio_mode == "3" or not os.path.exists(audio_path):
        cmd = base_cmd + ['-c:v', 'libx264', '-pix_fmt', 'yuv420p', output_path]

    elif audio_mode == "1":
        # Loop audio to match video duration
        cmd = (base_cmd
               + ['-stream_loop', '-1', '-i', audio_path]
               + ['-filter_complex', f'[1:a]volume={volume}[a]']
               + ['-map', '0:v', '-map', '[a]']
               + ['-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                  '-c:a', 'aac', '-b:a', '192k',
                  '-t', str(duration), output_path])

    elif audio_mode == "2":
        # Single audio pass — warn if audio is shorter than video
        audio_dur = get_duration(audio_path)
        if audio_dur < duration:
            print(f"⚠️  Audio ({audio_dur:.1f}s) is shorter than video ({duration:.1f}s)."
                  f" The tail will be silent.")
        cmd = (base_cmd
               + ['-i', audio_path]
               + ['-filter_complex', f'[1:a]volume={volume}[a]']
               + ['-map', '0:v', '-map', '[a]']
               + ['-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                  '-c:a', 'aac', '-b:a', '192k',
                  '-t', str(duration), output_path])
    else:
        raise ValueError(f"❌ Unknown AUDIO_MODE: {audio_mode}. Use '1', '2', or '3'.")

    print("🎞️  Encoding final video with ffmpeg...")
    result = subprocess.run(cmd, stderr=subprocess.PIPE)

    if result.returncode != 0:
        raise RuntimeError(
            f"❌ FFmpeg encoding failed:\n{result.stderr.decode()}"
        )

    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError(f"❌ Final video file was not created or is empty: {output_path}")

    print(f"✅ Final video encoded: {output_path}")


# ================== CLEANUP ==================

def cleanup(slideshow_raw, comp_raw, images_folder, final_video):
    """
    Remove temp files and clean the images folder — but ONLY if the
    final video exists and has content. Protects data on pipeline failure.
    """
    if not os.path.exists(final_video) or os.path.getsize(final_video) == 0:
        print("⚠️  Final video not confirmed. Skipping cleanup to preserve files for debugging.")
        return

    # Remove intermediate video files
    for path in [slideshow_raw, comp_raw]:
        if os.path.exists(path):
            os.remove(path)

    # Condition 3: Clean images folder after pipeline completes
    for f in glob.glob(os.path.join(images_folder, "*")):
        if os.path.isfile(f):
            os.remove(f)

    print("🧹 Temporary files and images folder cleaned.")


# ================== PIPELINE ==================

def run_video_pipeline(settings):
    """
    Main pipeline entry point. Runs all stages in order:
    1. Mount Drive
    2. Validate paths
    3. Upload images
    4. Convert to square
    5. Build slideshow
    6. Composite layers
    7. Encode final video
    8. Cleanup
    """
    print("=" * 50)
    print("🚀 Starting video pipeline...")
    print("=" * 50)

    # Stage 1: Mount Drive
    mount_drive()

    # Stage 2: Validate required paths
    check_path(settings['base'], "Base folder")
    check_path(settings['images_folder'], "Images folder", create=True)
    check_path(settings['square_folder'], "Square folder", create=True)

    for label, path in [
        ('Background video', settings['background']),
        ('Marquee PNG',      settings['marquee_png']),
        ('Overlay1 PNG',     settings['overlay1_png']),
        ('Overlay2 PNG',     settings['overlay2_png']),
        ('Bottom PNG',       settings['bottom_png']),
    ]:
        check_path(path, label)

    # Stage 3: Upload images
    input_images = check_and_upload_images(settings['images_folder'])

    # Stage 4: Convert to square (letterbox, no stretch)
    effective_size = (
        settings['SLIDE_W'] - 2 * settings['SLIDE_MARGIN'],
        settings['SLIDE_H'] - 2 * settings['SLIDE_MARGIN']
    )
    square_images = convert_images_to_square(
        input_images, settings['square_folder'], effective_size
    )

    # Stage 5: Build raw slideshow
    slideshow_raw = os.path.join(settings['base'], "slideshow_raw.mp4")
    build_slideshow(
        square_images, effective_size,
        settings['FPS'], settings['DURATION'],
        settings['EFFECT_DURATION'], slideshow_raw
    )

    # Calculate final video duration
    bg_duration   = get_duration(settings['background'])
    slide_duration = get_duration(slideshow_raw)
    final_duration = min(bg_duration, slide_duration)
    total_frames   = int(final_duration * settings['FPS'])

    print(f"📐 Background: {bg_duration:.2f}s | Slideshow: {slide_duration:.2f}s"
          f" | Final: {final_duration:.2f}s ({total_frames} frames)")

    # Stage 6: Load overlays and composite layers
    overlays = []

    mq_img = load_png(settings['marquee_png'], settings['FRAME_W'], settings['MARQUEE_H'])
    overlays.append({'img': mq_img, 'x': 0, 'y': settings['MARQUEE_TOP']})

    ov1_img = load_png(settings['overlay1_png'], settings['OV1_W'], settings['OV1_H'])
    overlays.append({
        'img': ov1_img,
        'x': (settings['FRAME_W'] - settings['OV1_W']) // 2,
        'y': settings['MARQUEE_TOP'] + settings['MARQUEE_H'] + 57
    })

    ov2_img = load_png(settings['overlay2_png'], settings['OV2_W'], settings['OV2_H'])
    overlays.append({
        'img': ov2_img,
        'x': (settings['FRAME_W'] - settings['OV2_W']) // 2,
        'y': settings['OV2_Y']
    })

    btn_img = load_png(settings['bottom_png'], settings['BTN_W'], settings['BTN_H'])
    overlays.append({
        'img': btn_img,
        'x': (settings['FRAME_W'] - settings['BTN_W']) // 2,
        'y': settings['BTN_Y']
    })

    comp_raw = os.path.join(settings['base'], "composite_raw.mp4")
    composite_layers(
        settings['background'], slideshow_raw, overlays, comp_raw,
        (settings['FRAME_W'], settings['FRAME_H']),
        settings['FPS'], total_frames, settings
    )

    # Stage 7: Encode final video with audio
    final_video = os.path.join(settings['base'], "final_video.mp4")
    encode_final(
        comp_raw, settings['audio_path'], settings['AUDIO_MODE'],
        final_video, final_duration, settings['AUDIO_VOL']
    )

    # Stage 8: Cleanup temp files (only if final video confirmed)
    cleanup(slideshow_raw, comp_raw, settings['images_folder'], final_video)

    print("=" * 50)
    print(f"🎉 Pipeline complete!")
    print(f"📹 Final video: {final_video}")
    print("=" * 50)


# ================== RUN ==================
run_video_pipeline(settings)
