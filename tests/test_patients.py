from clsmc.services.patients import normalize_birth_date, normalize_identity, normalize_name


def test_patient_normalization():
    assert normalize_identity(" 123 456 ") == "123456"
    assert normalize_name("  Peter   Wellington ") == "peter wellington"
    assert normalize_birth_date("1992-04-17") == "1992-04-17"
    assert normalize_birth_date("17/04/1992") == ""
