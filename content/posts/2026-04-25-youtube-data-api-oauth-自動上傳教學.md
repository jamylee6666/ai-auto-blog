---
title: "YouTube Data API + OAuth 自動上傳影片：Python 從認證到上傳字幕的完整教學"
date: 2026-04-25
draft: false
description: "用 Python 串接 YouTube Data API v3，從 OAuth 2.0 認證、上傳影片、設定多語言標題到上傳 CC 字幕的完整實作教學，包含重試機制和實際程式碼。"
categories:
  - Python 自動化
  - YouTube
tags:
  - YouTube Data API
  - OAuth 2.0
  - Python
  - 影片上傳
  - CC 字幕
  - Google Cloud Console
  - 自動化
---

我的 YouTube Shorts 自動化系統每天自動上傳兩支影片，從產出到上線完全不用手動操作。這篇講的是上傳這一段——怎麼用 Python 串接 YouTube Data API v3，搞定 OAuth 認證，然後自動上傳影片、設定標題描述 tags、上傳三語 CC 字幕。

如果你想看整體架構，可以先讀主文：[Python 打造全自動 YouTube Shorts 頻道的完整架構](/ai-auto-blog/posts/2026-04-25-python-youtube-shorts-自動化完整架構分享/)

## 前置作業：Google Cloud Console 設定

