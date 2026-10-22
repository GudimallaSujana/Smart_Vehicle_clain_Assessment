# AI-Based Smart Vehicle Claim Assessment

Indian-focused AI-assisted vehicle insurance claim assessment platform.

> **AI-assisted preliminary assessment only. Final claim eligibility, repair assessment, and settlement are subject to insurer verification, policy terms, documentation, inspection, and applicable regulations.**

This project is a digital bridge between:

**Vehicle Owner → AI Assessment → Insurance Evidence/Policy Analysis → Preliminary Claim Report → Insurer/Claim Team**

It is **not** an insurance company, does **not** make legally binding decisions, and does **not** guarantee claim approval or settlement.

---

## 1. Problem Statement

Vehicle owners in India often need help understanding what evidence to collect, what their uploaded documents say, whether policy dates/type appear relevant, and what a preliminary repair/settlement estimate might look like before speaking with the insurer/claim team.

This system provides decision support for:

- Accident image upload and quality validation
- Candidate vehicle damage analysis
- OCR-based document extraction
- Policy validity and consistency checks
- Configurable cost estimation
- Deductible application
- Explainable preliminary PDF report
- Manual-review routing for uncertain/high-risk cases

---

## 2. Indian Insurance Context

The UI/API use India-friendly terminology:

- Vehicle Registration Number
- RC / Registration Certificate
- Policy Number
- Insurer
- IDV
- Own Damage
- Third-Party
- Comprehensive / Package Policy
- Deductible / Excess
- No Claim Bonus context where applicable
- Accident Date
- Claim Date
- Garage / Workshop
- Repair Estimate
- Claim Reference Number

No insurer-specific rules are hard-coded. Policy rules are configurable under `configs/policy_rules.json`.

---

## 3. System Workflow

1. Vehicle Details
2. Accident Details
3. Upload Accident Images
4. Upload Documents
5. Image Quality Validation
6. Vehicle Damage Analysis
7. Damaged Part / Damage Type / Severity Support
8. OCR Document Extraction
9. Structured Field Extraction and User Review
10. Evidence Verification Dashboard
11. Policy Coverage/Validity Analysis
12. Cost Estimation
13. Deductible Application
14. Preliminary Settlement Estimate
15. Explainable PDF Report
16. Download / Share with insurer or claim representative

---

## 4. Project Structure

```text
smart-vehicle-claim-assessment/
├── backend/
│   └── app/
│       ├── main.py
│       ├── db.py
│       ├── schemas.py
│       ├── demo_data.py
│       ├── vision/
│       ├── documents/
│       ├── policy/
│       ├── estimation/
│       ├── reports/
│       ├── services/
│       └── utils/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── lib/
│   ├── package.json
│   └── vite.config.js
├── data/
│   ├── raw/
│   ├── processed/
│   ├── sample/
│   └── pricing/
├── models/
├── experiments/
├── outputs/
├── tests/
├── scripts/
├── configs/
├── docs/
├── requirements.txt
├── requirements-ml.txt
├── .env.example
└── README.md
```

---

## 5. Technology Stack

### Backend

- Python
- FastAPI
- SQLite for local development
- Pillow, NumPy, OpenCV-headless for image processing
- pypdf and optional Tesseract/Pytesseract for OCR
- ReportLab for PDF reports
- Pytest for testing

### Frontend

- React + Vite
- Tailwind CSS
- Lucide React icons
- Recharts for research dashboard charts

### Optional ML

- Ultralytics YOLO
- PyTorch / TorchVision
- Scikit-learn / Pandas
- EasyOCR

Heavy ML dependencies are kept in `requirements-ml.txt` so a student laptop can run the core app in CPU demo mode.

---

## 6. Dataset

Primary dataset referenced by the specification:

<https://www.kaggle.com/datasets/sudhanshu2198/ripik-hackfest>

### Inspection status

The workspace did not include a downloaded dataset. Kaggle CLI was not installed and credentials were not available, so the dataset was **not downloaded automatically**.

The public Kaggle page was inspected. Visible information:

- Title: **Vehicle Damage Insurance Verification**
- Visible structure: `train/`, `test/`
- Public-page task: damage type classification
- Public-page labels/classes:
  - `crack`
  - `scratch`
  - `tire flat`
  - `dent`
  - `glass shatter`
  - `lamp broken`
- Public-page summary: about **1.6 GB**, **12.0k files**
- License shown: **Apache 2.0**

Exact local file formats, annotation files, per-class counts, and detection support were **not locally verified**. See `docs/dataset_inspection.md`.

### Dataset setup

```bash
pip install kaggle
mkdir -p data/raw/ripik-hackfest
kaggle datasets download -d sudhanshu2198/ripik-hackfest -p data/raw/ripik-hackfest --unzip
python scripts/inspect_kaggle_dataset.py --data-dir data/raw/ripik-hackfest
python scripts/prepare_dataset.py --data-dir data/raw/ripik-hackfest
```

### Scientific honesty

