@echo off
title Push SIH26028 Code to GitHub
echo ============================================================
echo   Pushing code to GitHub: Ahmadtech407/sih26028-railway-block-planner
echo ============================================================
echo.
cd /d "%~dp0"
set "PATH=C:\Users\R. Akhil\.git-portable\git\cmd;%PATH%"

git remote set-url origin https://github.com/Ahmadtech407/sih26028-railway-block-planner.git
echo Remote configured:
git remote -v
echo.
echo Pushing branch 'main' to origin...
git push -u origin main
echo.
if %ERRORLEVEL% equ 0 (
    echo ============================================================
    echo   SUCCESS! All code has been pushed to GitHub.
    echo   Visit: https://github.com/Ahmadtech407/sih26028-railway-block-planner
    echo ============================================================
) else (
    echo.
    echo If authentication failed, generate a GitHub Personal Access Token:
    echo 1. Open https://github.com/settings/tokens
    echo 2. Click "Generate new token (classic)", select "repo"
    echo 3. Run: git remote set-url origin https://YOUR_TOKEN@github.com/Ahmadtech407/sih26028-railway-block-planner.git
    echo 4. Run: git push -u origin main
)
echo.
pause
