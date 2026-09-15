# Worker Intake AI

This repository contains a local research prototype for legal aid intake review. It is intentionally limited to synthetic data and a manual review workflow for milestone 1.

## Scope

- Research prototype: synthetic examples only.
- Staff can enter or load a fictional contract and worker intake notes.
- Manual review table preserves source provenance and correction history.
- Prediction panel is explicitly unavailable and not fabricated.
- Future AI extraction remains separate from statistical prediction.

## Tested dependency versions

The app was verified with the following versions:

- Python 3.13.9
- Streamlit 1.39.0
- pypdf 5.1.0
- pytest 8.3.3

## Local startup

1. Create a virtual environment:
   python3 -m venv .venv
   source .venv/bin/activate
2. Install dependencies:
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
3. Run the app:
   streamlit run app.py

Open the local address shown by Streamlit in the terminal.

## Design notes

- Documents remain in session memory only.
- The fixture extraction provider only supports the exact synthetic example included in `data/synthetic/`.
- Arbitrary documents never receive a fabricated result.
- OCR is not implemented; scanned PDFs without extractable text are rejected with a clear message.
- Unknown and disputed values are preserved rather than converted to "no."
- This is not a production privacy or legal-determination system.
