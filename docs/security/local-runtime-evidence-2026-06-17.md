# Local Runtime Evidence 2026-06-17

範圍：乾淨 Python venv、runtime dependency imports、settings server local smoke、安全測試與供應鏈檢查。
測試邊界：本機與 mock/no-op；不連線真實售票平台、不送出真實 Discord / Telegram 通知、不執行購票流程。

## Clean Runtime Venv

建立與安裝：

```bash
rm -rf /tmp/tickets-hunter-runtime-venv
python3 -m venv /tmp/tickets-hunter-runtime-venv
/tmp/tickets-hunter-runtime-venv/bin/python -m pip install --upgrade pip
/tmp/tickets-hunter-runtime-venv/bin/python -m pip install -r requirements-dev.txt
```

結果：安裝成功。`requirement.txt` runtime pins 與 `requirements-dev.txt` security/test tools 可在乾淨 venv 安裝。

## Runtime Import Smoke

已在乾淨 venv 匯入：

- `ddddocr`
- `zendriver`
- `tornado`
- `requests`
- `PIL`
- `cv2`
- `onnxruntime`

## Settings Server Smoke

使用 `settings.make_application(ocr=None)` 啟動本機 server，binding address 為 `127.0.0.1`，以 temporary app root 與 no-op `launch_maxbot` 驗證 non-ticketing path。

結果：

```text
imports=ok
modules=ddddocr,zendriver,tornado,requests,PIL,cv2,onnxruntime
bind_host=127.0.0.1
load_status=200
token_length=43
run_status=200
```

## Integration Tests

```bash
/tmp/tickets-hunter-runtime-venv/bin/python -m pytest -q
```

結果：

```text
37 passed in 0.28s
```

覆蓋重點：

- `/load` 回傳 runtime-only `_security.local_api_token` 與 loopback bind metadata。
- `/save`、`/reset`、`/run`、`/pause`、`/resume`、`/shutdown`、`/sendkey`、`/ocr`、通知測試端點缺 token 時回 403。
- 控制端點使用 POST，GET 相容路徑受 token 保護並回傳 deprecation header。
- plaintext secrets 可讀取與 migration，保存後 `settings.json` 不含 plaintext secret。
- malformed config 回 400。
- OCR invalid base64 與 oversized payload 回 400。
- `/sendkey` path traversal token 被拒絕，無檔案寫出 app root。
- Discord webhook / Telegram bot token exception response 已 redacted。
- iBon cookie helper 以 pure decision tests 覆蓋，不需 browser I/O。

## Security Toolchain

```bash
/tmp/tickets-hunter-runtime-venv/bin/python -m bandit -q -r src -x src/assets,src/www/dist --severity-level high --confidence-level high
```

結果：exit code 0；沒有 high/high finding。

```bash
/tmp/tickets-hunter-runtime-venv/bin/python -m pip_audit -r requirement.txt
```

結果：

```text
No known vulnerabilities found
```

```bash
/tmp/tickets-hunter-runtime-venv/bin/detect-secrets scan src scripts tests docs/security .github SECURITY.md requirement.txt requirements-dev.txt pyproject.toml --exclude-files '(^|/)(src/assets|src/www/dist)/|.*\.(png|gif|ico|ttf|mp3|wav|onnx)$'
```

結果：`"results": {}`；沒有 committed secret finding。

## Release Manifest / SBOM

```bash
/tmp/tickets-hunter-runtime-venv/bin/python scripts/release_manifest.py --output /tmp/tickets-hunter-release-manifest.json --sbom-output /tmp/tickets-hunter-sbom.cdx.json
```

結果：成功產生 release manifest 與 CycloneDX SBOM。

Source-asset manifest entries：7。涵蓋 `src/assets/model/*/custom.onnx`、`charsets.json`、`src/www/dist` assets。
