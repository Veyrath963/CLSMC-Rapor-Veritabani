from clsmc.services.report_patients import (
    extract_report_patient_snapshot,
    normalize_person_name,
)


def test_normalize_person_name_ignores_case_and_extra_spaces():
    assert normalize_person_name("  Peter   Wellington ") == "peter wellington"
    assert normalize_person_name("PETER WELLINGTON") == "peter wellington"


def test_old_vaka_can_extract_name_without_identity():
    bbcode = """
[b]Hasta Adı ve Soyadı:[/b]
Peter Wellington

[b]Tanı:[/b]
Üst solunum yolu enfeksiyonu
"""
    snapshot = extract_report_patient_snapshot("vaka", {}, bbcode)
    assert snapshot["full_name"] == "Peter Wellington"
    assert snapshot["identity_number"] == ""
    assert snapshot["diagnosis"] == "Üst solunum yolu enfeksiyonu"


def test_old_ex_and_autopsy_names_are_extractable_without_identity():
    ex_snapshot = extract_report_patient_snapshot(
        "ex",
        {},
        "[b]Hastanın Adı ve Soyadı:[/b]\nJohn Carter\n[b]Ön Ölüm Nedeni:[/b]\nTravma",
    )
    autopsy_snapshot = extract_report_patient_snapshot(
        "otopsi",
        {},
        "[b]Adı ve Soyadı:[/b]\nJohn Carter\n[b]Kesin Ölüm Nedeni:[/b]\nTravma",
    )
    assert ex_snapshot["full_name"] == "John Carter"
    assert autopsy_snapshot["full_name"] == "John Carter"
    assert not ex_snapshot["identity_number"]
    assert not autopsy_snapshot["identity_number"]


def test_birth_date_from_bbcode_is_normalized():
    snapshot = extract_report_patient_snapshot(
        "ems",
        {},
        "[b]Hastanın Adı ve Soyadı:[/b]\nJane Doe\n[b]Doğum Tarihi:[/b]\n17.04.1992",
    )
    assert snapshot["date_of_birth"] == "1992-04-17"
