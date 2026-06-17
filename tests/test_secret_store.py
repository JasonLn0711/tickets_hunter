import json
import stat

import secret_store


def test_store_and_sanitize_moves_secrets_to_permission_restricted_file(tmp_path):
    config = {
        "accounts": {
            "kktix_password": "secret-password",
            "kktix_account": "user@example.com",
        },
        "advanced": {
            "telegram_bot_token": "123456:ABCdefghijklmnopqrstuvwxyz_123",
        },
    }

    sanitized = secret_store.store_and_sanitize(config, str(tmp_path), clear_empty=True)

    assert sanitized["accounts"]["kktix_password"] == ""
    assert sanitized["accounts"]["kktix_account"] == "user@example.com"
    assert sanitized["advanced"]["telegram_bot_token"] == ""
    secret_path = tmp_path / secret_store.SECRET_STORE_FILENAME
    stored = json.loads(secret_path.read_text())
    assert stored["accounts.kktix_password"] == "secret-password"
    assert stat.S_IMODE(secret_path.stat().st_mode) == 0o600


def test_hydrate_restores_secrets_without_changing_preferences(tmp_path):
    config = {
        "accounts": {
            "kktix_password": "",
            "kktix_account": "user@example.com",
        },
        "advanced": {
            "telegram_bot_token": "",
        },
    }
    store = secret_store.LocalSecretStore(str(tmp_path))
    store.set_many({
        "accounts.kktix_password": "secret-password",
        "advanced.telegram_bot_token": "123456:ABCdefghijklmnopqrstuvwxyz_123",
    })

    hydrated = secret_store.hydrate(config, str(tmp_path))

    assert hydrated["accounts"]["kktix_password"] == "secret-password"
    assert hydrated["accounts"]["kktix_account"] == "user@example.com"
    assert hydrated["advanced"]["telegram_bot_token"] == "123456:ABCdefghijklmnopqrstuvwxyz_123"
