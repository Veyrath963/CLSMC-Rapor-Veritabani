from __future__ import annotations

import re
from datetime import date


def normalize_name(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).casefold()


def normalize_identity(value: str | None) -> str:
    return re.sub(r"\s+", "", (value or "").strip())


def normalize_birth_date(value: str | None) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    try:
        return date.fromisoformat(raw).isoformat()
    except ValueError:
        return ""


def duplicate_patient_query(model, identity_number: str, full_name: str, date_of_birth: str, exclude_id=None):
    query = model.query
    if exclude_id is not None:
        query = query.filter(model.id != exclude_id)
    if identity_number:
        match = query.filter(model.identity_number == identity_number).first()
        if match:
            return match
    if full_name and date_of_birth:
        for item in query.filter(model.date_of_birth == date_of_birth).all():
            if normalize_name(item.full_name) == normalize_name(full_name):
                return item
    return None


def patient_payload(patient) -> dict:
    return {
        "id": patient.id,
        "patient_number": patient.patient_number,
        "full_name": patient.full_name,
        "identity_number": patient.identity_number or "",
        "date_of_birth": patient.date_of_birth or "",
        "gender": patient.gender or "",
        "phone": patient.phone or "",
        "address": patient.address or "",
        "clinical_priority": getattr(patient, "clinical_priority", "stable") or "stable",
    }
