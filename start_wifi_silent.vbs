Set WshShell = CreateObject("WScript.Shell")

' Lấy đường dẫn thư mục hiện tại (nơi file VBS đang chạy)
currentDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)

' Tạo lệnh chạy Python với pythonw.exe (không hiện console)
pythonScript = currentDir & "\wifi_auto_connect.py"

' Chạy script Python ngầm (window style = 0 nghĩa là ẩn hoàn toàn)
WshShell.Run "pythonw.exe """ & pythonScript & """", 0, False

WScript.Quit