在寫任何程式碼之前，你需要到 [Google Cloud Console](https://console.cloud.google.com/) 做幾件事：

建立一個新專案，然後到「API 和服務」啟用 YouTube Data API v3。接著到「OAuth 同意畫面」設定應用程式名稱和範圍（scopes）。最後到「憑證」建立 OAuth 2.0 用戶端 ID，類型選「桌面應用程式」，下載 JSON 檔並命名為 `client_secret.json` 放到專案目錄。

需要注意的一個坑：如果你的 OAuth 應用程式處於「測試」狀態，只有你手動加入的測試使用者能授權。你自己的 Google 帳號要記得加進去。

## OAuth 2.0 認證流程

我的認證邏輯長這樣——第一次執行時跑完整的 OAuth 授權流程，之後就靠存在本地的 token 自動刷新：

```python
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/youtube",
]

def get_authenticated_service():
    creds = None

    # 嘗試讀取已存在的 token
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    # 沒有有效 token 就跑授權流程
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None

        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file(
                "client_secret.json", SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)
```

幾個重點說明：`SCOPES` 我用了三個——`youtube.upload` 是上傳影片用的，`youtube.force-ssl` 是上傳字幕和修改影片資訊用的，`youtube` 是設定播放清單和隱私用的。第一次執行會自動開啟瀏覽器讓你登入 Google 帳號授權，授權完畢 token 就存到 `token.json`，之後就不用再手動操作了。

token 過期時（通常一小時），`creds.refresh(Request())` 會自動刷新。如果 refresh token 也失效了（通常不會，但有時候 Google 會撤銷），就會 fallback 回完整的授權流程。

## 上傳影片

上傳的核心是 `youtube.videos().insert()`，搭配 `MediaFileUpload` 做分塊上傳：

```python
from googleapiclient.http import MediaFileUpload

def upload_video(youtube, metadata):
    body = {
        "snippet": {
            "title": metadata["title"],
            "description": metadata["description"],
            "tags": metadata["tags"],
            "categoryId": "23",  # Comedy
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        metadata["file_path"],
        mimetype="video/mp4",
        resumable=True,
        chunksize=1024 * 1024,  # 1MB chunks
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    # 分塊上傳，含重試機制
    response = None
    retry = 0
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                print(f"上傳進度：{int(status.progress() * 100)}%")
        except HttpError as e:
            if e.resp.status in [500, 502, 503, 504]:
                retry += 1
                if retry > 10:
                    return None
                sleep_seconds = random.random() * (2 ** retry)
                time.sleep(sleep_seconds)
            else:
                raise

    return response["id"]  # 回傳影片 ID
```

`resumable=True` 很重要——它讓上傳可以在中斷後續傳，而不是整個重來。`chunksize` 設 1MB，適合一般的家用網路。

重試機制用的是指數退避（exponential backoff）：第一次等 0-2 秒、第二次 0-4 秒、第三次 0-8 秒，以此類推。YouTube API 偶爾會回 500/502 的伺服器錯誤，這種通常等一下再試就好了。

## 設定多語言標題

上傳完影片後，我會自動翻譯標題和描述成英文和日文：

```python
def set_video_localizations(youtube, video_id, metadata):
    youtube.videos().update(
        part="snippet,localizations",
        body={
            "id": video_id,
            "snippet": {
                "title": metadata["title"],
                "description": metadata["description"],
                "tags": metadata["tags"],
                "categoryId": "23",
                "defaultLanguage": "zh-TW",
            },
            "localizations": {
                "en": {
                    "title": translate(metadata["title"], "en"),
                    "description": translate(metadata["description"], "en"),
                },
                "ja": {
                    "title": translate(metadata["title"], "ja"),
                    "description": translate(metadata["description"], "ja"),
                },
            },
        },
    ).execute()
```

翻譯我用的是 `deep-translator` 這個套件，它底層走 Google Translate，免費不用 API key。有一個小細節是翻譯時要把 hashtag 先提取出來不翻譯，翻完再接回去，不然 `#搞笑` 會被翻成 `#funny` 就失去原本的多語標籤效果了。

## 上傳 CC 字幕

字幕上傳用的是 `youtube.captions().insert()`：

```python
def upload_captions(youtube, video_id, srt_zh, srt_en, srt_ja):
    captions = [
        (srt_zh, "zh-TW", "中文字幕"),
        (srt_en, "en",    "English"),
        (srt_ja, "ja",    "日本語"),
    ]

    for srt_path, language, name in captions:
        if not srt_path or not os.path.exists(srt_path):
            continue

        media = MediaFileUpload(srt_path, mimetype="application/octet-stream")
        youtube.captions().insert(
            part="snippet",
            body={
                "snippet": {
                    "videoId": video_id,
                    "language": language,
                    "name": name,
                    "isDraft": False,
                }
            },
            media_body=media,
        ).execute()
```

SRT 格式的字幕 YouTube 可以直接接受。`language` 欄位要用正確的 BCP-47 語言代碼，繁中是 `zh-TW`。`isDraft: False` 表示字幕直接上線，不用到 YouTube Studio 手動審核。

## 我遇到的坑

**API 配額限制。** YouTube Data API 預設每天 10,000 個 quota 單位。上傳一支影片就要 1,600 單位，所以一天最多上傳 6 支。我一天兩支完全不會超標。

**OAuth 同意畫面的審核。** 如果你不需要讓其他人使用你的應用程式，保持「測試」狀態就好，不用送審。但測試模式下 token 每 7 天會過期，你可能需要偶爾重新授權一次。解法是把應用程式的發布狀態改成「正式版」——自己用的專案不需要送審，改完就不會再過期了。

**AI 生成內容標記。** YouTube 要求標記 AI 生成的內容，但目前 API 不支援自動設定這個標記，必須到 YouTube Studio 手動勾選。我的程式上傳後會印出提醒訊息。

**`force-ssl` scope。** 如果你一開始只設了 `youtube.upload` scope，後來要加字幕上傳功能，記得更新 scope 並刪掉舊的 `token.json` 重新授權，不然會一直收到 403 權限不足的錯誤。

## 需要安裝的套件

```bash
pip install google-api-python-client google-auth-oauthlib google-auth-httplib2
pip install deep-translator  # 多語言翻譯用
```

這篇講的是上傳環節。想了解影片素材怎麼來的，可以看 [Pexels API 免費影片素材下載教學](/ai-auto-blog/posts/2026-04-25-pexels-api-免費影片素材下載教學/)；想了解劇本怎麼自動生成的，可以看 [Claude API 自動生成影片劇本教學](/ai-auto-blog/posts/2026-04-25-claude-api-自動生成影片劇本教學/)。整體架構則在 [主文](/ai-auto-blog/posts/2026-04-25-python-youtube-shorts-自動化完整架構分享/) 裡。
