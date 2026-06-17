# Tickets Hunter Security Documentation

本目錄是 Tickets Hunter 的 security evidence hub，負責保存可追溯的安全稽核、後續 goal prompt、release 驗證、static-analysis triage 與本機驗證紀錄。專案的正確操作範圍是使用者自有帳號、個人合法使用、平台條款內的本機自動化，以及 local/mock-only 測試。

## 文件索引

- [Security audit report 2026-06-17](security-audit-2026-06-17.md)：OWASP / NIST 對應稽核、已完成控制與後續改善路線。
- [Codex goal follow-up 2026-06-17](codex-goal-security-followup-2026-06-17.md)：可重跑、可版本追溯的 Codex goal prompt。
- [Release artifact verification](release-artifact-verification.md)：使用 release manifest、SHA256 與 CycloneDX SBOM 驗證發布包。
- [Static-analysis triage 2026-06-17](static-analysis-triage-2026-06-17.md)：完整 Bandit 掃描結果分類、false-positive 判定與 legacy backlog 處理策略。
- [Local runtime evidence 2026-06-17](local-runtime-evidence-2026-06-17.md)：乾淨 venv、runtime imports、settings API smoke、安全測試、secret scan 與 release manifest/SBOM 證據。

## 安全驗證基準

開發與 release 前應維持下列檢查通過：

```bash
python -m compileall src tests
python -m pytest
python -m bandit -q -r src -x src/assets,src/www/dist --severity-level high --confidence-level high
python -m pip_audit -r requirement.txt
detect-secrets scan src scripts tests docs/security .github SECURITY.md requirement.txt requirements-dev.txt pyproject.toml --exclude-files '(^|/)(src/assets|src/www/dist)/|.*\.(png|gif|ico|ttf|mp3|wav|onnx)$'
```

## Safe Local Testing Scope

測試應以本機、mock、合成資料與非票務交易路徑為主。需要驗證設定頁、本機 API、OCR 或下載流程時，優先使用 `tests/` 中的 unit/integration tests，或在 `127.0.0.1` 上啟動 settings server。平台 adapter 變更應先抽出純決策 helper 並以 browser-free tests 覆蓋，再保留最小化的實際瀏覽器 smoke path。

## Release Verification Scope

Release artifact 應包含 `release-manifest.json` 與 `sbom.cdx.json`。使用者可用 manifest 的 SHA256 驗證 ZIP、可執行檔、model、charset、前端 dist 與 Chrome download manifest；維護者可用 SBOM 檢查 Python dependency pins 與供應鏈變更。
