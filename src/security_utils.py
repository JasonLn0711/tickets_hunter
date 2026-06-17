import copy
import hmac
import ipaddress
import os
import re
import secrets
from typing import Any, Dict, Iterable, Tuple
from urllib.parse import urlparse


LOCAL_BIND_HOST = "127.0.0.1"
MAX_JSON_BODY_BYTES = 1024 * 1024
MAX_CONFIG_STRING_LENGTH = 32768
MAX_OCR_IMAGE_BYTES = 2 * 1024 * 1024
SAFE_TMP_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
TELEGRAM_TOKEN_RE = re.compile(r"^\d+:[A-Za-z0-9_-]+$")
DISCORD_WEBHOOK_HOSTS = ("discord.com", "discordapp.com")
DISCORD_WEBHOOK_RE = re.compile(r"https://(?:discord(?:app)?\.com)/api/webhooks/[^\s\"']+")
TELEGRAM_TOKEN_SEARCH_RE = re.compile(r"\b\d{5,}:[A-Za-z0-9_-]{20,}\b")
SESSION_LIKE_RE = re.compile(r"(?i)\b(sid|session|cookie|token|password|webhook)([=:]\s*)([^\s,;\"']{8,})")


class ConfigValidationError(ValueError):
    def __init__(self, errors: Iterable[str]):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


def new_local_api_token() -> str:
    return secrets.token_urlsafe(32)


def is_loopback_address(remote_ip: str) -> bool:
    try:
        return ipaddress.ip_address(remote_ip).is_loopback
    except ValueError:
        return remote_ip in {"localhost"}


def token_matches(provided_token: str, expected_token: str) -> bool:
    if not provided_token or not expected_token:
        return False
    return hmac.compare_digest(provided_token, expected_token)


def build_safe_tmp_path(app_root: str, token: str) -> str:
    if not SAFE_TMP_TOKEN_RE.fullmatch(token or ""):
        raise ValueError("token must contain only A-Z, a-z, 0-9, _ or - and be at most 128 characters")

    app_root_abs = os.path.abspath(app_root)
    tmp_path = os.path.abspath(os.path.join(app_root_abs, token + ".tmp"))
    if os.path.commonpath([app_root_abs, tmp_path]) != app_root_abs:
        raise ValueError("token resolves outside the application directory")
    return tmp_path


