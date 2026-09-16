##colabe-code
```
# ============================================================
# FOOOCUS - COLAB FINAL STARTUP
# T4 / Python 3.10
# ============================================================

import os
import sys
import subprocess
import time
import socket

# ------------------------------------------------------------
# 1. Make sure we're in the correct directory
# ------------------------------------------------------------

os.chdir("/content")

FOOOCUS_DIR = "/content/Fooocus"
VENV_DIR = "/content/fooocus_venv"

PYTHON = f"{VENV_DIR}/bin/python"

print("=" * 60)
print("FOOOCUS STARTUP")
print("=" * 60)

# ------------------------------------------------------------
# 2. Verify installation
# ------------------------------------------------------------

if not os.path.exists(FOOOCUS_DIR):
    raise RuntimeError("Fooocus directory does not exist.")

if not os.path.exists(PYTHON):
    raise RuntimeError("Python 3.10 virtual environment does not exist.")

if not os.path.exists(f"{FOOOCUS_DIR}/entry_with_update.py"):
    raise RuntimeError("Fooocus entry_with_update.py is missing.")

print("\nFooocus:", FOOOCUS_DIR)
print("Python:", PYTHON)

# ------------------------------------------------------------
# 3. Python version
# ------------------------------------------------------------

print("\nPython version:")
subprocess.run([PYTHON, "--version"])

# ------------------------------------------------------------
# 4. GPU check
# ------------------------------------------------------------

print("\nGPU:")
subprocess.run(["nvidia-smi"])

# ------------------------------------------------------------
# 5. Environment
# ------------------------------------------------------------

os.environ["PATH"] = f"{VENV_DIR}/bin:" + os.environ["PATH"]
os.environ["MPLBACKEND"] = "Agg"

# ------------------------------------------------------------
# 6. Start Fooocus
# ------------------------------------------------------------

os.chdir(FOOOCUS_DIR)

print("\n" + "=" * 60)
print("STARTING FOOOCUS")
print("=" * 60)
print("""
Please wait.

The first startup can download:
- PyTorch dependencies
- Fooocus dependencies
- model files

DO NOT INTERRUPT THE CELL unless an ERROR appears.
""")

# ------------------------------------------------------------
# 7. Launch
# ------------------------------------------------------------

process = subprocess.Popen(
    [
        PYTHON,
        "-u",
        "entry_with_update.py",
        "--share",
        "--always-high-vram"
    ],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1
)

# ------------------------------------------------------------
# 8. Display live output
# ------------------------------------------------------------

public_url_found = False

try:
    for line in iter(process.stdout.readline, ""):

        if not line:
            break

        print(line, end="", flush=True)

        # Detect Gradio URLs
        if (
            "gradio.live" in line
            or "gradio.app" in line
            or "Running on public URL" in line
        ):
            public_url_found = True

            print("\n" + "=" * 60)
            print("FOOOCUS PUBLIC URL FOUND")
            print("=" * 60)
            print(line.strip())
            print("=" * 60)

except KeyboardInterrupt:
    print("\nStopping Fooocus...")
    process.terminate()

# ------------------------------------------------------------
# 9. Process status
# ------------------------------------------------------------

return_code = process.poll()

print("\nFooocus process status:", return_code)

if return_code is not None and return_code != 0:
    print("\nFooocus exited with an error.")
    print("Copy the error shown above and send it to me.")

```








## colab-code v2
```
# ==========================================
# Fooocus Google Colab Auto Setup
# ==========================================

import os, sys, subprocess

# Remove old Fooocus
os.chdir("/content")
subprocess.run("rm -rf Fooocus", shell=True)

# Remove conflicting UI packages
subprocess.run(
    "pip uninstall -y gradio gradio-client fastapi starlette jinja2 uvicorn pygit2 -q",
    shell=True
)

# Install Fooocus requirements
subprocess.run(
    "pip install -q pygit2 gradio fastapi starlette jinja2 uvicorn opencv-python-headless pillow numpy scipy",
    shell=True
)

# Clone Fooocus
subprocess.run(
    "git clone https://github.com/lllyasviel/Fooocus.git",
    shell=True
)

os.chdir("/content/Fooocus")

# Prevent Fooocus from automatically changing packages
file = "entry_with_update.py"

if os.path.exists(file):
    with open(file, "r", encoding="utf-8") as f:
        data = f.read()

    data = data.replace(
        "subprocess.run([sys.executable, '-m', 'pip', 'install'",
        "subprocess.run([sys.executable, '-m', 'pip', 'install', '--no-deps'"
    )

    with open(file, "w", encoding="utf-8") as f:
        f.write(data)

print("================================")
print("Fooocus setup completed")
print("Starting Fooocus...")
print("================================")

# Start Fooocus
os.system(
    "python entry_with_update.py --share --always-high-vram"
)
```
## colab-code v1

```
# STEP 0: Clean EVERYTHING
!pip uninstall -y cupy cupy-cuda12x cupy-cuda11x cupy numpy pymatting

# STEP 1: Install stable NumPy
!pip install numpy==1.26.4

# STEP 2: Install CPU-only pymatting (no CuPy dependency)
!pip install pymatting==1.1.8

# STEP 3: Install pygit2
!pip install pygit2==1.15.1

# STEP 4: Clone Fooocus
%cd /content
!rm -rf Fooocus
!git clone https://github.com/lllyasviel/Fooocus.git

# STEP 5: BLOCK CuPy import at runtime (critical hack)
import sys
sys.modules['cupy'] = None

# STEP 6: Run Fooocus
%cd /content/Fooocus
!python entry_with_update.py --share --always-high-vram
```
