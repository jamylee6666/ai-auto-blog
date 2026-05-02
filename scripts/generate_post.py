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

SYSTEM_PROMPT_EN = """You are a practical AI productivity blog writer who specializes in how-to articles that solve real, everyday problems. The current year is 2026 — when discussing tool versions, pricing, or trends, write as if you are publishing in 2026.

Rules:
- Focus on ONE specific use case per article (e.g., batch-reply emails with AI, auto-generate meeting notes)
- Opening: clearly state the reader's pain point — why they need this solution
- Middle: step-by-step instructions that a complete beginner can follow
- Always mention required tools/platforms and approximate time investment
- Closing: provide 2-3 advanced tips or next steps
- Use proper heading structure (H2, H3) for SEO
- Target 1200-1800 words
- Friendly, practical tone — like a knowledgeable friend teaching you

Internal links: Only add a "## Related Articles" section if the user prompt provides a list of real published articles AND at least one is topically relevant to this post. In that case, use ONLY the exact markdown links from the provided list (format: [Title](/posts/slug/)). If no list is provided, or none of the listed articles are relevant, OMIT the "## Related Articles" section entirely. NEVER fabricate URLs or use placeholder formats like [LINK: topic] or [連結: 主題].

Output format: Return ONLY the markdown content (no frontmatter, no title heading).
"""

SYSTEM_PROMPT_ZH = """你是一位專注於 AI 實用工具的部落格作者，專門撰寫幫助讀者解決真實問題的繁體中文教學文章。目前是 2026 年——在討論工具版本、定價或趨勢時，請以 2026 年發文的視角撰寫。

規則：
- 每篇聚焦一個具體場景（例如：用 AI 批量回 email、自動整理報表、產會議紀錄）
- 開頭（100-150字）：點出讀者的痛點，說明為什麼需要這個方法
- 中間：提供新手也能照做的具體步驟教學，說明需要哪些工具或平台、大概花多少時間
- 結尾：給出 2-3 個進階用法建議
- 使用正確的標題結構（H2、H3）以利 SEO
- 目標字數：1200-1800 字
- 語氣自然、親切、實用，像是一位懂 AI 的朋友在手把手教你

內部連結：只有當使用者 prompt 提供「已發表文章清單」且其中至少有一篇與本文主題相關時，才在文末加上「## 相關文章」區塊，並且只能使用清單中提供的真實 markdown 連結（格式：[文章標題](/posts/文章slug/)）。如果沒有提供清單，或清單中沒有任何文章與本文主題相關，請完全省略「## 相關文章」區塊。絕不可自行編造網址，也不可使用 [連結: 主題] 或 [LINK: topic] 之類的佔位符。

輸出格式：只回傳 Markdown 內文（不含 frontmatter，不含 H1 標題）。
"""

PROMPT_TEMPLATE_EN = """Write a practical AI tutorial blog post about: {topic}

Target audience: Office workers or freelancers who want to use AI tools to boost productivity — no coding background required
Categories: {categories}
SEO keywords to naturally include: {keywords}

Article structure to follow:
1. Opening: describe the reader's pain point and why they need this
2. Tools needed: list the tools/platforms with cost info (free tier if available)
3. Step-by-step guide: 3-7 concrete steps with clear instructions
4. Results: how much time it saves or what problem it solves
5. Closing: 2-3 advanced tips
{related_section}"""

PROMPT_TEMPLATE_ZH = """請用繁體中文撰寫一篇關於「{topic}」的實用 AI 教學文章。

目標讀者：希望用 AI 工具提升工作效率的上班族或自由工作者，不需要程式設計背景
文章分類：{categories}
自然融入的 SEO 關鍵字：{keywords}

請依照以下文章結構撰寫：
1. 開頭（100-150字）：描述讀者的痛點，說明為什麼需要這個方法
2. 工具介紹：需要哪些工具或平台，費用或免費方案說明
3. 步驟教學：3-7個具體操作步驟，每步驟有清楚說明（新手友善）
4. 實際效果：能省多少時間或解決什麼具體問題
5. 結尾：2-3個進階用法建議
{related_section}"""


def slugify(text: str) -> str:
    """將標題轉為 URL-friendly slug"""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')


_CJK_RE = re.compile(r'[一-鿿㐀-䶿]')


