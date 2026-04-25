---
title: "Claude API 自動生成影片劇本：我怎麼讓 AI 寫出搞笑動物短影片腳本"
date: 2026-04-25
draft: false
description: "用 Claude API (Sonnet 4.6) 自動生成 YouTube Shorts 影片劇本的實作教學，包含 prompt 設計技巧、結構化 JSON 回傳、禁用詞檢查機制和實際範例。"
categories:
  - Python 自動化
  - AI 應用
tags:
  - Claude API
  - Anthropic
  - Python
  - Prompt Engineering
  - JSON
  - YouTube Shorts
  - AI 生成內容
---

我的 YouTube Shorts 機器人每天自動產出兩支影片，而每支影片的劇本都是 Claude API 即時生成的。不是從資料庫裡隨機挑——是根據當天 YouTube 上的熱門趨勢，讓 AI 寫出全新的搞笑動物腳本。這篇來講我怎麼串接 Claude API、怎麼設計 prompt、怎麼讓它穩定回傳結構化的 JSON。

這篇是系列文章之一，整體架構請看：[Python 打造全自動 YouTube Shorts 頻道的完整架構](/ai-auto-blog/posts/2026-04-25-python-youtube-shorts-自動化完整架構分享/)

## 基本串接：用 anthropic 套件呼叫 Claude

安裝很簡單：

```bash
pip install anthropic
```

呼叫 Claude API 的基本程式碼：

```python
import anthropic

client = anthropic.Anthropic(api_key="你的 API Key")
message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=800,
    messages=[{"role": "user", "content": "你的 prompt"}],
)
result = message.content[0].text
```

