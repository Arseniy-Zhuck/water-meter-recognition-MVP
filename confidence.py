"""Conservative support score, NOT a calibrated correctness probability."""
import math
from meter_profiles import detect_profile

def score(value):
    try:
        v=float(value)
        return max(0.0,min(1.0,v)) if math.isfinite(v) else 0.0
    except (ValueError,TypeError):
        return 0.0

def profile_support(lines, profile_id, manual=False):
    if manual:
        return 1.0  # User supplied a constraint, not a model prediction.
    supporting=[]
    for line in lines:
        found,_=detect_profile([line])
        if found==profile_id:
            supporting.append(score(line.get("confidence")))
    return max(supporting,default=0.0)

def field_score(field, support=1.0, complete=True):
    if field.get("value") is None or not complete:
        return 0.0
    # Selection ambiguity already produces value=None upstream.
    return round(min(score(field.get("confidence")),score(support)),4)

def compact_result(serial,reading,profile_confidence=1.0,complete=True):
    rc=field_score(reading,profile_confidence,complete)
    sc=field_score(serial)
    return {"serial_number":serial.get("value") if sc else None,
            "serial_confidence":sc,
            "reading":reading.get("value") if rc else None,
            "reading_confidence":rc}