This project does **not** fabricate dataset statistics or model metrics. If training/evaluation has not been performed, metrics show **Not evaluated yet**.

---

## 7. Damage Detection Approach

No trained production model is bundled.

Current mode:

- CPU-friendly demo/fallback analyzer
- Image quality validation first
- Candidate damage-region detection using contrast/dark/edge heuristics
- Bounding-box overlay generation
- Damage type fallback labels such as scratch/dent/crack when supported by heuristic signal
- Component inference from view type and image region
- Severity from documented area/confidence/quality scoring

Fallback confidence is capped and labelled as not experimentally validated.

To add a real model:

1. Inspect/prepare a verified dataset.
2. Train a classifier for damage type if labels are folder/CSV classes.
3. Train YOLO only if real detection annotations exist.
4. Put weights in `models/`.
5. Set:

```bash
export SVC_YOLO_WEIGHTS=/absolute/path/to/models/best.pt
```

6. Run evaluation and update model docs with actual results only.

---

## 8. Severity Approach

Severity labels:

- Minor
- Moderate
- Severe
- Unknown when evidence/confidence is insufficient

Severity is based on:

- detected damaged area ratio
- damage type signal
- image quality
- fallback confidence

Hidden/internal damage is explicitly not assessed from external images alone.

---

## 9. OCR Approach

Document pipeline:

**Raw OCR/Text → Cleaning → Regex/NLP Field Extraction → Validation → Structured JSON → User Review**

Supported uploads:

- PDF
- JPG/JPEG
- PNG

Implemented OCR/text extraction:

- PDF text extraction using `pypdf` where possible
- Safe byte-text fallback for simple/test PDFs
- Optional Tesseract/Pytesseract for image OCR if installed
- Low-confidence or unavailable OCR routes to user correction/manual review

Extracted fields include possible:

- Registration Number
- Make / Model / Year / Colour
- Policy Number
- Policy Type
- Start Date / End Date
- IDV
- Deductible
- Coverage / Exclusions
- Accident Date / Claim Date
- Claim Reference Number
- Driving Licence Number / Expiry
- Repair Estimate Total

---

## 10. Policy Analysis Approach

Configurable rules live in `configs/policy_rules.json`.

The policy engine compares:

- extracted/configured policy information
- claim dates
- vehicle registration consistency
- policy type
- deductible
- IDV
- exclusions keywords where available
- detected damage context

Outputs:

- `ELIGIBLE`
- `NOT_ELIGIBLE`
- `NEEDS_VERIFICATION`
- `SUSPICIOUS_EVIDENCE`

It never says the claim **will** be approved.

---

## 11. Cost Estimation Approach

Formula:

```text
Repair Cost = Part/Repair Cost + Replacement Cost + Labour Cost + Material Cost
Estimated Settlement = Eligible Repair Cost − Applicable Deductible
```

The system does **not** invent real-time Indian spare-part prices.

Pricing sources:

- `data/pricing/pricing_template.csv` — for real/admin-approved prices
- `data/pricing/demo_pricing.csv` — demo-only sample values, clearly labelled
- manual/uploaded repair estimate where available
- admin endpoint `/api/admin/pricing`

If no price/manual estimate exists, output status is:

`NEEDS_PRICING_OR_MANUAL_ESTIMATE`

---

## 12. Explainability Features

### Vision

- Image quality status and warnings
- Bounding boxes / overlays
- damage type
- inferred component
- severity
- confidence
- explanation per finding
- duplicate-counting avoidance note

### Policy

Factor → Evidence → Effect → Status table.

Examples:

- Policy Validity → Active on accident date → Supports potential eligibility
- Deductible → ₹1,000 → Reduces preliminary settlement estimate
- Vehicle Registration → mismatch → manual verification required

### Report

PDF report includes:

1. Claim Information
2. Vehicle Information
3. Accident Information
4. Uploaded Evidence
5. AI Damage Findings
6. Extracted Policy Information
7. Policy Analysis
8. Preliminary Repair Estimate
9. Preliminary Settlement
10. Explanation and Validation Warnings
11. Limitations
12. Disclaimer

---

## 13. Evidence Verification and Edge Cases

The Evidence Verification Dashboard checks:

- evidence completeness
- image quality
- duplicate images
- required document availability
- vehicle registration consistency
- policy validity on accident date
- OCR/document readability
- image/document authenticity caveat
- accident-to-damage consistency

The system uses manual-review routing for:

- low confidence
- insufficient images
- blurry/dark/corrupted evidence
- duplicate evidence
- vehicle/document mismatch
- policy date/type issues
- suspicious evidence
- missing documents
- missing pricing
- contradictory accident description
- severe/hidden damage

See `docs/edge_cases.md`.

---

## 14. Installation

### Backend

