# Vendor Buddy

**Vendor payment investigation with evidence you can inspect.**

DataOps Innovation Hackathon 2026 · PS-2: AI-Powered Document Forensics and Contextual Intelligence System.

Vendor Buddy compares a vendor invoice with a purchase order, delivery receipt and approved vendor record. It extracts fields and SKU rows, identifies contextual discrepancies and limited visual anomalies, highlights original page regions, and generates an investigation dossier. It supports human review. It does not establish fraud or approve payments.

## Quick start: macOS / Linux

Use **Python 3.11 or newer**, including Python 3.13 with compatible dependency releases. Python 3.12 was used for the recorded validation.

```bash
cd vendor-buddy
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open **http://localhost:8000**. No API key is required. Click **Suspicious payment bundle** for the main demonstration. Supplied PDFs are already generated.

For scanned PDFs and images, install **Tesseract** with its English language data. macOS with Homebrew: `brew install tesseract`. Ubuntu/Debian: `sudo apt-get install tesseract-ocr`. Check `tesseract --version`. Digital text PDFs work without Tesseract.

Alternatively, double-click `start_mac.command` on macOS (Terminal may require `chmod +x start_mac.command`), or run `bash start.sh` on Linux. These scripts create a local virtual environment and install declared dependencies.

## Windows

Install Python 3.11 or newer and enable **Add Python to PATH**. In PowerShell:

```powershell
cd vendor-buddy
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open http://localhost:8000. You can also double-click `start_windows.bat`. For scans, install Tesseract separately and add its installation directory to PATH. Verify with `tesseract --version` in a new terminal. Activation-policy changes are unnecessary when using the explicit Python path above.

## Demonstration cases

| Case | Input | Expected result |
| --- | --- | --- |
| Consistent | Four matching digital PDFs | No findings from implemented checks |
| Suspicious | Four digital PDFs | Price mismatch, quantity mismatch, account change, numeric font outlier |
| Scanned | Three digital PDFs and one invoice PNG | OCR extraction, price/quantity/account findings |
| Duplicate | Suspicious bundle plus identical invoice copy | Hash duplicate plus findings on each invoice |

All files are fictional. `data/samples/ground_truth.json` is evaluation metadata only. The runtime reads document bytes and never reads that file. Uploaded files use the same extraction and investigation pipeline as demo cases. Test altered values and filenames to verify this.

### Main case facts

Aster Industrial Supplies / PO-2026-1042 / invoice INV-2026-071:

- Approved cable unit price: INR 500. Invoiced price: INR 650 for 100 units.
- Receipt records 80 cable units. Invoice bills 100.
- Invoice account ends in 6655. Approved vendor account ends in 4455.
- Invoice cable amount uses Courier-Bold 16 pt against median monetary text of 11 pt.
- Invoice total: INR 67,000. The INR 15,000 price difference and INR 13,000 invoice value of units beyond the uploaded receipt overlap. **Do not add them as an asserted loss.**

## Implemented capabilities

- Multi-file PDF/PNG/JPG ingestion; document and page identifiers; SHA-256 source hashes.
- PDF text extraction and English Tesseract OCR fallback for scans.
- Document headings plus a small TF-IDF / logistic regression classifier.
- Supported labelled fields and SKU table rows with quantity, unit price and amount.
- Line, subtotal and stated-total arithmetic checks.
- Comparisons constrained by vendor, PO and SKU identifiers; currency mismatch warning.
- Vendor account change detection, identical-file detection and invoice-number collisions.
- PDF numeric font/size outlier observations; limited raster numeric-height observation.
- Clickable source bounding boxes, extracted information, reviewer status and audit events.
- PDF dossier with evidence crops, JSON export, local case history and deletion.
- Optional OpenAI-compatible LLM narration from existing findings. Local detection does not require a hosted model.

## AI and methodology

Tesseract provides learned OCR. A deliberately small text classifier identifies known document categories. Deterministic checks investigate structured evidence. The typography module uses explainable heuristics, not a trained forgery model. The optional LLM writes a separate summary and cannot add detections to the finding list. See [architecture](docs/architecture.md) and [limitations](docs/limitations.md).

