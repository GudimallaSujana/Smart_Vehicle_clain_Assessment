# API Documentation

Base path: `/api`

## Core endpoints

- `GET /api/health` — backend, ML, OCR and CPU/GPU status
- `POST /api/claims` — create draft claim
- `GET /api/claims` — list claims
- `GET /api/claims/{claim_id}` — full claim detail
- `POST /api/claims/{claim_id}/images` — upload accident image (`multipart/form-data`: `file`, `view_type`)
- `POST /api/claims/{claim_id}/documents` — upload document (`multipart/form-data`: `file`, `document_type`)
- `PATCH /api/claims/{claim_id}/documents/{document_id}/fields` — user/admin OCR corrections
- `POST /api/claims/{claim_id}/analyze` — run validation, damage analysis, policy analysis, estimate and report generation
- `GET /api/claims/{claim_id}/damage` — damage findings
- `GET /api/claims/{claim_id}/policy` — policy analysis result
- `GET /api/claims/{claim_id}/estimate` — preliminary cost/settlement
- `GET /api/claims/{claim_id}/verification` — evidence verification dashboard data
- `GET /api/claims/{claim_id}/report` — PDF report
- `GET /api/claims/{claim_id}/images/{image_id}/file?overlay=true|false` — local image/overlay preview

## Admin/research endpoints

- `POST /api/demo/seed` — creates a demo claim from synthetic sample assets
- `GET /api/research/metrics` — actual experiment metrics or `Not evaluated yet`
- `GET /api/admin/pricing` — configured prices
- `POST /api/admin/pricing` — add admin-approved pricing item
- `POST /api/claims/{claim_id}/review` — manual reviewer note/decision
- `GET /api/edge-cases` — edge-case testing scenarios

## Example claim creation

```json
{
  "user": { "name": "Vehicle Owner" },
  "vehicle": {
    "registration_number": "TS09AB1234",
    "make": "Tata",
    "model": "Nexon",
    "year": 2021
  },
  "accident": {
    "accident_date": "2026-09-20",
    "claim_date": "2026-09-22",
    "accident_description": "Front bumper impact after low-speed collision."
  },
  "policy": {
    "policy_number": "POL123",
    "policy_type": "Comprehensive / Package Policy",
    "start_date": "2026-01-01",
    "end_date": "2026-12-31",
    "idv": 500000,
    "deductible": 1000
  },
  "demo_mode": false
}
```

## Disclaimer

All endpoints return decision-support information only. They do not approve/reject claims legally.
