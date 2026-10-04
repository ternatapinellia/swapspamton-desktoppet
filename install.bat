@echo off
setlocal
cd /d "%~dp0"
py -3.10 -m pip install --upgrade pip
if errorlevel 1 goto :error
py -3.10 -m pip install PyQt5 PyInstaller
if errorlevel 1 goto :error
echo Installation completed.
pause
exit /b 0
:error
echo Installation failed.
pause
exit /b 1
