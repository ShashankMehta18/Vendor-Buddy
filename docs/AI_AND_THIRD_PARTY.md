# AI assistance and third-party resources

## AI assistance disclosure

OpenAI Codex significantly assisted in authoring the application code, tests, sample document generator, technical documentation and presentation. OpenAI image generation created the Vendor Buddy logo. The team should review the code, reproduce the checks, verify demonstrations and describe its own decisions and contributions accurately. This disclosure supports the hackathon's AI-tool rules. No competing team's project or proprietary implementation was used.

## Dataset provenance

All demonstration vendor names, account numbers, invoices, orders and receipts are fictional and generated with `scripts/generate_samples.py`. The suspicious invoice intentionally varies price, receipt quantity, account details and numeric typography. Ground-truth labels are for evaluation and are never consumed by the application runtime. The scanned scenario rasterizes the invoice to exercise actual OCR.

## Dependencies and licensing assumptions

| Resource | Role | License family / note |
| --- | --- | --- |
| Python | Runtime | PSF |
| FastAPI | API | MIT |
| Starlette / Uvicorn | HTTP framework / server | BSD |
| python-multipart | Upload parsing | Apache-2.0 |
| PyMuPDF / MuPDF | PDF extraction, rendering | AGPL-3.0 or commercial terms; review deployment obligations |
| Pillow | Image handling | HPND |
| ReportLab | PDF dossier and sample documents | BSD |
| scikit-learn | TF-IDF and logistic classifier | BSD-3-Clause |
| NumPy / SciPy | Transitive numeric dependencies | BSD |
| Tesseract | External OCR executable and English model | Apache-2.0; installed separately |
| Optional hosted LLM | Finding narration | Provider-specific terms and data processing policy |

Consult installed package metadata and upstream license texts for exact versions and notices. `requirements-tested.txt` records direct dependency versions from the verification environment. No third-party source or model weights are vendored in this repository. Project code is AGPL-3.0-or-later to align with the selected PDF dependency. The presentation build uses OpenAI's artifact tooling outside the runtime application.

The Vendor Buddy logo was created with OpenAI image generation.
