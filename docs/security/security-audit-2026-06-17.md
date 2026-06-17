# Tickets Hunter 資安稽核報告

日期：2026-06-17
範圍：`tickets_hunter` repo 原始碼、設定介面、本機 API、瀏覽器自動化入口、Chrome downloader、release workflow、vendored model / web assets、security CI、release manifest / SBOM。
測試邊界：本機、mock-only、no-op automation smoke；不連線真實售票平台、不送出真實 Discord / Telegram 通知、不執行購票或壓測。

## 稽核結論

Tickets Hunter 的正確安全定位是「使用者本機控制的桌面自動化工具」：使用者自有帳號、個人合法使用、平台條款內操作、本機設定 API、可驗證 release artifact，以及可停止、可審計、可逐步測試的 browser automation adapter。

本次稽核與修補後，repo 未發現明確後門、持久化植入、惡意資料外送邏輯或刻意繞過使用者控制面的惡意程式碼。高風險控制面已收斂到 `127.0.0.1`，狀態改變 API 已加入本機 token gate 並轉為 POST，設定檔有 schema validation，runtime secrets 已從 `settings.json` 遷移到 optional OS keyring / permission-restricted local fallback，Chrome downloader 移除 insecure fallback 並加入安全解壓，release workflow 產生 SHA256 manifest 與 CycloneDX SBOM，logs / notification test errors 也加入中央 redaction。

目前 release gate 狀態：pytest、Bandit high/high、pip-audit、detect-secrets、release manifest/SBOM generation 均通過。完整 Bandit backlog 沒有 high severity finding；2 個 medium finding 經人工確認為 browser JavaScript DOM query false positives。

## 標準依據

- OWASP Top 10:2025：以 Broken Access Control、Security Misconfiguration、Software Supply Chain Failures、Cryptographic Failures、Injection、Insecure Design、Authentication Failures、Software or Data Integrity Failures、Security Logging & Alerting Failures、Mishandling of Exceptional Conditions 作為風險分類語彙。來源：https://owasp.org/Top10/2025/0x00_2025-Introduction/
- OWASP ASVS 5.0.0：以 access control、authentication、input validation、cryptographic controls、secrets/data protection、file/resource handling、logging/evidence 等 verification controls 對應 repo 控制項。來源：https://owasp.org/www-project-application-security-verification-standard/
- NIST SP 800-218 SSDF 1.1：以 PO / PS / PW / RV practices 管理 secure development、dependency/release supply chain、implementation controls 與 vulnerability review。來源：https://csrc.nist.gov/pubs/sp/800/218/final
- NIST CSF 2.0：以 Govern、Identify、Protect、Detect、Respond、Recover outcomes 表達風險治理、供應鏈、identity/access、data security 與 monitoring。來源：https://www.nist.gov/publications/nist-cybersecurity-framework-csf-20

## 資產與信任邊界

| 資產 | 位置 | 安全角色 | 主要控制 |
|---|---|---|---|
| 本機設定 API | `src/settings.py` | 使用者控制面 | loopback-only bind、local token、POST mutation endpoints、schema validation |
| 使用者偏好設定 | runtime `settings.json` | 非秘密偏好 | secret placeholders only、schema validation、malformed config rejection |
| Runtime secrets | OS keyring or `src/secrets.local.json` | 帳密、cookie、webhook、token | optional keyring、local fallback chmod `0600`、load-time migration、save-time sanitization |
| 瀏覽器自動化入口 | `src/nodriver_tixcraft.py`, `src/platforms/*` | browser adapter | TLS default verification、redacted debug logger、pure helper extraction path |
| Chrome downloader | `src/chrome_downloader.py` | 外部二進位下載 | HTTPS-only、safe zip validation、manifest hash、owner-only executable mode |
| OCR/model assets | `src/assets/model/*` | 本地推論模型 | release manifest SHA256 |
| Release workflow | `.github/workflows/build-release.yml` | Windows executable 發布 | security gates、release manifest、CycloneDX SBOM upload |
| Governance docs | `SECURITY.md`, `docs/security/*` | 操作與回報範圍 | supported scope、safe local testing、artifact verification、static triage |

## 已完成控制

