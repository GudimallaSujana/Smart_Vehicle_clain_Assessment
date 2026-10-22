# Model Card — Current Build

## Model status

No trained production computer-vision model is bundled in this repository.

Current mode:

- CPU-friendly heuristic fallback for demo/decision-support
- Image quality validation using PIL/OpenCV
- Candidate damage-region detection using high-contrast/dark-region heuristics
- Damage type inference limited to documented fallback logic
- Component labels inferred from image region/view, not a trained part detector

## Supported labels

Verified from the public Kaggle dataset page as damage-classification labels:

- crack
- scratch
- tire flat
- dent
- glass shatter
- lamp broken

The fallback generally emits `scratch`, `crack`, or `dent` from visual heuristics. It does not claim reliable tire-flat/glass/lamp classification without a trained model.

## Severity method

Severity is derived from:

- detected region area ratio
- inferred damage type
- image quality status
- capped fallback confidence

Labels:

- Minor
- Moderate
- Severe
- Unknown when evidence/confidence is insufficient

This method is documented but **not experimentally validated**. Metrics: **Not evaluated yet.**

## Explainability

The system outputs:

- bounding boxes / overlays
- damage label
- inferred component
- confidence score
- severity label and explanation
- quality warnings
- manual-review triggers

## Limitations

- Hidden/internal mechanical damage cannot be assessed from external images alone.
- Fallback confidence is not claim approval probability.
- Component detection is approximate unless a trained component detector is added.
- No AI-generation/manipulation detector is bundled.
- No insurer-specific policy decision is made.

## How to add a real model

1. Download and inspect datasets.
2. Verify labels and annotations.
3. For classification, train a classifier from a verified manifest.
4. For detection, use YOLO only with real bounding boxes/segmentation labels.
5. Place weights in `models/` and set:

```bash
export SVC_YOLO_WEIGHTS=/absolute/path/to/models/best.pt
```

6. Run evaluation and update docs with actual metrics only.
