"""
AI Auto Blog - 自動產生 SEO 優化部落格文章
使用 Claude API (Haiku 模型，最便宜：每篇約 $0.01-0.02)

使用方式:
  python scripts/generate_post.py "AI工具推薦"
  python scripts/generate_post.py "如何用ChatGPT賺錢" --lang zh
  python scripts/generate_post.py --batch keywords.txt
"""

import os
import sys
import re
import argparse
from datetime import datetime
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("請先安裝 anthropic SDK: pip install anthropic")
    sys.exit(1)

# 專案根目錄
PROJECT_ROOT = Path(__file__).parent.parent

# 載入 .env（切換到專案根目錄再讀，避免 unicode 路徑問題）
try:
    from dotenv import load_dotenv
    _orig_dir = os.getcwd()
    os.chdir(str(PROJECT_ROOT))
    load_dotenv(override=True)
    os.chdir(_orig_dir)
except ImportError:
    pass
CONTENT_DIR = PROJECT_ROOT / "content" / "posts"

# 確保目錄存在
CONTENT_DIR.mkdir(parents=True, exist_ok=True)

SYSTEM_PROMPT_EN = """You are an expert SEO blog writer. Write high-quality, engaging blog posts that are optimized for search engines.

Rules:
- Write in a conversational, helpful tone
- Use proper heading structure (H2, H3) for SEO
- Include actionable tips and real examples
- Write naturally — avoid keyword stuffing
- Target 1200-1800 words
- Include a compelling introduction and conclusion
- Add relevant internal linking suggestions as [LINK: topic] placeholders

Output format: Return ONLY the markdown content (no frontmatter, no title heading).
"""

SYSTEM_PROMPT_ZH = """你是一位專業的 SEO 部落格寫手，擅長撰寫高品質、吸引讀者並對搜尋引擎優化的繁體中文文章。

規則：
- 使用繁體中文撰寫，語氣自然親切、有幫助
- 使用正確的標題結構（H2、H3）以利 SEO
- 加入實用技巧和真實範例
- 自然融入關鍵字，避免過度堆砌
- 目標字數：1200-1800 字
- 包含引人入勝的開頭和結尾
- 可用 [連結: 主題] 作為內部連結建議佔位符

輸出格式：只回傳 Markdown 內文（不含 frontmatter，不含 H1 標題）。
"""

PROMPT_TEMPLATE_EN = """Write a blog post about: {topic}

Target audience: People interested in AI tools, technology, and online side hustles
Categories: {categories}
SEO keywords to naturally include: {keywords}

Make it practical, with step-by-step instructions or lists where appropriate.
"""

PROMPT_TEMPLATE_ZH = """請用繁體中文撰寫一篇關於「{topic}」的部落格文章。

目標讀者：對 AI 工具、科技趨勢、生產力提升和程式開發感興趣的繁體中文讀者
文章分類：{categories}
自然融入的 SEO 關鍵字：{keywords}

請提供實用內容，適當使用步驟說明或條列式清單。
"""


def slugify(text: str) -> str:
    """將標題轉為 URL-friendly slug"""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')


def generate_metadata(client, topic: str, lang: str) -> dict:
    """用 AI 產生文章的 metadata（標題、描述、關鍵字、分類）"""
    if lang == "zh":
        meta_prompt = f"""請為主題「{topic}」的繁體中文部落格文章提供以下資訊：
1. SEO 優化標題（吸引人，60字以內）
2. Meta 描述（155字以內）
3. 5個 SEO 關鍵字（逗號分隔）
4. 1-2個文章分類，從以下選擇：[AI工具, 副業賺錢, 教學指南, 生產力, 科技趨勢, 程式開發]
   並自動根據主題判斷最合適的分類
5. 3-5個標籤（繁體中文）

請以下列格式回傳（只回傳這些行，不要其他文字）：
TITLE: ...
DESCRIPTION: ...
KEYWORDS: ...
CATEGORIES: ...
TAGS: ...
"""
    else:
        meta_prompt = f"""For a blog post about "{topic}", provide:
1. SEO-optimized title (compelling, under 60 chars)
2. Meta description (under 155 chars)
3. 5 SEO keywords (comma-separated)
4. 1-2 categories — pick the most fitting from: [ai-tools, side-hustle, tutorials, productivity, tech-trends, dev]
5. 3-5 tags

Return in this exact format (only these lines, nothing else):
TITLE: ...
DESCRIPTION: ...
KEYWORDS: ...
CATEGORIES: ...
TAGS: ...
"""

    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        messages=[{"role": "user", "content": meta_prompt}]
    )

    text = resp.content[0].text
    meta = {}
    for line in text.strip().split('\n'):
        if ':' in line:
            key, val = line.split(':', 1)
            meta[key.strip().upper()] = val.strip()

    return {
        "title": meta.get("TITLE", topic),
        "description": meta.get("DESCRIPTION", ""),
        "keywords": meta.get("KEYWORDS", topic),
        "categories": [c.strip() for c in meta.get("CATEGORIES", "ai-tools").split(",")],
        "tags": [t.strip() for t in meta.get("TAGS", "").split(",")],
    }