```bash
cd smart-vehicle-claim-assessment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

Optional ML dependencies:

```bash
pip install -r requirements-ml.txt
```

### Frontend

```bash
cd smart-vehicle-claim-assessment/frontend
npm install
```

---

## 15. Environment Setup

Copy the example file:

```bash
cp .env.example .env
```

Important variables:

```bash
SVC_ENV=development
SVC_DB_PATH=outputs/app.sqlite3
SVC_STORAGE_DIR=outputs
SVC_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
SVC_YOLO_WEIGHTS=
SVC_DEMO_MODE=true
```

---

## 16. Running the Application

### Start backend

From project root:

```bash
python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
```

Health check:

```bash
curl http://localhost:8000/api/health
```

### Start frontend

In another terminal:

```bash
cd frontend
npm run dev -- --host 0.0.0.0 --port 5173
```

Open:

<http://localhost:5173>

Vite proxies `/api` to the backend.

### One-command local script

```bash
./scripts/run_dev.sh
```

---

## 17. Demo Mode

Use the landing page **Try Demo Mode** button or:

```bash
curl -X POST http://localhost:8000/api/demo/seed
```

Demo mode uses synthetic sample images/documents in `data/sample/`.

The UI displays:

**Demo Data — Not a Real Insurance Claim**

Demo prices are sample-only and not real Indian repair prices.

---

## 18. API Documentation

See `docs/api.md`.

Main endpoints:

- `POST /api/claims`
- `POST /api/claims/{claim_id}/images`
- `POST /api/claims/{claim_id}/documents`
- `POST /api/claims/{claim_id}/analyze`
- `GET /api/claims/{claim_id}`
- `GET /api/claims/{claim_id}/damage`
- `GET /api/claims/{claim_id}/policy`
- `GET /api/claims/{claim_id}/estimate`
- `GET /api/claims/{claim_id}/report`
- `GET /api/health`

---

## 19. Database

SQLite tables include:

- `users`
- `vehicles`
- `documents`
- `policies`
- `claims`
- `claim_images`
- `damage_assessments`
- `estimations`
- `verification_checks`
- `reviewer_notes`
- `pricing_items`

SQLite is for local development; the schema is structured so it can be migrated to PostgreSQL later.

---

## 20. Testing

Run from project root:

```bash
pytest
```

Test coverage includes:

- health endpoint
- claim creation
- image upload validation
- corrupted/invalid image handling
- document OCR/extraction pipeline
- policy analysis
- cost estimation and settlement calculation
- PDF report generation
- demo mode
- metrics helper functions
- edge behavior for mismatch/expired policy/no pricing

---

## 21. Evaluation

Research dashboard route:

- Frontend: Research page
- Backend: `GET /api/research/metrics`

Metrics are intentionally **Not evaluated yet** until real experiments are run.

Expected future metrics:

### Detection

- Precision
- Recall
- F1
- mAP@50
- mAP@50:95

### Classification

- Accuracy
- Precision
- Recall
- F1
- Confusion matrix

### Severity

- Accuracy
- F1
- Confusion matrix

### Cost estimation

- MAE
- RMSE
- MAPE

---

## 22. Troubleshooting

### `python-multipart` error

Install backend requirements:

```bash
pip install -r requirements.txt
```

### Image OCR returns empty text

Install Tesseract and Pytesseract or manually correct fields in the UI/API.

### Kaggle download fails

Ensure `~/.kaggle/kaggle.json` exists and permissions are correct, then rerun the dataset download command.

### No preliminary settlement

Check:

- policy deductible exists
- manual repair estimate uploaded/entered, or pricing configured
- non-demo claims do not use demo pricing

### Frontend cannot reach backend

Ensure backend is on port `8000` and frontend Vite proxy is running.

---

## 23. Limitations

- No trained production damage model is bundled.
- Current CV fallback is not experimentally evaluated.
- Component detection is approximate in fallback mode.
- OCR can be wrong; user review is required.
- Policy analysis is configurable decision support, not insurer-specific legal interpretation.
- No legal document authenticity verification is performed.
- No stolen-vehicle/government database integration is included.
- No AI-generated image detector is bundled.
- Hidden/internal mechanical damage cannot be estimated from external photos.
- Pricing must be configured or supplied by repair estimate; real-time prices are not invented.

---

## 24. Future Improvements

- Train damage classifier on verified Ripik dataset
- Add CarDD or other licensed detection datasets
- Add real component detection/segmentation model
- Add reviewer workflow with authentication
- Add PostgreSQL migrations
- Add object storage and signed URLs
- Add insurer policy-wording ingestion and RAG with citations
- Add authoritative RC/DL/policy verification integrations where legally available
- Add robust manipulation/AI-generated-image detection as a signal, not proof
- Add production-grade security, privacy and audit controls

---

## 25. Development Notes

- Current workspace was empty at start.
- No uploaded presentation file was found in the workspace, so no project presentation could be inspected.
- Public Kaggle dataset page was inspected, but local dataset files were not downloaded.
- The application runs without training data using sample/demo assets and fallback inference.

---

## 26. Final Disclaimer

This report/application is an AI-assisted preliminary assessment generated from the information and images provided. It does not constitute final claim approval, insurance advice, or a binding settlement. Final assessment is subject to verification by the respective insurer, policy terms, documentation, inspection, and applicable regulations.
