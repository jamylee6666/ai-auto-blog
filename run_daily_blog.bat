@echo off
cd /d "C:\Users\jamy.lee\Desktop\ai-project\ai-auto-blog"

set LOG=C:\Users\jamy.lee\Desktop\ai-project\ai-auto-blog\scripts\daily_blog.log

echo. >> "%LOG%"
echo === BAT START %DATE% %TIME% === >> "%LOG%"

C:\Python313\python.exe scripts\daily_post.py >> "%LOG%" 2>&1

echo === Git add/commit/push === >> "%LOG%"
git add content\posts\ scripts\daily_blog.log scripts\keywords_en_used.txt scripts\keywords_zh_used.txt >> "%LOG%" 2>&1

for /f "tokens=1-3 delims=/ " %%a in ("%DATE%") do set TODAY=%%c-%%a-%%b
git commit -m "feat: add %TODAY% daily posts" >> "%LOG%" 2>&1

git push origin main >> "%LOG%" 2>&1
set PUSH_RC=%ERRORLEVEL%
if not "%PUSH_RC%"=="0" (
    echo [ERROR] git push origin main failed with exit code %PUSH_RC% >> "%LOG%"
    echo === BAT END %TIME% [push failed, rc=%PUSH_RC%] === >> "%LOG%"
    exit /b %PUSH_RC%
)

echo === BAT END %TIME% === >> "%LOG%"
