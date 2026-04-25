---
title: "Windows Task Scheduler 自動跑 Python 腳本：排程設定與常見問題解決"
date: 2026-04-25
draft: false
description: "用 Windows 工作排程器 (Task Scheduler) 自動執行 Python 腳本的完整教學，包含 bat 檔寫法、編碼設定、日誌記錄和常見問題排除。"
categories:
  - Python 自動化
  - Windows
tags:
  - Windows Task Scheduler
  - Python
  - 排程
  - bat 批次檔
  - 自動化
  - cron
---

我的 YouTube Shorts 機器人每天早上 8 點和晚上 8 點各自動跑一次，全靠 Windows Task Scheduler。這篇講怎麼設定排程、bat 檔怎麼寫、還有我踩過的一堆坑。

這是系列文章的一部分，整體架構請看：[Python 打造全自動 YouTube Shorts 頻道的完整架構](/ai-auto-blog/posts/2026-04-25-python-youtube-shorts-自動化完整架構分享/)

## 為什麼用 Windows Task Scheduler

Linux 有 cron、macOS 有 launchd，Windows 就是 Task Scheduler。雖然介面有點老派，但該有的功能都有：定時執行、開機自動啟動、錯過時間後的補跑機制、甚至可以在電腦睡眠時喚醒執行。

我沒有選用 Python 的排程套件（像 `schedule` 或 `APScheduler`），原因是那些方案都需要一個 Python 程序一直跑在背景，萬一 crash 了就不會自動重啟。Task Scheduler 是系統層級的服務，穩定性遠比自己寫的 daemon 好。

## 第一步：寫 bat 批次檔

不要直接在 Task Scheduler 裡填 Python 指令，用 bat 檔包一層比較好管理。我的早上模式 `run_bot_morning.bat` 長這樣：

```bat
@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
cd /d C:\Users\jamy.lee\Desktop\ai-project\youtube-shorts-bot
if not exist logs mkdir logs
set LOGFILE=logs\morning_%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%.log
echo [%date% %time%] [MORNING] Starting bot... >> "%LOGFILE%"
C:\Python313\python.exe main.py auto --source veo >> "%LOGFILE%" 2>&1
echo [%date% %time%] [MORNING] Exit: %ERRORLEVEL% >> "%LOGFILE%"
echo [%date% %time%] MORNING Exit: %ERRORLEVEL% >> logs\run_history.log
```

晚上的 `run_bot_evening.bat` 只差在 `--source pexels`：

```bat
@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
cd /d C:\Users\jamy.lee\Desktop\ai-project\youtube-shorts-bot
C:\Python313\python.exe main.py auto --source pexels >> logs\evening.log 2>&1
```

幾個關鍵點：

`chcp 65001 > nul` 是設定控制台編碼為 UTF-8。如果不加這行，中文標題在 log 檔裡會變成亂碼。`> nul` 是把 chcp 的輸出訊息（「Active code page: 65001」）吃掉，不寫進 log。

`set PYTHONIOENCODING=utf-8` 是額外的保險，確保 Python 的 stdout/stderr 也用 UTF-8。

`cd /d C:\...` 的 `/d` 參數是切換磁碟機用的。如果你的專案不在 C 槽，沒有 `/d` 的話 `cd` 不會切換磁碟機。

Python 路徑一定要用**絕對路徑**。不要寫 `python main.py`，要寫 `C:\Python313\python.exe main.py`。因為 Task Scheduler 執行時的 PATH 環境變數可能跟你在 terminal 裡不一樣。

`>> "%LOGFILE%" 2>&1` 是把 stdout 和 stderr 都重導向到 log 檔。`>>` 是 append（追加），`>` 是 overwrite（覆蓋）。`2>&1` 是把 stderr 也導到同一個檔案。

## 第二步：設定 Task Scheduler

開啟 Task Scheduler 的方式：按 `Win + R`，輸入 `taskschd.msc`，Enter。

然後按以下步驟建立新工作：

在右邊的「動作」面板點「建立基本工作」。名稱取一個好認的，例如 `YouTube Bot Morning`。觸發程序選「每天」，設定開始時間（例如 08:00）。動作選「啟動程式」。程式或指令碼填你的 bat 檔路徑，例如 `C:\Users\jamy.lee\Desktop\ai-project\youtube-shorts-bot\run_bot_morning.bat`。「開始位置」填專案資料夾路徑 `C:\Users\jamy.lee\Desktop\ai-project\youtube-shorts-bot`。

