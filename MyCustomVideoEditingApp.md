## 🎬 My Custom Video Editing App

A powerful **automated video editing system** built using Python, OpenCV, and FFmpeg.  
This project generates professional-style vertical videos (Reels / TikTok / Shorts) using images, videos, overlays, and animations.

---

# 🚀 Features

## 🎞️ Video Processing
- Convert images into video slideshow
- Auto resize & crop images
- Merge multiple video layers
- Loop background video

## 🎨 Overlay System
- PNG transparent overlays (alpha blending)
- Marquee scrolling banner (top animation)
- Center overlays (UI cards / ads / text)
- Bottom CTA button layer

## 🎬 Animation Engine
- Bounce effect animation for images
- Smooth frame-by-frame motion
- Custom duration per image
- Elastic easing effect

## 🧠 Automation Engine
- Fully automatic layout system
- Auto-centering of elements
- Dynamic resolution handling
- Batch image processing
- Auto duration matching (video sync)

## 📦 Export System
- Final MP4 output (H.264)
- Optimized for social media
- High quality vertical format (1080x1920)

---

# 🏗️ System Architecture

```

INPUT IMAGES + ASSETS
↓
Image Processing (Pillow / ImageMagick)
↓
Slideshow Generator (OpenCV)
↓
Animation Engine (Bounce Effect)
↓
Background Video Loader (FFmpeg)
↓
Layer System (PNG Overlays)
↓
Frame Composer (OpenCV)
↓
Final Encoder (FFmpeg H.264)
↓
OUTPUT VIDEO (MP4)

```
id="arch1"

---

# ⚙️ Tech Stack

- 🐍 Python
- 🎥 OpenCV
- 🎞️ FFmpeg
- 🖼️ Pillow (PIL)
- 🧩 ImageMagick
- ☁️ Google Colab / Linux / Windows

---

# 📁 Project Structure

```

MyVideoEditor/
│
├── images/                # Input images
├── square/                # Processed images
│
├── assets/
│   ├── background.mp4
│   ├── marquee.png
│   ├── overlay1.png
│   ├── overlay2.png
│   ├── bottom.png
│
├── output/
│   ├── slideshow.mp4
│   ├── final_video.mp4
│
├── main.py                # Main pipeline
├── utils.py               # Helper functions
└── README.md

```
id="structure1"

---

# 🧠 How It Works

## 1️⃣ Input System
- User uploads images into `/images`
- System validates all files

---

## 2️⃣ Image Processing
- Resize images to required resolution
- Convert aspect ratio to fit slideshow frame
- Save processed images in `/square`

---

## 3️⃣ Slideshow Engine
Each image becomes a video sequence:
- Duration controlled by FPS
- Bounce animation applied using math functions:
  - exponential decay
  - cosine oscillation

---

## 4️⃣ Layer System (Core Concept)

Final video is composed of multiple layers:

### 🎬 Layer Stack:
1. Background Video
2. Marquee (scrolling top banner)
3. Overlay 1 (center UI card)
4. Slideshow (animated images)
5. Overlay 2 (bottom strip)
6. CTA Button

---

## 5️⃣ Frame Rendering Process

Each frame is built like:

```

frame = background
frame += marquee (scrolling)
frame += overlay1
frame += slideshow frame
frame += overlay2
frame += button

````
id="render1"

---

## 6️⃣ Video Export
- Frames combined using OpenCV
- Final encoding using FFmpeg
- Output optimized for mobile platforms

---

# 🧪 Installation

## Install dependencies

```bash
pip install opencv-python pillow numpy
sudo apt-get install ffmpeg imagemagick
````

---

# ▶️ How to Run

## Option 1: Python

```bash
python main.py
```

## Option 2: Google Colab

* Mount Google Drive
* Set file paths
* Run all cells step-by-step

---

# ⚙️ Configuration Options

You can customize:

## 🎥 Video Settings

* FPS (24 / 30 / 60)
* Resolution (default: 1080x1920)

## 🖼️ Layout Settings

* Marquee height & speed
* Overlay positions
* Slideshow size & margin

## 🎞️ Animation Settings

* Bounce intensity
* Slide duration
* Effect timing

---

# 💡 Use Cases

* 📱 Facebook / Instagram Reels ads
* 🎬 TikTok video automation
* 🏠 Real estate video showcase
* 🛍️ E-commerce product videos
* 📢 Marketing promotional reels

---

# 🧠 Key Concepts Used

* Frame-by-frame video rendering
* Alpha blending (transparent overlays)
* Mathematical animation functions
* FFmpeg encoding pipeline
* Modular video composition system
* Automation-based rendering engine

---

# 📚 Learning Resources / Tutorials

## 🎥 OpenCV + FFmpeg Video Editing

[https://www.youtube.com/results?search_query=python+opencv+ffmpeg+video+editing+tutorial](https://www.youtube.com/results?search_query=python+opencv+ffmpeg+video+editing+tutorial)

---

## 🎞️ Slideshow Video Generator

[https://www.youtube.com/results?search_query=ffmpeg+slideshow+video+python+tutorial](https://www.youtube.com/results?search_query=ffmpeg+slideshow+video+python+tutorial)

---

## 🧠 OpenCV VideoWriter Guide

[https://pyimagesearch.com/2016/02/22/writing-to-video-with-opencv/](https://pyimagesearch.com/2016/02/22/writing-to-video-with-opencv/)

---

## 🎬 Full Video Editor (Advanced)

[https://www.youtube.com/results?search_query=flutter+video+editor+ffmpeg+tutorial](https://www.youtube.com/results?search_query=flutter+video+editor+ffmpeg+tutorial)

---

# 🚀 Future Improvements

* 🎛️ Drag & drop timeline editor UI
* 🎨 Transition effects (fade, zoom, slide)
* 🎵 Audio syncing system
* 🧩 Template-based video generator
* 🌐 Web-based editor (React + FFmpeg)
* 📱 Mobile app version (Flutter)

---

# 👨‍💻 Author

Built using Python automation + FFmpeg video processing engine.

---

# 📜 License

This project is open-source for learning and personal use.

---
