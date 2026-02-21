@echo off
setlocal
chcp 65001 > nul

set "SCRIPT_DIR=%~dp0"

:: ── 가상환경 미설치 시 자동 설치 ───────────────────────────────────────────────
if not exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    echo 처음 실행입니다. 설치를 진행합니다...
    call "%SCRIPT_DIR%install.bat"
    if ERRORLEVEL 1 (
        echo 설치 실패. install.bat 를 직접 실행해 주세요.
        pause
        exit /b 1
    )
)

:: ── 앱 실행 ────────────────────────────────────────────────────────────────────
"%SCRIPT_DIR%.venv\Scripts\python.exe" "%SCRIPT_DIR%main.py"

:: 비정상 종료 시 오류 메시지 표시
if ERRORLEVEL 1 (
    echo.
    echo 앱이 오류로 종료됐습니다.
    echo 문제가 지속되면 install.bat 를 다시 실행해 주세요.
    pause
)
