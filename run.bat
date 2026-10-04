@echo off
setlocal
cd /d "%~dp0"

py -3.10 -c "import PyQt5" >nul 2>&1
if errorlevel 1 (
    echo PyQt5 is not installed for Python 3.10.
    echo Installing PyQt5...
    py -3.10 -m pip install PyQt5
    if errorlevel 1 (
        echo PyQt5 installation failed.
        pause
        exit /b 1
    )
)

py -3.10 index.py
if errorlevel 1 pause
endlocal
