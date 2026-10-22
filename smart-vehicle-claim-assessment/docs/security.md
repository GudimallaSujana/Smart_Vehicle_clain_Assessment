# Security and Privacy Notes

Implemented for local-development baseline:

- Safe filename generation
- Extension and content validation for JPG/PNG/PDF
- Upload-size limits via environment variables
- Path traversal protection
- SQLite storage outside source code
- Minimal logging that avoids full OCR text and personal details
- Configurable CORS
- Friendly error messages for invalid/corrupted files
- Generated reports and overlays stored under `outputs/`

Production hardening still required:

- Authentication and authorization
- Per-user claim isolation
- Malware scanning/sandboxing for uploads
- Object storage with signed URLs
- Encryption at rest and in transit
- Key/secret management
- Audit logs with privacy controls
- Data-retention and consent management
- Rate limits and abuse prevention
- Stronger document-authenticity verification with authoritative sources
- Secure deployment of OCR/ML workers

Do not deploy this local prototype directly for real customer claims without a full security review.
