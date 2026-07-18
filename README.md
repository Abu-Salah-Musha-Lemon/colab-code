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
