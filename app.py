import io
import logging
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import re
import threading
from contextlib import asynccontextmanager

from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, Field
from fastapi import FastAPI, File, UploadFile, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from rapidocr_onnxruntime import RapidOCR

import ocr_backend
from field_parser import extract_field
from meter_profiles import detect_profile, extract_profile_reading, unit_near
from confidence import compact_result, profile_support

Image.MAX_IMAGE_PIXELS = 12_000_000
MAX_BYTES = 12 * 1024 * 1024
lock = threading.Lock()
logger = logging.getLogger("meter_ocr")

class Result(BaseModel):
    model_config = ConfigDict(extra="forbid")
    serial_number: str | None = None
    serial_confidence: float = Field(default=0, ge=0, le=1)
    reading: str | None = None
    reading_confidence: float = Field(default=0, ge=0, le=1)

def empty():
    return Result().model_dump()

@asynccontextmanager
async def lifespan(app):
    ocr_backend.engine = RapidOCR(intra_op_num_threads=1, inter_op_num_threads=1,
                                 det_limit_side_len=736, det_limit_type="max", rec_batch_num=1)
    yield

app = FastAPI(title="Water Meter OCR",version="0.4.0",lifespan=lifespan,redoc_url=None)

@app.exception_handler(RequestValidationError)
async def invalid_request(request, exc):
    return JSONResponse(status_code=422,content=empty())

@app.exception_handler(HTTPException)
async def http_error(request, exc):
    return JSONResponse(status_code=exc.status_code,content=empty())

@app.exception_handler(Exception)
async def unexpected_error(request, exc):
    logger.error("OCR request failed",exc_info=exc)
    return JSONResponse(status_code=500,content=empty())

def parse_fields(lines):
    profile, found = detect_profile(lines)
    # Multiple manufacturers mean that pairing serial and register is not safe.
    if len(found)>1:
        return empty()
    reading = extract_profile_reading(lines,profile) if profile else {"value":None}
    serial = extract_field(lines,"serial")
    support = profile_support(lines,profile) if profile else 0.0
    if serial["value"] is None and profile:
        # Serial-only numeric lines, not display/specification lines.
        # Brand detection permits this branch; multiple candidates remain unresolved.
        serial_len = 9 if profile=="ekomera_5_3" else 8
        candidates={}
        display_digits = re.sub(r"\D","",reading.get("value") or "")
        for line in lines:
            text=line["text"].strip()
            if re.fullmatch(r"\d{"+str(serial_len)+r"}",text) and not unit_near(line,lines):
                if text==display_digits:
                    continue
                if line["confidence"]>=.65:
                    candidates[text]=max(candidates.get(text,0),line["confidence"])
        if len(candidates)==1:
            value,conf=next(iter(candidates.items()))
            serial={"value":value,"confidence":min(conf,support)}
    full_reading = reading.get("completeness")=="full_digit_register"
    return compact_result(serial,reading,support,full_reading)

@app.post("/api/read",response_model=Result,summary="Серийный номер и показания водосчётчика",
          responses={413:{"model":Result},415:{"model":Result},422:{"model":Result},
                     503:{"model":Result},500:{"model":Result}})
def read_meter(file: UploadFile = File(...)):
    if not lock.acquire(blocking=False):
        file.file.close()
        return JSONResponse(status_code=503,content=empty())
    try:
        data=file.file.read(MAX_BYTES+1)
        if len(data)>MAX_BYTES:
            return JSONResponse(status_code=413,content=empty())
        try:
            with Image.open(io.BytesIO(data)) as src:
                if src.format not in {"JPEG","PNG","WEBP","BMP"}:
                    return JSONResponse(status_code=415,content=empty())
                if src.width*src.height>Image.MAX_IMAGE_PIXELS:
                    return JSONResponse(status_code=413,content=empty())
                image=ImageOps.exif_transpose(src).convert("RGB")
        except (Image.DecompressionBombError,UnidentifiedImageError,OSError):
            return JSONResponse(status_code=415,content=empty())
        lines=ocr_backend.ocr_image(image)
        return parse_fields(lines)
    finally:
        lock.release()
        file.file.close()
