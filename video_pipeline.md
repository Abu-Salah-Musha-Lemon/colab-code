# 🎬 Automated Video Pipeline — Google Colab

A fully automated video production pipeline for Google Colab. Upload product or content images and the pipeline automatically composes them into a polished 9:16 vertical video with scrolling marquee, overlays, background video, bounce animations, and background audio — ready for Reels, TikTok, or Shorts.

---

## 📋 Table of Contents

- [Features](#-features)
- [Folder Structure](#-folder-structure)
- [Requirements](#-requirements)
- [Setup](#-setup)
- [Configuration](#-configuration)
- [How to Run](#-how-to-run)
- [Pipeline Stages](#-pipeline-stages)
- [Audio Modes](#-audio-modes)
- [Troubleshooting](#-troubleshooting)
- [Known Limitations](#-known-limitations)

---

## ✨ Features

- **Auto image upload** — prompts for upload, deletes old images, saves new ones, and shows save location
- **Letterbox conversion** — resizes images to square without stretching (black padding preserves aspect ratio)
- **Bounce animation** — each slide enters with a damped settle effect
- **Scrolling marquee** — horizontally scrolling PNG banner at consistent speed regardless of FPS
- **Multi-layer compositing** — background video + slideshow + up to 4 PNG overlays
- **Flexible audio modes** — loop, single play, or no audio
- **Safe cleanup** — only deletes temp files after confirming the final video was produced
- **Robust error handling** — raises clear errors instead of silent failures at every stage

---

## 📁 Folder Structure

Set up your Google Drive exactly like this before running:

```
MyDrive/
└── MyAutomation/
    ├── images/                  ← (auto-managed) upload destination
    ├── square/                  ← (auto-created) letterboxed images
    └── assets/
        ├── background/
        │   └── background.mp4   ← looping background video
        ├── marquee/
        │   └── marquee.png      ← scrolling banner (RGBA PNG, full width)
        ├── overlay1/
        │   └── overlay1.png     ← top overlay (e.g. brand logo bar)
        ├── overlay2/
        │   └── overlay2.png     ← lower overlay (e.g. price/info bar)
        ├── bottom/
        │   └── bottom.png       ← bottom CTA button graphic
        └── audio/
            └── audio125.mp3     ← background music
```

> **Note:** The `images/` and `square/` folders are created automatically. All asset files must be placed manually before running.

---

## 📦 Requirements

### Python packages
```
pillow
opencv-python-headless
numpy
```

### System packages
```
ffmpeg
imagemagick
```

### Environment
- **Google Colab** (required — uses `google.colab.drive` and `google.colab.files`)
- **Google Drive** mounted at `/content/drive`

---

## ⚙️ Setup

**1. Open in Google Colab**

Upload `video_pipeline.py` to your Colab environment or paste it into a notebook cell.

**2. Install dependencies**

Run this in a Colab cell before your main code:

```python
!pip install pillow opencv-python-headless -q
!apt-get install ffmpeg imagemagick -y -q
```

**3. Prepare your Google Drive**

Create the folder structure shown above and place all your asset files (background video, PNG overlays, audio) in the correct locations.

**4. Set your base path**

Edit the `base` variable at the top of the script to match your Drive folder:

```python
base = "/content/drive/MyDrive/MyAutomation"
```

---

## 🔧 Configuration

All settings are controlled through the `settings` dictionary:

| Setting | Default | Description |
|---|---|---|
| `FPS` | `30` | Frames per second of output video |
| `DURATION` | `2.8` | Seconds each image is shown |
| `EFFECT_DURATION` | `0.8` | Duration of bounce-in animation (seconds) |
| `FRAME_W` / `FRAME_H` | `1080` / `1920` | Output video resolution (9:16 vertical) |
| `SLIDE_W` / `SLIDE_H` | `1080` / `1080` | Square slide area dimensions |
| `SLIDE_MARGIN` | `0` | Padding inside slide area (pixels) |
| `MARQUEE_H` | `80` | Height of scrolling marquee banner |
| `MARQUEE_TOP` | `80` | Y position of marquee from top |
| `MARQUEE_SPEED` | `120` | Marquee scroll speed in **pixels per second** |
| `OV1_W` / `OV1_H` | `600` / `140` | Overlay 1 dimensions |
| `OV2_W` / `OV2_H` | `1080` / `140` | Overlay 2 dimensions |
| `OV2_Y` | `1447` | Overlay 2 Y position from top |
| `BTN_W` / `BTN_H` | `600` / `140` | Bottom button dimensions |
| `BTN_Y` | `1550` | Bottom button Y position |
| `AUDIO_MODE` | `'1'` | Audio mode (see below) |
| `AUDIO_VOL` | `1` | Audio volume multiplier |

---

## ▶️ How to Run

Run the pipeline with a single call at the bottom of the script:

```python
run_video_pipeline(settings)
```

When prompted, **upload your product/content images** (JPG, PNG, WEBP, BMP). The pipeline will:

1. Delete any old images from the images folder
2. Save your uploaded images and display each file path
3. Process and composite everything automatically
4. Save the final video to: `MyAutomation/final_video.mp4`
5. Clean up all temporary files

---

## 🔊 Audio Modes

| Mode | Value | Behaviour |
|---|---|---|
| Loop | `'1'` | Loops the audio file to fill the entire video duration |
| Single | `'2'` | Plays audio once; video tail is silent if audio is shorter |
| None | `'3'` | No audio — video only |

---

## 🔥 Pipeline Stages

```
Mount Drive
    ↓
Validate asset paths
    ↓
Upload & save images         ← Old images deleted first
    ↓
Convert to square (letterbox)
    ↓
Build slideshow (bounce effect per slide)
    ↓
Composite layers
   ├── Background video (looped)
   ├── Scrolling marquee
   ├── Overlay 1 (top bar)
   ├── Overlay 2 (info bar)
   ├── Slideshow frames
   └── Bottom CTA button
    ↓
Encode final video (ffmpeg + audio)
    ↓
Cleanup temp files           ← Only runs if final video confirmed
```

---

## 🛠️ Troubleshooting

**Drive mount fails**
Make sure your Colab runtime has Google Drive access enabled. Check: `Runtime → Change runtime type`.

**Missing asset error**
Check that all files exist in the correct paths shown in the Folder Structure section. File names are case-sensitive.

**VideoWriter fails to open**
The script tries `avc1`, `mp4v`, and `XVID` codecs automatically. If all fail, ensure `ffmpeg` is installed: `!apt-get install ffmpeg -y`.

**FFmpeg encoding error**
The full ffmpeg error message is printed. Common causes: corrupt composite video, missing audio file, or insufficient disk space in Colab's `/content/` directory.

**Audio is shorter than video (Mode 2)**
A warning is printed but the pipeline continues. The video tail will play silently. Either use Mode 1 (loop) or use a longer audio file.

**Images appear letterboxed / black bars visible**
This is by design — the pipeline preserves aspect ratio. If you want to fill the entire square, pre-crop your images before uploading.

**Pipeline crashed mid-run, images are deleted**
The cleanup stage only runs after the final video is confirmed. If the pipeline crashes before encoding, your images are preserved in the `images/` folder for the next run.

---

## ⚠️ Known Limitations

| Limitation | Detail |
|---|---|
| Google Colab only | Uses `google.colab` APIs — not compatible with local Jupyter or scripts |
| RAM usage scales with video length | All frames are processed in memory; very long videos may hit Colab's RAM limit |
| Single output resolution | Only 1080×1920 (9:16). To change, update `FRAME_W`, `FRAME_H`, and reposition all overlay Y values |
| No transition effects between slides | Slides cut directly; no cross-fade or wipe transitions |
| Overlay positions are hardcoded | Y positions must be adjusted manually in `settings` if resolution changes |
| Audio must be MP3 | Other formats may work but are untested |

---

## 📄 License

MIT License — free to use, modify, and distribute.

---
