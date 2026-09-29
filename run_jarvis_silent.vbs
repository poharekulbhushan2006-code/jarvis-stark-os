' ========================================================
' J.A.R.V.I.S. Silent Background Listener Runner
' Runs background_listener.py completely invisible without any command window.
' ========================================================

Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

strPath = objFSO.GetParentFolderName(WScript.ScriptFullName)
objShell.CurrentDirectory = strPath

strPython = strPath & "\.venv\Scripts\python.exe"

If Not objFSO.FileExists(strPython) Then
    strPython = "python.exe"
End If

strCommand = """" & strPython & """ """ & strPath & "\background_listener.py"""
' 0 = Hide window completely
objShell.Run strCommand, 0, False
