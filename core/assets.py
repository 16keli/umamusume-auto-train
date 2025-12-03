from pathlib import Path
from typing import Any, Dict

import cv2

from utils.screen import screen_height_to_scale

# /home/kev/python/umamusume-auto-train/core/assets.py

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tiff"}


def _is_image(path: Path) -> bool:
    return path.suffix.lower() in _IMAGE_EXTS and path.is_file()


def _load_dir(path: Path, scale: float = 1.0, convert_to_grayscale: bool = False) -> Dict[str, Any]:
    """
    Recursively load images from `path`, convert to grayscale, optionally resize
    by `scale` (relative to 4k baseline), and return a nested dict that mirrors
    the directory structure. Files are stored under their filename (including extension).
    """
    result: Dict[str, Any] = {}
    for entry in sorted(path.iterdir()):
        if entry.is_dir():
            result[entry.name] = _load_dir(entry, scale, convert_to_grayscale)
        elif _is_image(entry):
            # read with alpha channel if present
            img = cv2.imread(str(entry), cv2.IMREAD_UNCHANGED)
            if img is None:
                continue  # skip files that cv2 can't read

            if convert_to_grayscale:
                # handle BGRA, BGR, or already-grayscale
                if img.ndim == 3 and img.shape[2] == 4:
                    img = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
                elif img.ndim == 3:
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            if scale != 1.0:
                new_w = max(1, round(img.shape[1] * scale))
                new_h = max(1, round(img.shape[0] * scale))
                img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

            result[entry.name] = img.copy()
    return result


def load_assets(
    root: Path | str | None = None, screen_height: int | str = 1080, convert_to_grayscale: bool = False
) -> Dict[str, Any]:
    """
    Load all images under `root`, convert to grayscale, resize for `screen`, and
    return a nested dict that mirrors the filesystem.

    screen: either an integer pixel height (e.g. 1080) or a string like "1080p".
            Also accepts the named keys "720p", "1080p", "1440p", "4k".
    Resizing uses Lanczos filtering. Resizing is applied relative to a 4k baseline.
    """
    scale = screen_height_to_scale(screen_height)

    if root is None:
        root = Path(__file__).parent / "assets"
    root_path = Path(root)
    if not root_path.exists():
        raise FileNotFoundError(f"Assets directory not found: {root_path}")
    if not root_path.is_dir():
        raise NotADirectoryError(f"Assets path is not a directory: {root_path}")
    return _load_dir(root_path, scale, convert_to_grayscale)


# Optionally load at import time:
# ASSETS = load_assets()
# Example: img = ASSETS['subfolder']['example.png']
