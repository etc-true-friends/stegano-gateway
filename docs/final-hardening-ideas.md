# Final Hardening Ideas

This document tracks post-midterm enhancements for the /etc/friends gateway.

## 1. Policy-Based Attachment Sanitization

Goal: extend the mail gateway beyond image steganography and cover common
business-mail attachment threats.

Implemented signals:

- dangerous executable/script extensions such as `.lnk`, `.ps1`, `.vbs`,
  `.bat`, `.cmd`, `.exe`, `.scr`, `.hta`, `.js`
- macro-capable Office documents such as `.docm`, `.xlsm`, `.pptm`, `.xlsb`
- disk image/package/script-capable attachments such as `.iso`, `.img`, `.dmg`,
  `.chm`, `.jnlp`, `.xll`, `.svg`
- double-extension decoys such as `resume.pdf.lnk`
- declared image MIME type that is not actually an image
- social-engineering filename tags such as resume, invoice, contract, 이력서,
  견적서, 계약서

Delivery behavior:

- the risky original file is moved to quarantine storage
- the user receives a safe `_sanitized.txt` notice instead of the executable
- the audit log records `SUSPICIOUS` and `POLICY_SANITIZED`

This keeps the product behavior aligned with the project policy:

```text
detect -> sanitize/reconstruct -> deliver safe content
```

## 2. Stronger Image CDR Against LSB Payloads

Goal: support the mentor-requested scenario safely:

```text
dummy payload embedded in image -> gateway scan -> CDR -> extraction failure
```

Implemented CDR strengthening:

- metadata/ancillary data stripping
- alpha/palette normalization
- RGB/YCrCb/RGB color conversion
- explicit lowest-bit RGB normalization
- resize round-trip
- JPEG re-encoding

The test should use a harmless dummy payload, never real malware.

Recommended demo wording:

```text
We embedded a non-executable dummy payload into an image using an LSB method.
Before sanitization, the payload can be extracted. After CDR reconstruction,
the same extractor fails because the pixel-level payload is damaged.
```