def generate_post(topic: str, lang: str = "en") -> str:
    """產生一篇完整的部落格文章"""
    client = anthropic.Anthropic()  # 從環境變數 ANTHROPIC_API_KEY 讀取

    print(f"  [1/3] 產生文章 metadata...")
    meta = generate_metadata(client, topic, lang)

    print(f"  [2/3] 產生文章內容: {meta['title']}")
    if lang == "zh":
        system_prompt = SYSTEM_PROMPT_ZH
        content_prompt = PROMPT_TEMPLATE_ZH.format(
            topic=topic,
            categories=", ".join(meta["categories"]),
            keywords=meta["keywords"],
        )
    else:
        system_prompt = SYSTEM_PROMPT_EN
        content_prompt = PROMPT_TEMPLATE_EN.format(
            topic=topic,
            categories=", ".join(meta["categories"]),
            keywords=meta["keywords"],
        )

    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4000,
        system=system_prompt,
        messages=[{"role": "user", "content": content_prompt}]
    )

    content = resp.content[0].text

    # 組合 Hugo frontmatter + 內容
    date_str = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")
    slug = slugify(meta["title"])
    categories_yaml = "\n".join(f'  - "{c}"' for c in meta["categories"])
    tags_yaml = "\n".join(f'  - "{t}"' for t in meta["tags"])

    post = f"""---
title: "{meta['title']}"
date: {date_str}
draft: false
description: "{meta['description']}"
categories:
{categories_yaml}
tags:
{tags_yaml}
---

{content}
"""

    # 寫入檔案
    filename = f"{datetime.now().strftime('%Y-%m-%d')}-{slug}.md"
    filepath = CONTENT_DIR / filename

    # 避免覆蓋
    counter = 1
    while filepath.exists():
        filepath = CONTENT_DIR / f"{datetime.now().strftime('%Y-%m-%d')}-{slug}-{counter}.md"
        counter += 1

    filepath.write_text(post, encoding="utf-8")
    print(f"  [3/3] 文章已儲存: {filepath.relative_to(PROJECT_ROOT)}")

    # 顯示費用估算
    input_tokens = resp.usage.input_tokens
    output_tokens = resp.usage.output_tokens
    cost = (input_tokens * 0.25 + output_tokens * 1.25) / 1_000_000
    print(f"  預估費用: ${cost:.4f} (input: {input_tokens}, output: {output_tokens} tokens)")

    return str(filepath)


def batch_generate(keywords_file: str, lang: str = "en"):
    """從檔案批次產生文章，每行一個主題"""
    keywords_path = Path(keywords_file)
    if not keywords_path.exists():
        print(f"找不到檔案: {keywords_file}")
        sys.exit(1)

    topics = [line.strip() for line in keywords_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    print(f"共 {len(topics)} 個主題\n")

    for i, topic in enumerate(topics, 1):
        print(f"[{i}/{len(topics)}] {topic}")
        try:
            generate_post(topic, lang)
        except Exception as e:
            print(f"  錯誤: {e}")
        print()


def main():
    parser = argparse.ArgumentParser(description="AI Auto Blog - 自動產生 SEO 部落格文章")
    parser.add_argument("topic", nargs="?", help="文章主題")
    parser.add_argument("--lang", default="en", help="語言 (en/zh，預設 en)")
    parser.add_argument("--batch", help="批次模式：讀取關鍵字檔案，每行一個主題")

    args = parser.parse_args()

    # 檢查 API Key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("請設定環境變數 ANTHROPIC_API_KEY")
        print("  Windows: set ANTHROPIC_API_KEY=your-key-here")
        print("  Linux:   export ANTHROPIC_API_KEY=your-key-here")
        sys.exit(1)

    if args.batch:
        batch_generate(args.batch, args.lang)
    elif args.topic:
        generate_post(args.topic, args.lang)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
