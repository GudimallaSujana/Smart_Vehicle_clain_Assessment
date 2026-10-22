#!/usr/bin/env python3
"""Optional YOLO training entry point.

Requires a detection dataset with real bounding-box annotations. The Ripik
Hackfest dataset page indicates a damage-classification task; do not train YOLO
on it as a detector unless you have separately verified/created localization
annotations.
"""
from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-yaml", required=True, help="YOLO data.yaml with train/val paths and real classes")
    parser.add_argument("--weights", default="yolov8n.pt")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=640)
    args = parser.parse_args()
    if not Path(args.data_yaml).exists():
        raise SystemExit("data-yaml not found. Create it only after verifying detection annotations.")
    try:
        from ultralytics import YOLO
    except Exception as exc:
        raise SystemExit("Install optional ML dependencies: pip install -r requirements-ml.txt") from exc
    model = YOLO(args.weights)
    model.train(data=args.data_yaml, epochs=args.epochs, imgsz=args.imgsz)


if __name__ == "__main__":
    main()