PDF text extraction does not supply a calibrated confidence score. OCR scores reflect recognition, not authenticity. Classifier scores are uncalibrated. We do not assign a fraud probability.

## Optional hosted narration

Export `LLM_API_KEY`, `LLM_BASE_URL` and `LLM_MODEL` in the launching shell. See `.env.example`. That file is a reference and is **not loaded automatically**. The browser never receives the key. Click **Generate optional AI summary** to send finding explanations and actions to the configured provider. Source page images are not sent. Explanations can still reveal vendor information, so use authorized data and an appropriate provider. Narration was not live-provider tested in this delivery.

## Verification

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python scripts/evaluate.py
```

The recorded run passed **21 automated tests**. All **4 synthetic demonstration cases** matched their expected finding-category sets. These template-controlled cases are not a representative accuracy benchmark. See [evaluation.json](docs/evaluation.json). Tests include unseen values, renamed files, vendor and PO isolation, currency mismatch, actual OCR, corrupted files, bounding boxes, PDF evidence and an end-to-end API workflow. CI repeats these tests with Tesseract.

The HTML/CSS/JS frontend is included. JavaScript syntax and API behavior were checked. Interactive browser rendering was not verified in the authoring environment because local preview access was restricted. Run the UI once before recording.

## Architecture and repository

```text
app/engine.py        Extraction, classification, comparisons and visual observations
app/main.py          FastAPI API, uploads, case storage, review and optional narration
app/report.py        Evidence-backed PDF dossier
app/static/          Browser interface, CSS and JavaScript (no Node build required)
data/samples/        Fictional clean, suspicious, scanned and duplicate bundles
scripts/             Sample generator and reproducible evaluation
tests/               Pipeline and API tests
docs/                Architecture, limitations, disclosure, demo guide and sample dossier
```

Architecture diagram: [docs/architecture.md](docs/architecture.md).

## Data handling and deployment boundary

Bind to **127.0.0.1** for this local prototype. There is no multi-user authentication, tenant isolation, malware scanning or production job queue. Cases persist under `.local_data/` until deleted. That directory is ignored by Git. The UI's delete action removes the case's original uploads, rendered pages and JSON. Backups and copies outside the app are outside its control. Do not commit real vendor data or API keys.

Limits: 12 files/case, 15 MB/file, 60 MB/case, 12 pages/document. OCR timeout: 45 seconds/page. Use trusted demonstration files. General PDF/image processing still requires production resource isolation before public hosting.

## Docker (optional)

```bash
docker build -t diligence-vendor-buddy .
docker run --rm -p 127.0.0.1:8000:8000 diligence-vendor-buddy
```

Container data disappears on removal unless you mount `/app/.local_data`. Public hosting is outside the validated scope.

## GitHub submission

Create an empty GitHub repository, suggested name **Diligence-Vendor-Buddy**. From this project directory:

```bash
git init
git add .
git commit -m "Build Vendor Buddy vendor payment investigation prototype"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/Diligence-Vendor-Buddy.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your account. If GitHub created a README during repository creation, use an empty repository instead to avoid an unrelated-history conflict. Do not upload `.venv`, `.env` or `.local_data`. An archive is not a GitHub link: submit the accessible repository URL.

## Submission materials

- [Sample investigation dossier](docs/sample-investigation-dossier.pdf)
- [Demo sequence and narration](docs/demo-guide.md)
- [Technical architecture](docs/architecture.md)
- [Limitations and assumptions](docs/limitations.md)
- [AI assistance and third-party notices](docs/AI_AND_THIRD_PARTY.md)
- [Submission checklist](docs/submission-checklist.md)

## Licensing and provenance

Original project source is offered under **AGPL-3.0-or-later**. PyMuPDF has AGPL/commercial licensing conditions. See [LICENSE](LICENSE) and the third-party notice before redistribution or deployment. The sample corpus is generated by `scripts/generate_samples.py` and contains no real customer documents. Significant implementation and presentation assistance came from OpenAI Codex. The team must review and understand the submission and describe assistance accurately under the hackathon rules.
