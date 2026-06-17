from pathlib import Path

import pytest

import security_utils


def sample_config():
    return {
        "homepage": "https://kktix.com/events/example",
        "ticket_number": 2,
        "advanced": {
            "server_port": 16888,
            "discord_webhook_url": "",
            "telegram_bot_token": "",
        },
        "accounts": {
            "kktix_account": "",
            "kktix_password": "",
        },
        "ocr_captcha": {
            "path": "assets/model/universal",
        },
    }


def test_validate_config_accepts_matching_shape():
    config = sample_config()

    assert security_utils.validate_config(config, sample_config()) == config


def test_validate_config_rejects_unknown_keys():
    config = sample_config()
    config["backdoor"] = True

    with pytest.raises(security_utils.ConfigValidationError) as exc:
        security_utils.validate_config(config, sample_config())

    assert "backdoor is not an allowed setting" in str(exc.value)


def test_validate_config_rejects_script_homepage():
    config = sample_config()
    config["homepage"] = "javascript:alert(1)"

    with pytest.raises(security_utils.ConfigValidationError) as exc:
        security_utils.validate_config(config, sample_config())

    assert "homepage must be about:blank or an http(s) URL" in str(exc.value)


def test_validate_config_rejects_invalid_port():
    config = sample_config()
    config["advanced"]["server_port"] = 80

    with pytest.raises(security_utils.ConfigValidationError) as exc:
        security_utils.validate_config(config, sample_config())

    assert "advanced.server_port must be between 1024 and 65535" in str(exc.value)


def test_build_safe_tmp_path_accepts_safe_token(tmp_path):
    tmp_file = security_utils.build_safe_tmp_path(str(tmp_path), "token_123-OK")

    assert Path(tmp_file).parent == tmp_path
    assert Path(tmp_file).name == "token_123-OK.tmp"


def test_build_safe_tmp_path_rejects_path_traversal(tmp_path):
    with pytest.raises(ValueError):
        security_utils.build_safe_tmp_path(str(tmp_path), "../settings")


def test_safe_zip_member_names_rejects_traversal():
    is_safe, unsafe_name = security_utils.safe_zip_member_names(["chrome/chrome.exe", "../evil.exe"])

    assert not is_safe
    assert unsafe_name == "../evil.exe"


def test_token_matches_uses_exact_token():
    expected = security_utils.new_local_api_token()

    assert security_utils.token_matches(expected, expected)
    assert not security_utils.token_matches(expected + "x", expected)


def test_redact_text_masks_known_secret_values_and_tokens():
    text = (
        "password=secret-password "
        "https://discord.com/api/webhooks/123456/abcdef "
        "telegram 123456:ABCdefghijklmnopqrstuvwxyz_123"
    )

    redacted = security_utils.redact_text(text, ["secret-password"])

    assert "secret-password" not in redacted
    assert "abcdef" not in redacted
    assert "ABCdefghijklmnopqrstuvwxyz_123" not in redacted
    assert "password=***" in redacted
