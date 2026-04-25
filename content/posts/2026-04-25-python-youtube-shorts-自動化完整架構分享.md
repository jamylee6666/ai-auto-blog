---
title: "用 Python 打造全自動 YouTube Shorts 頻道｜從 API 串接到每天自動發片的完整架構"
date: 2026-04-25
draft: false
description: "分享我用 Python 打造的 YouTube Shorts 自動化系統，從 Claude API 寫劇本、Pexels/Veo 取素材、ffmpeg 合成影片到 YouTube API 自動上傳，每天排程自動產出兩支影片的實戰架構。"
categories:
  - Python 自動化
  - YouTube
tags:
  - Python
  - YouTube Shorts
  - 自動化
  - Claude API
  - Pexels API
  - Veo
  - ffmpeg
  - YouTube Data API
  - Windows Task Scheduler
  - 副業
---

我用這套系統，兩週內全自動產出了 24 支 YouTube Shorts，其中一支拿到 2000+ 觀看。整個月的 API 花費大約是 NT$115 的 Veo 費用加上 $5 USD 的 Claude 儲值。頻道目前 3 個訂閱，還在成長階段，但重點是——我幾乎不用動手，每天早晚各自動發一支片。

這篇文章是我這個專案的架構總覽。我會講清楚每個環節在幹嘛，細節的教學我分別寫在獨立的文章裡，文末有完整連結。

## 整體流程：一行指令搞定一切

整個系統的入口就是一行指令：

```bash
python main.py auto --source veo
```

或是晚上的省錢模式：

```bash
python main.py auto --source pexels
```

執行之後，系統會自動跑完以下四個步驟：

**Step 1：AI 寫劇本。** 系統先用 YouTube Data API 搜尋近兩週的熱門動物短影片（搜尋 "funny cat shorts"、"dog funny moments" 等關鍵字），抓回 TOP 10 的標題和觀看數，然後把這些趨勢資料丟給 Claude API（Sonnet 4.6），讓它參考高觀看數影片的橋段結構，生成一則全新的搞笑動物腳本。Claude 會回傳結構化的 JSON，包含繁中標題、3-5 句台詞、Pexels 搜尋關鍵字、Veo 影片生成 prompt 等欄位。

**Step 2：取得影片素材。** 早上的 Veo 模式會用 Google Veo 3.1 AI 生成一段原創影片；晚上的 Pexels 模式則是用 Pexels API 免費下載動物影片素材。兩種模式各有優缺——Veo 畫面和劇本完全吻合但要付費，Pexels 免費但素材不一定完全對題。系統設計了 fallback 機制：Veo 失敗就自動降級到 Pexels。

**Step 3：生成多語字幕。** 系統把中文台詞翻譯成英文和日文，產出三份 SRT 字幕檔。晚上的「廢話文學」模式還會額外用 Edge TTS 生成語音旁白，字幕時間軸會跟語音精準同步。

**Step 4：合成影片並上傳。** 用 ffmpeg 把素材影片裁切成 9:16 直式、疊上字幕、混合音訊，輸出最終的 mp4 檔。然後透過 YouTube Data API + OAuth 自動上傳，同時設定標題、描述、tags，並上傳中英日三語 CC 字幕。

## 雙模式設計：早上 Veo、晚上 Pexels

我的排程設計是一天發兩支片，用 Windows Task Scheduler 控制：

早上 8 點跑 `run_bot_morning.bat`，使用 `--source veo` 模式。這個模式走 Veo 3.1 AI 生成影片，畫面品質高，跟劇本內容完全對應，但每次大概要花幾塊台幣的 API 費用。

晚上 8 點跑 `run_bot_evening.bat`，使用 `--source pexels` 模式。這個模式是我的「廢話文學」系列——Claude 會生成那種「據統計，十隻貓裡面有十隻都是貓」風格的搞笑金句，搭配 Pexels 免費素材和 Edge TTS 的播報員語音旁白。完全零成本。

bat 檔的內容很簡單，關鍵就是設定好編碼和路徑：

```bat
@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
cd /d C:\Users\jamy.lee\Desktop\ai-project\youtube-shorts-bot
C:\Python313\python.exe main.py auto --source veo >> logs\morning.log 2>&1
```

## Claude API 劇本生成：讓 AI 模仿爆紅影片

這是整套系統最核心的部分。我不是隨機亂生成內容，而是先搜尋 YouTube 上近兩週觀看數最高的動物短影片，把這些標題當作「趨勢參考」丟給 Claude。

Prompt 裡我定義了不同動物的人設風格：狗是「傻萌暴衝型」、貓是「傲嬌毒舌型」、倉鼠是「吃貨貪心型」。Claude 回傳的 JSON 裡不只有台詞，還包含 Pexels 搜尋用的英文關鍵字和 Veo 用的影片生成 prompt，一次生成就把後續所有環節需要的資料都準備好。

