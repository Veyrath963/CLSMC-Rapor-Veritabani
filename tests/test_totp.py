from clsmc.security import generate_totp_secret, totp_code, verify_totp


def test_totp_roundtrip():
    secret = generate_totp_secret()
    code = totp_code(secret)
    assert verify_totp(secret, code)
    assert not verify_totp(secret, "000")
