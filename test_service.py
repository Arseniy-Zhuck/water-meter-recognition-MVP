import io
import pytest
from PIL import Image
from fastapi.testclient import TestClient
import app
import ocr_backend
from confidence import compact_result,field_score
from meter_profiles import normalize_display,PROFILES

KEYS={"serial_number","serial_confidence","reading","reading_confidence"}

def row(text,conf=.99,x=0,y=0):
    return {"text":text,"confidence":conf,"box":[[x,y],[x+250,y],[x+250,y+40],[x,y+40]]}

def photo():
    b=io.BytesIO();Image.new("RGB",(400,300),"white").save(b,"PNG");return b.getvalue()

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(app,"RapidOCR",lambda **kwargs:object())
    monkeypatch.setattr(ocr_backend,"ocr_image",lambda image:[])
    with TestClient(app.app,raise_server_exceptions=False) as c:yield c

def test_exact_contract_and_only_file(client):
    spec=client.get("/openapi.json").json()
    assert list(spec["paths"])==["/api/read"]
    assert set(spec["paths"]["/api/read"])=={"post"}
    ref=spec["paths"]["/api/read"]["post"]["requestBody"]["content"]["multipart/form-data"]["schema"]["$ref"].split("/")[-1]
    assert set(spec["components"]["schemas"][ref]["properties"])=={"file"}
    j=client.post("/api/read",files={"file":("x.png",photo())}).json()
    assert set(j)==KEYS and j==app.empty()

@pytest.mark.parametrize("path",["/","/health","/api/profiles","/api/demo","/redoc"])
def test_removed_routes(client,path):
    r=client.get(path)
    assert r.status_code==404 and set(r.json())==KEYS

def test_swagger(client):
    assert client.get("/docs").status_code==200

@pytest.mark.parametrize("route",["/api/read"])
def test_missing_file(client,route):
    r=client.post(route);assert r.status_code==422 and r.json()==app.empty()

def test_corrupt_image(client):
    r=client.post("/api/read",files={"file":("x.png",b"bad")})
    assert r.status_code==415 and r.json()==app.empty()

def test_busy(client):
    app.lock.acquire()
    try:
        r=client.post("/api/read",files={"file":("x.png",photo())})
        assert r.status_code==503 and set(r.json())==KEYS
    finally:app.lock.release()

def test_extraction(client,monkeypatch):
    lines=[row("BETAR",.85),row("No. 12345678",.92,y=80),row("00123456 m3",.98,y=160)]
    monkeypatch.setattr(ocr_backend,"ocr_image",lambda image:lines)
    j=client.post("/api/read",files={"file":("x.png",photo())}).json()
    assert j=={"serial_number":"12345678","serial_confidence":.92,"reading":"00123.456","reading_confidence":.85}

def test_partial_result():
    j=app.parse_fields([row("No. 12345678",.9)])
    assert j["serial_number"]=="12345678" and j["reading"] is None

def test_partial_register_not_full_reading():
    j=app.parse_fields([row("BETAR"),row("00123 m3",y=80)])
    assert j["reading"] is None and j["reading_confidence"]==0

def test_no_unknown_scale():
    assert app.parse_fields([row("00123456 m3")])["reading"] is None

def test_conflicting_brands():
    assert app.parse_fields([row("BETAR NORMA"),row("00123456 m3")])==app.empty()

def test_serial_without_label_betar():
    j=app.parse_fields([row("BETAR",.9),row("12345678",.97,y=80),row("00123456 m3",.98,y=160)])
    assert j["serial_number"]=="12345678" and j["serial_confidence"]==.9

def test_ambiguous_serial():
    j=app.parse_fields([row("BETAR"),row("12345678",y=80),row("87654321",y=160)])
    assert j["serial_number"] is None

@pytest.mark.parametrize("raw",["00123456","00123,456","00123.456","00123-456"])
@pytest.mark.parametrize("profile",list(PROFILES))
def test_format(profile,raw):
    assert normalize_display(raw,profile)["value"]=="00123.456"

@pytest.mark.parametrize("raw",["1234567","123456789","00O23456"])
def test_missing_digits(raw):
    assert not normalize_display(raw,"betar_5_3")["valid"]

def test_weakest_link():
    assert field_score({"value":"x","confidence":.95},.6)==.6
    assert field_score({"value":None,"confidence":.99},.9)==0
    assert field_score({"value":"x","confidence":.99},.9,False)==0
