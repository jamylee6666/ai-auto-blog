# AI Auto Blog

AI 自動產生 SEO 部落格文章，部署到 GitHub Pages，賺取被動收入。

## 快速開始

### 1. 安裝需求

```bash
# 安裝 Hugo
winget install Hugo.Hugo.Extended

# 安裝 Python 套件
pip install -r scripts/requirements.txt
```

### 2. 設定 API Key

```bash
# Windows
set ANTHROPIC_API_KEY=your-key-here

# 或永久設定（系統環境變數）
setx ANTHROPIC_API_KEY your-key-here
```

### 3. 產生文章

```bash
# 單篇文章
python scripts/generate_post.py "Best AI Tools for 2026"

# 中文文章
python scripts/generate_post.py "2026最好用的AI工具" --lang zh

# 批次產生（從檔案讀取主題）
python scripts/generate_post.py --batch scripts/sample_keywords.txt
```

### 4. 本地預覽

```bash
hugo server -D
# 打開 http://localhost:1313
```

### 5. 部署到 GitHub Pages

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/你的帳號/ai-auto-blog.git
git push -u origin main
```

然後到 GitHub repo → Settings → Pages → Source 選 "GitHub Actions"。

## 每日流程（約 20 分鐘）

1. 想幾個文章主題，寫進 `scripts/sample_keywords.txt`
2. 執行 `python scripts/generate_post.py --batch scripts/sample_keywords.txt`
3. 檢查產生的文章，微調內容
4. `git add . && git commit -m "New posts" && git push`
5. 網站自動更新！

## 變現設定

### Google AdSense
1. 等累積 20-30 篇文章後申請
2. 取得 AdSense ID（ca-pub-xxxxxxxx）
3. 填入 `hugo.toml` 的 `adsenseId`

### 聯盟行銷
在文章中加入推薦連結（AI 工具通常有 20-30% 分潤）

## 費用

- 託管：$0（GitHub Pages）
- AI 產文：每篇約 $0.01-0.02（Claude Haiku）
- 網域（選用）：$10/年

## 專案結構

```
ai-auto-blog/
├── content/posts/     ← 文章放這裡
├── scripts/
│   ├── generate_post.py    ← AI 產文腳本
│   └── sample_keywords.txt ← 關鍵字範例
├── themes/aiblog/     ← 部落格主題
├── .github/workflows/ ← 自動部署
└── hugo.toml          ← 網站設定
```