API Key 到 [Anthropic Console](https://console.anthropic.com/) 申請，充值方式是預付制，我充了 $5 USD，跑了快一個月還沒用完。每次呼叫 Sonnet 4.6 大概花 $0.01-0.02 USD，一天兩次也才 $0.04。

## Prompt 設計：讓 Claude 回傳結構化 JSON

這是整套系統裡最花時間調整的部分。我的目標是讓 Claude 一次回傳所有後續流程需要的資料——中文標題、台詞、Pexels 搜尋關鍵字、Veo prompt 等等，全部用 JSON 格式。

我實際使用的 prompt（精簡版）長這樣：

```
你是一個台灣搞笑動物短影片的腳本作家。
請根據以下近兩週 YouTube 熱門動物短影片，
模仿觀看數最高的橋段結構來創作：

- Funny Cat Reaction to Cucumber (530M views)
- Dog Fails Compilation (120M views)
- ...（系統自動填入的趨勢資料）

動物人設風格：
- 狗：「傻萌暴衝型」，第一人稱短句連發
- 貓：「傲嬌毒舌型」，話少但致命
- 倉鼠：「吃貨貪心型」，對食物無限執著

請以 JSON 格式回傳：
{
  "id": "英文小寫底線，例如 dog_new_trick",
  "title": "繁體中文標題",
  "lines": "第一句\\n第二句\\n第三句",
  "animal_search": "英文 Pexels 搜尋關鍵字",
  "animal_type": "動物中文名",
  "mood": "英文情緒",
  "tags": ["標籤1", "標籤2"],
  "veo_prompt": "英文影片畫面描述"
}
```

有幾個設計要點值得說明：

**趨勢資料是動態的。** 系統會先用 YouTube Data API 搜尋近 14 天的熱門動物短影片，取 TOP 10 的標題和觀看數，然後填入 prompt。這樣 Claude 每次看到的參考資料都不一樣，生成的內容也不會重複。

**animal_search 的規則最關鍵。** 我在 prompt 裡特別強調 animal_search 必須描述具體的視覺動作，不能用泛指詞。例如標題是「貓咪被小黃瓜嚇到」，animal_search 應該是 `cat startled scared jumps back cucumber`，不能寫 `funny cat alone`。這直接影響 Pexels 能不能搜到對的素材。

**veo_prompt 控制 AI 影片風格。** 我要求整體風格是「輕柔、溫暖、夢幻」——柔焦鏡頭、粉彩色調、自然柔光，並且一律加上 `9:16 vertical video, no humans, no text`。

## 解析 Claude 的回傳

Claude 有時候會在 JSON 外面包一層 markdown code block，所以我做了額外的清理：

```python
def parse_claude_response(text):
    text = text.strip()
    # 移除 markdown code block
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())
```

這段看起來簡單，但實際上省了我不少 debug 時間。Claude 大部分時候會乖乖回傳純 JSON，但偶爾會多加 `` ```json `` 標記。

## 禁用詞檢查：安全機制

因為是搞笑動物影片，台詞裡偶爾會出現不適當的用語。我設了一個禁用詞列表，在 Claude 回傳後立刻檢查：

```python
FORBIDDEN_WORDS = [
    "跳樓", "自殺", "死亡", "殺死", "墜落",
    "摔死", "撞死", "跌死", "死掉", "猝死", "喪命",
]

def has_forbidden_words(text):
    return [w for w in FORBIDDEN_WORDS if w in (text or "")]
```

如果檢測到禁用詞，系統會在原始 prompt 後面追加修正指令，自動重新生成一次：

```python
bad_words = has_forbidden_words(scene["title"]) + has_forbidden_words(scene["lines"])
if bad_words:
    retry_prompt = (
        original_prompt
        + f"\n\n【重要修正】上次生成的內容包含禁用詞「{'、'.join(bad_words)}」，"
        "請重新生成，絕對不能使用這些詞彙。"
    )
    scene = parse_claude_response(call_claude(retry_prompt))
```

重試一次之後如果還有禁用詞就直接放棄，fallback 到預設的內容庫隨機選一則。

## 動物關鍵字驗證

另一個我花了蠻多時間處理的問題是 Claude 回傳的 animal_search 有時候會漏掉動物名。例如標題是「貓咪偷吃零食」，animal_search 可能回傳 `sneaking eating snacks`，漏掉了 `cat`。

我做了一個自動補正機制：

```python
ANIMAL_KEYWORD_MAP = {
    "貓": "cat", "狗": "dog", "倉鼠": "hamster",
    "兔子": "rabbit", "鸚鵡": "parrot", ...
}

def validate_animal_search(title, animal_search):
    # 從中文標題找出預期的動物英文名
    for zh, en in ANIMAL_KEYWORD_MAP.items():
        if zh in title:
            if en not in animal_search.lower():
                return f"{en} {animal_search}"  # 自動補到前面
    return animal_search
```

這個驗證會在 Claude 回傳後自動執行，確保 Pexels 搜尋一定找得到正確的動物影片。

## 廢話文學模式：另一種 prompt 風格

晚上的 Pexels 模式我用的是「廢話文學」風格——那種「如果在非洲過了 60 秒，那在台灣就過了一分鐘」的搞笑金句。prompt 風格完全不同：

```
你是一位廢話文學大師。廢話文學的精髓是：
前半句鋪墊讓讀者以為要說深刻的事，
後半句用同義替換直接戳破，落差越大越好笑。
語氣必須正經嚴肅，越正經越有笑點。

經典範例：
- 「據統計，十隻貓裡面有十隻都是貓。」
- 「研究指出，一隻貓盯著你看的時候，牠正在看你。」

請以「貓」為主角，生成 3~5 句廢話文學金句。
```

廢話文學模式不需要趨勢搜尋，生成的內容搭配 Edge TTS 的播報員語音特別有效果。

## 實際回傳範例

一個 Claude 回傳的完整 JSON 看起來像這樣：

```json
{
  "id": "cat_cucumber_shock",
  "title": "貓咪遇見小黃瓜的世紀反應",
  "lines": "這是什麼東西？\n等等...它在動嗎？\n啊啊啊啊啊！\n（飛到三樓高）\n冷靜...我只是在做瑜珈",
  "animal_search": "cat startled scared jumps back cucumber surprised",
  "animal_type": "貓",
  "mood": "shocked",
  "tags": ["貓咪", "小黃瓜", "驚嚇反應"],
  "veo_prompt": "A fluffy orange tabby cat eating from a bowl, suddenly noticing a green cucumber placed behind it, cat arching its back and leaping backwards in exaggerated shock, soft warm kitchen lighting, pastel tones, dreamy bokeh background, 9:16 vertical video, no humans, no text"
}
```

這一份 JSON 就足以驅動後續的所有步驟——Pexels 用 `animal_search` 搜影片、Veo 用 `veo_prompt` 生成影片、YouTube 用 `title` 和 `tags` 設定影片資訊。

想了解 Pexels 搜尋怎麼運作的，請看：[Pexels API 免費影片素材下載教學](/ai-auto-blog/posts/2026-04-25-pexels-api-免費影片素材下載教學/)。排程怎麼設定的：[Windows Task Scheduler 自動排程教學](/ai-auto-blog/posts/2026-04-25-windows-task-scheduler-python-自動排程教學/)。完整架構：[主文](/ai-auto-blog/posts/2026-04-25-python-youtube-shorts-自動化完整架構分享/)。