| ID | 狀態 | 控制 | 修補摘要 | 標準對應 |
|---|---|---|---|---|
| TH-SEC-001 | 已完成 | 本機 API access control | `LocalOnlyHandler` 限制 loopback；`LocalMutationHandler` 要求 `X-Tickets-Hunter-Token` | OWASP A01/A07, ASVS access control/authentication, SSDF PW/RV |
| TH-SEC-002 | 已完成 | 狀態改變 API method control | `/run`、`/pause`、`/resume`、`/reset`、`/shutdown` 前端改用 POST；GET 相容路徑受 token 保護並標記 deprecated | OWASP A01/A05, ASVS API controls |
| TH-SEC-003 | 已完成 | `/sendkey` file-write boundary | `security_utils.build_safe_tmp_path()` 限制 token 字元、長度與 app root commonpath | OWASP A05/A08, ASVS input/file validation |
| TH-SEC-004 | 已完成 | 設定 schema validation | `security_utils.validate_config()` 拒絕未知欄位、錯型別、非法 port、script homepage、危險 OCR path scheme | OWASP A05/A06, SSDF PW.7/RV.1 |
| TH-SEC-005 | 已完成 | TLS default verification | 移除全域 TLS bypass 與 `InsecureRequestWarning` suppress | OWASP A02/A04, CSF PR.DS |
| TH-SEC-006 | 已完成 | Chrome downloader integrity | HTTPS-only；拒絕 `no_ssl`；safe zip member validation；Chrome download manifest SHA256；owner-only executable permission | OWASP A03/A08, SSDF PS/PW/RV |
| TH-SEC-007 | 已完成 | OCR endpoint resource boundary | local token、base64 validation、decoded payload size limit | OWASP A10/A05 |
| TH-SEC-008 | 已完成 | dependency vulnerability gate | 更新 vulnerable pins；`pip-audit -r requirement.txt` 通過 | OWASP A03, SSDF PS.3/RV.1 |
| TH-SEC-009 | 已完成 | secret lifecycle migration | plaintext runtime secrets load-time migration；`settings.json` 保存 placeholders；optional keyring / chmod `0600` local fallback；runtime hydrate 保持 UI 相容 | OWASP A02/A04, ASVS secrets/data protection, CSF PR.DS |
| TH-SEC-010 | 已完成 | release artifact manifest / SBOM | `scripts/release_manifest.py` 產生 SHA256 manifest 與 CycloneDX SBOM；release workflow upload | OWASP A03/A08, SSDF PS.2/PW.4 |
| TH-SEC-011 | 已完成 | logging and error redaction | `security_utils.redact_text()` masking webhook/token/session/password/cookie values；DebugLogger、notification test error paths covered | OWASP A09, ASVS logging, CSF DE.CM |
| TH-SEC-012 | 已完成 | product scope and abuse-resistance UX | settings page 加入 scope-control notice；refresh warning 改成最低必要頻率與平台公平使用語言；移除規避式文案 | OWASP A04/A10, SSDF PO.5 |
| TH-SEC-013 | 已完成 | platform adapter testability | iBon cookie/login decision helper 抽出 pure functions，browser-free tests 覆蓋 | SSDF PW.8/RV.1 |
| TH-SEC-014 | 已完成 | governance docs | `SECURITY.md`、`docs/security/README.md`、release verification、static triage、runtime evidence、PR checklist | NIST CSF GV/ID/PR, SSDF PO/RV |

## 測試與證據

主要新增/更新測試：

- `tests/test_settings_api_integration.py`：Tornado local API integration tests，覆蓋 `/load` token、mutation token gate、POST controls、secret migration/hydration、malformed config、OCR payload boundary、`/sendkey` path traversal rejection、notification error redaction。
- `tests/test_secret_store.py`：plaintext secret migration、permission-restricted local fallback、hydrate without changing preferences。
- `tests/test_release_manifest.py`：manifest source-asset hashing、`--require-dist` failure、CycloneDX SBOM component pins。
- `tests/test_ibon_decisions.py`：iBon cookie config / feature pure helper tests。
- `tests/test_security_static.py`：TLS bypass 不可回歸、loopback bind、mutation handler inheritance、wildcard CORS 移除、frontend token header、POST frontend controls、safe-use UI copy invariant、safe downloader invariant。
- `tests/test_chrome_downloader_security.py`：safe zip extraction、path traversal rejection、`no_ssl` rejection。
- `tests/test_security_utils.py`：config validation、safe tmp path、token compare、safe zip member names、secret redaction。

乾淨 runtime venv 驗證：

```text
/tmp/tickets-hunter-runtime-venv/bin/python -m pytest -q
37 passed in 0.28s
```

Runtime import / settings smoke：

```text
imports=ok
modules=ddddocr,zendriver,tornado,requests,PIL,cv2,onnxruntime
bind_host=127.0.0.1
load_status=200
token_length=43
run_status=200
```

Security tools：

```text
Bandit high/high gate: passed
Full Bandit: 0 high, 2 medium false positives, 259 low backlog
pip-audit: No known vulnerabilities found
detect-secrets: results {}
release manifest / SBOM generation: passed
```

證據文件：

