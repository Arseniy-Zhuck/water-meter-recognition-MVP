import re

def extract_field(lines, field, explicit=False, decimal_places=None):
    candidates = []
    for line in lines:
        text = line["text"].strip()
        if field == "reading":
            matches = list(re.finditer(r"(?<![\w])\d{1,10}(?:[.,]\d{1,4})?(?![\w])", text))
        else:
            matches = list(re.finditer(r"(?<![A-Za-z0-9])[A-Za-z]{0,3}\d[A-Za-z0-9\-/]{3,23}(?![A-Za-z0-9])", text))
        for match in matches:
            raw = match.group()
            if field == "reading":
                value = raw.replace(",", ".")
                # A full-image integer could be a model/year/serial, not a reading.
                evidence = bool(re.search(r"m[³3]|м[³3]|reading", text, re.I) or "." in value)
                if re.fullmatch(r"\d{4,10}", raw):
                    xs = [p[0] for p in line["box"]]; ys = [p[1] for p in line["box"]]
                    height = max(ys) - min(ys)
                    for other in lines:
                        if re.fullmatch(r"[mм](?:[³3])?", other["text"].strip(), re.I):
                            ox = min(p[0] for p in other["box"])
                            oy = sum(p[1] for p in other["box"]) / 4
                            if 0 <= ox - max(xs) <= 3 * height and min(ys) - height <= oy <= max(ys) + height:
                                evidence = True
                if decimal_places is not None and explicit:
                    value = value.replace(".", "").zfill(decimal_places + 1)
                    if decimal_places:
                        value = value[:-decimal_places] + "." + value[-decimal_places:]
            else:
                value = raw
                evidence = bool(re.search(r"serial|s/n|no\.?|№|номер", text, re.I))
            candidates.append({**line, "value": value, "raw_value": raw,
                               "evidence": "selected_region" if explicit else
                               "label_or_decimal" if evidence else "unlabelled"})
    # Collapse identical values, but do not choose among conflicting candidates.
    unique = {}
    for c in candidates:
        if c["value"] not in unique or c["confidence"] > unique[c["value"]]["confidence"]:
            unique[c["value"]] = c
    candidates = sorted(unique.values(), key=lambda c: (c["evidence"] != "unlabelled", c["confidence"]), reverse=True)
    eligible = [c for c in candidates if c["evidence"] != "unlabelled" and c["confidence"] >= .65]
    selected = eligible[0] if len(eligible) == 1 else None
    return {"value": selected["value"] if selected else None,
            "confidence": selected["confidence"] if selected else None,
            "source": "selected_region" if explicit else "automatic_heuristic",
            "needs_review": True,
            "candidates": candidates[:20]}
