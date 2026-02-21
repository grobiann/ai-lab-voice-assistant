@echo off
setlocal EnableDelayedExpansion
chcp 65001 > nul

echo.
echo ==================================================
echo   Voice Typer 설치
echo ==================================================

:: ── Python 확인 ────────────────────────────────────────────────────────────────
echo.
echo [1/4] Python 버전 확인 중...
set PYTHON_CMD=

for %%P in (python python3) do (
    %%P --version > nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        for /f "tokens=2" %%V in ('%%P --version 2^>^&1') do (
            set PYVER=%%V
        )
        set PYTHON_CMD=%%P
        goto :found_python
    )
)

echo   [오류] Python 이 설치되어 있지 않습니다.
echo   설치 주소: https://www.python.org/downloads/
echo   설치 시 "Add Python to PATH" 옵션을 반드시 체크하세요.
pause
exit /b 1

:found_python
echo   [OK] Python !PYVER! 발견

:: ── 가상환경 ────────────────────────────────────────────────────────────────────
echo.
echo [2/4] 가상환경 설정 중...
if not exist ".venv\" (
    %PYTHON_CMD% -m venv .venv
    echo   [OK] 가상환경 생성됨
) else (
    echo   [OK] 기존 가상환경 재사용
)

:: ── 패키지 설치 ─────────────────────────────────────────────────────────────────
echo.
echo [3/4] 패키지 설치 중 (처음 실행 시 수 분이 걸릴 수 있습니다)...
.venv\Scripts\pip install --upgrade pip --quiet
.venv\Scripts\pip install -r requirements.txt
if !ERRORLEVEL! NEQ 0 (
    echo   [오류] 패키지 설치 실패
    pause
    exit /b 1
)
echo   [OK] 패키지 설치 완료

:: ── .env 파일 ──────────────────────────────────────────────────────────────────
echo.
echo [4/4] 환경 파일 설정 중...
if not exist ".env" (
    copy ".env.example" ".env" > nul
    echo   [OK] .env 파일 생성됨
    echo   [!] tier3 / cloud 모드 사용 시 .env 파일에 API 키를 입력하세요
) else (
    echo   [OK] .env 파일 유지 (기존 설정 보존)
)

:: ── 완료 ───────────────────────────────────────────────────────────────────────
echo.
echo ==================================================
echo   설치 완료!
echo.
echo   실행: run.bat 더블클릭
echo.
echo   STT 단계 변경: config.py 의 STT_MODE 수정
echo     tier1 (빠름) / tier2 (균형, 기본) / tier3 (최고정밀)
echo ==================================================
echo.
pause
