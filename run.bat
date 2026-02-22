@echo off
setlocal EnableDelayedExpansion
chcp 65001 > nul

set "SCRIPT_DIR=%~dp0"

:: ── 최초 실행: 가상환경이 없으면 자동 설치 ───────────────────────────────────────
if not exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    echo.
    echo ==================================================
    echo   Voice Typer  [First Run Setup]
    echo ==================================================
    echo.

    :: Python 확인
    python --version > nul 2>&1
    if ERRORLEVEL 1 (
        echo [ERROR] Python not found.
        echo.
        echo   Install Python 3.10+ from:
        echo   https://www.python.org/downloads/
        echo   (Check "Add Python to PATH" during install)
        echo.
        pause
        exit /b 1
    )

    :: 가상환경 생성
    echo [1/2] Creating virtual environment...
    python -m venv "%SCRIPT_DIR%.venv"
    if ERRORLEVEL 1 (
        echo [ERROR] Failed to create venv
        pause & exit /b 1
    )

    :: 패키지 설치
    echo [2/2] Installing packages... (may take 1-3 min on first run)
    "%SCRIPT_DIR%.venv\Scripts\pip" install --upgrade pip --quiet
    "%SCRIPT_DIR%.venv\Scripts\pip" install -r "%SCRIPT_DIR%requirements.txt"
    if ERRORLEVEL 1 (
        echo [ERROR] Package installation failed
        pause & exit /b 1
    )

    echo.
    echo ==================================================
    echo   Setup complete! Starting app...
    echo ==================================================
    echo.
)

:: .env 없으면 example 에서 자동 복사
if not exist "%SCRIPT_DIR%.env" (
    if exist "%SCRIPT_DIR%.env.example" (
        copy "%SCRIPT_DIR%.env.example" "%SCRIPT_DIR%.env" > nul
    )
)

:: ── 앱 실행 ────────────────────────────────────────────────────────────────────
"%SCRIPT_DIR%.venv\Scripts\python.exe" "%SCRIPT_DIR%main.py"

:: 비정상 종료 시 오류 메시지 표시
if ERRORLEVEL 1 (
    echo.
    echo 앱이 오류로 종료됐습니다.
    pause
)
