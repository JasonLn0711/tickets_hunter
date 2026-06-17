from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_tls_verification_is_not_globally_disabled():
    source = read("src/nodriver_tixcraft.py")

    assert "ssl._create_default_https_context" not in source
    assert "create_unverified_context" not in source
    assert "InsecureRequestWarning" not in source


def test_settings_server_binds_to_loopback_only():
    source = read("src/settings.py")

    assert "app.listen(server_port, address=security_utils.LOCAL_BIND_HOST)" in source


def test_mutation_endpoints_require_local_token():
    source = read("src/settings.py")

    for class_name in [
        "ShutdownHandler",
        "PauseHandler",
        "ResumeHandler",
        "RunHandler",
        "ResetJsonHandler",
        "SaveJsonHandler",
        "SendkeyHandler",
        "TestDiscordWebhookHandler",
        "TestTelegramHandler",
        "OcrHandler",
    ]:
        assert f"class {class_name}(LocalMutationHandler)" in source


def test_wildcard_cors_removed_from_local_control_handlers():
    source = read("src/settings.py")

    assert 'Access-Control-Allow-Origin", "*"' not in source
    assert "Access-Control-Allow-Origin', '*'" not in source


def test_frontend_installs_local_api_token():
    source = read("src/www/settings.js")

    assert "X-Tickets-Hunter-Token" in source
    assert "installLocalApiToken(data._security.local_api_token)" in source
    assert "delete data._security" in source


def test_frontend_uses_post_for_state_changing_controls():
    source = read("src/www/settings.js")

    for function_name in [
        "maxbot_reset_api",
        "maxbot_run_api",
        "maxbot_shutdown_api",
        "maxbot_pause_api",
        "maxbot_resume_api",
    ]:
        function_body = source.split(f"function {function_name}", 1)[1].split("\n}", 1)[0]
        assert "$.post" in function_body
        assert "$.get" not in function_body


def test_frontend_scope_controls_avoid_evasion_language():
    combined = read("src/www/settings.html") + "\n" + read("src/www/settings.js")

    assert "scope-control-notice" in combined
    assert "個人合法使用" in combined
    assert "personal lawful use" in combined
    assert "different networks" not in combined
    assert "分散風險" not in combined


def test_downloader_uses_safe_zip_extraction():
    source = read("src/chrome_downloader.py")

    assert "safe_extract_zip(zip_file, download_dir)" in source
    assert "url.replace(\"https://\", \"http://\")" not in source
