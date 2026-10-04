@echo off
setlocal
cd /d "%~dp0"

py -3.10 -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo PyInstaller is not installed. Run install.bat first.
    pause
    exit /b 1
)

for %%F in (
    index.py
    dialogues.py
    SPT_dialogue_pack.py
    SPT-DeskPet.spec
) do (
    if not exist "%%F" (
        echo Missing %%F
        pause
        exit /b 1
    )
)

if not exist "image" (
    echo Missing image folder
    pause
    exit /b 1
)

for %%F in (
    pet1.png
    pet2.png
    pet3.png
    pet4.png
    pet5.png
    pet6.png
    pet7.png
    pet8.png
    pet9.png
    pet10.png
    bubble.png
    panel.png
    panel2.png
    message.ico
) do (
    if not exist "image\%%F" (
        echo Missing image\%%F
        pause
        exit /b 1
    )
)

if not exist "GAMES" (
    echo Missing GAMES folder
    pause
    exit /b 1
)

if not exist "spt_sfx\voice_spam.wav" (
    echo Missing spt_sfx\voice_spam.wav
    pause
    exit /b 1
)

if not exist "spt_sfx\voice_spamlaugh.wav" (
    echo Missing spt_sfx\voice_spamlaugh.wav
    pause
    exit /b 1
)

if not exist "spt_sfx\voice_spamlaugh_long.wav" (
    echo Missing spt_sfx\voice_spamlaugh_long.wav
    pause
    exit /b 1
)

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

py -3.10 -m PyInstaller --clean --noconfirm SPT-DeskPet.spec

if errorlevel 1 (
    echo PyInstaller build failed.
    pause
    exit /b 1
)

if exist note.txt (
    copy /Y note.txt dist\note.txt >nul
)

if exist spam_volume.json (
    copy /Y spam_volume.json dist\spam_volume.json >nul
)

if exist spt_sfx (
    xcopy /E /I /Y spt_sfx dist\spt_sfx >nul
)

if exist GAMES (
    xcopy /E /I /Y GAMES dist\GAMES >nul
)

if exist image (
    xcopy /E /I /Y image dist\image >nul
)

if exist dist\SPT-DeskPet.exe (
    echo.
    echo Build complete:
    echo dist\SPT-DeskPet.exe
    echo.
    echo External image folder:
    echo dist\image
    echo.
) else (
    echo EXE was not created.
    pause
    exit /b 1
)

pause
endlocal