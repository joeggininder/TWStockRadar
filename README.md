# TWStockRadar｜台股籌碼共振雷達

這是 Android 原生 App 的**可編譯原始碼**，並非已完成的 APK。GitHub Actions 可在上傳後嘗試編譯 debug APK。

## 在 GitHub 手機版上傳

1. 下載本 ZIP，在手機「我的檔案」中解壓縮。
2. 開啟 https://github.com/joeggininder/TWStockRadar ，使用瀏覽器「電腦版網站」模式。
3. 選 **Add file → Upload files**，將解壓後的檔案與資料夾內容上傳到 repository 根目錄，保留 `.github` 等資料夾階層；若手機瀏覽器無法選擇資料夾，建議使用電腦完成上傳。
4. 若已存在 README.md，可先不選 README.md，避免重名衝突。
5. Commit changes。進入 **Actions → Build Android APK → Run workflow**。執行成功後，在該次執行的 **Artifacts** 下載 `TWStockRadar-debug-apk`，解壓取得 `app-debug.apk`。

## 資料更新

每日平日 18:40（台灣時間）執行 `.github/workflows/daily.yml`，產生 `data/latest.json`。App 預設讀取本 repository 的 raw JSON。

**重要限制：目前尚未串接真實台股資料供應商。** 排程執行不代表真實股票資料每天已更新；`data/source.json` 尚須有可驗證的法人、TDCC、融資、分點觀測資料，否則清單保持空白，避免虛構股票。

## 四條件

- 法人連買至少三日，3 日累計買超張數／20 日平均成交量 ≥ 5%。
- TDCC 千張大戶持股比例上升且股東人數下降（TDCC 原則上每週更新）。
- 5 日融資餘額下降。
- 券商分點至少 3 日連買，且有非隔日沖的佐證與來源；這部分可能需要付費資料授權。

四條件**同時驗證**才會出現在清單。缺資料不會被視為符合。此為研究用觀察指標，非買賣建議。

## 尚未完成

真實台股資料自動擷取、分點授權資料、環球晶／群聯風險推播、每週五檔分析頁、APK 實機測試。這些功能不可視為已上線。
