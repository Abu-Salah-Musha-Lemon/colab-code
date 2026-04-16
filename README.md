## colab-code

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
