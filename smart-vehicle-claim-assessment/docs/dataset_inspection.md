# Dataset Inspection — Kaggle Ripik Hackfest

Dataset URL: <https://www.kaggle.com/datasets/sudhanshu2198/ripik-hackfest>

## What was inspected in this build

The workspace did not contain a downloaded dataset. Kaggle CLI was not installed and no Kaggle credentials were available, so the dataset was **not automatically downloaded**. The public Kaggle page was inspected.

Public-page information visible during inspection:

- Dataset title: **Vehicle Damage Insurance Verification**
- Problem framing: vehicle damage **classification** for claim-verification support
- Listed damage labels/classes on the public page:
  1. `crack`
  2. `scratch`
  3. `tire flat`
  4. `dent`
  5. `glass shatter`
  6. `lamp broken`
- Visible structure: `train/` and `test/`
- Public page note: test set contains images only and requires predicting damage type
- Public page summary: approximately **1.6 GB** and **12.0k files**
- License shown on page: **Apache 2.0**

## What was not verified locally

Because the dataset was not downloaded, this build does **not** claim local verified statistics for:

- Exact train/test counts
- Per-class image counts
- Exact image formats (`jpg`, `png`, etc.)
- Exact CSV/annotation schema
- Bounding boxes or segmentation annotations
- Detection labels for vehicle components

## Task suitability

Based on public-page text, the dataset appears to support **damage type classification**, not direct object detection or part localization. It can help a classifier predict labels such as crack/scratch/dent, but it does not directly support bounding-box damage detection or vehicle-part detection unless local inspection reveals annotation files.

Therefore this project uses it as a future primary classification dataset, while the app currently runs in:

- **Demo/fallback inference mode** without fabricated model metrics
- Optional training mode after the user downloads and verifies the dataset
- Optional YOLO/detection training only if real bounding-box annotations are supplied or created

## How to place the dataset

1. Create Kaggle API credentials at <https://www.kaggle.com/settings>.
2. Install Kaggle CLI if needed:

```bash
pip install kaggle
```

3. Download and extract:

```bash
mkdir -p data/raw/ripik-hackfest
kaggle datasets download -d sudhanshu2198/ripik-hackfest -p data/raw/ripik-hackfest --unzip
```

4. Inspect the local files:

```bash
python scripts/inspect_kaggle_dataset.py --data-dir data/raw/ripik-hackfest
```

5. Only after inspection, prepare a manifest:

```bash
python scripts/prepare_dataset.py --data-dir data/raw/ripik-hackfest
```

## Scientific honesty rule

Do not update README metrics or model-card results until experiments are run on verified labels. If no evaluation has been performed, report: **Not evaluated yet.**