- `docs/security/local-runtime-evidence-2026-06-17.md`
- `docs/security/static-analysis-triage-2026-06-17.md`
- `docs/security/release-artifact-verification.md`

## Release Artifact Evidence

`scripts/release_manifest.py` source-only run 產生 7 個 source asset entries：

| Artifact | SHA-256 |
|---|---|
| `src/assets/model/tixcraft_tm/charsets.json` | `507cdc38407ad3e14ef14dd921dc7632faad446b1c3aebccd327c2d66ffee200` |
| `src/assets/model/tixcraft_tm/custom.onnx` | `0af6e030897e395412253ac9829f4337860a889406feec3ed865f5ba48e9288c` |
| `src/assets/model/universal/charsets.json` | `dacca8a06a0de9e8a4a14785d220cdc146558aca5ad193289b46ecacdaf11f7b` |
| `src/assets/model/universal/custom.onnx` | `cc792c57bd9ec427ed25213291e46cec776161aaa6bf1801348f99f5f6249cd3` |
| `src/www/dist/bootstrap/bootstrap.min.css` | `d85327d99c7a3ee1f9b5d0500d1370acea3ad2db39c163c2f51f232baedbdede` |
| `src/www/dist/bootstrap/bootstrap.min.js` | `e4fd49181388c48ec5040bd3fe66f57c29c8e67fcd8502b3354b96ec7ab47cc7` |
| `src/www/dist/jquery.min.js` | `3ca827277b8a53349518737c55c253b7e5d17a9d4cb3464b7c1c211164705d01` |

Packaged release workflow 會在 build 後用 `--require-dist` 產生並上傳 `release-manifest.json` 與 `sbom.cdx.json`。

## OWASP / NIST 對應矩陣

| 控制 | OWASP Top 10:2025 | OWASP ASVS 5.0.0 layer | NIST SSDF | NIST CSF 2.0 |
|---|---|---|---|---|
| Local-only API + token gate | A01, A07 | Access control, authentication, API/web service verification | PW.8, RV.1 | PR.AA, PR.AC |
| POST mutation endpoints | A01, A05 | API method semantics, CSRF-style control protection | PW.7, RV.1 | PR.AC |
| Config schema validation | A05, A06, A10 | Input validation, configuration verification | PW.7, RV.1 | PR.PS, DE.CM |
| Runtime secret store | A02, A04 | Secrets management, data protection | PW.6, RV.2 | PR.DS, PR.AA |
| TLS default verification | A02, A04 | Cryptographic controls, secure communication | PW.6, RV.1 | PR.DS |
| Safe Chrome download/extract | A03, A08 | File/resource integrity, dependency trust | PS.2, PW.4, RV.1 | GV.SC, PR.PS |
| Release manifest / SBOM | A03, A08 | Software supply chain verification | PS.2, PS.3, RV.1 | GV.SC, ID.RA |
| Redacted logging | A09 | Logging and monitoring, sensitive data handling | RV.1, RV.3 | DE.CM |
| Scope-control UX | A04, A10 | Secure design and abuse-resistance controls | PO.5, PW.1 | GV.RM, PR.PS |
| Platform helper extraction | A04 | Testable secure design | PW.8, RV.1 | ID.IM, DE.CM |

## 第一性原理建議

這個 repo 的最高價值不是擴張更多平台操作技巧，而是把「使用者在本機可控、可停止、可驗證、可負責任地操作自動化」做成工程上的預設。最簡單、最穩的演進路線是：

1. 保持 localhost-only + runtime token，而不是導入完整遠端帳號系統。
2. 讓 `settings.json` 只保存 preferences，讓 secrets 由 keyring / local secret store 管理。
3. 把平台大型流程逐步拆成 pure decision helpers + thin browser adapters，降低安全修補和測試成本。
4. 把 release trust 放在 manifest、SBOM、hash、dependency audit 和 CI gate，而不是只依賴人工檢查 zip。
5. 把合法使用與平台 stewardship 寫進 settings UX 和 docs，讓產品邊界在操作前可見。
6. 將低風險 static-analysis backlog 視為 maintainability debt，結合平台 adapter refactor 消化，而不是為了消 warning 破壞 browser fallback 行為。

## 殘餘風險與後續路線

目前主要殘餘風險是平台自動化檔案仍偏大、browser fallback flow 有大量 legacy `try/except/pass`，造成 static-analysis noise 與維護成本。後續應以每次一個平台的方式，把 ticket selection、login state、sold-out/redirect handling、captcha/OCR decision 拆成 browser-free helper，再用 adapter 留住最小化 browser I/O。

Release governance 已具備可用 baseline；下一層可加入 signed release artifacts、dependency review automation、SBOM diff review、以及 per-platform smoke fixtures。
