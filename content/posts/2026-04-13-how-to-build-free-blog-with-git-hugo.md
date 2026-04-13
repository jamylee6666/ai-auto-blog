---
title: "如何用 Git + Hugo 架設免費部落格網站｜從零開始完整教學"
date: 2026-04-13T10:00:00+08:00
draft: false
description: "想架設自己的部落格但不想花錢嗎？本教學帶你用 Hugo 靜態網站產生器 + GitHub Pages，完全免費架設個人部落格，並透過 GitHub Actions 實現自動化部署。適合初學者的詳細步驟說明。"
categories:
  - "Tutorials"
  - "教學"
tags:
  - "Hugo"
  - "Git"
  - "GitHub Pages"
  - "靜態網站"
  - "部落格"
  - "免費架站"
---

想要擁有自己的部落格，卻不想每個月支付主機費用嗎？透過 **Hugo** 靜態網站產生器搭配 **GitHub Pages**，你可以完全免費架設一個速度快、好維護的個人部落格。這篇教學將帶你從零開始，一步一步完成整個設定。

---

## 1. 什麼是 Hugo 靜態網站產生器

Hugo 是一款用 Go 語言開發的**靜態網站產生器（Static Site Generator）**，以極快的建置速度聞名。

### 靜態網站 vs 動態網站

| 特性 | 靜態網站 | 動態網站（如 WordPress） |
|------|---------|------------------------|
| 速度 | 極快 | 較慢（需查資料庫） |
| 安全性 | 高（無後端） | 較低（需維護更新） |
| 費用 | 可免費（GitHub Pages） | 需要主機費用 |
| 維護難度 | 低 | 較高 |

### Hugo 的主要優點

- **速度極快**：千頁以上的網站幾秒內建置完成
- **版本控制**：文章用 Markdown 寫，天然適合 Git 管理
- **免費部署**：搭配 GitHub Pages 完全免費
- **主題豐富**：官方主題庫有數百款免費主題

---

## 2. 在 GitHub 上建立 Repository

