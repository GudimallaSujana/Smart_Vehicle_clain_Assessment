#!/usr/bin/env python3
"""Prepare classification/detection dataset manifests after local data inspection.

This script intentionally refuses to infer unsupported labels. If the dataset has
class folders, it can write a classification manifest. If YOLO/COCO annotations
are present, extend this script for detection training.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--out", default="data/processed/classification_manifest.csv")
    args = parser.parse_args()
    root = Path(args.data_dir)
    if not root.exists():
        raise SystemExit(f"Missing dataset root: {root}")
    rows = []
    for img in root.rglob("*"):
        if img.is_file() and img.suffix.lower() in IMAGE_EXTS:
            label = img.parent.name
            rows.append({"path": str(img), "label_from_parent_folder": label})
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["path", "label_from_parent_folder"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {out}. Verify labels before training.")


if __name__ == "__main__":
    main()
