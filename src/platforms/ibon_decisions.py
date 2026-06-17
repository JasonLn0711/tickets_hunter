def has_ibon_cookie_config(config_dict):
    accounts = config_dict.get("accounts", {})
    ibonqware = accounts.get("ibonqware", "") if isinstance(accounts, dict) else ""
    return isinstance(ibonqware, str) and len(ibonqware) > 1


def detect_ibon_cookie_features(cookie_value):
    cookie = cookie_value if isinstance(cookie_value, str) else ""
    return {
        "mem_id": "mem_id=" in cookie,
        "mem_email": "mem_email=" in cookie,
        "huiwanTK": "huiwanTK=" in cookie,
        "ibonqwareverify": "ibonqwareverify=" in cookie,
    }