首先，你需要一個 [GitHub](https://github.com) 帳號。

### 建立新 Repository

1. 登入 GitHub，點擊右上角的 **「+」** → **「New repository」**
2. 填入以下資訊：
   - **Repository name**：`your-blog-name`（例如 `my-hugo-blog`）
   - **Description**：選填，簡單描述你的部落格
   - **Visibility**：選 **Public**（GitHub Pages 免費版需要公開）
   - 勾選 **「Add a README file」**
3. 點擊 **「Create repository」**

```
你的 GitHub 帳號：your-username
你的 Repo 名稱：your-blog-name
未來網址：https://your-username.github.io/your-blog-name/
```

### 把 Repo Clone 到本機

```bash
git clone https://github.com/your-username/your-blog-name.git
cd your-blog-name
```

---

## 3. 安裝 Hugo

### Windows 安裝方式

推薦使用 **Chocolatey** 套件管理器：

```bash
# 先安裝 Chocolatey（在 PowerShell 以系統管理員身分執行）
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# 安裝 Hugo Extended（需要 Extended 版才能編譯部分主題的 SCSS）
choco install hugo-extended
```

或是直接從 [Hugo 官方 GitHub Releases](https://github.com/gohugoio/hugo/releases) 下載 `.zip` 檔，解壓縮後將 `hugo.exe` 加入系統環境變數 `PATH`。

### macOS 安裝方式

```bash
brew install hugo
```

### Linux 安裝方式

```bash
sudo apt update
sudo apt install hugo
```

### 確認安裝成功

```bash
hugo version
# 應輸出類似：hugo v0.123.0+extended ...
```

---

## 4. 建立 Hugo 專案並加入主題

### 初始化 Hugo 專案

在你剛 clone 下來的資料夾裡，建立 Hugo 網站：

```bash
# 在 Repo 資料夾內執行（注意最後的點，代表在目前資料夾建立）
hugo new site . --force
```

執行後會產生以下結構：

```
your-blog-name/
├── archetypes/
├── content/          ← 文章放這裡
├── layouts/
├── static/
├── themes/           ← 主題放這裡
└── hugo.toml         ← 主設定檔
```

### 加入 Stack 主題（使用 Git Submodule）

這裡以熱門的 **Stack** 主題為範例。Stack 是一款支援深色模式、有側邊欄的現代部落格主題。

**為什麼要用 Git Submodule？**

主題本身是別人的 Git Repository。用 `submodule` 的方式加入，可以：
- 追蹤主題的版本，方便日後升級
- 不用把主題的完整程式碼複製進自己的 Repo
- 讓 CI/CD（如 GitHub Actions）能自動拉取主題

```bash
# 將 Stack 主題加為 submodule
git submodule add https://github.com/CaiJimmy/hugo-theme-stack/ themes/hugo-theme-stack

# 初始化 submodule（如果是 clone 別人的 Repo，需要這步）
git submodule update --init --recursive
```

執行後，主題會被下載到 `themes/hugo-theme-stack/` 資料夾，並且根目錄會多出一個 `.gitmodules` 檔案：

```
[submodule "themes/hugo-theme-stack"]
    path = themes/hugo-theme-stack
    url = https://github.com/CaiJimmy/hugo-theme-stack/
```

> **注意**：日後如果有人 clone 你的 Repo，需要執行 `git submodule update --init --recursive` 才能下載主題。或是 clone 時加上 `--recurse-submodules` 參數。

---

## 5. 基本設定（hugo.toml）

編輯根目錄的 `hugo.toml`，以下是一個基本設定範例：

```toml
# 網站基礎 URL（部署到 GitHub Pages 的網址）
baseURL = "https://your-username.github.io/your-blog-name/"

# 網站語言
languageCode = "zh-tw"

# 網站標題（顯示在瀏覽器分頁和首頁）
title = "Your Blog Title"

# 使用的主題名稱（要和 themes/ 底下的資料夾名稱一致）
theme = "hugo-theme-stack"

[params]
  description = "這是你的部落格描述，會出現在搜尋結果中。"
  author = "Your Name"
  mainSections = ["posts"]

  [params.sidebar]
    subtitle = "在這裡寫你的部落格副標題"

  [params.article]
    toc = true          # 顯示文章目錄
    readingTime = true  # 顯示預估閱讀時間

[taxonomies]
  tag = "tags"
  category = "categories"
```

> **小提示**：`baseURL` 非常重要，要和你實際部署的網址一致，否則圖片和連結會無法正常載入。

---

## 6. 寫第一篇文章

Hugo 的文章使用 **Markdown** 格式撰寫，並透過 `frontmatter`（文章最上方的 `---` 區塊）設定文章的元資料。

### 使用指令建立新文章

```bash
hugo new posts/my-first-post.md
```

這會在 `content/posts/` 底下建立一個新檔案。

### 文章格式說明

開啟剛建立的檔案，內容如下：

```markdown
---
title: "我的第一篇文章"
date: 2026-04-13T10:00:00+08:00
draft: true
description: "這篇文章的摘要，會出現在文章列表和 SEO 描述中。"
categories:
  - "教學"
tags:
  - "Hugo"
  - "部落格"
---

在這裡開始寫你的文章內容。

## 第一個章節

你可以使用 Markdown 語法：

- **粗體文字**
- *斜體文字*
- [超連結](https://example.com)

### 插入程式碼

\```bash
echo "Hello, Hugo!"
\```
```

> **重要**：`draft: true` 代表草稿，不會被發布。改成 `draft: false` 才會出現在網站上。

### 本機預覽

```bash
# 啟動本機預覽伺服器（包含草稿）
hugo server -D

# 瀏覽器開啟 http://localhost:1313 即可預覽
```

每次儲存文章，瀏覽器會自動重新整理，方便即時看到效果。

---

## 7. 用 GitHub Actions 自動部署到 GitHub Pages

這是整個教學最關鍵的部分。設定好之後，每次你把文章 `push` 到 GitHub，網站就會自動更新，完全不需要手動操作。

### 建立 GitHub Actions Workflow 檔案

在專案根目錄建立以下路徑的檔案：

**`.github/workflows/deploy.yml`**

```yaml
name: Deploy Hugo to GitHub Pages

on:
  push:
    branches:
      - main  # 當 push 到 main 分支時觸發

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: "pages"
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          submodules: recursive  # 重要：這樣才能下載主題
          fetch-depth: 0

      - name: Setup Hugo
        uses: peaceiris/actions-hugo@v3
        with:
          hugo-version: 'latest'
          extended: true  # 使用 Hugo Extended 版本

      - name: Build
        run: hugo --minify --baseURL "https://your-username.github.io/your-blog-name/"

      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: ./public

  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    needs: build
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

> **注意**：記得把 `your-username` 和 `your-blog-name` 替換成你自己的 GitHub 帳號名稱和 Repo 名稱。

### 在 GitHub 上開啟 Pages 設定

1. 進入你的 GitHub Repo
2. 點擊 **「Settings」**（上方 Tab）
3. 左側選單找到 **「Pages」**
4. 在 **「Source」** 選擇 **「GitHub Actions」**
5. 儲存設定

### 推送程式碼觸發部署

```bash
# 加入所有檔案到暫存區
git add .

# 提交 commit
git commit -m "feat: 建立 Hugo 部落格並加入第一篇文章"

# 推送到 GitHub
git push origin main
```

推送後，到 GitHub Repo 的 **「Actions」** Tab 可以看到部署進度。約 1-2 分鐘後，你的部落格就會上線！

---

## 8. 自訂域名（可選）

如果你有自己購買的域名，可以把它連結到 GitHub Pages，讓網址從 `your-username.github.io/your-blog-name/` 變成 `blog.yourdomain.com`。

### 步驟一：在 GitHub 設定自訂域名

1. 進入 Repo **「Settings」** → **「Pages」**
2. 在 **「Custom domain」** 欄位輸入你的域名（例如 `blog.yourdomain.com`）
3. 點擊 **「Save」**

GitHub 會在你的 Repo 根目錄自動建立一個 `CNAME` 檔案，內容就是你填入的域名。

### 步驟二：在 DNS 服務商新增紀錄

到你購買域名的服務商（例如 Cloudflare、GoDaddy、Namecheap 等），新增一筆 **CNAME 記錄**：

| 類型 | 名稱 | 內容 |
|------|------|------|
| CNAME | blog | your-username.github.io |

DNS 設定需要幾分鐘到幾小時才會生效。

### 步驟三：更新 hugo.toml 的 baseURL

```toml
# 改成你的自訂域名
baseURL = "https://blog.yourdomain.com/"
```

### 啟用 HTTPS

GitHub Pages 支援免費的 SSL 憑證（由 Let's Encrypt 提供）。在 **「Pages」** 設定頁面，勾選 **「Enforce HTTPS」** 即可。

---

## 總結

恭喜！你已經學會了如何：

1. **了解 Hugo** 靜態網站產生器的優點
2. **建立 GitHub Repo** 作為程式碼和文章的家
3. **安裝 Hugo** 在本機開發環境
4. **加入主題**（透過 Git Submodule 管理）
5. **設定 hugo.toml** 讓網站顯示正確資訊
6. **撰寫文章**（Markdown + frontmatter）
7. **自動部署**（GitHub Actions + GitHub Pages）
8. **綁定自訂域名**（可選）

整個流程設定好之後，日後新增文章只需要：
1. 在 `content/posts/` 新增 `.md` 檔案
2. `git add` → `git commit` → `git push`

GitHub Actions 會自動幫你部署，讓你專注在寫作本身。

---

*有任何問題或建議，歡迎在下方留言討論！*
