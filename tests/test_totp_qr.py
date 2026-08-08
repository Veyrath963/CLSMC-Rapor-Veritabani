import base64

from clsmc.security import build_totp_provisioning_uri, generate_qr_svg_data_uri


def test_totp_provisioning_uri_contains_standard_parameters():
    uri = build_totp_provisioning_uri(
        "JBSWY3DPEHPK3PXP",
        "Darius Blackwell",
        issuer="CLSMC Medical Center",
    )
    assert uri.startswith("otpauth://totp/")
    assert "secret=JBSWY3DPEHPK3PXP" in uri
    assert "issuer=CLSMC+Medical+Center" in uri
    assert "digits=6" in uri
    assert "period=30" in uri


def test_qr_svg_data_uri_is_self_contained_svg():
    uri = build_totp_provisioning_uri("JBSWY3DPEHPK3PXP", "Admin")
    data_uri = generate_qr_svg_data_uri(uri)
    prefix = "data:image/svg+xml;base64,"
    assert data_uri.startswith(prefix)
    svg = base64.b64decode(data_uri[len(prefix):])
    assert b"<svg" in svg
    assert len(svg) > 1000