建立完之後，對工作點右鍵「內容」，有幾個設定要調：

在「一般」分頁，勾選「不論使用者登入與否均執行」。這樣就算你鎖螢幕或登出，工作也會跑。另外，勾選「以最高權限執行」可以避免一些權限問題。

在「條件」分頁，勾選「電源 > 喚醒電腦以執行此工作」。這樣電腦睡眠中也會被叫醒來跑排程。取消勾選「只有在電腦使用 AC 電源時才啟動此工作」，不然筆電用電池時就不會跑。

在「設定」分頁，勾選「如果工作失敗，每隔 X 分鐘重新啟動」。我設 10 分鐘重試、最多 3 次。還有「如果工作已在執行，請勿啟動新的執行個體」，避免同時跑兩個 instance。

## 第三步：測試

設定完之後，對工作點右鍵「執行」，手動觸發一次看看。然後去檢查 log 檔有沒有正確產生，內容是不是正常的。

如果什麼都沒發生，先到 Task Scheduler 的「歷程記錄」分頁看有沒有錯誤。常見的問題是歷程記錄被關掉了——在 Task Scheduler 的主畫面右邊有「啟用所有工作歷程記錄」的選項，點一下開啟。

## 常見問題排除

**問題：工作顯示「成功」但 Python 沒有實際執行。** 通常是路徑錯了。bat 檔裡的 Python 路徑和專案路徑都要確認是正確的絕對路徑。一個快速的測試方法是在 cmd 裡直接執行整個 bat 指令，看有沒有報錯。

**問題：中文亂碼。** 確認 bat 檔有 `chcp 65001` 和 `set PYTHONIOENCODING=utf-8`。另外，Python 程式碼裡開檔案寫入時也要指定 `encoding="utf-8"`。我在 `main.py` 的開頭還做了這個：

```python
import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
```

**問題：「不論使用者登入與否均執行」設定後要輸入密碼。** 對，這是正常的。Windows 需要你的登入密碼才能在你沒登入的情況下以你的身份執行程式。如果你改過密碼，記得回來更新。

**問題：睡眠喚醒後網路連不上。** 有些電腦從睡眠喚醒後，Wi-Fi 重連需要幾秒鐘。如果你的腳本一開始就需要網路，可以在 bat 檔裡加一個等待：

```bat
timeout /t 30 /nobreak > nul
```

這會等 30 秒再開始執行 Python，讓網路有時間連上。

**問題：想在指定日期暫停排程。** 直接到 Task Scheduler 對工作點右鍵「停用」就好，不用刪除。要恢復時再「啟用」。

## 日誌管理

我在 bat 檔裡用日期時間命名 log 檔（`morning_20260425_0800.log`），這樣每次執行都有獨立的 log，方便回溯。另外還有一個 `run_history.log` 只記錄每次的結束時間和 exit code，快速掃一眼就知道最近幾天有沒有失敗。

Python 程式碼裡我也用了 `RotatingFileHandler`，log 檔超過 5MB 自動輪替，保留最近 5 個。這樣不用擔心 log 檔無限增長吃光硬碟空間。

## 和其他排程方案的比較

如果你用 Linux 或 macOS，對應的做法是 cron job。cron 的設定更簡潔（一行搞定），但 Windows Task Scheduler 的 GUI 對新手比較友善，而且有更細膩的條件控制（電源、網路、喚醒等）。

如果你想要跨平台的解決方案，也可以考慮用 GitHub Actions 跑排程。但要注意 GitHub Actions 的免費方案每月有 2,000 分鐘的限制，而且影片處理（ffmpeg 合成）在雲端跑會比較慢。

想了解整套系統其他環節的細節，可以看：[Claude API 劇本生成教學](/ai-auto-blog/posts/2026-04-25-claude-api-自動生成影片劇本教學/)、[Pexels API 素材下載教學](/ai-auto-blog/posts/2026-04-25-pexels-api-免費影片素材下載教學/)、[YouTube API 上傳教學](/ai-auto-blog/posts/2026-04-25-youtube-data-api-oauth-自動上傳教學/)。整體架構在[主文](/ai-auto-blog/posts/2026-04-25-python-youtube-shorts-自動化完整架構分享/)裡。
