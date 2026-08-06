from clsmc.security import generate_totp_secret, verify_totp


def test_totp_secret_has_expected_length():
    assert len(generate_totp_secret()) >= 16


def test_invalid_totp_is_rejected():
    assert verify_totp("JBSWY3DPEHPK3PXP", "000000", at_time=0) is False
