#!/usr/bin/env python3
"""Inspect the Kaggle Ripik Hackfest dataset after the user downloads it.

Usage:
  python scripts/inspect_kaggle_dataset.py --data-dir data/raw/ripik-hackfest

The script does not invent labels. It reports actual directory names, image
formats, annotation files and class-like folders present on disk.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
ANNOT_EXTS = {".txt", ".xml", ".json", ".csv", ".parquet"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True, help="Path to extracted Kaggle dataset root")
    parser.add_argument("--out", default="docs/dataset_local_inspection.json")
    args = parser.parse_args()
    root = Path(args.data_dir)
    if not root.exists():
        raise SystemExit(f"Dataset directory not found: {root}")

    image_formats = Counter()
    annotation_formats = Counter()
    images_by_parent = Counter()
    examples = defaultdict(list)
    total_images = 0
    for path in root.rglob("*"):
        if path.is_file():
            ext = path.suffix.lower()
            if ext in IMAGE_EXTS:
                total_images += 1
                image_formats[ext] += 1
                parent = str(path.parent.relative_to(root))
                images_by_parent[parent] += 1
                if len(examples[parent]) < 5:
                    examples[parent].append(str(path.relative_to(root)))
            elif ext in ANNOT_EXTS:
                annotation_formats[ext] += 1

    class_like_folders = []
    for parent, count in images_by_parent.items():
        parts = Path(parent).parts
        if parts:
            class_like_folders.append(parts[-1])
    result = {
        "root": str(root),
        "total_images": total_images,
        "image_formats": dict(image_formats),
        "annotation_formats": dict(annotation_formats),
        "images_by_parent_folder": dict(images_by_parent.most_common()),
        "class_like_folder_names": sorted(set(class_like_folders)),
        "examples": dict(examples),
        "direct_detection_support": "Only if bounding-box/segmentation annotation files are present. Folder labels alone support classification, not localization.",
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
