Set objWMI = GetObject("winmgmts:\\.\root\cimv2")
Set colProcesses = objWMI.ExecQuery("SELECT * FROM Win32_Process WHERE Name = 'pythonw.exe' OR Name = 'python.exe'")

isRunning = False
processInfo = ""

For Each objProcess In colProcesses
    ' Kiểm tra nếu process đang chạy file wifi_auto_connect.py
    commandLine = objProcess.CommandLine
    If Not IsNull(commandLine) Then
        If InStr(commandLine, "wifi_auto_connect.py") > 0 Then
            isRunning = True
            processInfo = processInfo & vbCrLf & _
                         "Process ID: " & objProcess.ProcessId & vbCrLf & _
                         "Name: " & objProcess.Name & vbCrLf & _
                         "Command: " & commandLine & vbCrLf & _
                         "Memory: " & FormatNumber(objProcess.WorkingSetSize / 1024 / 1024, 2) & " MB"
        End If
    End If
Next

If isRunning Then
    MsgBox "✅ WiFi Auto-Connect đang chạy!" & vbCrLf & processInfo, vbInformation, "Trạng thái WiFi Script"
Else
    MsgBox "❌ WiFi Auto-Connect KHÔNG chạy!" & vbCrLf & vbCrLf & _
           "Hãy chạy file 'start_wifi_silent.vbs' để khởi động.", vbExclamation, "Trạng thái WiFi Script"
End If
