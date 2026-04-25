---
title: "Pexels API 免費影片素材自動下載：Python 串接搜尋、篩選、防重複的實戰教學"
date: 2026-04-25
draft: false
description: "用 Python 串接 Pexels API 免費下載影片素材的完整教學，包含 API 申請、搜尋優化、亮度篩選、防重複機制和多層 fallback 策略的實際程式碼。"
categories:
  - Python 自動化
  - API 教學
tags:
  - Pexels API
  - Python
  - 免費素材
  - 影片下載
  - API
  - YouTube Shorts
  - 自動化
---

我的 YouTube Shorts 機器人每天晚上用 Pexels API 自動下載一段動物影片素材，完全免費。Pexels 每月給 20,000 次 API 請求，對個人專案來說用不完。這篇講我怎麼串接 Pexels API、怎麼搜尋到好用的影片、還有那些提高素材品質的小技巧。

這篇是系列文章之一，整體架構請看：[Python 打造全自動 YouTube Shorts 頻道的完整架構](/ai-auto-blog/posts/2026-04-25-python-youtube-shorts-自動化完整架構分享/)

## 申請 Pexels API Key

到 [https://www.pexels.com/api/](https://www.pexels.com/api/) 註冊帳號，填一下你的用途說明，通常幾分鐘內就能拿到 API Key。完全免費，不需要綁信用卡。

拿到 Key 之後放到 `config.json` 裡：

```json
{
  "pexels_api_key": "你的 API Key"
}
```

## 基本搜尋：呼叫影片搜尋 API

Pexels 的影片搜尋 endpoint 是 `https://api.pexels.com/videos/search`，用 GET 請求，API Key 放在 header：

```python
import requests

headers = {"Authorization": "你的 API Key"}
params = {
    "query": "cat funny alone",
    "orientation": "portrait",  # 直式，適合 Shorts
    "per_page": 30,
    "size": "medium",
    "page": 1,
}

resp = requests.get(
    "https://api.pexels.com/videos/search",
    headers=headers, params=params, timeout=15
)
data = resp.json()
videos = data.get("videos", [])
```

幾個參數的說明：`orientation: "portrait"` 會優先回傳直式影片，這對 YouTube Shorts 的 9:16 畫面很重要。`per_page: 30` 一次拿 30 個結果，增加挑選的餘地。`size: "medium"` 可以避免搜尋到一些超高解析度但檔案太大的影片。

## 搜尋品質優化：自動注入修飾詞

我發現直接用 Claude 生成的關鍵字搜尋，有時候會拿到昏暗、畫質差的影片。所以我在搜尋前會自動加上幾層修飾詞：

```python
# 1. 自動加 "alone"，避免影片裡出現人類
if "alone" not in search_query.lower():
    search_query += " alone"

# 2. 注入亮度修飾詞，偏向明亮色調
brightness_kw = ["bright", "sunny", "daylight", "vivid"]
if not any(kw in search_query.lower() for kw in brightness_kw):
    search_query += " bright"

# 3. 隨機注入情緒修飾詞
mood_options = ["cute", "happy", "playful", "funny"]
mood_inject = random.choice(mood_options)
search_query += f" {mood_inject}"
```

加 `alone` 是因為 Pexels 的動物影片有不少是人抱著寵物拍的，不適合用在搞笑短影片裡。加 `bright` 是為了篩掉那些在昏暗房間拍的低品質影片。情緒修飾詞（`cute`、`happy` 等）則是用隨機的方式增加每次搜尋的多樣性。

## 篩選邏輯：長度、重複、畫質

拿到搜尋結果後，我會做幾層篩選：

```python
cache = load_cache()  # 記錄已使用過的影片 ID

# 第一層：長度合適 + 沒用過
suitable = [
    v for v in videos
    if 5 <= v["duration"] <= 60
    and v["id"] not in cache["used_ids"]
]

# 如果全都用過了，換頁搜尋
if not suitable:
    alt_page = random.choice([p for p in range(1, 6) if p != start_page])
    # 用新的 page 參數重新搜尋...

# 再不行就放寬：允許用過的（但長度合適）
if not suitable:
    suitable = [v for v in videos if 5 <= v["duration"] <= 60]

# 最後的最後：什麼都行
if not suitable:
    suitable = videos
```

防重複機制是用一個 JSON 檔案記錄已經用過的影片 ID。`cache["used_ids"]` 只保留最近 200 個，避免檔案太大。頁碼我也用 `random.randint(1, 4)` 隨機化，這樣就算搜尋同樣的關鍵字也不會每次拿到同一批結果。

## 動物關鍵字驗證：確保搜到對的動物

這是我覺得最實用的一個設計。有時候搜尋 "cat scared cucumber" 回來的結果裡混著狗或倉鼠的影片——Pexels 的搜尋演算法不是那麼精準。

我的做法是檢查 Pexels 回傳的影片頁面 URL slug 是否包含預期的動物名：

```python
def url_contains_animal(video_url, animal):
    slug = video_url.lower().replace("-", " ")
    return animal.lower() in slug

# 優先選 URL 含預期動物名的影片
if expected_animal:
    matched = [v for v in suitable
               if url_contains_animal(v["url"], expected_animal)]
    if matched:
        suitable = matched
    else:
        # 全部不符合？用精簡查詢重新搜尋
        rescue_query = f"{expected_animal} alone"
        # 重新呼叫 API...
```

例如標題是「貓咪偷吃零食」，`expected_animal` 就是 `cat`。如果搜尋結果的 URL 都不含 `cat`（例如全是 `pexels.com/video/dog-playing-xxx`），系統就會放棄原始查詢，改用最簡單的 `cat alone` 重新搜尋。

這個機制有三層 fallback：精簡查詢（`cat alone`）→ 動物 + funny（`cat funny`）→ 放棄驗證用原始結果。確保無論如何都能拿到一段影片。

## 下載影片：選擇最佳畫質

Pexels 每段影片會提供多個不同解析度的版本。我的選擇邏輯是優先找直式（高度 > 寬度）且解析度在 500-1920 之間的：

```python
video_files = chosen["video_files"]
best_file = None
for vf in video_files:
    w, h = vf["width"], vf["height"]
    if h > w and 500 <= h <= 1920:
        if best_file is None or h > best_file["height"]:
            best_file = vf

# 沒有直式就選最高畫質的
if not best_file:
    for vf in sorted(video_files, key=lambda x: x["height"], reverse=True):
        if vf["height"] <= 1920:
            best_file = vf
            break
```

下載用 streaming 模式，避免一次把整段影片塞進記憶體：

```python
resp = requests.get(best_file["link"], timeout=60, stream=True)
with open(filepath, "wb") as f:
    for chunk in resp.iter_content(chunk_size=1024 * 1024):
        f.write(chunk)
```

## API 用量控制

雖然 Pexels 每月有 20,000 次的額度，但我還是設了保守的上限（預設 500 次/月），避免因為 bug 或迴圈失控而用光額度：

```python
def check_api_budget(cache, max_calls=500):
    if cache["api_calls"] >= max_calls:
        print(f"API 用量已達上限 ({cache['api_calls']}/{max_calls})")
        return False
    return True
```

每次 API 呼叫後都會 `cache["api_calls"] += 1` 並存檔。每月手動或自動重置計數器。實際上我一天最多用 5-6 次 API 呼叫（搜尋 + fallback 重搜），一個月不到 200 次。

## 完整的搜尋 + 下載函數

把上面的邏輯串起來，核心函數的呼叫方式很簡單：

```python
filepath = search_and_download(
    search_query="cat staring camera alone",
    output_dir="cache/",
    min_duration=5,
    max_duration=60,
    expected_animal="cat",
)
# filepath = "cache/pexels_12345678.mp4" 或 None（失敗）
```

回傳影片的本地路徑，後續就交給 ffmpeg 合成引擎處理。

想了解影片合成和上傳的部分，請看：[YouTube Data API 自動上傳教學](/ai-auto-blog/posts/2026-04-25-youtube-data-api-oauth-自動上傳教學/)。劇本怎麼生成的：[Claude API 劇本生成教學](/ai-auto-blog/posts/2026-04-25-claude-api-自動生成影片劇本教學/)。排程設定：[Windows Task Scheduler 教學](/ai-auto-blog/posts/2026-04-25-windows-task-scheduler-python-自動排程教學/)。整體架構：[主文](/ai-auto-blog/posts/2026-04-25-python-youtube-shorts-自動化完整架構分享/)。
