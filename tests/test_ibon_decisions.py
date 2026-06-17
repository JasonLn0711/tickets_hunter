from platforms.ibon_decisions import detect_ibon_cookie_features, has_ibon_cookie_config


def test_has_ibon_cookie_config_requires_non_empty_cookie():
    assert not has_ibon_cookie_config({"accounts": {"ibonqware": ""}})
    assert not has_ibon_cookie_config({"accounts": {"ibonqware": "x"}})
    assert has_ibon_cookie_config({"accounts": {"ibonqware": "mem_id=123"}})


def test_detect_ibon_cookie_features_is_pure_and_explicit():
    features = detect_ibon_cookie_features(
        "mem_id=123; mem_email=user@example.com; huiwanTK=abc; ibonqwareverify=ok"
    )

    assert features == {
        "mem_id": True,
        "mem_email": True,
        "huiwanTK": True,
        "ibonqwareverify": True,
    }


def test_detect_ibon_cookie_features_handles_missing_values():
    features = detect_ibon_cookie_features(None)

    assert features == {
        "mem_id": False,
        "mem_email": False,
        "huiwanTK": False,
        "ibonqwareverify": False,
    }
