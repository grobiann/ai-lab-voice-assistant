' run.vbs — 콘솔 창 없이 Voice Typer 실행
' 더블클릭하면 까만 창 없이 오버레이만 표시됩니다.
' (콘솔 출력이 필요하면 run.bat 을 사용하세요)

Dim fso, scriptDir, pythonPath, mainPath, cmd
Dim WshShell

Set fso      = CreateObject("Scripting.FileSystemObject")
Set WshShell = CreateObject("WScript.Shell")

scriptDir  = fso.GetParentFolderName(WScript.ScriptFullName) & "\"
pythonPath = scriptDir & ".venv\Scripts\pythonw.exe"
mainPath   = scriptDir & "main.py"

' 가상환경이 없으면 install.bat 먼저 실행 (설치 중에는 콘솔 표시)
If Not fso.FileExists(pythonPath) Then
    WshShell.Run Chr(34) & scriptDir & "install.bat" & Chr(34), 1, True
End If

' 설치 후에도 pythonw.exe 가 없으면 오류 메시지
If Not fso.FileExists(pythonPath) Then
    MsgBox "설치 실패." & vbCrLf & "install.bat 를 직접 실행해 주세요.", 16, "Voice Typer 오류"
    WScript.Quit 1
End If

' pythonw.exe 로 실행 — windowStyle=0(숨김), waitOnReturn=False(비동기)
cmd = Chr(34) & pythonPath & Chr(34) & " " & Chr(34) & mainPath & Chr(34)
WshShell.Run cmd, 0, False
