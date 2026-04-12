"""
AI Auto Blog - 每日自動發文腳本
每天從英文和中文關鍵字檔各取一個，產生文章，並標記已使用過的關鍵字。

使用方式:
  python scripts/daily_post.py           # 英文 + 中文各一篇
  python scripts/daily_post.py --en-only # 只發英文
  python scripts/daily_post.py --zh-only # 只發中文
  python scripts/daily_post.py --dry-run # 預覽關鍵字但不產生文章
"""

import os
import sys
import argparse
import random
from pathlib import Path
from datetime import datetime

# 確保能找到同目錄的模組
SCRIPTS_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))

# 載入 .env
try:
    from dotenv import load_dotenv
    _orig_dir = os.getcwd()
    os.chdir(str(PROJECT_ROOT))
    load_dotenv(override=True)
    os.chdir(_orig_dir)
except ImportError:
    pass

KEYWORDS_EN = SCRIPTS_DIR / "keywords_en.txt"
KEYWORDS_ZH = SCRIPTS_DIR / "keywords_zh.txt"
USED_EN = SCRIPTS_DIR / "keywords_en_used.txt"
USED_ZH = SCRIPTS_DIR / "keywords_zh_used.txt"


def load_keywords(filepath: Path) -> list[str]:
    """讀取關鍵字檔，忽略空行"""
    if not filepath.exists():
        return []
    return [line.strip() for line in filepath.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_used(filepath: Path) -> set[str]:
    """讀取已使用的關鍵字集合"""
    if not filepath.exists():
        return set()
    return {line.strip() for line in filepath.read_text(encoding="utf-8").splitlines() if line.strip()}


def mark_used(keyword: str, used_file: Path):
    """將關鍵字加入已使用清單"""
    with open(used_file, "a", encoding="utf-8") as f:
        f.write(keyword + "\n")


def pick_keyword(keywords_file: Path, used_file: Path) -> str | None:
    """從可用關鍵字中隨機挑一個（排除已使用的）"""
    all_kw = load_keywords(keywords_file)
    used_kw = load_used(used_file)

    available = [kw for kw in all_kw if kw not in used_kw]

    if not available:
        print(f"  [警告] {keywords_file.name} 的關鍵字已全部用完，重置已使用清單...")
        # 全用完時重置，重新開始循環
        if used_file.exists():
            used_file.unlink()
        available = all_kw

    if not available:
        print(f"  [錯誤] {keywords_file.name} 是空的")
        return None

    return random.choice(available)


def run_daily(run_en: bool = True, run_zh: bool = True, dry_run: bool = False):
    """執行每日發文"""
    from generate_post import generate_post

    today = datetime.now().strftime("%Y-%m-%d")
    print(f"=== AI Auto Blog 每日發文 [{today}] ===\n")

    results = []

    if run_en:
        kw = pick_keyword(KEYWORDS_EN, USED_EN)
        if kw:
            print(f"[英文] 關鍵字: {kw}")
            if dry_run:
                print("  [dry-run] 跳過實際產生")
            else:
                try:
                    filepath = generate_post(kw, lang="en")
                    mark_used(kw, USED_EN)
                    results.append(("en", kw, filepath, True))
                except Exception as e:
                    print(f"  [錯誤] {e}")
                    results.append(("en", kw, None, False))
            print()

    if run_zh:
        kw = pick_keyword(KEYWORDS_ZH, USED_ZH)
        if kw:
            print(f"[中文] 關鍵字: {kw}")
            if dry_run:
                print("  [dry-run] 跳過實際產生")
            else:
                try:
                    filepath = generate_post(kw, lang="zh")
                    mark_used(kw, USED_ZH)
                    results.append(("zh", kw, filepath, True))
                except Exception as e:
                    print(f"  [錯誤] {e}")
                    results.append(("zh", kw, None, False))
            print()

    if not dry_run and results:
        print("=== 完成 ===")
        for lang, kw, path, ok in results:
            status = "OK" if ok else "FAILED"
            rel = Path(path).relative_to(PROJECT_ROOT) if path else "—"
            print(f"  [{lang.upper()}] [{status}] {kw} → {rel}")

        # Auto-deploy: commit and push generated posts
        successful = [r for r in results if r[3]]
        if successful:
            import subprocess
            keywords = ", ".join(r[1] for r in successful)
            try:
                subprocess.run(["git", "add", "-A"], cwd=str(PROJECT_ROOT), check=True)
                subprocess.run(
                    ["git", "commit", "-m", f"auto: daily post [{today}] {keywords}"],
                    cwd=str(PROJECT_ROOT), check=True
                )
                subprocess.run(["git", "push"], cwd=str(PROJECT_ROOT), check=True)
                print("\n  [git] 已推送至 GitHub，部署中...")
            except subprocess.CalledProcessError as e:
                print(f"\n  [git 錯誤] {e}")


def main():
    parser = argparse.ArgumentParser(description="每日自動發文")
    parser.add_argument("--en-only", action="store_true", help="只發英文文章")
    parser.add_argument("--zh-only", action="store_true", help="只發中文文章")
    parser.add_argument("--dry-run", action="store_true", help="預覽關鍵字，不實際呼叫 API")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY") and not args.dry_run:
        print("請設定環境變數 ANTHROPIC_API_KEY")
        sys.exit(1)

    run_en = not args.zh_only
    run_zh = not args.en_only

    run_daily(run_en=run_en, run_zh=run_zh, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
