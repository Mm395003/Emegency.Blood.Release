V69 - Print Agent compiler fix

The PrintAgent is a standalone C# EXE using TcpListener instead of HttpListener and has no PowerShell/VBS dependency.
1. Run BUILD_PrintAgent.bat (normal double click, no admin).
2. If build succeeds, run PrintAgent.exe or START_PrintAgent.bat.
3. Open http://127.0.0.1:8765/status to verify.
4. For user auto-start, run INSTALL_USER_AUTOSTART.bat (no admin).

If Kaspersky reports a detection, do not allow or exclude the file; contact IT and provide the detection details.