def list_existing_posts(lang: str, limit: int = 30) -> list[dict]:
    """讀取 content/posts/ 已存在的文章，回傳同語言的 [{title, slug}] 清單。

    用途：給 AI 真實的內部文章清單，避免它在「相關文章」區塊產出假連結。
    語言判斷：標題包含 CJK 字元視為中文，否則視為英文。
    slug 採用檔名（不含 .md），對應 Hugo 預設 URL `/posts/{slug}/`。
    """
    if not CONTENT_DIR.exists():
        return []

    posts = []
    for md in sorted(CONTENT_DIR.glob("*.md"), reverse=True):
        if md.name == "welcome.md":
            continue
        try:
            text = md.read_text(encoding="utf-8")
        except Exception:
            continue
        if not text.startswith("---"):
            continue
        parts = text.split("---", 2)
        if len(parts) < 3:
            continue
        fm = parts[1]
        m = re.search(r'^title:\s*"([^"]+)"', fm, re.MULTILINE)
        if not m:
            m = re.search(r"^title:\s*'([^']+)'", fm, re.MULTILINE)
        if not m:
            continue
        title = m.group(1).strip()
        is_zh = bool(_CJK_RE.search(title))
        post_lang = "zh" if is_zh else "en"
        if post_lang != lang:
            continue
        posts.append({"title": title, "slug": md.stem})
        if len(posts) >= limit:
            break
    return posts


def build_related_section(lang: str) -> str:
    """為文章產生 prompt 結尾的相關文章指示段落（含真實連結清單或省略指示）。"""
    posts = list_existing_posts(lang)
    if not posts:
        if lang == "zh":
            return (
                "\n注意：目前沒有其他已發表文章，請完全省略「## 相關文章」區塊，"
                "不要產生任何 [連結: ...] / [LINK: ...] 等假連結或佔位符。"
            )
        return (
            "\nNOTE: There are no other published articles yet. "
            "OMIT the \"## Related Articles\" section entirely. "
            "Do NOT generate placeholder links like [LINK: topic] or fake URLs."
        )

    if lang == "zh":
        listing = "\n".join(f"- [{p['title']}](/posts/{p['slug']}/)" for p in posts)
        return (
            "\n已發表的內部文章清單（僅在主題真的相關時，才挑 2-3 篇放進文末「## 相關文章」區塊；"
            "請逐字使用以下 markdown 連結，不要改寫標題或路徑）：\n"
            f"{listing}\n\n"
            "如果上述清單沒有任何文章與本文主題相關，請完全省略「## 相關文章」區塊，"
            "絕對不要編造網址或使用 [連結: 主題] / [LINK: topic] 等佔位符。"
        )

    listing = "\n".join(f"- [{p['title']}](/posts/{p['slug']}/)" for p in posts)
    return (
        "\nPublished internal articles available for linking (only pick 2-3 if topically relevant; "
        "use the markdown links below verbatim — do not rewrite titles or paths):\n"
        f"{listing}\n\n"
        "If none of the above are topically relevant to this post, OMIT the \"## Related Articles\" "
        "section entirely. Never fabricate URLs or use placeholders like [LINK: topic]."
    )


def generate_metadata(client, topic: str, lang: str) -> dict:
    """用 AI 產生文章的 metadata（標題、描述、關鍵字、分類）"""
    if lang == "zh":
        meta_prompt = f"""請為主題「{topic}」的繁體中文部落格文章提供以下資訊：
1. SEO 優化標題（吸引人，60字以內）
2. Meta 描述（155字以內）
3. 5個 SEO 關鍵字（逗號分隔）
4. 1-2個文章分類，從以下選擇：[辦公自動化, 內容創作, 資料處理, 學習提升, AI工具教學, 生產力]
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
4. 1-2 categories — pick the most fitting from: [office-automation, content-creation, data-processing, learning, ai-tools, productivity]
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
    related_section = build_related_section(lang)
    if lang == "zh":
        system_prompt = SYSTEM_PROMPT_ZH
        content_prompt = PROMPT_TEMPLATE_ZH.format(
            topic=topic,
            categories=", ".join(meta["categories"]),
            keywords=meta["keywords"],
            related_section=related_section,
        )
    else:
        system_prompt = SYSTEM_PROMPT_EN
        content_prompt = PROMPT_TEMPLATE_EN.format(
            topic=topic,
            categories=", ".join(meta["categories"]),
            keywords=meta["keywords"],
            related_section=related_section,
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
