"""Explicit display layouts; never restore missing OCR digits by zero-padding."""
import re

PROFILES = {
    "betar_5_3": {"title": "БЕТАР СГВ-15 / СХВ-15 — табло 5+3",
                   "integer_digits": 5, "fraction_digits": 3,
                   "source": "https://shopbetar.ru/upload/iblock/9b7/9b78021dfd35a90d4cbec2cc2712c3d7.PDF"},
    "norma_5_3": {"title": "НОРМА СВКМ-15 — табло 5+3",
                   "integer_digits": 5, "fraction_digits": 3,
                   "source": "https://normais.nt-rt.ru/images/manuals/1.pdf"},
    "ekomera_5_3": {"title": "ЭКОМЕРА ЭКО-15 — табло 5+3",
                     "integer_digits": 5, "fraction_digits": 3,
                     "source": "https://ekomera.ru/wp-content/uploads/2023/10/Паспорт-ЭКОМЕРА-15-50новый.pdf"},
    "generic_5_3": {"title": "Вручную подтверждено: 5 чёрных + 3 красных",
                      "integer_digits": 5, "fraction_digits": 3, "source": None},
}
# All profiles apply to the stated display variant, not every production year or meter revision.
def detect_profile(lines):
    text = " ".join(x["text"] for x in lines).upper()
    found = []
    if re.search(r"БЕТАР|BETAR|[S56Б]ETAP|[СC][ГGCFХX]?[ВB][ -]?15|CFB[ -]?15|CXB[ -]?15", text):
        found.append("betar_5_3")
    if re.search(r"НОРМА|NORMA|HOPMA|[СC][ВB]КМ|CBKM", text):
        found.append("norma_5_3")
    if re.search(r"ЭКОМЕРА|EKOMERA|MEPA|ЭКО[ -]?15|3KO[ -]?15", text):
        found.append("ekomera_5_3")
    return found[0] if len(found) == 1 else None, found

def normalize_display(raw, profile_id):
    p = PROFILES[profile_id]
    # Remove unit suffix only. Do not silently turn letters into digits.
    raw = re.sub(r"\s*[mм][³3]?\s*$", "", raw, flags=re.I).strip()
    if not re.fullmatch(r"[0-9\s.,\-]+", raw):
        return {"valid": False, "reason": "non_numeric_display"}
    digits = re.sub(r"[^0-9]", "", raw)
    n, d = p["integer_digits"], p["fraction_digits"]
    if len(digits) == n + d:
        return {"valid": True, "value": digits[:n]+"."+digits[n:],
                "display_value": digits[:n]+","+digits[n:],
                "integer_m3": str(int(digits[:n])), "fraction_m3": "0."+digits[n:],
                "completeness": "full_digit_register", "raw_digits": digits}
    if len(digits) == n:
        return {"valid": True, "value": digits, "display_value": digits,
                "integer_m3": str(int(digits)), "fraction_m3": None,
                "completeness": "integer_only", "raw_digits": digits}
    return {"valid": False, "reason": "digit_count_mismatch",
            "observed_digits": len(digits), "expected_digits": [n, n+d]}

def unit_near(line, lines):
    box = line["box"]
    left, right = min(x for x,y in box), max(x for x,y in box)
    top, bottom = min(y for x,y in box), max(y for x,y in box)
    h = max(1, bottom-top)
    if re.search(r"[mм][³3]\s*$", line["text"], re.I):
        return True
    for other in lines:
        if re.fullmatch(r"[mм](?:[³3])?", other["text"].strip(), re.I):
            ox = min(x for x,y in other["box"])
            oy = sum(y for x,y in other["box"])/4
            if 0 <= ox-right <= 3*h and top-h <= oy <= bottom+h:
                return True
    return False

def register_lines(lines):
    """Also group split numeric chunks on one baseline, never across arbitrary rows."""
    result = list(lines)
    for a in lines:
        if not re.fullmatch(r"[\d.,\- ]+", a["text"].strip()):
            continue
        ax = max(x for x,y in a["box"]); ay=sum(y for x,y in a["box"])/4
        ah=max(y for x,y in a["box"])-min(y for x,y in a["box"])
        for b in lines:
            if a is b or not re.fullmatch(r"[\d.,\- ]+(?:\s*[mм][³3]?)?",b["text"].strip(), re.I):
                continue
            bx=min(x for x,y in b["box"]); by=sum(y for x,y in b["box"])/4
            bh=max(y for x,y in b["box"])-min(y for x,y in b["box"])
            if 0 <= bx-ax <= max(ah,bh)*1.6 and abs(ay-by)<=max(ah,bh)*.45:
                ps=a["box"]+b["box"];x1=min(x for x,y in ps);x2=max(x for x,y in ps)
                y1=min(y for x,y in ps);y2=max(y for x,y in ps)
                result.append({"text":a["text"]+b["text"],"confidence":min(a["confidence"],b["confidence"]),
                               "box":[[x1,y1],[x2,y1],[x2,y2],[x1,y2]], "merged":True})
    return result

def extract_profile_reading(lines, profile_id, explicit=False):
    candidates=[]; rejected=[]
    for row in register_lines(lines):
        raw=row["text"].strip()
        # Only an isolated register line; specifications, dates and serial labels excluded.
        if not re.fullmatch(r"[\d.,\- ]+(?:\s*[mм][³3]?)?",raw,re.I):
            continue
        if not explicit and not unit_near(row,lines):
            continue
        parsed=normalize_display(raw,profile_id)
        item={**row,**parsed}
        if parsed["valid"]: candidates.append(item)
        else: rejected.append(item)
    unique={}
    for c in candidates:
        old=unique.get(c["value"])
        if old is None or old["confidence"]<c["confidence"]:unique[c["value"]]=c
    candidates=list(unique.values())
    # A combined 8-digit register supersedes the same 5-digit integer subregion.
    complete=[c for c in candidates if c["completeness"]=="full_digit_register"]
    if len(complete)==1:
        candidates=[c for c in candidates if c["completeness"]=="full_digit_register" or
                    c["raw_digits"]!=complete[0]["raw_digits"][:5]]
    eligible=[c for c in candidates if c["confidence"]>=.65]
    chosen=eligible[0] if len(eligible)==1 else None
    return {"value":chosen["value"] if chosen else None,
            "display_value":chosen["display_value"] if chosen else None,
            "integer_m3":chosen["integer_m3"] if chosen else None,
            "fraction_m3":chosen["fraction_m3"] if chosen else None,
            "completeness":chosen["completeness"] if chosen else "unresolved",
            "confidence":chosen["confidence"] if chosen else None,
            "profile":profile_id, "format":"5+3", "decimal_places":3,
            "source":"selected_region" if explicit else "profile_and_geometry",
            "needs_review":True, "candidates":candidates[:20], "rejected":rejected[:20]}
