import base64
import json
import tempfile
from pathlib import Path

import pytest

tornado_testing = pytest.importorskip("tornado.testing")

import settings
import security_utils


class SettingsApiSecurityTest(tornado_testing.AsyncHTTPTestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.app_root = Path(self.tmpdir.name)
        self.original_get_app_root = settings.util.get_app_root
        self.original_launch_maxbot = settings.launch_maxbot
        self.original_requests_post = settings.requests.post
        settings.util.get_app_root = lambda: str(self.app_root)
        settings.launch_maxbot = lambda: None
        settings.GLOBAL_SERVER_SHUTDOWN = False
        super().setUp()

    def tearDown(self):
        super().tearDown()
        settings.util.get_app_root = self.original_get_app_root
        settings.launch_maxbot = self.original_launch_maxbot
        settings.requests.post = self.original_requests_post
        self.tmpdir.cleanup()

    def get_app(self):
        return settings.make_application(ocr=None)

    def get_token(self):
        response = self.fetch("/load")
        assert response.code == 200
        data = json.loads(response.body.decode("utf-8"))
        return data["_security"]["local_api_token"]

    def auth_headers(self):
        return {"X-Tickets-Hunter-Token": self.get_token()}

    def test_load_returns_loopback_token_metadata(self):
        response = self.fetch("/load")

        assert response.code == 200
        data = json.loads(response.body.decode("utf-8"))
        assert data["_security"]["local_api_token"]
        assert data["_security"]["bind_host"] == security_utils.LOCAL_BIND_HOST

    def test_mutation_endpoints_reject_missing_token(self):
        for endpoint in [
            "/save",
            "/reset",
            "/run",
            "/pause",
            "/resume",
            "/shutdown",
            "/sendkey",
            "/ocr",
            "/test_discord_webhook",
            "/test_telegram",
        ]:
            response = self.fetch(endpoint, method="POST", body="{}", raise_error=False)
            assert response.code == 403, endpoint

    def test_control_endpoints_accept_post_and_protect_get_compatibility(self):
        token = self.get_token()
        headers = {"X-Tickets-Hunter-Token": token}
        for endpoint in ["/reset", "/run", "/pause", "/resume", "/shutdown"]:
            response = self.fetch(endpoint, method="POST", body="", headers=headers, raise_error=False)
            assert response.code == 200, endpoint

        get_response = self.fetch("/run", headers=headers, raise_error=False)
        assert get_response.code == 200
        assert get_response.headers.get("X-Tickets-Hunter-Deprecated") == "use POST /run"

    def test_save_migrates_plaintext_secrets_and_load_hydrates_them(self):
        config = settings.get_default_config()
        config["homepage"] = "https://kktix.com/events/example"
        config["accounts"]["kktix_password"] = "secret-password"
        config["accounts"]["tixcraft_sid"] = "sid-secret-value"
        config["advanced"]["telegram_bot_token"] = "123456:ABCdefghijklmnopqrstuvwxyz_123"

        response = self.fetch(
            "/save",
            method="POST",
            body=json.dumps(config),
            headers=self.auth_headers(),
            raise_error=False,
        )
        assert response.code == 200

        stored_config = json.loads((self.app_root / settings.CONST_MAXBOT_CONFIG_FILE).read_text())
        assert stored_config["accounts"]["kktix_password"] == ""
        assert stored_config["accounts"]["tixcraft_sid"] == ""
        assert stored_config["advanced"]["telegram_bot_token"] == ""
        assert "secret-password" not in (self.app_root / settings.CONST_MAXBOT_CONFIG_FILE).read_text()

        load_response = self.fetch("/load")
        hydrated = json.loads(load_response.body.decode("utf-8"))
        assert hydrated["accounts"]["kktix_password"] == "secret-password"
        assert hydrated["accounts"]["tixcraft_sid"] == "sid-secret-value"
        assert hydrated["advanced"]["telegram_bot_token"] == "123456:ABCdefghijklmnopqrstuvwxyz_123"

    def test_existing_plaintext_settings_are_migrated_on_load(self):
        config = settings.get_default_config()
        config["accounts"]["fami_password"] = "legacy-secret"
        (self.app_root / settings.CONST_MAXBOT_CONFIG_FILE).write_text(json.dumps(config), encoding="utf-8")

        response = self.fetch("/load")

        assert response.code == 200
        hydrated = json.loads(response.body.decode("utf-8"))
        assert hydrated["accounts"]["fami_password"] == "legacy-secret"
        stored_config = json.loads((self.app_root / settings.CONST_MAXBOT_CONFIG_FILE).read_text())
        assert stored_config["accounts"]["fami_password"] == ""

    def test_malformed_config_is_rejected(self):
        config = settings.get_default_config()
        config["homepage"] = "javascript:alert(1)"

        response = self.fetch(
            "/save",
            method="POST",
            body=json.dumps(config),
            headers=self.auth_headers(),
            raise_error=False,
        )

        assert response.code == 400
        assert b"homepage must be about:blank" in response.body

    def test_ocr_rejects_invalid_and_oversized_payloads(self):
        headers = self.auth_headers()
        invalid_response = self.fetch(
            "/ocr",
            method="POST",
            body=json.dumps({"image_data": "not valid base64"}),
            headers=headers,
            raise_error=False,
        )
        assert invalid_response.code == 400

        oversized = base64.b64encode(b"x" * (security_utils.MAX_OCR_IMAGE_BYTES + 1)).decode("ascii")
        oversized_response = self.fetch(
            "/ocr",
            method="POST",
            body=json.dumps({"image_data": oversized}),
            headers=headers,
            raise_error=False,
        )
        assert oversized_response.code == 400

    def test_sendkey_rejects_path_traversal_token(self):
        response = self.fetch(
            "/sendkey",
            method="POST",
            body=json.dumps({"token": "../escape"}),
            headers=self.auth_headers(),
            raise_error=False,
        )

        assert response.code == 400
        assert not (self.app_root.parent / "escape.tmp").exists()

    def test_notification_test_errors_redact_webhook_and_bot_token(self):
        webhook_url = "https://discord.com/api/webhooks/123456/abcdef-secret"
        bot_token = "123456:ABCdefghijklmnopqrstuvwxyz_123"

        def failing_post(url, **kwargs):
            raise settings.requests.RequestException(f"failed for {url} using {webhook_url} and {bot_token}")

        settings.requests.post = failing_post

        discord_response = self.fetch(
            "/test_discord_webhook",
            method="POST",
            body=json.dumps({"webhook_url": webhook_url}),
            headers=self.auth_headers(),
            raise_error=False,
        )
        telegram_response = self.fetch(
            "/test_telegram",
            method="POST",
            body=json.dumps({"bot_token": bot_token, "chat_id": "123456"}),
            headers=self.auth_headers(),
            raise_error=False,
        )

        combined = discord_response.body.decode("utf-8") + telegram_response.body.decode("utf-8")
        assert "abcdef-secret" not in combined
        assert bot_token not in combined
        assert "***" in combined
