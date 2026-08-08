from __future__ import annotations

import json
import re
from datetime import date


REPORT_PATIENT_FIELD_MAP = {
    "vaka": {
        "name": "adsoyad",
        "identity": "kimlik_no",
        "birth_date": "dogum_tarihi",
        "gender": "cinsiyet",
        "phone": "telefon",
        "address": "adres",
        "diagnosis": "tani",
        "treatment": "islemler",
        "medication": None,
        "notes": ("vaka_aciklama", "muayene"),
    },
    "adli": {
        "name": "adli_adsoyad",
        "identity": "adli_kimlik_no",
        "birth_date": "adli_dogum_tarihi",
        "gender": "adli_cinsiyet",
        "phone": "adli_telefon",
        "address": "adli_adres",
        "diagnosis": "adli_yaralanmalar",
        "treatment": "adli_islemler",
        "medication": None,
        "notes": ("adli_olay",),
    },
    "ems": {
        "name": "ems_adsoyad",
        "identity": "ems_kimlik_no",
        "birth_date": "ems_dogum_tarihi",
        "gender": None,
        "phone": None,
        "address": None,
        "diagnosis": "ems_bulgular",
        "treatment": "ems_mudahale",
        "medication": "ems_ilaclar",
        "notes": ("ems_ihbar", "ems_olay_degerlendirme"),
    },
    "ex": {
        "name": "ex_adsoyad",
        "identity": None,
        "birth_date": None,
        "gender": "ex_cinsiyet",
        "phone": None,
        "address": None,
        "diagnosis": "ex_on_neden",
        "treatment": "ex_mudahale",
        "medication": None,
        "notes": ("ex_bulgular",),
    },
    "otopsi": {
        "name": "otp_adsoyad",
        "identity": None,
        "birth_date": None,
        "gender": "otp_cinsiyet",
        "phone": None,
        "address": None,
        "diagnosis": "otp_kesin_neden",
        "treatment": None,
        "medication": None,
        "notes": ("otp_genel_gorunum", "otp_ic_bulgular", "otp_sonuc"),
    },
}

REPORT_PATIENT_BBCODE_LABELS = {
    "vaka": {
        "name": ("Hasta Adı ve Soyadı",),
        "identity": ("Kimlik Numarası",),
        "birth_date": ("Doğum Tarihi",),
        "gender": ("Cinsiyet",),
        "phone": ("Telefon Numarası", "Telefon"),
        "address": ("Adres",),
        "diagnosis": ("Tanı",),
        "treatment": ("Uygulanan İşlemler",),
    },
    "adli": {
        "name": ("Hasta Adı ve Soyadı",),
        "identity": ("Kimlik Numarası",),
        "birth_date": ("Doğum Tarihi",),
        "gender": ("Cinsiyet",),
        "phone": ("Telefon Numarası", "Telefon"),
        "address": ("Adres",),
        "diagnosis": ("Tespit Edilen Yaralanmalar", "Yaralanmalar"),
        "treatment": ("Uygulanan Tıbbi İşlemler",),
    },
    "ems": {
        "name": ("Hastanın Adı ve Soyadı",),
        "identity": ("Kimlik Numarası",),
        "birth_date": ("Doğum Tarihi",),
        "diagnosis": ("Bulgular", "Klinik Bulgular"),
        "treatment": ("Uygulanan Müdahaleler",),
        "medication": ("Uygulanan İlaçlar",),
    },
    "ex": {
        "name": ("Hastanın Adı ve Soyadı",),
        "gender": ("Cinsiyet",),
        "diagnosis": ("Ön Ölüm Nedeni",),
        "treatment": ("Uygulanan Müdahaleler", "Müdahaleler"),
    },
    "otopsi": {
        "name": ("Adı ve Soyadı",),
        "gender": ("Cinsiyet",),
        "diagnosis": ("Kesin Ölüm Nedeni",),
    },
}


def normalize_person_name(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).casefold()


def safe_form_data(raw) -> dict:
    if isinstance(raw, dict):
        return dict(raw)
    try:
        parsed = json.loads(raw or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def clean_value(value) -> str:
    raw = re.sub(r"\s+", " ", str(value or "").strip())
    if raw in {"", "—", "-", "Bulunmuyor / —", "Bulunmuyor"}:
        return ""
    return raw


def normalize_birth_date_any(value: str | None) -> str:
    raw = clean_value(value)
    if not raw:
        return ""
    try:
        return date.fromisoformat(raw).isoformat()
    except ValueError:
        pass
    for separator in (".", "/", "-"):
        parts = raw.split(separator)
        if len(parts) == 3 and len(parts[0]) <= 2:
            try:
                day, month, year = [int(part) for part in parts]
                return date(year, month, day).isoformat()
            except (TypeError, ValueError):
                continue
    return ""


def _plain_bbcode_lines(bbcode: str | None) -> list[str]:
    plain = re.sub(r"\[[^\]]+\]", "", bbcode or "")
    return [line.strip() for line in plain.replace("\r", "\n").split("\n")]


def extract_bbcode_value(bbcode: str | None, labels: tuple[str, ...]) -> str:
    lines = _plain_bbcode_lines(bbcode)
    normalized_labels = {
        re.sub(r"\s+", " ", label.strip().rstrip(":")).casefold()
        for label in labels
    }
    for index, line in enumerate(lines):
        candidate = re.sub(r"\s+", " ", line.strip().rstrip(":")).casefold()
        if candidate not in normalized_labels:
            continue
        for next_line in lines[index + 1:]:
            value = clean_value(next_line)
            if value:
                return value
    return ""


def _form_value(data: dict, key: str | None) -> str:
    return clean_value(data.get(key, "")) if key else ""


def extract_report_patient_snapshot(report_type: str, form_data, bbcode: str | None = None) -> dict:
    data = safe_form_data(form_data)
    field_map = REPORT_PATIENT_FIELD_MAP.get(report_type, {})
    label_map = REPORT_PATIENT_BBCODE_LABELS.get(report_type, {})

    def resolve(logical_name: str) -> str:
        value = _form_value(data, field_map.get(logical_name))
        if value:
            return value
        labels = label_map.get(logical_name, ())
        return extract_bbcode_value(bbcode, labels) if labels else ""

    notes = []
    for key in field_map.get("notes", ()):
        value = _form_value(data, key)
        if value and value not in notes:
            notes.append(value)

    snapshot = {
        "full_name": resolve("name"),
        "identity_number": re.sub(r"\s+", "", resolve("identity")),
        "date_of_birth": normalize_birth_date_any(resolve("birth_date")),
        "gender": resolve("gender"),
        "phone": resolve("phone"),
        "address": resolve("address"),
        "diagnosis": resolve("diagnosis"),
        "treatment": resolve("treatment"),
        "medication": resolve("medication"),
        "clinical_note": "\n\n".join(notes),
    }
    return snapshot


def has_meaningful_clinical_content(snapshot: dict) -> bool:
    return any(
        clean_value(snapshot.get(key))
        for key in ("diagnosis", "treatment", "medication", "clinical_note")
    )
