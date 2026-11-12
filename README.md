# Water meter recognition MVP

Python 3.10+, CPU. FastAPI + RapidOCR ONNX Runtime.

## Run

```sh
python -m venv .venv
# Linux
. .venv/bin/activate
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8011 --workers 1
```

Swagger: `/docs`. POST `/api/read`: multipart field `file` only.

```json
{"serial_number":null,"serial_confidence":0.0,"reading":null,"reading_confidence":0.0}
```

Recognized values are strings. Unrecognized values are null with confidence 0.
Confidence is a conservative OCR support score, not a calibrated probability.
Profiles: BETAR, NORMA, EKOMERA; 5 integer and 3 fractional register digits.

Datasets and model binaries are not stored in Git. RapidOCR installs its default ONNX models with its package; no custom trained weights are required for this MVP.

## Tests

```sh
pip install -r requirements-dev.txt
python -m pytest test_service.py -q
```

Implementation and repository packaging performed by Atlas AI agent at the owner's request.
