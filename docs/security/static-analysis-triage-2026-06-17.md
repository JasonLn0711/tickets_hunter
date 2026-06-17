# Static Analysis Triage 2026-06-17

範圍：`src/` Python source，排除 `src/assets` 與 `src/www/dist` vendored/binary assets。
工具：Bandit 1.9.4，Python 3.12 clean runtime venv。
執行時間：2026-06-17。

## Gate Result

High-severity / high-confidence gate 通過：

```bash
/tmp/tickets-hunter-runtime-venv/bin/python -m bandit -q -r src -x src/assets,src/www/dist --severity-level high --confidence-level high
```

結果：exit code 0；沒有 high/high finding。

## Full Scan Summary

完整掃描指令：

```bash
/tmp/tickets-hunter-runtime-venv/bin/python -m bandit -r src -x src/assets,src/www/dist -f json -o /tmp/tickets-hunter-bandit-full.json
```

結果摘要：

| 分類 | 數量 | 處理策略 |
|---|---:|---|
| High severity | 0 | release gate 目前乾淨 |
| Medium severity | 2 | 已人工 triage；均為 JavaScript selector/table parsing string，被 Bandit 誤判為 SQL expression |
| Low severity | 259 | 納入 legacy hardening backlog；不作為本次 release blocker |
| High/high findings | 0 | 滿足本次安全目標 |

Bandit test ID 分布：

| Test ID | 數量 | 說明 | Triage |
|---|---:|---|---|
| B110 | 176 | `try/except/pass` | 多數位於 browser automation best-effort DOM probing；後續平台 adapter refactor 時逐步改成 debug-log 或明確 fallback |
| B311 | 61 | 非密碼學用途 `random` | 用於等待時間、座位/票區策略與 UI automation jitter；非 cryptographic use，保留 |
| B105 | 13 | hardcoded password-like string | 多數為空字串 default config、placeholder 或 test fixture；secret lifecycle 已將 runtime secrets 移出 `settings.json` |
| B112 | 3 | `try/except/continue` | browser automation fallback；後續平台 helper 拆分時逐步加可測分支 |
| B404 | 3 | subprocess import | `util.py`/launcher 路徑需要 subprocess；`shell=True` 已移除 |
| B603 | 2 | subprocess without shell | 本機 launcher 使用 bounded argv list；保留 |
| B608 | 2 | hardcoded SQL expression | 誤判；實際為 browser `tab.evaluate()` 的 JavaScript DOM query string |
| B107 | 1 | default password arg | 測試或空 default path；不保存真 secret |

## Medium Findings

| Finding | 位置 | Triage |
|---|---|---|
| B608 hardcoded SQL expression | `src/platforms/ibon.py:2018` | False positive。該字串是送入瀏覽器的 JavaScript DOM parsing code，內容使用 `document.querySelectorAll('table.rwdtable tbody tr')`，不是 SQL statement，也不接資料庫。 |
| B608 hardcoded SQL expression | `src/platforms/kham.py:3390` | False positive。該字串是送入瀏覽器的 JavaScript seating-map decision code，使用 `document.querySelector(...)`，不是 SQL statement，也不接資料庫。 |

## Residual Backlog

後續 static-analysis hardening 的高槓桿方向：

1. 平台 adapter 持續拆出 pure decision helpers，讓 `try/except/pass` 從大型 browser flow 移到可測 fallback。
2. 把 platform DOM probing 的 expected-missing-element paths 改成結構化 debug event，減少 B110 noise。
3. 將非密碼學 `random` 用途集中到明確命名 helper，例如 `automation_jitter_seconds()`，讓 security intent 更清楚。
4. 對 subprocess launcher 保持 argv-list-only invariant，避免回歸 `shell=True`。

## Release Decision

本次 full Bandit scan 沒有 high severity finding，high/high gate 通過；medium findings 經人工確認為 JavaScript DOM query false positives。剩餘低風險 findings 是 legacy automation maintainability backlog，已納入後續 platform adapter refactor，而不是本次安全 release blocker。
