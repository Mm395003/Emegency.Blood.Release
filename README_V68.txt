Emergency Blood Release Protocol V68
Print Agent: standalone Windows EXE (no VBS, no PS1, no ExecutionPolicy changes)

1. Extract this folder.
2. Double-click BUILD_PrintAgent.bat once. This uses the Windows .NET Framework C# compiler and does not require Administrator rights.
3. Double-click INSTALL_USER_AUTOSTART.bat (do NOT Run as administrator).
4. Reboot Windows.
5. Test http://127.0.0.1:8765/status
6. Open index.html and print a Compatibility Tag.

The agent targets the exact Windows printer: ZDesigner GK420t.
If Kaspersky blocks PrintAgent.exe, do not allow/exclude it yourself. Provide the Kaspersky detection message to IT for review.
