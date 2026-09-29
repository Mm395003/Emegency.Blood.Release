@echo off
setlocal
set "CSC=%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if not exist "%CSC%" set "CSC=%WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc.exe"
if not exist "%CSC%" (
  echo .NET Framework 4.x C# compiler was not found on this PC.
  echo Please ask IT to install/enable .NET Framework 4.x.
  pause
  exit /b 1
)
echo Building PrintAgent.exe...
"%CSC%" /nologo /target:exe /platform:anycpu /out:"%~dp0PrintAgent.exe" /reference:System.dll "%~dp0PrintAgent.cs"
if errorlevel 1 (
  echo Build failed.
  pause
  exit /b 1
)
echo Build completed successfully: PrintAgent.exe
echo.
echo Run PrintAgent.exe to test the agent.
pause
