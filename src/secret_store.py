import json
import os
import stat
from copy import deepcopy
from typing import Any, Dict, Iterable, Optional, Tuple


SECRET_STORE_FILENAME = "secrets.local.json"
KEYRING_SERVICE = "tickets_hunter"
SECRET_FIELD_PATHS = (
    ("accounts", "tixcraft_sid"),
    ("accounts", "ibonqware"),
    ("accounts", "funone_session_cookie"),
    ("accounts", "fansigo_cookie"),
    ("advanced", "discord_webhook_url"),
    ("advanced", "telegram_bot_token"),
)


def is_secret_path(path: Tuple[str, str]) -> bool:
    section, key = path
    if (section, key) in SECRET_FIELD_PATHS:
        return True
    return section == "accounts" and (key.endswith("_password") or key.endswith("_sid") or key.endswith("_cookie"))


def iter_secret_paths(config_dict: Dict[str, Any]) -> Iterable[Tuple[str, str]]:
    for section, value in config_dict.items():
        if not isinstance(value, dict):
            continue
        for key in value:
            path = (section, key)
            if is_secret_path(path):
                yield path


def dotted(path: Tuple[str, str]) -> str:
    return ".".join(path)


def get_nested(config_dict: Dict[str, Any], path: Tuple[str, str]) -> Any:
    section, key = path
    value = config_dict.get(section, {})
    if isinstance(value, dict):
        return value.get(key)
    return None


def set_nested(config_dict: Dict[str, Any], path: Tuple[str, str], value: str) -> None:
    section, key = path
    if section not in config_dict or not isinstance(config_dict[section], dict):
        config_dict[section] = {}
    config_dict[section][key] = value


def sanitize_config(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    sanitized = deepcopy(config_dict)
    for path in iter_secret_paths(sanitized):
        value = get_nested(sanitized, path)
        if isinstance(value, str) and value:
            set_nested(sanitized, path, "")
    return sanitized


class LocalSecretStore:
    def __init__(self, app_root: str):
        self.app_root = os.path.abspath(app_root)
        self.path = os.path.join(self.app_root, SECRET_STORE_FILENAME)

    def load(self) -> Dict[str, str]:
        if not os.path.exists(self.path):
            return {}
        try:
            with open(self.path, encoding="utf-8") as infile:
                data = json.load(infile)
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(data, dict):
            return {}
        return {str(k): str(v) for k, v in data.items() if isinstance(v, str) and v}

    def save(self, data: Dict[str, str]) -> None:
        tmp_path = self.path + ".tmp"
        os.makedirs(self.app_root, exist_ok=True)
        with open(tmp_path, "w", encoding="utf-8") as outfile:
            json.dump(data, outfile, indent=2, sort_keys=True)
        os.chmod(tmp_path, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(tmp_path, self.path)
        os.chmod(self.path, stat.S_IRUSR | stat.S_IWUSR)

    def set_many(self, values: Dict[str, str]) -> None:
        data = self.load()
        data.update({k: v for k, v in values.items() if v})
        self.save(data)

    def delete_many(self, keys: Iterable[str]) -> None:
        data = self.load()
        for key in keys:
            data.pop(key, None)
        self.save(data)

    def get(self, key: str) -> Optional[str]:
        return self.load().get(key)

    def clear(self) -> None:
        try:
            os.remove(self.path)
        except FileNotFoundError:
            pass


class OptionalKeyringStore:
    def __init__(self, app_root: str):
        self.local = LocalSecretStore(app_root)
        try:
            import keyring  # type: ignore
        except Exception:
            keyring = None
        self.keyring = keyring

    def set_many(self, values: Dict[str, str]) -> None:
        if self.keyring is None:
            self.local.set_many(values)
            return
        failed = {}
        for key, value in values.items():
            try:
                self.keyring.set_password(KEYRING_SERVICE, key, value)
            except Exception:
                failed[key] = value
        if failed:
            self.local.set_many(failed)

    def delete_many(self, keys: Iterable[str]) -> None:
        keys = list(keys)
        if self.keyring is not None:
            for key in keys:
                try:
                    self.keyring.delete_password(KEYRING_SERVICE, key)
                except Exception:
                    pass
        self.local.delete_many(keys)

    def get(self, key: str) -> Optional[str]:
        if self.keyring is not None:
            try:
                value = self.keyring.get_password(KEYRING_SERVICE, key)
                if value:
                    return value
            except Exception:
                pass
        return self.local.get(key)

    def clear(self, paths: Iterable[Tuple[str, str]]) -> None:
        if self.keyring is not None:
            for path in paths:
                try:
                    self.keyring.delete_password(KEYRING_SERVICE, dotted(path))
                except Exception:
                    pass
        self.local.clear()


def get_store(app_root: str) -> OptionalKeyringStore:
    return OptionalKeyringStore(app_root)


def collect_non_empty_secrets(config_dict: Dict[str, Any]) -> Dict[str, str]:
    values = {}
    for path in iter_secret_paths(config_dict):
        value = get_nested(config_dict, path)
        if isinstance(value, str) and value:
            values[dotted(path)] = value
    return values


def store_and_sanitize(config_dict: Dict[str, Any], app_root: str, clear_empty: bool = False) -> Dict[str, Any]:
    values = collect_non_empty_secrets(config_dict)
    store = get_store(app_root)
    if values:
        store.set_many(values)
    if clear_empty:
        empty_keys = []
        for path in iter_secret_paths(config_dict):
            value = get_nested(config_dict, path)
            if value == "":
                empty_keys.append(dotted(path))
        if empty_keys:
            store.delete_many(empty_keys)
    return sanitize_config(config_dict)


def hydrate(config_dict: Dict[str, Any], app_root: str) -> Dict[str, Any]:
    hydrated = deepcopy(config_dict)
    store = get_store(app_root)
    for path in iter_secret_paths(hydrated):
        current_value = get_nested(hydrated, path)
        if isinstance(current_value, str) and current_value:
            continue
        stored_value = store.get(dotted(path))
        if stored_value:
            set_nested(hydrated, path, stored_value)
    return hydrated


def clear(app_root: str, default_config: Dict[str, Any]) -> None:
    get_store(app_root).clear(iter_secret_paths(default_config))