def validate_config(config_dict: Dict[str, Any], default_config: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(config_dict, dict):
        raise ConfigValidationError(["config must be a JSON object"])

    errors = []
    normalized = copy.deepcopy(config_dict)
    _validate_node(normalized, default_config, "", errors)
    _validate_semantics(normalized, errors)
    if errors:
        raise ConfigValidationError(errors)
    return normalized


def _validate_node(value: Any, template: Any, path: str, errors: list) -> None:
    label = path or "config"

    if isinstance(template, dict):
        if not isinstance(value, dict):
            errors.append(f"{label} must be an object")
            return

        allowed_keys = set(template.keys())
        for key in value.keys():
            if key not in allowed_keys:
                errors.append(f"{_join_path(path, key)} is not an allowed setting")

        for key, template_value in template.items():
            if key in value:
                _validate_node(value[key], template_value, _join_path(path, key), errors)
        return

    if isinstance(template, bool):
        if not isinstance(value, bool):
            errors.append(f"{label} must be a boolean")
        return

    if isinstance(template, int) and not isinstance(template, bool):
        if not isinstance(value, int) or isinstance(value, bool):
            errors.append(f"{label} must be an integer")
        return

    if isinstance(template, float):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            errors.append(f"{label} must be a number")
        return

    if isinstance(template, str):
        if not isinstance(value, str):
            errors.append(f"{label} must be a string")
            return
        if "\x00" in value:
            errors.append(f"{label} must not contain NUL bytes")
        if len(value) > MAX_CONFIG_STRING_LENGTH:
            errors.append(f"{label} is too long")


def _validate_semantics(config_dict: Dict[str, Any], errors: list) -> None:
    advanced = config_dict.get("advanced", {})
    accounts = config_dict.get("accounts", {})
    ocr_captcha = config_dict.get("ocr_captcha", {})

    homepage = config_dict.get("homepage", "")
    if homepage and homepage != "about:blank":
        parsed_homepage = urlparse(homepage)
        if parsed_homepage.scheme not in {"http", "https"} or not parsed_homepage.netloc:
            errors.append("homepage must be about:blank or an http(s) URL")

    server_port = advanced.get("server_port")
    if isinstance(server_port, int) and not (1024 <= server_port <= 65535):
        errors.append("advanced.server_port must be between 1024 and 65535")

    ticket_number = config_dict.get("ticket_number")
    if isinstance(ticket_number, int) and not (1 <= ticket_number <= 99):
        errors.append("ticket_number must be between 1 and 99")

    webhook_url = advanced.get("discord_webhook_url", "").strip()
    if webhook_url and not is_valid_discord_webhook_url(webhook_url):
        errors.append("advanced.discord_webhook_url must be an HTTPS Discord webhook URL")

    telegram_token = advanced.get("telegram_bot_token", "").strip()
    if telegram_token and not TELEGRAM_TOKEN_RE.fullmatch(telegram_token):
        errors.append("advanced.telegram_bot_token has an invalid format")

    ocr_path = ocr_captcha.get("path", "")
    if isinstance(ocr_path, str) and _looks_like_control_scheme(ocr_path):
        errors.append("ocr_captcha.path must be a filesystem path, not a script or URL scheme")

    for key, value in accounts.items():
        if isinstance(value, str) and len(value) > MAX_CONFIG_STRING_LENGTH:
            errors.append(f"accounts.{key} is too long")


def is_valid_discord_webhook_url(webhook_url: str) -> bool:
    parsed = urlparse(webhook_url)
    if parsed.scheme != "https":
        return False
    if not any(parsed.netloc == host or parsed.netloc.endswith("." + host) for host in DISCORD_WEBHOOK_HOSTS):
        return False
    return parsed.path.startswith("/api/webhooks/")


def _looks_like_control_scheme(value: str) -> bool:
    lowered = value.strip().lower()
    return lowered.startswith(("javascript:", "data:", "http://", "https://", "file://"))


def _join_path(prefix: str, key: str) -> str:
    return key if not prefix else prefix + "." + key


def collect_config_secret_values(config_dict: Dict[str, Any]) -> list:
    secrets = []
    for section in ("accounts", "advanced"):
        values = config_dict.get(section, {})
        if not isinstance(values, dict):
            continue
        for key, value in values.items():
            if not isinstance(value, str) or not value:
                continue
            lowered = key.lower()
            if any(marker in lowered for marker in ("password", "cookie", "token", "webhook", "sid", "qware")):
                secrets.append(value)
    return secrets


def redact_text(text: str, extra_secrets: Iterable[str] = ()) -> str:
    redacted = str(text)
    for secret in sorted({s for s in extra_secrets if isinstance(s, str) and len(s) >= 4}, key=len, reverse=True):
        redacted = redacted.replace(secret, "***")
    redacted = DISCORD_WEBHOOK_RE.sub("https://discord.com/api/webhooks/***", redacted)
    redacted = TELEGRAM_TOKEN_SEARCH_RE.sub("***", redacted)
    redacted = SESSION_LIKE_RE.sub(lambda match: match.group(1) + match.group(2) + "***", redacted)
    return redacted


def safe_zip_member_names(member_names: Iterable[str]) -> Tuple[bool, str]:
    for name in member_names:
        normalized = name.replace("\\", "/")
        if normalized.startswith("/") or normalized.startswith("../") or "/../" in normalized:
            return False, name
        if normalized in {"..", "."}:
            return False, name
        parts = [part for part in normalized.split("/") if part]
        if any(part == ".." for part in parts):
            return False, name
    return True, ""
