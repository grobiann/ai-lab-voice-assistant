' Voice Typer 런처 (자동 설치 포함)
' ─────────────────────────────────────────────
' 처음 실행: 필요한 패키지를 자동으로 설치합니다.
' 이후 실행: 콘솔 창 없이 바로 시작됩니다.
' ─────────────────────────────────────────────
Option Explicit

Dim fso, WshShell, scriptDir
Dim pythonPath, mainPath

Set fso      = CreateObject("Scripting.FileSystemObject")
Set WshShell = CreateObject("WScript.Shell")

scriptDir  = fso.GetParentFolderName(WScript.ScriptFullName) & "\"
pythonPath = scriptDir & ".venv\Scripts\pythonw.exe"
mainPath   = scriptDir & "main.py"

' ── 최초 실행: 가상환경이 없으면 설치 ──────────────────────────────────────────
If Not fso.FileExists(pythonPath) Then
    Call FirstTimeSetup()
End If

' 설치 완료 확인
If Not fso.FileExists(pythonPath) Then
    MsgBox "설치에 실패했습니다." & vbCrLf & _
           "문제가 지속되면 run.bat 를 실행하거나 Python 설치 여부를 확인하세요.", _
           16, "Voice Typer 오류"
    WScript.Quit 1
End If

' .env 없으면 example 에서 자동 복사
If Not fso.FileExists(scriptDir & ".env") Then
    If fso.FileExists(scriptDir & ".env.example") Then
        fso.CopyFile scriptDir & ".env.example", scriptDir & ".env"
    End If
End If

' ── 앱 실행 (콘솔 창 없음) ─────────────────────────────────────────────────────
WshShell.Run Chr(34) & pythonPath & Chr(34) & " " & Chr(34) & mainPath & Chr(34), 0, False


' ── 최초 설치 루틴 ─────────────────────────────────────────────────────────────
Sub FirstTimeSetup()
    ' 임시 배치 파일 작성 후 실행 (인코딩 문제 없는 ASCII 커맨드로 구성)
    Dim tmpBat : tmpBat = scriptDir & "_setup_tmp.bat"
    Dim Q      : Q      = Chr(34)   ' 큰따옴표 단축

    Dim f : Set f = fso.CreateTextFile(tmpBat, True)

    f.WriteLine "@echo off"
    f.WriteLine "chcp 65001 > nul"
    f.WriteLine "echo."
    f.WriteLine "echo =================================================="
    f.WriteLine "echo   Voice Typer  [First Run Setup]"
    f.WriteLine "echo =================================================="
    f.WriteLine "echo."

    ' Python 확인
    f.WriteLine "python --version > nul 2>&1"
    f.WriteLine "if ERRORLEVEL 1 ("
    f.WriteLine "    echo [ERROR] Python not found."
    f.WriteLine "    echo."
    f.WriteLine "    echo   Install Python 3.10+ from:"
    f.WriteLine "    echo   https://www.python.org/downloads/"
    f.WriteLine "    echo   (Check 'Add Python to PATH' during install)"
    f.WriteLine "    echo."
    f.WriteLine "    pause"
    f.WriteLine "    exit /b 1"
    f.WriteLine ")"

    ' 가상환경 생성
    f.WriteLine "echo [1/2] Creating virtual environment..."
    f.WriteLine "python -m venv " & Q & scriptDir & ".venv" & Q
    f.WriteLine "if ERRORLEVEL 1 ("
    f.WriteLine "    echo [ERROR] Failed to create venv"
    f.WriteLine "    pause & exit /b 1"
    f.WriteLine ")"

    ' 패키지 설치
    f.WriteLine "echo [2/2] Installing packages... (may take 1-3 min on first run)"
    f.WriteLine Q & scriptDir & ".venv\Scripts\pip" & Q & " install --upgrade pip --quiet"
    f.WriteLine Q & scriptDir & ".venv\Scripts\pip" & Q & _
                " install -r " & Q & scriptDir & "requirements.txt" & Q
    f.WriteLine "if ERRORLEVEL 1 ("
    f.WriteLine "    echo [ERROR] Package installation failed"
    f.WriteLine "    pause & exit /b 1"
    f.WriteLine ")"

    ' 완료
    f.WriteLine "echo."
    f.WriteLine "echo =================================================="
    f.WriteLine "echo   Setup complete! Starting app..."
    f.WriteLine "echo =================================================="
    f.WriteLine "timeout /t 2 > nul"
    f.Close

    ' 설치 실행 (콘솔 표시, 완료까지 대기)
    WshShell.Run Chr(34) & tmpBat & Chr(34), 1, True

    ' 임시 파일 삭제
    On Error Resume Next
    fso.DeleteFile tmpBat
    On Error GoTo 0
End Sub
