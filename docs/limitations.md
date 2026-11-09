# Implemented scope and limitations

## Supported

English digital PDFs and legible English scans; labelled fields; item tables containing SKU, description, quantity, unit price and amount; one currency per linked monetary comparison. Documents connect through vendor, PO and SKU. The report preserves findings and original page references. File hashes, review events, local history and deletion are implemented.

## Partial

Document classification uses a small example corpus and familiar headings. Layout extraction is template-constrained. Numeric typography and raster token-height outliers cover a narrow visual-anomaly class. OCR confidence is not calibrated for authenticity. Handwritten fields, signatures, copied image regions and sophisticated forgeries are not reliably analyzed. Several reference documents for one PO may produce several comparisons; the prototype does not reconcile aggregate multi-receipt accounting.

## Unsupported

Arbitrary invoice layouts, handwriting recognition guarantees, signature authenticity, document issuer authentication, live ERP or bank checks, tax compliance, multi-currency conversion, purchase approvals, fraud probabilities, autonomous payment decisions, multi-tenant deployment and production forensic chain-of-custody compliance.

## Interpretation

A vendor account difference may be an authorized change. A short recorded delivery may reflect additional receipts or advance billing. A font outlier may be legitimate emphasis. A hash match establishes duplicate bytes, not duplicate payment. A clean result means no implemented checks fired; it does not certify authenticity. Missing records and extraction failures reduce coverage and appear as warnings. Vendor-master authorization is an input assumption, not something this app verifies.

## Evaluation boundary

Four generated cases use controlled layouts. Ground truth is separate from runtime analysis. Unit tests include unseen vendor names, prices and PO identifiers, but do not establish broad layout generalization. No real-world accuracy percentage, customer ROI or production latency guarantee is asserted. Optional hosted narration has a coded integration but was not live-provider tested. Browser rendering requires a local pre-demo check.

## Planned

Broader table/layout models, receipt aggregation, currency and amendment workflows, calibrated detection evaluation, signature-placement analysis, ERP connectors, authentication and durable audit controls. These are future work.
