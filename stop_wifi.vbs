Set objWMI = GetObject("winmgmts:\\.\root\cimv2")
Set colProcesses = objWMI.ExecQuery("SELECT * FROM Win32_Process WHERE Name = 'pythonw.exe' OR Name = 'python.exe'")

killedCount = 0
processDetails = ""

For Each objProcess In colProcesses
    ' Kiểm tra nếu process đang chạy file wifi_auto_connect.py
    commandLine = objProcess.CommandLine
    If Not IsNull(commandLine) Then
        If InStr(commandLine, "wifi_auto_connect.py") > 0 Then
            processDetails = processDetails & "PID: " & objProcess.ProcessId & " - " & objProcess.Name & vbCrLf
            objProcess.Terminate()
            killedCount = killedCount + 1
        End If
    End If
Next

If killedCount > 0 Then
    MsgBox "✅ Đã dừng " & killedCount & " process!" & vbCrLf & vbCrLf & processDetails, vbInformation, "Dừng WiFi Script"
Else
    MsgBox "⚠️ Không tìm thấy process nào đang chạy!" & vbCrLf & vbCrLf & _
           "Script có thể đã được dừng từ trước.", vbExclamation, "Dừng WiFi Script"
End If