我還做了禁用詞檢查——生成的內容如果出現不當用語，系統會自動重新生成一次。

詳細的 Claude API 串接教學，包含完整的 prompt 範例和回傳格式，請看：[Claude API 自動生成影片劇本：我怎麼讓 AI 寫出搞笑動物短影片腳本](/ai-auto-blog/posts/2026-04-25-claude-api-自動生成影片劇本教學/)

## Pexels API：免費影片素材的自動化下載

Pexels 提供免費的影片素材 API，每月 20,000 次請求，對個人專案來說綽綽有餘。我的系統會自動搜尋直式影片、篩選合適長度、避免重複下載，還會自動注入亮度和情緒修飾詞來提高搜尋品質。

有一個我覺得蠻聰明的設計是「動物關鍵字驗證」——系統會從中文標題提取預期的動物名（例如標題有「貓」就預期搜尋結果要有 cat），然後檢查 Pexels 回傳的影片 URL slug 是否包含這個動物。如果搜尋結果全部不相關，會自動用精簡查詢重新搜尋。

完整教學：[Pexels API 免費影片素材自動下載：Python 串接搜尋、篩選、防重複的實戰教學](/ai-auto-blog/posts/2026-04-25-pexels-api-免費影片素材下載教學/)

## YouTube Data API：OAuth 認證 + 自動上傳

上傳的部分用的是 YouTube Data API v3。第一次需要做 OAuth 授權（會跳出 Google 登入頁面），之後 token 存在本地，自動刷新。

上傳完影片後，系統還會自動做幾件事：用 `videos().update()` 設定多語言標題（英文、日文），然後用 `captions().insert()` 上傳三語 CC 字幕。上傳有指數退避的重試機制，遇到 500/502/503 等伺服器錯誤時會自動等待重試。

完整教學：[YouTube Data API + OAuth 自動上傳影片：Python 從認證到上傳字幕的完整教學](/ai-auto-blog/posts/2026-04-25-youtube-data-api-oauth-自動上傳教學/)

## Windows Task Scheduler：讓它每天自己跑

最後一塊拼圖就是排程。我用 Windows Task Scheduler 設定了兩個工作：早上 8 點和晚上 8 點各跑一次。就算電腦睡眠也能自動喚醒執行。

需要注意的坑：bat 檔裡一定要用 `chcp 65001` 設定 UTF-8 編碼，不然中文標題會亂碼；Python 路徑要用絕對路徑；log 要重導向到檔案，方便事後 debug。

完整教學：[Windows Task Scheduler 自動跑 Python 腳本：排程設定與常見問題解決](/ai-auto-blog/posts/2026-04-25-windows-task-scheduler-python-自動排程教學/)

## 真實數據：花費與成效

最後分享一下實際的數字：

頻道 @jamylee2033，目前 3 個訂閱者、約 24 支影片。最高一支影片拿到 2000+ 觀看，大部分影片的觀看數則偏低。老實說，訂閱數成長很慢，但觀看數偶爾會因為演算法推薦而爆發一次。

每月花費方面，Veo API 大約 NT$115，Claude 儲值 $5 USD（大約 NT$160），加起來一個月不到 NT$300。Pexels 是免費的，Edge TTS 也是免費的。如果完全只跑晚上的 Pexels 模式，那就是零成本。

程式碼方面，核心檔案就是 `main.py`（主流程控制）、`video_downloader.py`（Pexels 下載器）、`video_editor.py`（ffmpeg 合成）、`youtube_uploader.py`（YouTube 上傳），加上 `tts_engine.py`、`veo_generator.py` 等輔助模組。

## 這套系統適合誰？

如果你有基本的 Python 能力，想試試看用自動化來經營 YouTube 頻道，這套架構可以當作參考。它不是什麼保證賺錢的方案——我的頻道到現在也還沒開始獲利。但它展示了一件事：用現有的 API 和工具，一個人可以在幾天內搭建出一套完整的內容產出管線。

所有衛星文章的連結整理在這裡，方便你針對有興趣的環節深入了解：

- [Claude API 自動生成影片劇本教學](/ai-auto-blog/posts/2026-04-25-claude-api-自動生成影片劇本教學/)
- [YouTube Data API + OAuth 自動上傳教學](/ai-auto-blog/posts/2026-04-25-youtube-data-api-oauth-自動上傳教學/)
- [Pexels API 免費影片素材下載教學](/ai-auto-blog/posts/2026-04-25-pexels-api-免費影片素材下載教學/)
- [Windows Task Scheduler Python 自動排程教學](/ai-auto-blog/posts/2026-04-25-windows-task-scheduler-python-自動排程教學/)
