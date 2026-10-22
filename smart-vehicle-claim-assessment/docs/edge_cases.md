# Edge-Case, Validation and Authenticity Specification Mapping

The system treats edge cases as validation, consistency, authenticity, eligibility and assessment checks — not as automatic fraud detection.

## Decision-support states

- `ELIGIBLE` / `VERIFIED`
- `NEEDS_VERIFICATION`
- `NOT_ELIGIBLE` / `INELIGIBLE`
- `SUSPICIOUS_EVIDENCE`

The UI and API avoid accusing a user of fraud. Suspicious or contradictory evidence routes to manual review.

## Implemented checks

| Area | Current implementation | Manual-review path |
|---|---|---|
| Image quality | Resolution, blur, brightness, corruption validation | Failed/low-quality images ask re-upload or review |
| Evidence completeness | Checks missing images, single image only, missing close-up/context | `Insufficient visual evidence for reliable assessment` |
| Duplicate images | SHA-256 and perceptual-hash near-duplicate detection | Avoids double-counting and asks confirmation |
| Vehicle identity consistency | Registration cross-check between claim, RC/policy extracted fields | Mismatch -> `SUSPICIOUS_EVIDENCE`; missing -> `NEEDS_VERIFICATION` |
| OCR/document extraction | PDF text/byte fallback, optional Tesseract image OCR, regex extraction | Low/no OCR -> user correction/manual review |
| Policy validity | Accident date vs configurable policy dates | Expired/not active -> `NOT_ELIGIBLE` decision-support, not final rejection |
| Policy type | Configurable own-damage vs third-party-only terms | Third-party-only own-damage path -> potential not eligible/manual verification |
| Deductible/IDV | Extracted/configured values used in estimate | Missing deductible -> no reliable settlement |
| Accident-to-damage consistency | Simple direction keyword vs detected component check | Contradiction -> `NEEDS_VERIFICATION` |
| Damage double counting | Groups by inferred component + damage type | Keeps highest-severity/confidence duplicate |
| Pricing unavailable | Does not invent costs | Requires manual estimate/admin pricing |
| Severe/hidden damage | Severe external damage warns hidden/internal cannot be assessed | Manual inspection required |

## Not authoritative / future work

These are surfaced as requiring verification because no authoritative detector/source is bundled:

- AI-generated image detection
- Photoshop/manipulation detection
- Stolen vehicle status
- Government RC/DL verification
- Historical image reuse across insurers/claims
- Multiple-vehicle association model
- Non-car classifier
- EXIF/GPS authenticity verification

Missing EXIF metadata is never treated as proof of fraud.

## Edge-case testing mode

The backend exposes `GET /api/edge-cases` and tests cover several representative cases. Additional scenario fixtures can be added under `tests/`.
