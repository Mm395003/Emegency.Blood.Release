@echo off
setlocal
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SRC=%~dp0START_PrintAgent.bat"
if not exist "%SRC%" (
  echo START_PrintAgent.bat not found.
  pause
  exit /b 1
)
copy /Y "%SRC%" "%STARTUP%\Emergency_Blood_PrintAgent.bat" >nul
if errorlevel 1 (
  echo Could not install user startup.
  pause
  exit /b 1
)
echo Print Agent startup installed for this Windows user.
echo No Administrator rights required.
pause
